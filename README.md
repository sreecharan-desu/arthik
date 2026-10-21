---
title: Arthik Concierge
emoji:
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---

# arthik

ai concierge backend for hotel search, ranking and payments.

## features

- concierge agent: stateful langgraph agent that reasons over search and booking actions (`routers/agent.py`)
- hotel search with weighted ranking on price, rating and local facilities
- bookings and payu payments with hash verification and webhook handling
- google sign-in, users and pdf invoices
- api reference: [API.md](API.md)

## stack

fastapi · python 3.12 · langchain / langgraph · postgres (neon) + alembic · redis · docker · vercel / hugging face spaces

## run locally

```bash
uv sync                      # or: pip install -r requirements.txt
cp .env.example .env         # fill in the values
make migrate                 # alembic upgrade head
make start                   # uvicorn on :8000
make test                    # pytest tests/
```

## env

copy `.env.example` to `.env`. it lists `DATABASE_URL`, `SECRET_KEY`, the payu keys and urls, the google oauth client, `BASETEN_API_KEY`, `INTERNAL_API_KEY` and `REDIS_URL`.

---

built by [sreecharan desu](https://www.sreecharandesu.in) · [more projects](https://www.sreecharandesu.in/work)
