# 🌾 Agri Market Monitor

**Automated analytical briefing for global agricultural commodity markets.**

A Streamlit dashboard that pulls real-time CBOT futures prices, automatically downloads and parses the latest USDA WASDE PDF report, tracks the FAO Food Price Index, and monitors weather conditions across key growing regions — all summarised by an AI analyst you choose.

---

## Features

| Section | What it does |
|---|---|
| **AI Briefing** | Generates a structured analytical report (Polish) via Gemini, OpenAI, Anthropic, or OpenRouter. Clearly separates real-time futures data from historical WASDE context. |
| **Market Prices** | Live CBOT futures for wheat, corn & soybeans (ZW=F, ZC=F, ZS=F). Shows 1D / 1W / 1M change and 52-week high/low. Auto-refreshes every 15 min. |
| **USDA WASDE Monitor** | Auto-downloads the current WASDE PDF from USDA, extracts World supply/use tables with dynamic marketing-year detection and mass-balance validation. Falls back gracefully if parsing fails. |
| **FAO Food Price Index** | 36-month chart of FFPI and sub-indices (Cereals, Oils, Dairy, Meat, Sugar) with 2022 crisis reference line. |
| **Commodity Correlations** | Pearson correlation heatmap + 30-day rolling correlation between all selected commodities. |
| **Seasonality** | Monthly average price patterns over all available years with per-month statistics table. |
| **Weather Monitor** | Current conditions + 7-day forecast + 90-day history for Iowa, Kansas, Ukraine, and Mato Grosso (Brazil). Includes water balance (ET₀ vs precipitation). Fetched in parallel for fast load. |
| **PDF Export** | One-click PDF report with AI summary, price table, WASDE data, FAO chart and weather snapshot. |

---

## Live Demo

Deploy your own instance on Streamlit Community Cloud in under 5 minutes — see [Deployment](#deployment) below.

---

## Data Sources

| Source | Data | Refresh |
|---|---|---|
| [yfinance](https://pypi.org/project/yfinance/) | CBOT futures (ZW=F, ZC=F, ZS=F) | Every 15 min |
| [USDA WASDE](https://www.usda.gov/oce/commodity/wasde/) | World supply/use tables — PDF auto-parsed | Monthly (6h cache) |
| [FAO FAOSTAT](https://www.fao.org/worldfoodsituation/foodpricesindex/en/) | Food Price Index | Monthly (live fetch + hardcoded fallback) |
| [Open-Meteo](https://open-meteo.com/) | Weather — current + forecast + 90-day history | Every 30 min |

> **Disclaimer:** All data is for informational and educational purposes only. This application does not constitute investment advice.

---

## AI Providers

You can use any of the following providers — just bring your own API key:

| Provider | Model | Get key |
|---|---|---|
| Google Gemini | `gemini-1.5-flash` | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| OpenAI | `gpt-4o-mini` | [platform.openai.com](https://platform.openai.com/api-keys) |
| Anthropic Claude | `claude-3-haiku-20240307` | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| OpenRouter | `openai/gpt-4o-mini` | [openrouter.ai](https://openrouter.ai/settings/keys) |

---

## Deployment

### Streamlit Community Cloud (recommended — free)

1. **Fork or push this repo to your GitHub account.**

2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.

3. Set the following fields:

   | Field | Value |
   |---|---|
   | Repository | `your-username/agri-market-monitor` |
   | Branch | `main` |
   | Main file path | `app.py` |

4. Click **Deploy**. Streamlit Cloud will install dependencies from `requirements.txt` automatically.

5. Your app will be live at `https://your-app-name.streamlit.app`.

> **No secrets required at deploy time** — the API key is entered by the user directly in the sidebar at runtime.

### Run locally

```bash
# 1. Clone the repo
git clone https://github.com/your-username/agri-market-monitor.git
cd agri-market-monitor

# 2. Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Project Structure

```
agri-market-monitor/
├── app.py                # Main Streamlit application
├── data_fetcher.py       # WASDE PDF parser, yfinance, FAO, price calculations
├── llm_summary.py        # AI prompt builder + multi-provider API calls
├── weather_fetcher.py    # Open-Meteo API (parallel fetch)
├── report_generator.py   # PDF export
├── requirements.txt
├── cache/                # Disk cache (auto-created, gitignored)
└── fonts/                # Fonts for PDF export
```

---

## Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[yfinance](https://pypi.org/project/yfinance/)** — CBOT futures data
- **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)** — WASDE PDF parsing
- **[Plotly](https://plotly.com/python/)** — Interactive charts
- **[pandas](https://pandas.pydata.org/)** — Data processing
- **[requests](https://requests.readthedocs.io/) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)** — Web scraping
- **[Open-Meteo API](https://open-meteo.com/)** — Weather data (no API key needed)

---

## WASDE Parser — How It Works

The parser auto-downloads the latest WASDE PDF from the USDA website each month:

1. Scrapes `https://www.usda.gov/oce/commodity/wasde/` for the current PDF link
2. Downloads the PDF and extracts text with PyMuPDF
3. **Dynamically detects** the marketing-year labels (e.g. `2025/26 Est.`) — no hardcoded years
4. Extracts the **World** supply/use row for Wheat, Corn, and Soybeans
5. **Validates** each row with plausible range checks and a mass-balance assertion (`BegStk + Prod ≈ DomTotal + EndStk ± 5 Mt`)
6. Caches results for 6 hours; falls back to hardcoded May 2025 data if the fetch or parse fails

---

## Configuration

All settings are in the sidebar — no `.env` file needed:

| Setting | Description |
|---|---|
| AI Provider | Choose between Gemini, OpenAI, Claude, OpenRouter |
| API Key | Entered at runtime, never stored |
| Commodities | Toggle Wheat / Corn / Soybeans |
| Auto-refresh | 30 min / 1h / 2h / 4h intervals |
| WASDE override | Manually enter WASDE data if needed |

---

## Known Limitations

- WASDE PDF parsing depends on USDA's layout staying consistent. If USDA changes their PDF format, the parser falls back to the last cached data.
- Futures prices are delayed ~15 minutes (yfinance limitation).
- FAO Food Price Index is released once per month; the app uses hardcoded data as a reliable fallback when the live API is unavailable.

---

## Author

**Arkadiusz Oczkowski** — Licensed Securities Broker  
Portfolio project · Data is informational only and does not constitute investment advice.
