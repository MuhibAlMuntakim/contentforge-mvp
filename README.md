# 🚀 ContentForge — Multi-Platform AI Content Publisher

ContentForge is a production-ready, multi-platform publishing engine powered by **Python, Streamlit, CrewAI, Pydantic, and SQLite**. 

It allows you to input a single piece of "Master Content" and uses an autonomous AI Crew (powered by Google Gemini) to automatically rewrite, optimize, and format the content for 12 different social media platforms. It then executes the actual live API publish via modular Python adapters.

Current live integration status:
- Facebook publishing is implemented using Meta Graph API (text, image, and single-video post flows).
- Twitter publishing is implemented.
- Other publishers may run as stub/draft flows depending on credentials and adapter implementation.

**Built as a robust MVP prioritizing architecture, logging, separation of concerns, and API safety.**

---

## 🏗 System Architecture

The workflow is strongly typed and strictly structured into distinct modules:

```text
Intake (Streamlit UI) 
  → Validation (Pydantic rules)
    → Intelligence (CrewAI & Gemini)
      → Execution Engine (Dynamic Publishers)
        → Audit Report & Persistence (SQLite)
```

### Layer Breakdown

| Layer | Module Path | Purpose |
|-------|-------------|---------|
| **UI** | `app/streamlit_app.py` | Modern 6-Step Streamlit Wizard interface |
| **Schema** | `core/models.py` | Pydantic data models enforcing strict types |
| **Validation** | `core/validators.py` | Rules preventing invalid payloads (e.g., character limits) |
| **Intelligence** | `core/crew.py` | 4-Agent CrewAI pipeline for content adaptation |
| **Publishing** | `publishers/` | Live, decoupled API integrators (.e.g., Tweepy) |
| **Workflow** | `core/workflow.py` | Execution orchestrator |
| **Storage** | `core/storage.py` | SQLite DB persisting every state transition |

---

## 🧠 The Intelligence Layer (CrewAI + Gemini)
The `ContentAdaptationCrew` pipeline is responsible for content strategy *only*. 
It does **not** make HTTP requests to social APIs (enforcing separation of concerns). 

It features 4 distinct personas:
1. **Content Analyst** — Extracts the core message and target audience.
2. **Platform Adapter** — Re-writes the copy to precisely fit the constraints of the selected platform (e.g., TikTok vs. LinkedIn).
3. **Tone Specialist** — Refines the brand voice to match platform culture.
4. **Compliance Checker** — A safety net that reviews constraints, sets `Needs Review` flags, and checks for spam signals. 

> **Fallback Mode:** If no LLM keys are provided in `.env`, the system automatically falls back to an instant, deterministic rule-based processing engine to guarantee 100% uptime.

---

## 🌐 Supported Platforms

| Tier | Platforms | Strategy | Risk Level |
|------|-----------|----------|------------|
| **T1** | Twitter/X, LinkedIn, Blogger, Medium, Facebook, Pinterest | Full automation | Low |
| **T2** | YouTube, Instagram | Semi-automated | Low |
| **T3** | TikTok, Snapchat | Cautious rollout | Medium |
| **T4** | Reddit, Quora | **Always Drafts** | High |

---

## 🔐 Security & Extensibility

1. **Failure Isolation:** Error on one platform (e.g., a Twitter Rate Limit) will never stop another platform (e.g., LinkedIn) from publishing.
2. **Tier 4 Safety:** Reddit and Quora inputs are hardcoded by strategy to be placed into `Needs Review` pending manual human intervention.
3. **Modular Extensibility:** Adding a new platform is as simple as defining a new script in `publishers/` and adding it to the `Platform` enum. 

---

## 💻 Local Quick Start

### 1. Installation
Clone the repo and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory.

Fastest setup:
```bash
cp .env.example .env
```

Then fill required credentials for the platforms you want to publish to.

To enable the Gemini-powered AI engine:
```ini
GEMINI_API_KEY="your_google_api_key_here"
```

To enable live publishing for Facebook:
```ini
FACEBOOK_APP_ID="xxx"
FACEBOOK_APP_SECRET="xxx"
FACEBOOK_PAGE_ID="xxx"
FACEBOOK_PAGE_TOKEN="xxx"
```

To enable live publishing for Twitter:
```ini
TWITTER_API_KEY="xxx"
TWITTER_API_SECRET="xxx"
TWITTER_ACCESS_TOKEN="xxx"
TWITTER_ACCESS_SECRET="xxx"
```

Notes:
- Links are optional. If no links are provided in input, no links are appended to the published content.
- AI-generated links are sanitized; only user-provided links are allowed into final publish payloads.
- Keep `.env` secret. Never commit real keys/tokens.

### 3. Run the App
Launch the Streamlit interface:
```bash
streamlit run app/streamlit_app.py
```

### 4. Run Tests
Execute the comprehensive Pytest suite (70 tests):
```bash
pytest tests/ -v
```
