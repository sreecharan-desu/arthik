# Concierge Backend API Documentation

## Auth Endpoints

### Login (Standard)

```bash
curl -X POST "http://localhost:8000/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin-password"
```

### Google OAuth Login

`GET /auth/google/login` -> Returns redirect URL.

---

## Chat Orchestrator

### POST /chat

Input: `{ "user_id": 1, "message": "I need a cheap pool hotel in Hyderabad", "language": "en" }`

```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"user_id":1, "message":"I need a cheap pool hotel in Hyderabad", "language":"en"}'
```

Response:

```json
{
  "intent": "search",
  "slot_data": { "location": "Hyderabad", "budget_max": 5000 },
  "candidates": [
    {
      "service": {
        "id": 12,
        "name": "Luxury Safari",
        "price": 2500,
        "rating": 4.5,
        "location": "Hyderabad"
      },
      "score": 0.85
    }
  ]
}
```

---

## Hotels Search

### GET /hotels/search

```bash
curl -X GET "http://localhost:8000/hotels/search?location=Hyderabad&budget_max=5000&facilities=pool,wifi"
```

---

## Bookings

### POST /booking

```bash
curl -X POST "http://localhost:8000/booking" \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1, "service_id": 5, "booking_datetime": "2026-04-12T10:00:00", "special_requests": "Late arrival"}'
```

Response: Contains PayU payload (hash, keys).

---

## Payments

### POST /payment/webhook

Simulate a successful payment:

```bash
curl -X POST "http://localhost:8000/payment/webhook" \
     -d "txnid=TXN_123&status=success&hash=VALID_HASH&key=MERCHANT_KEY&amount=1000.00&email=user@example.com"
```

---

## Vendor Portal

### POST /vendor/update

```bash
curl -X POST "http://localhost:8000/vendor/update" \
     -H "Content-Type: application/json" \
     -d '{"service_id": 5, "price": 1200.0, "is_available": true}'
```

Triggers a WebSocket broadcast on `ws://localhost:8000/vendor/ws/updates`.
