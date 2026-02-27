from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Service, LocalProvider
from utils.ranking import calculate_ranking_score
from typing import List, Optional
from internal_auth import verify_internal_key
import hashlib
from utils.cache import get_cache, set_cache

router = APIRouter(prefix="/hotels", tags=["hotels"])

def perform_hotel_search(
    db: Session,
    location: Optional[str] = None,
    budget_min: float = 0.0,
    budget_max: float = 1000000.0,
    rating_min: float = 0.0,
    facilities: Optional[str] = None,
):
    # Construct a cache key
    raw_key = f"{location}_{budget_min}_{budget_max}_{rating_min}_{facilities}"
    cache_key = "hotel_search:" + hashlib.md5(raw_key.encode()).hexdigest()
    
    # Try fetching from cache
    cached_data = get_cache(cache_key)
    if cached_data:
        return cached_data

    query = db.query(Service).join(LocalProvider)
    
    if location:
        query = query.filter(Service.location.ilike(f"%{location}%"))
    
    query = query.filter(Service.price >= budget_min)
    query = query.filter(Service.price <= budget_max)
    query = query.filter(Service.rating >= rating_min)
    query = query.filter(Service.is_available == True)
    
    results = query.all()
    
    if not results:
        set_cache(cache_key, [], ttl_minutes=15)
        return []
    
    requested_facilities = facilities.split(",") if facilities else []
    criteria = {
        "location": location or "",
        "facilities": requested_facilities
    }
    
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
    
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    final_results = scored_results[:20]
    
    # Store results in cache
    set_cache(cache_key, final_results, ttl_minutes=15)
    
    return final_results


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
    return perform_hotel_search(
        db=db,
        location=location,
        budget_min=budget_min,
        budget_max=budget_max,
        rating_min=rating_min,
        facilities=facilities
    )
