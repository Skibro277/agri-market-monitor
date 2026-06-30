import time
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from data_fetcher import (
    fetch_commodity_prices,
    compute_price_changes,
    fetch_wasde_data,
    fetch_fao_data,
)
from llm_summary import generate_summary, PROVIDERS
from weather_fetcher import fetch_all_weather, get_weather_description
from report_generator import generate_pdf_report

st.set_page_config(
    page_title="Agri Market Monitor | Briefing Rynków Rolnych",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "mailto:aoczkowski@example.com",
        "About": (
            "**Agri Market Monitor** — automatyczny briefing analityczny rynków surowców rolnych.\n\n"
            "Autor: Arkadiusz Oczkowski, Licencjonowany Makler Papierów Wartościowych.\n\n"
            "Dane: USDA WASDE · FAO FPPI · CBOT via yfinance · Open-Meteo. "
            "Projekt portfolio — dane mają charakter informacyjny i nie stanowią rekomendacji inwestycyjnej."
        ),
    },
)

_GLOBAL_CSS = """
<style>
/* ===== FORCE LIGHT THEME ===== */
:root { color-scheme: light !important; }
html, body { background-color: #FFFFFF !important; color: #0F172A !important; }
.stApp { background-color: #FFFFFF !important; }
[data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
[data-testid="stHeader"] { background-color: #FFFFFF !important; }
[data-testid="stSidebar"] { background-color: #F4F6FA !important; }
[data-testid="stSidebar"] * { color: #0F172A !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] select { background-color: #FFFFFF !important; color: #0F172A !important; }
div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #0F172A !important; }
[data-testid="stMetricValue"] { color: #0F172A !important; }
[data-testid="stMetricLabel"] { color: #64748B !important; }
button[data-baseweb="tab"] { color: #0F172A !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #0F2A47 !important; border-bottom-color: #C9A227 !important; }
/* ===== END FORCE LIGHT THEME ===== */

/* Hero header */
.hero {
    background: linear-gradient(135deg, #0F2A47 0%, #1E3A66 100%);
    color: #F8FAFC;
    padding: 28px 36px;
    border-radius: 10px;
    margin-bottom: 22px;
    border-left: 6px solid #C9A227;
    box-shadow: 0 2px 10px rgba(15,42,71,0.12);
}
.hero h1 {
    color: #FFFFFF !important;
    font-size: 30px !important;
    margin: 0 0 6px 0 !important;
    font-weight: 700;
}
.hero .hero-sub {
    color: #CBD5E1;
    font-size: 15px;
    margin-bottom: 12px;
    line-height: 1.45;
}
.hero .hero-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    font-size: 13px;
    color: #E2E8F0;
    border-top: 1px solid rgba(201,162,39,0.35);
    padding-top: 12px;
}
.hero .hero-meta b { color: #C9A227; font-weight: 600; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #F8FAFC;
    border-right: 1px solid #E2E8F0;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #0F2A47;
    font-size: 15px !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 8px;
}

/* Author card */
.author-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #C9A227;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 6px;
}
.author-card .author-name {
    font-weight: 700;
    font-size: 15px;
    color: #0F2A47;
    margin-bottom: 2px;
}
.author-card .author-role {
    font-size: 12.5px;
    color: #475569;
    line-height: 1.4;
}

/* Section card */
.section-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 5px solid #C9A227;
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 18px;
}

/* AI summary card */
.ai-card {
    background: #F0F4FF;
    border: 1px solid #DBEAFE;
    border-left: 5px solid #0F2A47;
    border-radius: 8px;
    padding: 20px 24px;
    font-size: 0.95rem;
    line-height: 1.75;
    color: #1E293B;
}

/* Buttons */
.stButton > button {
    background: #0F2A47 !important;
    color: #FFFFFF !important;
    border-color: #0F2A47 !important;
    font-weight: 600;
    letter-spacing: 0.02em;
    border-radius: 6px;
}
.stButton > button:hover {
    background: #1E3A66 !important;
    border-color: #C9A227 !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 500;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #0F2A47 !important;
    border-bottom-color: #C9A227 !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 10px 14px;
}
[data-testid="stMetricLabel"] p {
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748B !important;
}

/* Footer */
.app-footer {
    margin-top: 48px;
    padding: 22px 0 8px 0;
    border-top: 2px solid #C9A227;
    color: #475569;
    font-size: 12.5px;
    line-height: 1.5;
}
.app-footer .footer-name {
    color: #0F2A47;
    font-weight: 600;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0;
    border-radius: 6px;
}

/* Divider accent */
hr { border-color: #E2E8F0 !important; }

/* Hide Streamlit chrome */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)

TICKER_LABELS = {"ZW=F": "Pszenica", "ZC=F": "Kukurydza", "ZS=F": "Soja"}

COLOR_NAVY   = "#0F2A47"
COLOR_GOLD   = "#C9A227"
COLOR_GREEN  = "#16a34a"
COLOR_RED    = "#dc2626"
COLOR_AMBER  = "#f59e0b"
COLOR_BLUE   = "#2563EB"

PLOTLY_LIGHT = dict(
    template="plotly_white",
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    font=dict(family="Inter, sans-serif", color="#1E293B"),
    margin=dict(l=10, r=10, t=40, b=10),
)


# ─── Session state init ───────────────────────────────────────────────────────

if "last_update"        not in st.session_state: st.session_state.last_update = {}
if "auto_refresh_at"    not in st.session_state: st.session_state.auto_refresh_at = None
if "ai_summary_text"    not in st.session_state: st.session_state.ai_summary_text = None
if "wasde_override"     not in st.session_state: st.session_state.wasde_override = None
if "wasde_manual_date"  not in st.session_state: st.session_state.wasde_manual_date = None

_WASDE_ROWS = [
    ("Wheat",    "Production"),
    ("Wheat",    "Consumption"),
    ("Wheat",    "Ending Stocks"),
    ("Corn",     "Production"),
    ("Corn",     "Consumption"),
    ("Corn",     "Ending Stocks"),
    ("Soybeans", "Production"),
    ("Soybeans", "Consumption"),
    ("Soybeans", "Ending Stocks"),
]


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="author-card">
        <div class="author-name">Arkadiusz Oczkowski</div>
        <div class="author-role">Licencjonowany Makler Papierów Wartościowych<br>Projekt portfolio</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### AI — Provider")
    ai_provider = st.selectbox(
        "Wybierz model AI",
        list(PROVIDERS.keys()),
        label_visibility="collapsed",
    )
    pinfo = PROVIDERS[ai_provider]
    gemini_key = st.text_input(
        "Klucz API",
        type="password",
        placeholder=pinfo["hint"],
        help=f"Pobierz klucz: {pinfo['url']}",
        label_visibility="collapsed",
    )
    st.caption(f"[Pobierz klucz →]({pinfo['url']})")

    st.markdown("### Surowce")
    show_wheat = st.checkbox("Pszenica (ZW=F)", value=True)
    show_corn  = st.checkbox("Kukurydza (ZC=F)", value=True)
    show_soy   = st.checkbox("Soja (ZS=F)", value=True)

    selected_tickers = (
        (["ZW=F"] if show_wheat else []) +
        (["ZC=F"] if show_corn  else []) +
        (["ZS=F"] if show_soy   else [])
    )

    st.markdown("### Auto-odświeżanie")
    auto_refresh = st.toggle("Włącz", value=False)
    if auto_refresh:
        interval_label = st.selectbox(
            "Interwał",
            ["30 minut", "1 godzina", "2 godziny", "4 godziny"],
            index=1,
        )
        interval_map = {"30 minut": 1800, "1 godzina": 3600, "2 godziny": 7200, "4 godziny": 14400}
        interval_sec = interval_map[interval_label]

        now = time.time()
        if st.session_state.auto_refresh_at is None:
            st.session_state.auto_refresh_at = now + interval_sec

        remaining = st.session_state.auto_refresh_at - now
        if remaining <= 0:
            st.cache_data.clear()
            st.session_state.auto_refresh_at = now + interval_sec
            st.rerun()
        else:
            mins, secs = divmod(int(remaining), 60)
            st.caption(f"Następne odświeżenie za: {mins}m {secs:02d}s")
    else:
        st.session_state.auto_refresh_at = None

    # ── Ręczna edycja danych WASDE ──────────────────────────────────────────
    st.markdown("### Dane WASDE")
    with st.expander("✏️ Wprowadź dane ręcznie", expanded=False):
        st.caption(
            "Wpisz dane z aktualnego raportu USDA WASDE "
            "([pobierz PDF →](https://www.usda.gov/oce/commodity/wasde/)). "
            "Wszystkie wartości w mln ton (Mt)."
        )
        wasde_report_date = st.text_input(
            "Raport WASDE (miesiąc/rok)",
            value=st.session_state.wasde_manual_date or "Maj 2025",
            placeholder="np. Czerwiec 2025",
        )

        _LABELS_PL = {
            "Wheat": "Pszenica", "Corn": "Kukurydza", "Soybeans": "Soja",
            "Production": "Produkcja", "Consumption": "Konsumpcja", "Ending Stocks": "Zapasy końcowe",
        }

        # Default values (USDA WASDE May 2025)
        _DEFAULTS = {
            ("Wheat",    "Production"):    798.4,
            ("Wheat",    "Consumption"):   805.3,
            ("Wheat",    "Ending Stocks"): 258.1,
            ("Corn",     "Production"):   1225.6,
            ("Corn",     "Consumption"):  1234.2,
            ("Corn",     "Ending Stocks"): 289.4,
            ("Soybeans", "Production"):    422.0,
            ("Soybeans", "Consumption"):   393.3,
            ("Soybeans", "Ending Stocks"): 124.3,
        }

        # Pre-fill from existing override or defaults
        _existing = {}
        if st.session_state.wasde_override is not None:
            for _, row in st.session_state.wasde_override.iterrows():
                _existing[(row["Commodity"], row["Metric"])] = row["Current (Mt)"]

        wasde_inputs = {}
        last_commodity = None
        for commodity, metric in _WASDE_ROWS:
            if commodity != last_commodity:
                st.markdown(f"**{_LABELS_PL[commodity]}**")
                last_commodity = commodity
            key = f"wasde_{commodity}_{metric}"
            default_val = _existing.get((commodity, metric), _DEFAULTS[(commodity, metric)])
            wasde_inputs[(commodity, metric)] = st.number_input(
                f"{_LABELS_PL[metric]} (Mt)",
                value=float(default_val),
                min_value=0.0,
                step=0.1,
                format="%.1f",
                key=key,
            )

        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("💾 Zapisz dane", width='stretch'):
                rows = []
                for (commodity, metric), curr_val in wasde_inputs.items():
                    prev_val = _DEFAULTS[(commodity, metric)]
                    change = curr_val - prev_val
                    change_pct = (change / prev_val * 100) if prev_val != 0 else 0.0
                    rows.append({
                        "Commodity":     commodity,
                        "Metric":        metric,
                        "Current (Mt)":  curr_val,
                        "Previous (Mt)": prev_val,
                        "Change (Mt)":   round(change, 2),
                        "Change %":      round(change_pct, 2),
                    })
                st.session_state.wasde_override = pd.DataFrame(rows)
                st.session_state.wasde_manual_date = wasde_report_date
                st.session_state.ai_summary_text = None
                st.success("Dane WASDE zaktualizowane!")
                st.rerun()
        with col_reset:
            if st.button("🔄 Resetuj", width='stretch'):
                st.session_state.wasde_override = None
                st.session_state.wasde_manual_date = None
                st.session_state.ai_summary_text = None
                st.rerun()

    st.markdown("### Źródła danych")
    st.markdown("- [USDA WASDE](https://www.usda.gov/oce/commodity/wasde/)")
    st.markdown("- [FAO Food Price Index](https://www.fao.org/worldfoodsituation/foodpricesindex/en/)")
    st.markdown("- [yfinance](https://pypi.org/project/yfinance/) · [Open-Meteo](https://open-meteo.com/)")

    if st.session_state.last_update:
        st.markdown("### Ostatnia aktualizacja")
        for src, ts in st.session_state.last_update.items():
            st.caption(f"{src}: {ts}")


# ─── Hero Header ──────────────────────────────────────────────────────────────

col_hero, col_btn = st.columns([4, 1])
with col_hero:
    st.markdown(f"""
    <div class="hero">
        <h1>🌾 Agri Market Monitor</h1>
        <div class="hero-sub">
            Automatyczny briefing analityczny rynków surowców rolnych
        </div>
        <div class="hero-meta">
            <span><b>Dane:</b> USDA WASDE · FAO FPPI · CBOT Futures · Open-Meteo</span>
            <span><b>AI:</b> {ai_provider}</span>
            <span><b>Sesja:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_btn:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    if st.button("🔄 Odśwież dane", width='stretch'):
        st.cache_data.clear()
        st.session_state.ai_summary_text = None
        st.rerun()


