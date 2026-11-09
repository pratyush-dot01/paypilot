# PayPilot 🚀

> **AI-powered payment and business assistant** — Built for the PayPal AI Hackathon

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![React 19](https://img.shields.io/badge/react-19-61DAFB.svg)](https://react.dev)
[![PayPal Sandbox](https://img.shields.io/badge/PayPal-Sandbox-003087.svg)](https://developer.paypal.com)

PayPilot is an intelligent fintech platform that combines an AI agent (Google Gemini / OpenAI) with real PayPal payment execution, MongoDB-grounded financial data, automated invoice management, and proactive payment reminders — all in one smart business assistant.

---

## 🎯 Problem Statement

Freelancers, consultants, and small businesses lose significant time chasing payments, managing invoices manually, and tracking overdue accounts. Existing tools are fragmented: accounting software, payment gateways, and communication apps never talk to each other.

**PayPilot solves this** by embedding an AI agent directly into the financial workflow — the assistant understands natural language, retrieves live financial data, creates invoices, executes real PayPal payments, and proactively reminds clients, all from a single chat interface.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Grounded AI Agent** | Gemini/OpenAI-powered assistant with real database context — no fabricated data |
| 💳 **PayPal Integration** | Full OAuth2, Order creation, customer approval, capture, webhooks |
| 📄 **Invoice Management** | Auto-numbered `INV-YYYY-XXXX`, GST calculations, overdue detection |
| 📊 **Financial Analytics** | Month-over-Month revenue, forecasts, anomaly detection |
| 🔔 **Smart Reminders** | AI-generated, human-approved, delivery-honest notification system |
| ⚙️ **Background Automation** | APScheduler with 6 scheduled financial monitoring jobs |
| 🛡️ **Production-Grade** | Decimal arithmetic, payment idempotency, production DB guard (503) |

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 8, Tailwind CSS v4, Lucide React, Recharts, `@paypal/react-paypal-js`, React Router v7 |
| **Backend** | Python 3.10+, FastAPI, Motor (async MongoDB), Pydantic v2, Uvicorn, HTTPX, APScheduler |
| **AI Intelligence** | Google Gemini 1.5 Flash / OpenAI GPT-4o (configurable), grounded on live MongoDB data |
| **Payments** | PayPal REST API v2 (OAuth 2.0, Orders API, Capture, Webhooks) |
| **Database** | MongoDB Atlas (production) / in-memory async mock (development) |
| **Arithmetic** | Python `Decimal` with `ROUND_HALF_UP` for all financial calculations |

---

## 📁 Project Architecture

```
paypal/
├── frontend/                        # React + Vite Application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx          # Responsive navigation with mobile drawer
│   │   │   ├── Topbar.jsx           # Header with hamburger toggle
│   │   │   ├── PayPalCheckoutModal.jsx  # PayPal SDK checkout integration
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx        # Live KPI metrics & charts
│   │   │   ├── AIAssistant.jsx      # Full AI chat interface
│   │   │   ├── Invoices.jsx         # Invoice table + Pay with PayPal
│   │   │   ├── Transactions.jsx     # Filterable transaction history
│   │   │   ├── Analytics.jsx        # Financial intelligence dashboard
│   │   │   └── Settings.jsx         # Configuration (no credentials exposed)
│   │   ├── context/
│   │   │   └── NavigationContext.jsx # Mobile navigation state
│   │   └── services/
│   │       └── api.js               # Centralized Axios API client
│   ├── .env.example                 # Environment variable template
│   └── vite.config.js
│
├── backend/                         # FastAPI Application
│   ├── app/
│   │   ├── core/config.py           # Pydantic BaseSettings (.env reader)
│   │   ├── database/session.py      # Motor async client + production guard
│   │   ├── models/schemas.py        # Pydantic v2 schemas
│   │   ├── ai/                      # AI Agent Architecture
│   │   │   ├── agent_controller.py  # Orchestrates intent, tool calling & confirmations
│   │   │   ├── llm_service.py       # Gemini / OpenAI API client
│   │   │   ├── intent_classifier.py # 9-category financial intent classifier
│   │   │   ├── entity_extractor.py  # Entity parsing (amounts, dates, names)
│   │   │   ├── context_grounder.py  # MongoDB live data grounding
│   │   │   └── tools/               # 22 modular AI execution tools
│   │   ├── services/                # Business logic
│   │   │   ├── payment_service.py   # PayPal capture, idempotency, webhooks
│   │   │   ├── paypal_service.py    # PayPal REST API v2 client
│   │   │   ├── reminder_service.py  # AI reminders with deduplication
│   │   │   ├── scheduler_service.py # APScheduler lifecycle management
│   │   │   └── ...
│   │   └── routes/                  # FastAPI routers
│   ├── tests/
│   │   ├── test_api.py              # Pytest suite (27 tests)
│   │   └── run_tests.py             # Standalone runner (33 tests)
│   ├── .env.example                 # Credential template (never commit .env)
│   ├── requirements.txt
│   └── Procfile                     # Render.com deployment
│
├── render.yaml                      # Render deployment configuration
├── LICENSE                          # MIT License
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start (Local Development)

### Prerequisites

- Python 3.10+
- Node.js 20+ and pnpm
- MongoDB (local instance or MongoDB Atlas)
- PayPal Developer account (Sandbox)

### 1. Clone & Configure Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS/Linux

pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your credentials (see Environment Variables section)
```

### 2. Configure Frontend

```bash
cd frontend
pnpm install

cp .env.example .env.local
# Edit .env.local:
# VITE_API_BASE_URL=http://localhost:8000
```

### 3. Start Backend

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Start Frontend

```bash
cd frontend
pnpm run dev
```

The app is now running at `http://localhost:5173`.

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `MONGODB_URL` | MongoDB connection string | ✅ |
| `DATABASE_NAME` | Database name (default: `paypilot`) | ✅ |
| `ENVIRONMENT` | `development` or `production` | ✅ |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | ✅ |
| `PAYPAL_CLIENT_ID` | PayPal app Client ID | ✅ |
| `PAYPAL_CLIENT_SECRET` | PayPal app Client Secret | ✅ |
| `PAYPAL_BASE_URL` | `https://api-m.sandbox.paypal.com` (sandbox) | ✅ |
| `PAYPAL_WEBHOOK_ID` | PayPal Webhook ID from Developer Dashboard | Optional |
| `PAYPAL_MODE` | `sandbox` or `live` | ✅ |
| `AI_PROVIDER` | `gemini` or `openai` | ✅ |
| `GEMINI_API_KEY` | Google AI Studio API key | For AI features |
| `OPENAI_API_KEY` | OpenAI API key | Alternative to Gemini |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API URL (`http://localhost:8000` locally) |

---

## 💳 PayPal Sandbox Setup

1. Go to [PayPal Developer Dashboard](https://developer.paypal.com/dashboard)
2. Create a Sandbox application under **Apps & Credentials**
3. Copy `Client ID` and `Secret` to `backend/.env`
4. Create a Sandbox buyer account for testing payments
5. For webhooks: register `https://your-backend.com/api/payments/webhook` and copy the Webhook ID

> ⚠️ **Never use Sandbox credentials in production.** Create a separate Live application.

---

## 🤖 AI Setup

The AI engine works in two modes:

**Grounded Local Mode** (no API key required): Uses rule-based intent classification, entity extraction, and MongoDB live data grounding. Full financial queries, invoice checks, and analytics work offline.

**LLM Mode** (Gemini or OpenAI API key configured): Enhanced natural language understanding, more nuanced responses, and richer tool execution.

To enable LLM mode:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```
Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## 🧪 Running Tests

```bash
cd backend

# Pytest suite (27 integration tests)
pytest -v tests/test_api.py

# Full standalone runner (33 tests including E2E workflows)
python -u tests/run_tests.py

# Frontend production build
cd ../frontend && pnpm run build
```

**Test Results (Phase 8 Final):**
- ✅ Pytest: **27/27 passed** (12.13s)
- ✅ Standalone Runner: **33/33 passed** (includes live PayPal Sandbox API call)
- ✅ Vite Build: **Clean build** (3.27s, 0 errors)

---

## 🌐 Production Deployment

### Backend → Render

1. Connect your GitHub repo to [Render](https://render.com)
2. Create a **Web Service**, set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Root directory:** `backend`
3. Add all environment variables from `backend/.env.example`
4. Health check path: `/health`

### Frontend → Vercel

1. Import repository to [Vercel](https://vercel.com)
2. Set:
   - **Framework:** Vite
   - **Root directory:** `frontend`
   - **Build command:** `pnpm run build`
   - **Output directory:** `dist`
3. Add `VITE_API_BASE_URL` environment variable pointing to your Render backend URL

### Database → MongoDB Atlas

1. Create a free cluster at [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a database user and get your connection string
3. Add connection string as `MONGODB_URL` in backend environment

> ⚠️ PayPilot uses PayPal **Sandbox** in this release. For live payments, replace sandbox credentials with live PayPal API credentials and change `PAYPAL_MODE=live`.

---

## 📡 API Documentation

Once running, visit:
- **Interactive docs:** `http://localhost:8000/docs` (Swagger UI)
- **Alternative docs:** `http://localhost:8000/redoc`

Key endpoints:
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check with DB connectivity |
| `POST` | `/api/ai/chat` | AI agent chat with tool execution |
| `POST` | `/api/payments/create-order` | Create PayPal order from invoice |
| `POST` | `/api/payments/capture-order` | Capture approved payment |
| `POST` | `/api/payments/webhook` | PayPal webhook receiver |
| `GET` | `/api/invoices/` | List invoices with filters |
| `GET` | `/api/analytics/financial-intelligence` | MoM revenue & forecasts |

---

## 🔒 Security Notes

- **No authentication system is implemented** — PayPilot is designed as a single-user business tool (hackathon scope). Add JWT/OAuth for multi-user production use.
- PayPal `Client Secret` is strictly server-side — never exposed to the frontend.
- LLM API keys are strictly server-side — never in frontend bundles.
- Payment amounts are always retrieved from MongoDB, never from untrusted client input.
- Webhook signature verification is implemented via PayPal's verification API.
- In production mode, missing MongoDB connection returns HTTP 503 instead of falling back to in-memory mock.

---

## 📸 Screenshots

> _Add screenshots of Dashboard, AI Assistant, Invoices, Analytics, and PayPal Checkout here._

---

## 🎬 Demo Video

> _Add a link to a 2-3 minute demo video demonstrating: Dashboard → AI invoice creation → PayPal checkout → Captured payment → Analytics._

---

## 🏆 Hackathon Context

PayPilot was built for the **PayPal AI Hackathon**. It demonstrates:
1. **Real PayPal API integration** — not mocked; live Sandbox Order creation and capture
2. **Grounded AI with tool calling** — 22 financial tools executed by the LLM agent
3. **Financial intelligence** — live MongoDB grounding, MoM analysis, anomaly detection
4. **End-to-end payment automation** — from AI invoice creation to PayPal capture to ledger update

---

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

---

## 👨‍💻 Author

**Pratyush Kumar** — [pratyush@paypilot.in](mailto:pratyush@paypilot.in)
