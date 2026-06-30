import io
from datetime import datetime
import streamlit as st
import pandas as pd

def _build_system_prompt() -> str:
    today = datetime.now().strftime("%d %B %Y")
    return (
        f"Today is {today}. You are a senior agricultural commodities analyst at an investment fund. "
        "You will receive two types of data with DIFFERENT time horizons — treat them accordingly:\n"
        "1. FUTURES PRICES (CBOT) — these are CURRENT, real-time market prices as of today. "
        "They reflect the market's latest expectations and should be treated as the primary signal for current sentiment.\n"
        "2. USDA WASDE DATA — these are HISTORICAL supply/demand projections from a specific past report date (stated in the data). "
        "They are NOT current — treat them as fundamental reference context only, NOT as the current market outlook. "
        "IMPORTANT: When discussing WASDE data, always explicitly mention the report date it comes from, "
        "and frame it as historical context, not a current projection.\n"
        "3. FAO Food Price Index — monthly index data, use the date shown in the data.\n\n"
        "Write a concise analytical briefing. "
        "Style: professional, factual, no fluff. Write the response in POLISH. "
        "Do NOT use markdown headers (###, ####) — use plain text with numbered sections and bold emphasis (**text**) instead. "
        "Structure: (1) Aktualna sytuacja rynkowa (oparta na cenach futures), "
        "(2) Kontekst fundamentalny (dane WASDE z [data raportu] — historyczne), "
        "(3) Ryzyka i czynniki do obserwacji, "
        "(4) Ogólna ocena sentymentu rynkowego. "
        "Length: max 450 words."
    )

PROVIDERS = {
    "Gemini (Google)":  {"hint": "AIza...",          "url": "https://aistudio.google.com/app/apikey"},
    "OpenAI (ChatGPT)": {"hint": "sk-...",            "url": "https://platform.openai.com/api-keys"},
    "Anthropic (Claude)":{"hint": "sk-ant-...",       "url": "https://console.anthropic.com/settings/keys"},
    "OpenRouter":        {"hint": "sk-or-v1-...",     "url": "https://openrouter.ai/settings/keys"},
}

PROVIDER_MODELS = {
    "Gemini (Google)":   "gemini-1.5-flash",
    "OpenAI (ChatGPT)":  "gpt-4o-mini",
    "Anthropic (Claude)":"claude-3-haiku-20240307",
    "OpenRouter":        "openai/gpt-4o-mini",
}


def _format_price_data(price_df: pd.DataFrame | None) -> str:
    if price_df is None or price_df.empty:
        return "Brak danych cenowych.\n"
    labels = {"ZW=F": "Pszenica (CBOT)", "ZC=F": "Kukurydza (CBOT)", "ZS=F": "Soja (CBOT)"}
    lines = ["### Ceny surowców futures (USD/bu):"]
    for _, row in price_df.iterrows():
        ticker = row.get("Ticker", "")
        name = labels.get(ticker, ticker)
        price = row.get("Current Price", "N/A")
        ch1m = row.get("1M Change %", None)
        ch1m_str = f"{ch1m:+.2f}%" if ch1m is not None else "N/A"
        lines.append(f"- {name}: {price} USD ({ch1m_str} MoM)")
    return "\n".join(lines) + "\n"


def _format_wasde_data(wasde_df: pd.DataFrame | None, wasde_report_date: str | None = None) -> str:
    if wasde_df is None or wasde_df.empty:
        return "Brak danych USDA WASDE.\n"
    date_label = wasde_report_date or "Maj 2025"
    lines = [
        f"### USDA WASDE — historyczne prognozy globalnych bilansów (raport: {date_label}):",
        f"UWAGA: To są dane z raportu WASDE z {date_label} — NIE są to aktualne prognozy.",
    ]
    for _, row in wasde_df.iterrows():
        commodity = row.get("Commodity", "")
        metric = row.get("Metric", "")
        current = row.get("Current (Mt)", "N/A")
        change_pct = row.get("Change %", None)
        change_str = f"{change_pct:+.2f}%" if change_pct is not None and not pd.isna(change_pct) else "N/A"
        lines.append(f"- {commodity} — {metric}: {current} Mt ({change_str} vs poprzedni raport)")
    return "\n".join(lines) + "\n"


