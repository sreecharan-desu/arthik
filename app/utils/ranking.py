def calculate_ranking_score(service, criteria, price_min, price_max):
    # Weights
    W_PRICE = 0.35
    W_RATING = 0.30
    W_FACILITY = 0.25
    W_LOCATION = 0.10

    # Price Score
    if price_max == price_min:
        price_score = 1.0
    else:
        # Clamped normalization
        price_val = max(price_min, min(price_max, service.price))
        price_score = 1.0 - (price_val - price_min) / (price_max - price_min)
    
    # Rating Score
    rating_score = (service.rating or 0) / 5.0
    
    # Facility Score
    requested_facilities = criteria.get('facilities', [])
    if not requested_facilities:
        facility_score = 1.0
    else:
        service_tags = service.tags or []
        matched = len(set(requested_facilities) & set(service_tags))
        facility_score = matched / len(requested_facilities)
    
    # Location Score
    requested_location = criteria.get('location', '').lower()
    service_location = service.location.lower() if service.location else ''
    
    if requested_location in service_location:
        location_score = 1.0
    elif requested_location in (service.provider.city.lower() if service.provider else ''):
        location_score = 0.8
    else:
        location_score = 0.5
        
    final_score = (
        W_PRICE * price_score +
        W_RATING * rating_score +
        W_FACILITY * facility_score +
        W_LOCATION * location_score
    )
    
    return round(final_score, 4)
