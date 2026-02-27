from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from app.models.models import Users
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated, Optional
from starlette import status
from pydantic import BaseModel, Field
from .auth import get_current_user
from app.services.bot import generate_chat_responses

router = APIRouter(
    prefix="/agent",
    tags=["agent"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


@router.post("/chat", status_code=status.HTTP_200_OK)
async def chat_endpoint(
    request: ChatRequest,
    user: user_dependency, 
    db: db_dependency
):
    
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
        
    
    user_record = db.query(Users).filter(Users.id == user.get('id')).first()
    
    if not user_record:
         raise HTTPException(status_code=404, detail='User not found')

   
    user_data = {
        "first_name": user_record.first_name,
        "last_name": user_record.last_name,
        "preferred_language": user_record.preferred_language,
        "room_number": user_record.room_number
    }

    
    return StreamingResponse(
        generate_chat_responses(
            message=request.message, 
            user_data=user_data, 
            checkpoint_id=str(user.get('id'))
        ),
        media_type="text/event-stream"
    )