# ─── Fetch all data ───────────────────────────────────────────────────────────

with st.spinner("Pobieranie danych rynkowych…"):
    price_df,  price_err  = fetch_commodity_prices(selected_tickers or None)
    wasde_df,  wasde_err, wasde_url, wasde_auto_date = fetch_wasde_data()
    fao_df,    fao_err    = fetch_fao_data()
    weather    = fetch_all_weather()

# Effective WASDE date: manual override takes priority, then auto-fetched, then fallback
_wasde_auto_date = wasde_auto_date or "Maj 2025"

# Apply manual WASDE override if set
if st.session_state.wasde_override is not None:
    wasde_df = st.session_state.wasde_override
    _wasde_effective_date = st.session_state.wasde_manual_date or "Maj 2025"
    _wasde_source = f"Ręcznie ({_wasde_effective_date})"
else:
    _wasde_effective_date = _wasde_auto_date
    _wasde_source = f"Auto-fetch USDA WASDE ({_wasde_effective_date})" if wasde_auto_date else "USDA WASDE Maj 2025 (wbudowane)"

now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
st.session_state.last_update = {
    "Ceny futures": now_str + ("" if not price_err else " (cache)"),
    "USDA WASDE":   _wasde_source,
    "FAO FPPI":     now_str,
    "Pogoda":       now_str,
}

