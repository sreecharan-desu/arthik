import os
import json
from uuid import uuid4
from typing import List, Annotated, TypedDict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from langchain_community.utilities import GoogleSerperAPIWrapper

# Load environment variables
load_dotenv(override=True)
baseten_api_key = os.getenv("BASETEN_API_KEY")

# Initialize LLMs
summarizer = ChatOpenAI(base_url="https://inference.baseten.co/v1", model="openai/gpt-oss-120b", api_key=baseten_api_key)
llm = ChatOpenAI(base_url="https://inference.baseten.co/v1", model="moonshotai/Kimi-K2-Instruct-0905", api_key=baseten_api_key)


serper = GoogleSerperAPIWrapper()

@tool
def search_places(query: str) -> str:
    """
    Use this tool to search Google for real-time information about places, 
    local attractions, restaurants, weather, or general knowledge that is 
    not in the internal database. 
    
    Args:
        query: A highly specific search query (e.g., "Best Italian restaurants near Eiffel Tower", "Weather in Tokyo today").
    """
    try:
        results = serper.run(query)
        return str(results)
    except Exception as e:
        return f"Error performing Google search: {str(e)}"

tools = [search_places]
llm_with_tools = llm.bind_tools(tools)


# --- STATE DEFINITION ---
class State(TypedDict):
    messages: Annotated[List, add_messages]
    summary: str
    summarized_until: int
    window_size: int
    user_data: dict


# --- GRAPH NODES ---
async def tools_router(state: State):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tool_node"
    return END

async def tool_node(state: State):
    """Custom tool node that handles tool calls from the LLM"""
    tool_calls = state["messages"][-1].tool_calls
    tool_messages = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        if tool_name == "search_places":
            tool_result = search_places.invoke(tool_args)
            tool_message = ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_messages.append(tool_message)
            
    return {"messages": tool_messages}

async def chatbot(state: State):
    # 1. Extract the user context injected from FastAPI
    user_data = state.get("user_data", {})
    
    # 2. Build the personalized system prompt
    user_context = ""
    if user_data:
        user_context = (
            f"\n\n--- User Context ---\n"
            f"Name: {user_data.get('first_name', 'Guest')} {user_data.get('last_name', '')}\n"
            f"Preferred Language: {user_data.get('preferred_language', 'en')}\n"
            f"Room Number: {user_data.get('room_number', 'Not assigned')}\n"
            f"--------------------\n"
            f"IMPORTANT: You MUST communicate with the user in their Preferred Language. "
            f"Address them by their name."
        )

    sys_msg = SystemMessage(content=f"You are a helpful multilingual hotel concierge assistant. You have access to tools. Use them when necessary.{user_context}")
    
    messages_to_pass = [sys_msg]
    
    if state.get("summary"):
        summary_msg = AIMessage(content=f"Here is a summary of our earlier conversation: {state['summary']}")
        messages_to_pass.append(summary_msg)
        
    summarized_until = state.get("summarized_until", 0)
    messages_to_pass += state["messages"][summarized_until:]

    print(f"Passing {len(messages_to_pass)} messages to the LLM.")
    response = await llm_with_tools.ainvoke(messages_to_pass)

    return {"messages": [response]}


def summarize(state: State):
    summary = state.get("summary", "")
    summarized_until = state.get("summarized_until", 0)
    # Give defaults in case they aren't initialized yet
    window_size = state.get("window_size", 6)
    messages = state.get("messages", [])

    while len(messages) - summarized_until >= window_size:
        cut_idx = summarized_until + window_size
        
        if cut_idx < len(messages) and getattr(messages[cut_idx], "type", "") == "tool":
            cut_idx -= 1
            
        new_chunk = messages[summarized_until:cut_idx]

        summary_prompt = [
            {"role": "system", "content": "Update the existing summary with the new conversation chunk. Keep it concise but preserve important facts."},
            {"role": "system", "content": f"Existing summary:\n{summary}"}
        ] + new_chunk
        
        summary_response = summarizer.invoke(summary_prompt)
        summary = summary_response.content
        summarized_until = cut_idx
    
    # Ensure defaults are set on first pass
    return {
        "summary": summary.strip(), 
        "summarized_until": summarized_until,
        "window_size": window_size
    }



graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tool_node", tool_node)
graph_builder.add_node("summarize", summarize)

graph_builder.set_entry_point("summarize")
graph_builder.add_edge("summarize", "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_router, {"tool_node": "tool_node", END: END})
graph_builder.add_edge("tool_node", "chatbot")





def serialise_ai_message_chunk(chunk):
    if isinstance(chunk, AIMessage):
        return chunk.content
    else:
        raise TypeError(f"Object of type {type(chunk).__name__} is not correctly formatted for serialisation")
    


# We need the raw URL without the "+pg8000" dialect for psycopg
DB_URI = os.getenv("DATABASE_URL")
if DB_URI and DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)
if DB_URI and "+pg8000" in DB_URI:
    DB_URI = DB_URI.replace("+pg8000", "")
    
# Neon/Serverless Postgres requires SSL enabled
if DB_URI and "?" not in DB_URI:
    DB_URI += "?sslmode=require"


async def generate_chat_responses(message: str, user_data: dict, checkpoint_id: str):
    """
    Main entry point for the FastAPI route to interact with the bot.
    """
    config = {"configurable": {"thread_id": checkpoint_id}}
    state_input = {
        "messages": [HumanMessage(content=message)],
        "user_data": user_data 
    }

    try:
        # Open an async connection specifically for LangGraph's memory
        async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
            await checkpointer.setup() 
            graph = graph_builder.compile(checkpointer=checkpointer)

            # Stream the events normally
            events = graph.astream_events(
                state_input,
                version="v2",
                config=config
            )
            
            async for event in events:
                event_type = event["event"]
                node_name = event.get("metadata", {}).get("langgraph_node")

                # 1. Handle streaming the actual text response back to the user
                if event_type == "on_chat_model_stream" and node_name == "chatbot":
                    chunk = event["data"]["chunk"]
                    # More robust serialization
                    if hasattr(chunk, "content"):
                        chunk_content = chunk.content
                    elif isinstance(chunk, dict) and "content" in chunk:
                        chunk_content = chunk["content"]
                    else:
                        chunk_content = ""
                    
                    if chunk_content:
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk_content})}\n\n"
                
                # 2. Detect when the LLM decides to call a tool
                elif event_type == "on_chat_model_end" and node_name == "chatbot":
                    output = event["data"]["output"]
                    tool_calls = getattr(output, "tool_calls", [])
                    
                    # Check if it called the Google Search tool
                    google_calls = [call for call in tool_calls if call["name"] == "search_places"]
                    if google_calls:
                        google_query = google_calls[0]["args"].get("query", "")
                        yield f"data: {json.dumps({'type': 'google_search_start', 'query': google_query})}\n\n"
                
                # 3. Detect when a tool finishes executing
                elif event_type == "on_tool_end":
                    # If Google Search finished
                    if event["name"] == "search_places":
                        query_searched = event["data"]["input"].get("query", "Unknown query")
                        yield f"data: {json.dumps({'type': 'google_search_results', 'query': query_searched})}\n\n"
            
            # 4. End of the complete stream
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

    except Exception as e:
        error_msg = f"Internal Error: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        yield f"data: {json.dumps({'type': 'end'})}\n\n"