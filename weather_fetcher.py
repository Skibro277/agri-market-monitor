"""
Dane pogodowe z Open-Meteo API (bezpłatne, bez klucza).
Monitorowane regiony upraw: USA (Iowa, Kansas), Ukraina, Brazylia (Mato Grosso).
"""

import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

REGIONS = {
    "Iowa (Kukurydza/Soja, USA)":     {"lat": 41.88, "lon": -93.10, "emoji": "🌽"},
    "Kansas (Pszenica ozima, USA)":   {"lat": 38.69, "lon": -98.35, "emoji": "🌾"},
    "Ukraina (Pszenica/Kukurydza)":   {"lat": 48.38, "lon": 31.18,  "emoji": "🇺🇦"},
    "Mato Grosso (Soja, Brazylia)":   {"lat": -12.83,"lon": -51.92, "emoji": "🌿"},
}

BASE_URL = "https://api.open-meteo.com/v1/forecast"
HIST_URL = "https://archive-api.open-meteo.com/v1/archive"


def _fetch_region_current(lat: float, lon: float) -> dict | None:
    """Bieżące warunki + prognoza 7 dni."""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation,wind_speed_10m,relative_humidity_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration",
            "forecast_days": 7,
            "timezone": "auto",
        }
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _fetch_region_history(lat: float, lon: float, days: int = 90) -> dict | None:
    """Historia opadów i temperatur (ostatnie N dni)."""
    try:
        end = datetime.today().date()
        start = end - timedelta(days=days)
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "auto",
        }
        resp = requests.get(HIST_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


WEATHER_CODES = {
    0: ("Bezchmurnie", "☀️"),
    1: ("Przeważnie pogodnie", "🌤️"),
    2: ("Częściowe zachmurzenie", "⛅"),
    3: ("Pochmurno", "☁️"),
    45: ("Mgła", "🌫️"),
    48: ("Mgła szronowa", "🌫️"),
    51: ("Mżawka", "🌦️"),
    53: ("Mżawka umiarkowana", "🌦️"),
    55: ("Mżawka gęsta", "🌧️"),
    61: ("Deszcz słaby", "🌧️"),
    63: ("Deszcz umiarkowany", "🌧️"),
    65: ("Deszcz silny", "🌧️"),
    71: ("Śnieg słaby", "🌨️"),
    73: ("Śnieg umiarkowany", "❄️"),
    75: ("Śnieg silny", "❄️"),
    80: ("Przelotny deszcz", "🌦️"),
    81: ("Przelotne opady umiarkowane", "🌦️"),
    82: ("Gwałtowny przelotny deszcz", "⛈️"),
    95: ("Burza", "⛈️"),
    96: ("Burza z gradem", "⛈️"),
    99: ("Burza silna z gradem", "⛈️"),
}


def get_weather_description(code: int) -> tuple[str, str]:
    return WEATHER_CODES.get(code, ("Nieznane", "🌡️"))


def _fetch_region(name: str, info: dict) -> tuple[str, dict]:
    """Fetches current conditions + history for one region. Designed for parallel execution."""
    current = _fetch_region_current(info["lat"], info["lon"])
    history_raw = _fetch_region_history(info["lat"], info["lon"], days=90)

    history_df = None
    if history_raw and "daily" in history_raw:
        d = history_raw["daily"]
        history_df = pd.DataFrame({
            "Date": pd.to_datetime(d.get("time", [])),
            "Temp (°C)": d.get("temperature_2m_mean", []),
            "Opady (mm)": d.get("precipitation_sum", []),
        }).dropna()

    return name, {
        "emoji": info["emoji"],
        "lat": info["lat"],
        "lon": info["lon"],
        "current": current,
        "history_df": history_df,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_all_weather() -> dict:
    """
    Zwraca słownik {region_name: {current, history_df}} lub None dla błędów.
    Pobiera dane dla wszystkich regionów równolegle (ThreadPoolExecutor),
    co redukuje czas ładowania z ~8×timeout do ~1×timeout.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict = {}
    with ThreadPoolExecutor(max_workers=len(REGIONS)) as executor:
        futures = {
            executor.submit(_fetch_region, name, info): name
            for name, info in REGIONS.items()
        }
        for future in as_completed(futures):
            try:
                name, data = future.result(timeout=20)
                results[name] = data
            except Exception:
                pass

    # Restore original insertion order
    return {name: results[name] for name in REGIONS if name in results}
