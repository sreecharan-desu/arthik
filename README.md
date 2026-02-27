# Arthik Concierge Backend

FastAPI + SQLAlchemy + PayU + Neon Postgres

## High-Level Architecture

```mermaid
graph TD
    %% Define User and Interface
    User((Guest / User))
    Frontend[Mobile/Web App]

    %% API Gateway / Backend
    subgraph "FastAPI Backend Core"
        API[FastAPI Gateway]
        RouterAuth[Auth Router]
        RouterHotel[Hotels & Search]
        RouterBooking[Booking Manager]
        RouterPayment[Payment Processor]
        RouterVendor[Vendor Portal & WS]
        RouterAgent[AI Concierge Node]
    end

    %% AI Infrastructure
    subgraph "AI Orchestration (LangGraph)"
        AgentFlow[LangGraph Workflow]
        Summarizer[Conversation Summarizer]
        ChatNode[Baseten / OpenAI LLM]
        ToolNode[Tool Executor]

        AgentFlow --> Summarizer
        Summarizer --> ChatNode
        ChatNode --> ToolNode
        ToolNode --> ChatNode
    end

    %% External integrations
    subgraph "Cloud & External Services"
        PayU[PayU Payment Gateway]
        LLMProvider[LLM Provider: Baseten/OpenAI]
        Postgres[(Neon Serverless Postgres)]
        S3[PDF Storage / Static Assets]
    end

    %% Connections
    User <--> Frontend
    Frontend <--> API

    API --> RouterAuth
    API --> RouterHotel
    API --> RouterBooking
    API --> RouterPayment
    API --> RouterVendor
    API --> RouterAgent

    RouterAgent <--> AgentFlow
    AgentFlow <--> Postgres

    RouterPayment <--> PayU
    RouterAgent <--> LLMProvider

    RouterAuth & RouterHotel & RouterBooking & RouterPayment & RouterVendor --> Postgres
    RouterPayment --> S3

    %% Styling
    style User fill:#f0f0f0,stroke:#333,stroke-width:2px
    style Frontend fill:#fff,stroke:#666,stroke-width:2px
    style API fill:#69f,stroke:#333,stroke-width:3px
    style Postgres fill:#4CAF50,stroke:#333,stroke-width:2px,color:#fff
    style AgentFlow fill:#FF9800,stroke:#333,stroke-width:2px,color:#fff
    style PayU fill:#03A9F4,stroke:#333,stroke-width:1px,color:#fff
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

- **Deterministic Ranking**: Services are ranked using a weighted formula (Price, Rating, Facilities, Location).
- **PayU Sandbox**: Integrated payment flow with hash generation and webhook verification.
- **AI Concierge**: Chat endpoint with intent extraction and automated service search/booking.
- **Real-time Updates**: WebSocket broadcast for vendor service updates.
- **Automated Invoices**: PDF generation upon payment confirmation.

## API Documentation

See [API.md](./API.md) for endpoint details and example curl commands.
