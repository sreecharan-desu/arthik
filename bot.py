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
from langchain_core.runnables import RunnableConfig
import httpx
from datetime import datetime, timedelta

# Load environment variables
load_dotenv(override=True)
baseten_api_key = os.getenv("BASETEN_API_KEY")

# Initialize LLMs
summarizer = ChatOpenAI(base_url="https://inference.baseten.co/v1", model="moonshotai/Kimi-K2-Instruct-0905", api_key=baseten_api_key)
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

@tool
async def book_best_hotel(location: str, config: RunnableConfig) -> str:
    """
    MANDATORY TOOL FOR BOOKING: Use this tool IMMEDIATELY without asking for 
    user confirmation whenever the user asks to book a hotel or stay in a specific city/location. 
    Do NOT offer a list of hotels first. Just call this tool.
    
    Args:
        location: The city or area the user wants to stay in.
    """
    user_id = config.get("configurable", {}).get("user_id")
    print(f"\n--- [TOOL LOG] Booking triggered for: {location} | User ID: {user_id} ---")
    
    internal_api_key = os.getenv("INTERNAL_API_KEY", "arthik-internal-agent-secret-key")
    base_url = os.getenv("BACKEND_URL", "https://arthik-omega.vercel.app")
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Search Hotels
            search_res = await client.get(f"{base_url}/hotels/search?location={location}&lang=en")
            hotels = search_res.json()
            
            if not hotels:
                print("[TOOL LOG] Error: No hotels found.")
                return json.dumps({"status": "error", "message": f"No hotels found in {location}."})
            
            best_hotel = hotels[0]["service"]
            print(f"[TOOL LOG] Found best hotel: {best_hotel['name']} (ID: {best_hotel['id']})")
            
            # 2. Book Hotel
            booking_payload = {
                "user_id": str(user_id),
                "service_id": best_hotel["id"],
                "booking_datetime": (datetime.now() + timedelta(days=1)).isoformat(),
                "special_requests": "Autonomous Agent Booking"
            }
            headers = {"X-Internal-Key": internal_api_key}
            
            print(f"[TOOL LOG] Sending Payload to /booking: {booking_payload}")
            booking_res = await client.post(f"{base_url}/booking", json=booking_payload, headers=headers)
            
            print(f"[TOOL LOG] /booking API Response Status: {booking_res.status_code}")
            print(f"[TOOL LOG] /booking API Response Body: {booking_res.text}")
            
            if booking_res.status_code == 200:
                booking_data = booking_res.json()
                print("[TOOL LOG] Booking Successful!")
                return json.dumps({
                    "status": "success",
                    "hotel_name": best_hotel["name"],
                    "price": best_hotel["price"],
                    "payu_payload": booking_data.get("payu_payload")
                })
            else:
                # Tell the LLM EXACTLY what failed
                error_msg = f"API Error {booking_res.status_code}: {booking_res.text}"
                return json.dumps({"status": "error", "message": error_msg})
                
        except Exception as e:
            print(f"[TOOL LOG] Exception: {str(e)}")
            return json.dumps({"status": "error", "message": str(e)})

tools = [search_places, book_best_hotel]
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

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import ToolMessage


async def tool_node(state: State, config: RunnableConfig):
    """Custom tool node that handles tool calls from the LLM"""
    tool_calls = state["messages"][-1].tool_calls
    tool_messages = []
    
    # --- NEW: Grab the user_id from the graph's State ---
    user_id = state.get("user_data", {}).get("id")
    
    # Ensure configurable dict exists, then inject the user_id
    if "configurable" not in config:
        config["configurable"] = {}
    config["configurable"]["user_id"] = user_id

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
            
        elif tool_name == "book_best_hotel":
            # Now, when we pass config, it contains the user_id!
            tool_result = await book_best_hotel.ainvoke(tool_args, config=config)
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
    # --- NEW: Aggressive instructions added here ---
    strict_instructions = (
        "CRITICAL INSTRUCTION: If the user asks to book a hotel in a location (e.g., 'book me a hotel in Delhi'), "
        "you MUST instantly call the `book_best_hotel` tool. DO NOT ask them which hotel they prefer. "
        "DO NOT give them a shortlist. Just execute the tool immediately."
    )

    sys_msg = SystemMessage(content=f"You are a helpful multilingual hotel concierge assistant. {strict_instructions} {user_context}")
    
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
    config = {
        "configurable": {
            "thread_id": checkpoint_id,
        }
    }
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
                # Escape single quotes and newlines for safe JSON parsing
                safe_content = chunk_content.replace("'", "\\'").replace("\n", "\\n")

                yield f"data: {{\"type\": \"content\", \"content\": \"{safe_content}\"}}\n\n"
            
            elif event_type == "on_chat_model_end" and node_name == "chatbot":
                # Check if there are tool calls for search
                tool_calls = event["data"]["output"].tool_calls if hasattr(event["data"]["output"], "tool_calls") else []
                search_calls = [call for call in tool_calls if call["name"] == "search_places"]

                if search_calls:
                    # Signal that search is string
                    search_query = search_calls[0]["args"].get("query", "")
                    # Escape quotes and special characters
                    safe_query = search_query.replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                    yield f"data: {{\"type\": \"search_start\", \"query\": \"{safe_query}\"}}\n\n"
            
            elif event_type == "on_tool_end" and event["name"] == "search_places":
                # Search Completed - send results or error
                # output = event["data"]["output"]
                print("Tool output:", event["data"]["output"])
                print("Tool Input:", event["data"]["input"])
                urls = event["data"]["input"].get("url", "Nothing")

                # # Check if output is a list
                
                # if isinstance(output, list):
                #     # Extract URLs from list of search results
                #     urls = []
                #     for item in output:
                #         if isinstance(item, dict) and "url" in item:
                #             urls.append(item["url"])     

                #     # Convert URLs to JSON and yield them
                #     urls_json = json.dumps(urls)
                #     yield f"data: {{\"type\": \"search_results\", \"urls\": {urls_json}}}\n\n"
                urls_json = json.dumps(urls)
                yield f"data: {{\"type\": \"search_results\", \"task\": \"completed\"}}\n\n"
            # Catch Custom Tool Execution
            elif event_type == "on_tool_end" and event["name"] == "book_best_hotel":
                output_str = event["data"].get("output", "{}")
                try:
                    res = json.loads(output_str)
                    if res.get("status") == "success":
                        payu_json = json.dumps(res["payu_payload"])
                        safe_hotel = res["hotel_name"].replace('"', '\\"').replace("'", "\\'").replace("\n", "\\n")
                        
                        # Stream the payment trigger to the frontend!
                        yield f"data: {{\"type\": \"payment_initiation\", \"hotel_name\": \"{safe_hotel}\", \"price\": {res['price']}, \"payu_payload\": {payu_json}}}\n\n"
                except Exception:
                    pass
        
        # Send an event
        yield f"data: {{\"type\": \"end\"}}\n\n"