from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import openai
import os
import json
from .hotels import search_hotels
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(BaseModel):
    user_id: int
    message: str
    language: str = "en"

SYSTEM_PROMPT = """
You are a concierge assistant. Extract intent and slot data from the user message.
Intents: search, book, clarify
Respond ONLY with a JSON object:
{
  "intent": "search|book|clarify",
  "slot_data": {
    "location": "string",
    "budget_max": number,
    "facilities": ["pool", "wifi", ...],
    "checkin": "ISO date",
    "checkout": "ISO date",
    "service_id": number,
    "booking_datetime": "ISO date"
  }
}
"""

@router.post("")
async def chat_interaction(chat_msg: ChatMessage, db: Session = Depends(get_db)):
    # Language detection / Intent extraction via LLM
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    
    intent_data = {
        "intent": "clarify",
        "slot_data": {}
    }

    if api_key and not api_key.startswith("sk-placeholder"):
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": chat_msg.message}
                ],
                response_format={"type": "json_object"}
            )
            intent_data = json.loads(response.choices[0].message.content)
        except Exception as e:
            # Fallback or error
            print(f"LLM Error: {e}")
    else:
        # Simple fallback parser for demo
        msg = chat_msg.message.lower()
        if "hyderabad" in msg:
            intent_data = {
                "intent": "search",
                "slot_data": {"location": "Hyderabad", "budget_max": 5000}
            }
        elif "book" in msg:
            intent_data = {
                "intent": "book",
                "slot_data": {"service_id": 1, "booking_datetime": "2026-04-12T10:00:00"}
            }

    # Execute intent
    if intent_data["intent"] == "search":
        slots = intent_data["slot_data"]
        candidates = search_hotels(
            location=slots.get("location"),
            budget_max=slots.get("budget_max", 1000000.0),
            facilities=",".join(slots.get("facilities", [])),
            db=db
        )
        return {
            "intent": "search",
            "slot_data": slots,
            "candidates": candidates
        }
    
    return intent_data
