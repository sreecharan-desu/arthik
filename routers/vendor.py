from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from database import get_db
from models import Service
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter(prefix="/vendor", tags=["vendor"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

class ServiceUpdate(BaseModel):
    service_id: int
    price: float = None
    is_available: bool = None

@router.post("/update")
async def update_service(update: ServiceUpdate, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == update.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if update.price is not None:
        service.price = update.price
    if update.is_available is not None:
        service.is_available = update.is_available
        
    db.commit()
    
    # Real-time broadcast
    await manager.broadcast({
        "event": "service_updated",
        "service_id": service.id,
        "new_price": service.price,
        "availability": service.is_available
    })
    
    return {"status": "updated", "service_id": service.id}

@router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