errors = [e for e in [price_err, wasde_err, fao_err] if e]
if errors:
    with st.expander("⚠️ Ostrzeżenia źródeł danych", expanded=False):
        for err in errors:
            st.warning(err)

changes_df, price_last_date = compute_price_changes(price_df)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1 — AI Summary
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 🤖 AI Summary — Briefing Analityczny")

# ── Ostrzeżenie o nieaktualnych danych WASDE ────────────────────────────────
_WASDE_MONTHS_PL = {
    # Polish month names (various grammatical cases)
    "styczeń": 1, "stycznia": 1,
    "luty": 2, "lutego": 2,
    "marzec": 3, "marca": 3,
    "kwiecień": 4, "kwietnia": 4,
    "maj": 5, "maja": 5,
    "czerwiec": 6, "czerwca": 6,
    "lipiec": 7, "lipca": 7,
    "sierpień": 8, "sierpnia": 8,
    "wrzesień": 9, "września": 9,
    "październik": 10, "października": 10,
    "listopad": 11, "listopada": 11,
    "grudzień": 12, "grudnia": 12,
    # English month names — needed for dates returned by PDF auto-fetch
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

def _parse_wasde_date(date_str: str | None) -> datetime | None:
    """Parse a WASDE report date string in either Polish or English into a datetime."""
    if not date_str:
        return None
    parts = date_str.lower().strip().split()
    if len(parts) >= 2:
        # Try first token as month name, last token as year (handles "June 2026", "Czerwiec 2026")
        month_num = _WASDE_MONTHS_PL.get(parts[0])
        try:
            year = int(parts[-1])
            if month_num and 2000 <= year <= 2100:
                return datetime(year, month_num, 1)
        except ValueError:
            pass
    return None

_wasde_date_str = _wasde_effective_date
_wasde_parsed = _parse_wasde_date(_wasde_date_str)
_days_old = (datetime.now() - _wasde_parsed).days if _wasde_parsed else 999

def _next_wasde_release(from_date: datetime) -> datetime:
    """
    Returns the expected next WASDE release date after `from_date`.
    WASDE is released once a month, typically on the 10th–12th.
    We use the 10th as a conservative estimate; if the 10th has already
    passed this month we return the 10th of next month.
    """
    candidate = from_date.replace(day=10, hour=0, minute=0, second=0, microsecond=0)
    if candidate <= from_date:
        # Move to next month
        if from_date.month == 12:
            candidate = candidate.replace(year=from_date.year + 1, month=1)
        else:
            candidate = candidate.replace(month=from_date.month + 1)
    return candidate

_now = datetime.now()
_next_release = _next_wasde_release(_now)

# Check if the cached report date is older than the expected last release
_last_expected_release = _next_wasde_release(_now.replace(day=1) - timedelta(days=1))
_cached_report_parsed  = _parse_wasde_date(_wasde_date_str)
_new_report_likely     = (
    _cached_report_parsed is not None
    and _last_expected_release > _cached_report_parsed
    and st.session_state.wasde_override is None
    and not wasde_auto_date  # only show if auto-fetch failed/not done
)

if wasde_auto_date and st.session_state.wasde_override is None:
    _col_msg, _col_btn = st.columns([4, 1])
    with _col_msg:
        st.success(
            f"✅ **Dane WASDE pobrane automatycznie** — raport USDA WASDE **{wasde_auto_date}**. "
            f"Następny raport USDA oczekiwany ok. **{_next_release.strftime('%d %B %Y')}**.",
            icon=None,
        )
    with _col_btn:
        if st.button("🔄 Odśwież WASDE", width='stretch', help="Wymuś ponowne pobranie najnowszego raportu PDF z USDA"):
            import os, glob as _glob
            for f in _glob.glob(os.path.join(os.path.dirname(__file__), "cache", "wasde_auto*")):
                try: os.remove(f)
                except: pass
            st.cache_data.clear()
            st.session_state.ai_summary_text = None
            st.rerun()
elif _new_report_likely:
    _col_msg2, _col_btn2 = st.columns([4, 1])
    with _col_msg2:
        st.info(
            f"📢 **Nowy raport WASDE może być już dostępny** — ostatni oczekiwany ok. "
            f"**{_last_expected_release.strftime('%d %B %Y')}**, "
            f"a pobrane dane są z **{_wasde_date_str}**. "
            "Kliknij 'Odśwież WASDE' aby pobrać najnowszy raport.",
            icon=None,
        )
    with _col_btn2:
        if st.button("🔄 Odśwież WASDE", width='stretch'):
            import os, glob as _glob
            for f in _glob.glob(os.path.join(os.path.dirname(__file__), "cache", "wasde_auto*")):
                try: os.remove(f)
                except: pass
            st.cache_data.clear()
            st.session_state.ai_summary_text = None
            st.rerun()
elif _days_old > 45:
    st.warning(
        f"⚠️ **Dane WASDE mogą być nieaktualne** — używane dane pochodzą z raportu **{_wasde_date_str}** "
        f"(ok. {_days_old // 30} mies. temu). "
        "AI wykorzysta je wyłącznie jako historyczny kontekst fundamentalny. "
        "Aby poprawić jakość raportu, wpisz dane z najnowszego raportu USDA WASDE "
        "w panelu bocznym → **Dane WASDE**.",
        icon=None,
    )

if not gemini_key:
    st.info("Wprowadź klucz Gemini API w panelu bocznym, aby wygenerować briefing.", icon="🔑")
else:
    if st.button("✨ Generuj / odśwież briefing AI"):
        st.session_state.ai_summary_text = None
        st.cache_data.clear()

    if st.session_state.ai_summary_text is None:
        with st.spinner(f"{ai_provider} generuje analizę…"):
            try:
                summary, err = generate_summary(
                    provider=ai_provider,
                    api_key=gemini_key,
                    price_df_json=changes_df.to_json() if not changes_df.empty else "",
                    wasde_df_json=wasde_df.to_json() if wasde_df is not None and not wasde_df.empty else "",
                    fao_df_json=fao_df.to_json() if fao_df is not None and not fao_df.empty else "",
                    wasde_report_date=_wasde_effective_date,
                )
                st.session_state.ai_summary_text = summary if not err else f"❌ {err}"
            except Exception as e:
                st.session_state.ai_summary_text = f"❌ Błąd: {e}"

    txt = st.session_state.ai_summary_text
    if txt:
        if txt.startswith("❌"):
            st.error(txt)
        else:
            st.markdown('<div class="ai-card">', unsafe_allow_html=True)
            st.markdown(txt)
            st.markdown('</div>', unsafe_allow_html=True)

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Ceny rynkowe
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 📈 Ceny Rynkowe")

if not changes_df.empty:
    _date_note = f"Ostatnie notowanie: **{price_last_date}** (sesja CBOT, ceny z 15-min opóźnieniem). Dane odświeżane co 15 min." if price_last_date else ""
    if _date_note:
        st.caption(_date_note)
    cols = st.columns(len(changes_df))
    for i, (_, row) in enumerate(changes_df.iterrows()):
        ch1m = row["1M Change %"]
        with cols[i]:
            st.metric(
                label=f"{TICKER_LABELS.get(row['Ticker'], row['Ticker'])} ({row['Ticker']})",
                value=f"{row['Current Price']:.2f}",
                delta=f"{ch1m:+.2f}%" if ch1m is not None else None,
            )

    def _color(val):
        if val is None or (isinstance(val, float) and pd.isna(val)): return ""
        return f"color:{COLOR_GREEN}" if val > 0 else (f"color:{COLOR_RED}" if val < 0 else "")

    disp = pd.DataFrame([{
        "Surowiec":      TICKER_LABELS.get(r["Ticker"], r["Ticker"]),
        "Ticker":        r["Ticker"],
        "Cena (USD/bu)": f"{r['Current Price']:.2f}",
        "1D %":          r["1D Change %"],
        "1T %":          r["1W Change %"],
        "1M %":          r["1M Change %"],
        "52T max":       f"{r['52W High']:.2f}" if pd.notna(r.get("52W High")) else "—",
        "52T min":       f"{r['52W Low']:.2f}"  if pd.notna(r.get("52W Low"))  else "—",
    } for _, r in changes_df.iterrows()])

    fmt = {c: (lambda x: f"{x:+.2f}%" if x is not None and not (isinstance(x, float) and pd.isna(x)) else "N/A")
           for c in ["1D %", "1T %", "1M %"]}
    st.dataframe(
        disp.style.map(_color, subset=["1D %", "1T %", "1M %"]).format(fmt),
        hide_index=True,
    )
else:
    st.warning("Brak danych cenowych.")

if price_df is not None and not price_df.empty:
    avail = [t for t in (selected_tickers or list(TICKER_LABELS)) if t in price_df.columns]
    if avail:
        ticker_sel = st.selectbox(
            "Wykres historyczny (12 mies.):",
            avail, format_func=lambda x: f"{TICKER_LABELS.get(x, x)} ({x})",
        )
        cutoff_12m = pd.Timestamp.today() - pd.DateOffset(months=12)
        s = price_df[ticker_sel].dropna()
        s = s[s.index >= cutoff_12m]
        fig = go.Figure(go.Scatter(
            x=s.index, y=s.values, mode="lines",
            name=TICKER_LABELS.get(ticker_sel, ticker_sel),
            line=dict(color=COLOR_NAVY, width=2),
            fill="tozeroy", fillcolor="rgba(15,42,71,0.07)",
        ))
        fig.update_layout(
            **PLOTLY_LIGHT, height=360,
            yaxis=dict(showgrid=True, gridcolor="#E2E8F0", title="USD/bu"),
            hovermode="x unified",
        )
        st.plotly_chart(fig)

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3 — USDA WASDE
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 🌽 USDA WASDE Monitor")
if st.session_state.wasde_override is not None:
    st.info(
        f"📋 Dane wprowadzone ręcznie — raport: **{st.session_state.wasde_manual_date or 'brak daty'}**. "
        "Aby zresetować, użyj przycisku 'Resetuj' w panelu bocznym (sekcja Dane WASDE).",
        icon="✏️",
    )
else:
    if wasde_auto_date:
        st.caption(f"Źródło: Auto-fetch USDA WASDE ({wasde_auto_date}). Dane pobrane automatycznie z raportu PDF USDA.")
    else:
        st.caption("Źródło: USDA WASDE Maj 2025 (dane wbudowane). Aby wprowadzić nowsze dane, użyj panelu bocznego → Dane WASDE.")
if wasde_url:
    st.caption(f"Oryginalny raport PDF USDA: [{wasde_url}]({wasde_url})")

if wasde_df is not None and not wasde_df.empty:
    def _hl(val):
        if val is None or (isinstance(val, float) and pd.isna(val)): return ""
        try: v = float(val)
        except: return ""
        if abs(v) < 1: return ""
        return (f"background-color:rgba(22,163,74,0.12);color:{COLOR_GREEN}" if v > 0
                else f"background-color:rgba(220,38,38,0.12);color:{COLOR_RED}")

    fmt_w = {
        "Current (Mt)":  lambda x: f"{x:.1f}" if pd.notna(x) else "N/A",
        "Previous (Mt)": lambda x: f"{x:.1f}" if pd.notna(x) else "N/A",
        "Change (Mt)":   lambda x: f"{x:+.1f}" if pd.notna(x) else "N/A",
        "Change %":      lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A",
    }
    st.dataframe(
        wasde_df.style.map(_hl, subset=["Change %"]).format(fmt_w),
        hide_index=True,
    )

    stocks = wasde_df[wasde_df["Metric"] == "Ending Stocks"].copy()
    if not stocks.empty:
        st.markdown("#### Zapasy końcowe (Mt)")
        bar_colors = [COLOR_NAVY, COLOR_BLUE, COLOR_GOLD]
        fig_b = go.Figure()
        for i, (_, row) in enumerate(stocks.iterrows()):
            c = bar_colors[i % len(bar_colors)]
            fig_b.add_trace(go.Bar(name=f"{row['Commodity']} bieżący",   x=[row["Commodity"]], y=[row["Current (Mt)"]],  marker_color=c, opacity=0.9))
            if pd.notna(row.get("Previous (Mt)")):
                fig_b.add_trace(go.Bar(name=f"{row['Commodity']} poprzedni", x=[row["Commodity"]], y=[row["Previous (Mt)"]], marker_color=c, opacity=0.35))
        fig_b.update_layout(
            **PLOTLY_LIGHT, height=300, barmode="group",
            yaxis=dict(title="Mt", showgrid=True, gridcolor="#E2E8F0"),
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_b)
else:
    st.warning("Brak danych WASDE.")

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4 — FAO Food Price Index
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 🌍 FAO Food Price Index")

CATS       = ["Food Price Index", "Cereals", "Oils", "Dairy", "Meat", "Sugar"]
CAT_COLORS = [COLOR_NAVY, COLOR_BLUE, COLOR_GOLD, "#EA580C", "#9333EA", "#0891B2"]
CRISIS_PEAK = 160.3

if fao_df is not None and not fao_df.empty:
    fao_plot = fao_df.copy()
    fao_plot["Date"] = pd.to_datetime(fao_plot["Date"])
    fao_plot = fao_plot.sort_values("Date")
    cutoff = fao_plot["Date"].max() - pd.DateOffset(months=24)
    fao_plot = fao_plot[fao_plot["Date"] >= cutoff]

    fig_fao = go.Figure()
    for cat, col in zip(CATS, CAT_COLORS):
        if cat in fao_plot.columns:
            fig_fao.add_trace(go.Scatter(
                x=fao_plot["Date"], y=fao_plot[cat],
                mode="lines", name=cat,
                line=dict(color=col, width=2),
            ))
    fig_fao.add_hline(
        y=CRISIS_PEAK, line_dash="dot", line_color=COLOR_RED,
        annotation_text=f"Szczyt 2022: {CRISIS_PEAK}",
        annotation_position="top right",
        annotation_font_color=COLOR_RED,
    )
    fig_fao.update_layout(
        **PLOTLY_LIGHT, height=400,
        yaxis=dict(title="Indeks FAO (2014-2016=100)", showgrid=True, gridcolor="#E2E8F0"),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig_fao)

    latest = fao_plot.iloc[-1]
    mcols = st.columns(len(CATS))
    for i, cat in enumerate(CATS):
        if cat in latest:
            val = latest[cat]
            with mcols[i]:
                st.metric(cat, f"{val:.1f}",
                          delta=f"{val - CRISIS_PEAK:+.1f} vs szczyt",
                          delta_color="inverse")
else:
    st.warning("Brak danych FAO.")

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Korelacje surowców
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 🔗 Korelacje Surowców")
st.caption("Korelacja Pearsona cen dziennych za ostatnie 5 lat. Wartość bliska +1 = silna współzależność.")

if price_df is not None and not price_df.empty and len(price_df.columns) >= 2:
    corr = price_df.dropna().corr()
    labels = [TICKER_LABELS.get(t, t) for t in corr.columns]

    fig_corr = go.Figure(go.Heatmap(
        z=corr.values,
        x=labels, y=labels,
        colorscale=[
            [0.0, "#dc2626"], [0.5, "#F8FAFC"], [1.0, "#0F2A47"]
        ],
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=14, color="#0F172A"),
        hoverongaps=False,
    ))
    fig_corr.update_layout(
        **PLOTLY_LIGHT, height=340,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, autorange="reversed"),
    )
    st.plotly_chart(fig_corr)

    avail_tickers = [t for t in price_df.columns if t in TICKER_LABELS]
    if len(avail_tickers) >= 2:
        st.markdown("#### Korelacja krocząca 30-dniowa")
        pairs = [(avail_tickers[i], avail_tickers[j])
                 for i in range(len(avail_tickers))
                 for j in range(i + 1, len(avail_tickers))]
        fig_roll = go.Figure()
        pair_colors = [COLOR_NAVY, COLOR_BLUE, COLOR_GOLD]
        for idx, (a, b) in enumerate(pairs):
            roll = price_df[a].rolling(30).corr(price_df[b]).dropna()
            fig_roll.add_trace(go.Scatter(
                x=roll.index, y=roll.values, mode="lines",
                name=f"{TICKER_LABELS[a]} / {TICKER_LABELS[b]}",
                line=dict(color=pair_colors[idx % len(pair_colors)], width=2),
            ))
        fig_roll.add_hline(y=0, line_dash="dot", line_color="#9CA3AF", opacity=0.6)
        fig_roll.update_layout(
            **PLOTLY_LIGHT, height=300,
            yaxis=dict(title="Korelacja", range=[-1, 1],
                       showgrid=True, gridcolor="#E2E8F0"),
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig_roll)
else:
    st.info("Zaznacz co najmniej 2 surowce w ustawieniach, by zobaczyć korelacje.")

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Sezonowość
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 📅 Sezonowość Cen")
st.caption("Średnia cena dla każdego miesiąca na przestrzeni dostępnych danych. Pomaga identyfikować typowe szczyty i dołki roku.")