def _format_fao_data(fao_df: pd.DataFrame | None) -> str:
    if fao_df is None or fao_df.empty:
        return "Brak danych FAO FPPI.\n"
    try:
        fao_df = fao_df.sort_values("Date")
        latest = fao_df.iloc[-1]
        prev = fao_df.iloc[-2] if len(fao_df) >= 2 else None
        lines = ["### FAO Food Price Index (najnowsze dane):"]
        for cat in ["Food Price Index", "Cereals", "Oils", "Dairy", "Meat", "Sugar"]:
            if cat in latest:
                val = latest[cat]
                if prev is not None and cat in prev and prev[cat] != 0:
                    chg = (val - prev[cat]) / prev[cat] * 100
                    lines.append(f"- {cat}: {val:.1f} ({chg:+.1f}% MoM)")
                else:
                    lines.append(f"- {cat}: {val:.1f}")
        return "\n".join(lines) + "\n"
    except Exception:
        return "Błąd formatowania danych FAO.\n"


def _call_gemini(api_key: str, prompt: str) -> str:
    from google import genai as google_genai
    client = google_genai.Client(api_key=api_key)
    model = PROVIDER_MODELS["Gemini (Google)"]
    resp = client.models.generate_content(
        model=model,
        config=google_genai.types.GenerateContentConfig(
            system_instruction=_build_system_prompt(),
        ),
        contents=prompt,
    )
    return resp.text


def _call_openai(api_key: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=PROVIDER_MODELS["OpenAI (ChatGPT)"],
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=800,
    )
    return resp.choices[0].message.content


def _call_anthropic(api_key: str, prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=PROVIDER_MODELS["Anthropic (Claude)"],
        max_tokens=800,
        system=_build_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _call_openrouter(api_key: str, prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    resp = client.chat.completions.create(
        model=PROVIDER_MODELS["OpenRouter"],
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=800,
    )
    return resp.choices[0].message.content


_CALLERS = {
    "Gemini (Google)":    _call_gemini,
    "OpenAI (ChatGPT)":   _call_openai,
    "Anthropic (Claude)": _call_anthropic,
    "OpenRouter":         _call_openrouter,
}


@st.cache_data(ttl=3600, show_spinner=False)
def generate_summary(
    provider: str,
    api_key: str,
    price_df_json: str,
    wasde_df_json: str,
    fao_df_json: str,
    wasde_report_date: str | None = None,
) -> tuple[str, str | None]:
    try:
        price_df = pd.read_json(io.StringIO(price_df_json)) if price_df_json else None
        wasde_df = pd.read_json(io.StringIO(wasde_df_json)) if wasde_df_json else None
        fao_df   = pd.read_json(io.StringIO(fao_df_json))   if fao_df_json   else None

        today_str = datetime.now().strftime("%d.%m.%Y")
        data_context = (
            f"### DATA POBRANIA CENI FUTURES: {today_str} (aktualne, real-time)\n"
            + _format_price_data(price_df) + "\n"
            + _format_wasde_data(wasde_df, wasde_report_date) + "\n"
            + _format_fao_data(fao_df)
        )
        prompt = f"Poniżej dane rynkowe do analizy:\n\n{data_context}"

        caller = _CALLERS.get(provider)
        if caller is None:
            return "", f"Nieznany provider: {provider}"

        text = caller(api_key, prompt)
        return text, None

    except Exception as e:
        msg = str(e)
        if any(k in msg for k in ("API key", "api_key", "INVALID_ARGUMENT", "401", "403", "authentication")):
            return "", "Nieprawidłowy klucz API. Sprawdź klucz i wybrany provider."
        if any(k in msg.lower() for k in ("quota", "429", "rate_limit")):
            return "", "Przekroczono limit zapytań. Spróbuj ponownie za chwilę."
        return "", f"Błąd generowania podsumowania: {msg}"
