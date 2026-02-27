from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Service, LocalProvider
from utils.ranking import calculate_ranking_score
from typing import List, Optional

router = APIRouter(prefix="/hotels", tags=["hotels"])

@router.get("/search")
def search_hotels(
    location: Optional[str] = None,
    budget_min: float = 0.0,
    budget_max: float = 1000000.0,
    rating_min: float = 0.0,
    facilities: Optional[str] = None,
    checkin: Optional[str] = None,
    checkout: Optional[str] = None,
    lang: str = "en",
    db: Session = Depends(get_db)
):
    query = db.query(Service).join(LocalProvider)
    
    if location:
        query = query.filter(Service.location.ilike(f"%{location}%"))
    
    query = query.filter(Service.price >= budget_min)
    query = query.filter(Service.price <= budget_max)
    query = query.filter(Service.rating >= rating_min)
    query = query.filter(Service.is_available == True)
    
    results = query.all()
    
    # Calculate scores and rank
    requested_facilities = facilities.split(",") if facilities else []
    criteria = {
        "location": location or "",
        "facilities": requested_facilities
    }
    
    if not results:
        return []
    
    prices = [r.price for r in results]
    p_min = min(prices)
    p_max = max(prices)
    
    scored_results = []
    for service in results:
        score = calculate_ranking_score(service, criteria, p_min, p_max)
        scored_results.append({
            "service": {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "price": service.price,
                "rating": service.rating,
                "type": service.type,
                "tags": service.tags,
                "location": service.location,
                "provider": service.provider.name if service.provider else None
            },
            "score": score
        })
    
    # Sort by score descending
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    
    return scored_results[:20]
