---
title: Arthik Concierge
emoji: 🏨
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
---

# Arthik Concierge Backend

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F24?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Power BI](https://img.shields.io/badge/Power_BI-F2C811?style=for-the-badge&logo=power-bi&logoColor=black)

FastAPI + SQLAlchemy + PayU + Neon Postgres

## High-Level Architecture

```mermaid
graph LR
    %% Definitions
    User((Guest))
    UI[Mobile / Web Frontend]

    subgraph "Serverless API (Vercel)"
        API[FastAPI Gateway]
        Auth[Auth Service]
        Hotel[Hotel Search]
        Booking[Booking Engine]
        Payment[Payment Gateway]
    end

    subgraph "AI Brain (Hugging Face)"
        Agent[LangGraph Concierge]
        LLM[GPT-4o / Kimi LLM]
        Tools[Search & Action Tools]
    end

    subgraph "Infrastructure"
        DB[(Neon Postgres)]
        Redis[[Redis Cache]]
        PayU([PayU Payment])
    end

    %% Flow
    User <==> UI
    UI <==> API

    %% API Routing
    API ---> Auth
    API ---> Hotel
    API ---> Booking
    API ---> Payment
    API <==> Agent

    %% Internal Connections
    Hotel --- Redis
    Agent <==> LLM
    Agent --- Tools

    %% Database Links
    Auth & Hotel & Booking & Payment & Agent ==> DB

    %% External
    Payment <==> PayU

    %% Styling
    classDef core fill:#f9fafd,stroke:#2563eb,stroke-width:2px,color:#1e40af
    classDef infra fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#166534
    classDef ai fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#9a3412

    class API,Auth,Hotel,Booking,Payment core
    class DB,Redis,PayU infra
    class Agent,LLM,Tools ai
```

## Setup

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   npm install
   ```

2. **Environment Variables**
   Create a `.env` file based on the following template:

   ```env
   DATABASE_URL=postgres://<user>:<pass>@<host>:5432/<db>
   SECRET_KEY=...
   PAYU_MERCHANT_KEY=...
   PAYU_MERCHANT_SALT=...
   PAYU_BASE_URL=https://sandbox.payu.in
   PAYU_SUCCESS_URL=https://<your-domain>/payment/success
   PAYU_FAILURE_URL=https://<your-domain>/payment/fail
   PAYU_WEBHOOK_SECRET=...
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   OPENAI_API_KEY=...
   APP_URL=...
   PDF_TEMP_PATH=./tmp/pdfs
   ```

3. **Database Migrations**

   ```bash
   make migrate
   ```

4. **Seed Data**

   ```bash
   make seed
   ```

5. **Start Server**
   ```bash
   make start
   ```

## Key Features

- **Multi-Cloud Deployment**: Backend optimized for Vercel (API) and Hugging Face Spaces (AI) synchronization.
- **Deterministic Ranking**: Services are ranked using a weighted formula (Price, Rating, Facilities, Location) for optimal discovery.
- **PayU Integration**: Full-stack payment lifecycle handling with hash security, callbacks, and status tracking.
- **AI Concierge (LangGraph)**: Stateful chat agent with persistent memory, intent extraction, and autonomous search.
- **Automated Invoices**: Dynamically generated PDF reports dispatched upon payment confirmation.

## API Documentation

See [API.md](./API.md) for endpoint details and example curl commands.
