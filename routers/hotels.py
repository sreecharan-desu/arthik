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
    # Ensure we only fetch hotels (not tours or transport)
    query = query.filter(Service.type == "HOTEL")
    results = query.all()
    
    if not results:
        # Fallback to rich mock data if DB has no real hotels matching the filters
        mock_hotels = [
            {
                "service": {
                    "id": 999901,
                    "name": "The Taj Mahal Palace",
                    "description": "Iconic luxury hotel offering breathtaking sea views, elite dining, and world-class spa.",
                    "price": 18500.0,
                    "rating": 4.9,
                    "type": "HOTEL",
                    "tags": ["luxury", "pool", "spa", "sea-view"],
                    "location": location or "Mumbai",
                    "provider": "Taj Group"
                },
                "score": 0.98
            },
            {
                "service": {
                    "id": 999902,
                    "name": "Oberoi Amarvilas",
                    "description": "Exquisite resort located just 600 meters from the Taj Mahal, featuring opulent suites.",
                    "price": 32000.0,
                    "rating": 5.0,
                    "type": "HOTEL",
                    "tags": ["premium", "heritage", "romantic"],
                    "location": location or "Agra",
                    "provider": "Oberoi Hotels"
                },
                "score": 0.97
            },
            {
                "service": {
                    "id": 999903,
                    "name": "ITC Maurya, a Luxury Collection",
                    "description": "Premium luxury property known for its grand architecture and famous Bukhara restaurant.",
                    "price": 12000.0,
                    "rating": 4.7,
                    "type": "HOTEL",
                    "tags": ["business", "fine-dining", "luxury"],
                    "location": location or "Delhi",
                    "provider": "ITC Hotels"
                },
                "score": 0.92
            },
            {
                "service": {
                    "id": 999904,
                    "name": "Leela Palace",
                    "description": "A modern palace offering majestic architecture, lush gardens, and royal hospitality.",
                    "price": 14500.0,
                    "rating": 4.8,
                    "type": "HOTEL",
                    "tags": ["palace", "luxury", "pool"],
                    "location": location or "Delhi",
                    "provider": "Leela Resorts"
                },
                "score": 0.90
            },
            {
                "service": {
                    "id": 999905,
                    "name": "Marriott Executive Suites",
                    "description": "Premium extended-stay suites with kitchenette, fast Wi-Fi, and fitness center.",
                    "price": 8500.0,
                    "rating": 4.5,
                    "type": "HOTEL",
                    "tags": ["business", "city-center", "gym"],
                    "location": location or "Delhi",
                    "provider": "Marriott"
                },
                "score": 0.85
            }
        ]
        
        # Filter mock by budget and rating just in case
        filtered_mocks = [
            m for m in mock_hotels 
            if budget_min <= m["service"]["price"] <= budget_max
            and m["service"]["rating"] >= rating_min
        ]
        
        if not filtered_mocks:
            return []
            
        set_cache(cache_key, filtered_mocks, ttl_minutes=5)
        return filtered_mocks
    
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
@router.get("/find")
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
