---
title: Arthik Concierge
emoji: 🏨
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---

# server-arthik

High-performance AI-driven backend engine for the Arthik Hospitality Ecosystem. This repository orchestrates hotel search, deterministic ranking, and secure payment processing.

![Architecture](https://res.cloudinary.com/dy2fjgt46/image/upload/v1772230850/Arthik-architecture_oyp5y7.png)

## Technical Overview

Built with FastAPI, LangGraph, and PostgreSQL, server-arthik serves as the intelligence layer for the ecosystem. It provides stateful AI concierge capabilities and robust integration with external payment gateways.

## Key Capabilities

- **AI Orchestration**: Stateful concierge agent powered by LangGraph for reasoning and action execution.
- **Deterministic Ranking**: Multi-weighted search algorithm factoring in price, rating, and local facilities.
- **Secure Payments**: Complete PayU lifecycle integration, including hash verification and webhook handling.
- **Automated Operations**: Digital invoice generation and real-time availability management.

## Technology Stack

- **Framework**: FastAPI (Python 3.12+)
- **Intelligence**: LangChain / LangGraph with Kimi-K2 LLM
- **Data**: PostgreSQL (Neon Serverless)
- **Performance**: Redis Caching
- **Deployment**: Vercel Serverless / Hugging Face Spaces

## Getting Started

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a .env file and configure the following:
   - DATABASE_URL
   - PAYU_MERCHANT_KEY
   - PAYU_MERCHANT_SALT
   - BASETEN_API_KEY
   - INTERNAL_API_KEY

3. **Database Migrations**

   ```bash
   python3 migrations.py
   ```

4. **Start Server**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Infrastructure

The architecture is designed for high availability and low latency, utilizing a multi-cloud strategy for compute and data persistence.

---\n*The Arthik Engineering Team*
