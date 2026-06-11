# NutriGuard AI — Travel Health Copilot

> **Google Cloud Rapid Agent Hackathon 2026** | Fivetran Partner Track Submission

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Gemini](https://img.shields.io/badge/Powered_by-Gemini_2.5_Flash-orange)](https://ai.google.dev)
[![Fivetran](https://img.shields.io/badge/Partner-Fivetran-green)](https://fivetran.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## What is NutriGuard AI?

NutriGuard AI is a **multi-agent travel health copilot** that keeps chronically ill and allergy-prone travellers safe abroad. Powered by Google Gemini and orchestrated through Google Cloud Agent Builder, it:

- **Reads your medical reports** via Gemini Vision OCR
- **Detects dangerous drug-food interactions** for your specific destination cuisine (e.g. Warfarin + Natto in Japan)
- **Curates safe local meals** based on your health profile
- **Generates a multilingual Waiter Card** translated by Gemini
- **Locates nearby hospitals and pharmacies** via Google Maps
- **Tracks real-time food prices** from Agmarknet → Fivetran → BigQuery

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Interface (Streamlit)                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                      ┌─────────▼──────────┐
                      │  Orchestrator Agent  │   ← Google Cloud Agent Builder
                      └──────┬──────┬───────┘
         ┌────────────┬───────┘      └──────────────┐
         │            │                              │
    ┌────▼───┐  ┌─────▼──────┐  ┌─────────┐  ┌─────▼────────┐
    │ Health │  │ Nutrition  │  │ Travel  │  │   Safety     │
    │ Agent  │  │   Agent    │  │  Agent  │  │   Agent      │
    └────┬───┘  └─────┬──────┘  └────┬────┘  └──────┬───────┘
         │            │              │               │
         └────────────┴──────────────┴───────────────┘
                                │
                ┌───────────────▼────────────────┐
                │      FoodKnowledgeService       │
                └──┬──────┬──────┬──────┬────────┘
                   │      │      │      │
              ┌────▼─┐ ┌──▼─┐ ┌──▼──┐ ┌▼────────────┐
              │ IFCT │ │USDA│ │Drug │ │  Cuisine KB │
              │ (IN) │ │(US)│ │ DB  │ │ (179 dishes)│
              └──────┘ └────┘ └─────┘ └─────────────┘

                    ⚡ Fivetran Data Pipeline ⚡
         ┌─────────────────────────────────────────────┐
         │  Agmarknet API → Fivetran → BigQuery         │
         │  WHO Advisories → Fivetran → BigQuery        │
         └─────────────────────────────────────────────┘

                  🤖 Gemini Intelligence Layer 🤖
         ┌─────────────────────────────────────────────┐
         │  OCR Vision: PDF/Image medical reports       │
         │  NLP Intent: Query routing (safety/price/map)│
         │  Translation: Multilingual Waiter Cards      │
         │  Extraction: Structured medical profiles     │
         └─────────────────────────────────────────────┘
```

---

## Key Features

### 1. Medication ↔ Destination Cuisine Risk Engine (Unique Feature)
Detects clinically dangerous drug-food combinations specific to the destination cuisine:

| Medication | Destination | Risk | Specific Dishes to Avoid |
|-----------|------------|------|--------------------------|
| Warfarin  | Japan       | 🔴 Critical | Natto, Seaweed Salad, Edamame |
| Atorvastatin | Thailand | 🔴 High | Pomelo Salad, Som Tum |
| Metformin | Japan | 🟠 High | Sake, Sake-broth dishes |
| MAO Inhibitors | Korea | 🔴 Critical | Kimchi, Doenjang Jjigae |

### 2. Gemini Vision OCR
Paste or upload medical reports (PDF/image) → Gemini extracts conditions, allergies, medications with structured JSON output.

### 3. Fivetran Data Pipeline
Real-time food commodity price intelligence via Agmarknet → Fivetran → BigQuery, making NutriGuard agents data-warehouse-aware.

### 4. QueryAgent with Gemini Intent Routing
Ask anything in natural language:
- *"Can I eat sushi in Tokyo?"*
- *"What is the price of Bajra today?"*
- *"Where is the nearest hospital in Bangkok?"*

---

## Fivetran Integration

NutriGuard uses **Fivetran as the data backbone** to ingest and normalize real-world live data:

```
External APIs                    Fivetran                    BigQuery
─────────────                    ────────                    ────────
Agmarknet Prices  ──connector──► agmarknet_prices   ──────► nutriguard_ai.commodity_prices
WHO Advisories    ──connector──► who_travel_advisories ────► nutriguard_ai.country_alerts
Hospital Datasets ──connector──► healthcare_facilities ────► nutriguard_ai.hospitals
```

Set your Fivetran API credentials:
```bash
FIVETRAN_API_KEY=your_key
FIVETRAN_API_SECRET=your_secret
```

---

## Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/nutriguard-ai
cd nutriguard-ai

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY=your_gemini_key
export GOOGLE_MAPS_API_KEY=your_maps_key  # optional
export FIVETRAN_API_KEY=your_fivetran_key  # optional

# Run the dashboard
streamlit run dashboard.py

# Run tests
python test_agents_and_ocr.py
```

---

## Data Sources

| Source | Type | Usage |
|--------|------|-------|
| IFCT 2017 | Local CSV | Indian food nutrition |
| USDA Foundation Foods | Local CSV | Global food nutrition |
| DrugBank 6.0 | Local JSON | 10,000+ drug interactions |
| World Cuisine KB | Local CSV | 179 dishes from 25+ cuisines |
| Agmarknet API | Live → Fivetran | Agricultural commodity prices |
| Google Maps API | Live | Hospital/pharmacy geolocation |
| Gemini 2.5 Flash | API | OCR, translation, NLP |

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Built with

- [Google Cloud Agent Builder](https://cloud.google.com/agent-builder)
- [Gemini 2.5 Flash](https://ai.google.dev)
- [Fivetran](https://fivetran.com)
- [Google Maps Platform](https://developers.google.com/maps)
- [Streamlit](https://streamlit.io)
