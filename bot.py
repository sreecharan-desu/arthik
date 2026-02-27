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

# Load environment variables
load_dotenv(override=True)
baseten_api_key = os.getenv("BASETEN_API_KEY")

# Initialize LLMs
summarizer = ChatOpenAI(base_url="https://inference.baseten.co/v1", model="openai/gpt-oss-120b", api_key=baseten_api_key)
llm = ChatOpenAI(base_url="https://inference.baseten.co/v1", model="moonshotai/Kimi-K2-Instruct-0905", api_key=baseten_api_key)



@tool
async def fetch_website_content(url: str, query: str = "") -> str:
    """Fetches content from a website."""
    # Placeholder for your actual implementation
    return f"Simulated content from {url} for query {query}"

tools = [fetch_website_content]
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

        if tool_name == "fetch_website_content":
            tool_result = await fetch_website_content.ainvoke(tool_args)
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

    # Open an async connection specifically for LangGraph's memory
    async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
        
        
        await checkpointer.setup() 
        
        # Compile the graph dynamically using the Postgres memory
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

            if event_type == "on_chat_model_stream" and node_name == "chatbot":
                chunk_content = serialise_ai_message_chunk(event["data"]["chunk"])
                safe_content = chunk_content.replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
                yield f"data: {{\"type\": \"content\", \"content\": \"{safe_content}\"}}\n\n"
            
            elif event_type == "on_chat_model_end" and node_name == "chatbot":
                tool_calls = event["data"]["output"].tool_calls if hasattr(event["data"]["output"], "tool_calls") else []
                search_calls = [call for call in tool_calls if call["name"] == "fetch_website_content"]

                if search_calls:
                    search_query = search_calls[0]["args"].get("query", "")
                    safe_query = search_query.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                    yield f"data: {{\"type\": \"search_start\", \"query\": \"{safe_query}\"}}\n\n"
            
            elif event_type == "on_tool_end" and event["name"] == "fetch_website_content":
                urls = event["data"]["input"].get("url", "Nothing")
                urls_json = json.dumps(urls)
                yield f"data: {{\"type\": \"search_results\", \"urls\": {urls_json}}}\n\n"
        
        yield f"data: {{\"type\": \"end\"}}\n\n"