MONTH_NAMES = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
               "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

if price_df is not None and not price_df.empty:
    avail_s = [t for t in (selected_tickers or list(TICKER_LABELS)) if t in price_df.columns]
    if avail_s:
        season_ticker = st.selectbox(
            "Surowiec (sezonowość):",
            avail_s,
            format_func=lambda x: f"{TICKER_LABELS.get(x, x)} ({x})",
            key="season_sel",
        )
        s = price_df[[season_ticker]].copy().dropna()
        s.index = pd.to_datetime(s.index)
        s["month"] = s.index.month
        s["year"]  = s.index.year

        monthly = s.groupby(["year", "month"])[season_ticker].mean().reset_index()
        pivot = monthly.pivot(index="month", columns="year", values=season_ticker)

        fig_sea = go.Figure()
        years = sorted(pivot.columns)
        year_colors = px.colors.sequential.Blues
        step = max(1, len(year_colors) // max(len(years), 1))

        for i, yr in enumerate(years):
            col_i = year_colors[min(i * step, len(year_colors) - 1)]
            y_vals = pivot[yr].values
            is_current = (yr == years[-1])
            fig_sea.add_trace(go.Scatter(
                x=MONTH_NAMES,
                y=y_vals,
                mode="lines",
                name=str(yr),
                line=dict(
                    color=COLOR_NAVY if is_current else col_i,
                    width=3 if is_current else 1,
                    dash="solid" if is_current else "dot",
                ),
                opacity=1.0 if is_current else 0.55,
            ))

        avg = pivot.mean(axis=1)
        fig_sea.add_trace(go.Scatter(
            x=MONTH_NAMES, y=avg.values, mode="lines",
            name="Średnia",
            line=dict(color=COLOR_GOLD, width=2, dash="dash"),
        ))

        fig_sea.update_layout(
            **PLOTLY_LIGHT, height=380,
            yaxis=dict(title="USD/bu", showgrid=True, gridcolor="#E2E8F0"),
            hovermode="x unified",
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig_sea)

        stats = pivot.T.describe().T[["mean", "min", "max", "std"]].copy()
        stats.index = MONTH_NAMES
        stats.columns = ["Średnia", "Min", "Max", "Odch. std"]
        st.dataframe(
            stats.style.format(lambda x: f"{x:.2f}" if pd.notna(x) else "—"),
            )
else:
    st.info("Brak danych cenowych do analizy sezonowości.")

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Dane pogodowe
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 🌦️ Warunki Pogodowe — Regiony Upraw")
st.caption("Dane z Open-Meteo API (aktualizacja co 30 min). Temperatura, opady i historia 90 dni dla kluczowych regionów upraw.")

if weather:
    region_names = list(weather.keys())
    tabs = st.tabs([f"{weather[r]['emoji']} {r.split('(')[0].strip()}" for r in region_names])

    for tab, region in zip(tabs, region_names):
        with tab:
            data = weather[region]
            cur  = data.get("current")
            h_df = data.get("history_df")

            if cur and "current" in cur:
                c = cur["current"]
                temp  = c.get("temperature_2m", "N/A")
                prec  = c.get("precipitation", 0)
                wind  = c.get("wind_speed_10m", "N/A")
                humid = c.get("relative_humidity_2m", "N/A")
                wcode = c.get("weather_code", 0)
                wdesc, wicon = get_weather_description(int(wcode) if wcode else 0)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric(f"{wicon} Warunki", wdesc)
                m2.metric("🌡️ Temperatura", f"{temp} °C")
                m3.metric("💧 Opady (1h)", f"{prec} mm")
                m4.metric("💨 Wiatr", f"{wind} km/h")

                if "daily" in cur:
                    d = cur["daily"]
                    dates    = d.get("time", [])
                    t_max    = d.get("temperature_2m_max", [])
                    t_min    = d.get("temperature_2m_min", [])
                    prec_sum = d.get("precipitation_sum", [])
                    et0      = d.get("et0_fao_evapotranspiration", [])

                    if dates and t_max:
                        st.markdown("##### Prognoza 7 dni")
                        fig_f = go.Figure()
                        fig_f.add_trace(go.Scatter(
                            x=dates, y=t_max, name="T max (°C)",
                            mode="lines+markers", line=dict(color=COLOR_RED, width=2),
                        ))
                        fig_f.add_trace(go.Scatter(
                            x=dates, y=t_min, name="T min (°C)",
                            mode="lines+markers", line=dict(color=COLOR_BLUE, width=2),
                        ))
                        fig_f.add_trace(go.Bar(
                            x=dates, y=prec_sum, name="Opady (mm)",
                            yaxis="y2", marker_color=COLOR_NAVY, opacity=0.5,
                        ))
                        fig_f.update_layout(
                            **PLOTLY_LIGHT, height=300,
                            yaxis=dict(title="Temp (°C)", showgrid=True, gridcolor="#E2E8F0"),
                            yaxis2=dict(title="Opady (mm)", overlaying="y", side="right", showgrid=False),
                            legend=dict(orientation="h", y=-0.25),
                            hovermode="x unified",
                        )
                        st.plotly_chart(fig_f)

                        if et0:
                            avg_et0   = sum(et0) / len(et0)
                            total_prec = sum(prec_sum) if prec_sum else 0
                            balance   = total_prec - sum(et0) if et0 else None
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Śr. ET₀ (7d)", f"{avg_et0:.1f} mm/d",
                                      help="Ewapotranspiracja FAO — im wyższa, tym większe zapotrzebowanie na wodę")
                            c2.metric("Suma opadów (7d)", f"{total_prec:.1f} mm")
                            if balance is not None:
                                c3.metric("Bilans wodny (7d)", f"{balance:+.1f} mm",
                                          delta_color="normal" if balance >= 0 else "inverse",
                                          delta=("✅ Nadwyżka" if balance >= 0 else "⚠️ Niedobór"))
            else:
                st.warning(f"Brak danych pogodowych dla {region}.")

            if h_df is not None and not h_df.empty:
                st.markdown("##### Historia 90 dni")
                fig_h = go.Figure()
                fig_h.add_trace(go.Scatter(
                    x=h_df["Date"], y=h_df["Temp (°C)"], name="Temp śr. (°C)",
                    mode="lines", line=dict(color=COLOR_RED, width=1.5),
                ))
                fig_h.add_trace(go.Bar(
                    x=h_df["Date"], y=h_df["Opady (mm)"], name="Opady (mm)",
                    yaxis="y2", marker_color=COLOR_NAVY, opacity=0.5,
                ))
                fig_h.update_layout(
                    **PLOTLY_LIGHT, height=250,
                    yaxis=dict(title="Temp (°C)", showgrid=True, gridcolor="#E2E8F0"),
                    yaxis2=dict(title="Opady (mm)", overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", y=-0.3),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_h)
else:
    st.warning("Brak danych pogodowych.")

st.divider()


# ════════════════════════════════════════════════════════════════════════════
# SECTION 8 — PDF Export
# ════════════════════════════════════════════════════════════════════════════

st.markdown("## 📄 Eksport Raportu PDF")
st.caption("Raport zawiera: AI Summary, ceny futures, WASDE, FAO FPPI i warunki pogodowe.")

col_pdf, col_info = st.columns([1, 3])
with col_pdf:
    if st.button("📥 Generuj PDF", width='stretch'):
        with st.spinner("Generowanie PDF…"):
            try:
                pdf_bytes = generate_pdf_report(
                    price_changes_df=changes_df if not changes_df.empty else None,
                    wasde_df=wasde_df,
                    fao_df=fao_df,
                    weather_data=weather,
                    ai_summary=st.session_state.get("ai_summary_text"),
                    ai_provider=ai_provider,
                )
                st.session_state["pdf_bytes"] = pdf_bytes
            except Exception as e:
                st.error(f"Błąd generowania PDF: {e}")

if "pdf_bytes" in st.session_state:
    fname = f"agri_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    col_pdf.download_button(
        label="⬇️ Pobierz PDF",
        data=st.session_state["pdf_bytes"],
        file_name=fname,
        mime="application/pdf",
        width='stretch',
    )
    with col_info:
        st.success(f"Raport gotowy: **{fname}**")

st.divider()


# ─── Footer ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="app-footer">
    <span class="footer-name">Arkadiusz Oczkowski</span> — Licencjonowany Makler Papierów Wartościowych &nbsp;·&nbsp; Nr licencji MPW &nbsp;·&nbsp; Projekt portfolio<br>
    <span class="footer-name">Agri Market Monitor</span> — automatyczny briefing analityczny rynków surowców rolnych.<br>
    Dane: <b>USDA WASDE</b> · <b>FAO Food Price Index</b> · <b>CBOT via yfinance</b> · <b>Open-Meteo</b> · <b>{ai_provider} AI</b><br>
    <span style="color:#94A3B8;font-size:11.5px;">
    ⚠️ <b>Zastrzeżenie prawne:</b> Materiały prezentowane w aplikacji mają charakter wyłącznie informacyjny i edukacyjny.
    Nie stanowią rekomendacji inwestycyjnej w rozumieniu Rozporządzenia Ministra Finansów z dnia 19 października 2005 r.
    w sprawie informacji stanowiących rekomendacje dotyczące instrumentów finansowych lub ich emitentów (Dz.U. 2005 nr 206 poz. 1715)
    ani usługi doradztwa inwestycyjnego w rozumieniu Ustawy z dnia 29 lipca 2005 r. o obrocie instrumentami finansowymi.
    Inwestowanie wiąże się z ryzykiem utraty części lub całości zainwestowanych środków.
    </span>
</div>
""", unsafe_allow_html=True)
