"""
Generowanie raportu PDF - Agri Market Monitor.
Uzywa fpdf2 z fontem DejaVu (Unicode). Schemat kolorow: ciemny tekst na bialym tle.
"""

from __future__ import annotations
import glob
import re
import os
from datetime import datetime
import pandas as pd


def _safe(text) -> str:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return "N/A"
    return str(text)


def _replace_polish(text: str) -> str:
    mapping = {
        "\u0105": "a", "\u0104": "A", "\u0107": "c", "\u0106": "C",
        "\u0119": "e", "\u0118": "E", "\u0142": "l", "\u0141": "L",
        "\u0144": "n", "\u0143": "N", "\u00f3": "o", "\u00d3": "O",
        "\u015b": "s", "\u015a": "S", "\u017a": "z", "\u0179": "Z",
        "\u017c": "z", "\u017b": "Z",
    }
    for k, v in mapping.items():
        text = text.replace(k, v)
    return text


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting for plain-text PDF output."""
    text = re.sub(r"#{1,6}\s*", "", text)          # headings
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # italic
    text = re.sub(r"__(.+?)__", r"\1", text)        # bold alt
    text = re.sub(r"`(.+?)`", r"\1", text)          # inline code
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)     # images
    text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text) # links
    text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"\n{3,}", "\n\n", text)          # triple newlines
    return text.strip()


def _find_dejavu_fonts() -> str | None:
    """Search for DejaVu fonts directory in common locations."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/",
        "/usr/share/fonts/dejavu/",
        "/usr/share/fonts/TTF/",
        os.path.join(os.path.dirname(__file__), "fonts") + "/",
        "/run/current-system/sw/share/fonts/truetype/dejavu/",
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "DejaVuSans.ttf")):
            return path

    for pattern in ["/nix/store/*/share/fonts/truetype/dejavu/"]:
        matches = glob.glob(pattern)
        for m in matches:
            if os.path.isfile(os.path.join(m, "DejaVuSans.ttf")):
                return m

    return None


# A4 usable width = 210 - 14*2 = 182mm
_PW = 182


def generate_pdf_report(
    price_changes_df: pd.DataFrame | None,
    wasde_df: pd.DataFrame | None,
    fao_df: pd.DataFrame | None,
    weather_data: dict | None,
    ai_summary: str | None,
    ai_provider: str = "AI",
) -> bytes:
    """Zwraca bajty PDF gotowe do pobrania."""
    from fpdf import FPDF

    NAVY     = (15,  42,  71)
    GOLD     = (180, 130,  20)
    GREEN    = (22,  163,  74)
    RED      = (220,  38,  38)
    DARK     = (30,   32,  40)
    GRAY     = (100, 110, 125)
    WHITE    = (255, 255, 255)
    LIGHT_BG = (248, 250, 252)

    font_dir = _find_dejavu_fonts()
    use_unicode = font_dir is not None

    class PDF(FPDF):
        def _setup_font(self):
            if use_unicode and "DejaVuSans" not in self.fonts:
                self.add_font("DejaVuSans", "",   font_dir + "DejaVuSans.ttf",                 uni=True)
                self.add_font("DejaVuSans", "B",  font_dir + "DejaVuSans-Bold.ttf",            uni=True)
                self.add_font("DejaVuSans", "I",  font_dir + "DejaVuSansMono-Oblique.ttf",     uni=True)
                self.add_font("DejaVuSans", "BI", font_dir + "DejaVuSansMono-BoldOblique.ttf", uni=True)

        def _font(self, style="", size=9):
            self._setup_font()
            if use_unicode:
                self.set_font("DejaVuSans", style, size)
            else:
                self.set_font("Helvetica", style, size)

        def _txt(self, text: str) -> str:
            return text if use_unicode else _replace_polish(text)

        def header(self):
            # Full-width navy bar
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 20, "F")
            # Title on left
            self._font("B", 13)
            self.set_text_color(*GOLD)
            self.set_xy(14, 4)
            self.cell(100, 8, self._txt("Agri Market Monitor"), align="L")
            # Date on right
            self._font("", 7.5)
            self.set_text_color(*WHITE)
            self.set_xy(14, 4)
            self.cell(_PW, 8, self._txt(f"Wygenerowano: {datetime.now().strftime('%d.%m.%Y %H:%M')}"), align="R")
            # Sub-line
            self._font("", 7)
            self.set_text_color(180, 200, 220)
            self.set_xy(14, 12)
            self.cell(_PW, 6, self._txt("Automatyczny briefing analityczny rynkow surowcow rolnych"), align="L")
            # Move cursor below header
            self.set_y(26)

        def footer(self):
            self.set_y(-12)
            self._font("", 7)
            self.set_text_color(*GRAY)
            self.cell(0, 5, self._txt(
                f"Agri Market Monitor  |  Dane: USDA WASDE, FAO FPPI, yfinance, Open-Meteo  |  Strona {self.page_no()}"
            ), align="C")

        def section_title(self, title: str):
            self.ln(4)
            self._font("B", 9)
            self.set_text_color(*WHITE)
            self.set_fill_color(*NAVY)
            self.cell(_PW, 6.5, self._txt(title), fill=True, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

        def table_header(self, headers: list[str], widths: list[int]):
            self._font("B", 7.5)
            self.set_text_color(*NAVY)
            self.set_fill_color(*LIGHT_BG)
            for h, w in zip(headers, widths):
                self.cell(w, 6, self._txt(h), fill=True, border=1)
            self.ln()

        def table_row(self, values: list[str], widths: list[int], colors: list | None = None):
            self._font("", 7.5)
            self.set_fill_color(*WHITE)
            for i, (v, w) in enumerate(zip(values, widths)):
                color = colors[i] if colors and i < len(colors) else DARK
                self.set_text_color(*color)
                self.cell(w, 5.5, self._txt(str(v)), border=1)
            self.ln()

        def check_page_break(self, needed_mm: float = 30):
            """Add a new page if less than needed_mm remain."""
            if self.get_y() > (297 - 14 - needed_mm):
                self.add_page()

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 26, 14)
    pdf.add_page()
    pdf._setup_font()

    # ── Title block ──────────────────────────────────────────────────────────
    pdf._font("B", 18)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, pdf._txt("Briefing Analityczny"), new_x="LMARGIN", new_y="NEXT")
    pdf._font("", 9.5)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5.5, pdf._txt(f"Rynki surowcow rolnych  \u2014  {datetime.now().strftime('%B %Y')}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf._font("", 8)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 5, pdf._txt(f"Przygotowany przez: Arkadiusz Oczkowski  |  Licencjonowany Makler Papierow Wartosciowych"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    # Gold separator line
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.6)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(4)

    # ── AI Summary ───────────────────────────────────────────────────────────
    if ai_summary and not ai_summary.startswith("❌"):
        pdf.check_page_break(40)
        provider_label = ai_provider.upper() if ai_provider else "AI"
        pdf.section_title(f"AI SUMMARY \u2014 {provider_label}")
        pdf._font("", 8.5)
        pdf.set_text_color(*DARK)
        clean = _strip_markdown(ai_summary)
        # Write paragraph by paragraph for better spacing
        for para in clean.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            pdf.check_page_break(15)
            pdf.multi_cell(_PW, 5.2, pdf._txt(para))
            pdf.ln(2)
        pdf.ln(2)

    # ── Commodity Prices ─────────────────────────────────────────────────────
    if price_changes_df is not None and not price_changes_df.empty:
        pdf.check_page_break(35)
        pdf.section_title("CENY FUTURES (CBOT)")
        labels = {"ZW=F": "Pszenica", "ZC=F": "Kukurydza", "ZS=F": "Soja"}
        # 182mm total: 55+32+32+32+31 = 182
        col_w = [55, 32, 32, 32, 31]
        pdf.table_header(["Surowiec", "Cena (USD/bu)", "1D %", "1T %", "1M %"], col_w)

        for _, row in price_changes_df.iterrows():
            row_vals = [labels.get(row["Ticker"], row["Ticker"]), f"{row['Current Price']:.2f}"]
            row_colors = [DARK, DARK]
            for key in ["1D Change %", "1W Change %", "1M Change %"]:
                val = row.get(key)
                if val is not None and not (isinstance(val, float) and pd.isna(val)):
                    row_vals.append(f"{val:+.2f}%")
                    row_colors.append(GREEN if val > 0 else (RED if val < 0 else DARK))
                else:
                    row_vals.append("N/A")
                    row_colors.append(GRAY)
            pdf.table_row(row_vals, col_w, row_colors)
        pdf.ln(3)

    # ── WASDE ────────────────────────────────────────────────────────────────
    if wasde_df is not None and not wasde_df.empty:
        pdf.check_page_break(45)
        pdf.section_title("USDA WASDE \u2014 BILANSE GLOBALNE")
        # 182mm total: 34+42+26+26+27+27 = 182
        col_w = [34, 42, 26, 26, 27, 27]
        pdf.table_header(
            ["Surowiec", "Wskaznik", "Biezacy (Mt)", "Poprz. (Mt)", "Zmiana (Mt)", "Zmiana %"],
            col_w,
        )
        for _, row in wasde_df.iterrows():
            chg = row.get("Change (Mt)")
            chg_pct = row.get("Change %")
            chg_val = f"{chg:+.1f}" if pd.notna(chg) else "N/A"
            chg_pct_val = f"{chg_pct:+.2f}%" if pd.notna(chg_pct) else "N/A"
            chg_color = GREEN if pd.notna(chg) and chg > 0 else (RED if pd.notna(chg) and chg < 0 else GRAY)
            pct_color = GREEN if pd.notna(chg_pct) and chg_pct > 0 else (RED if pd.notna(chg_pct) and chg_pct < 0 else GRAY)
            pdf.table_row(
                [
                    _safe(row.get("Commodity")),
                    _safe(row.get("Metric")),
                    f"{row['Current (Mt)']:.1f}" if pd.notna(row.get("Current (Mt)")) else "N/A",
                    f"{row['Previous (Mt)']:.1f}" if pd.notna(row.get("Previous (Mt)")) else "N/A",
                    chg_val,
                    chg_pct_val,
                ],
                col_w,
                [DARK, DARK, DARK, DARK, chg_color, pct_color],
            )
        pdf.ln(3)

    # ── FAO ──────────────────────────────────────────────────────────────────
    if fao_df is not None and not fao_df.empty:
        pdf.check_page_break(35)
        pdf.section_title("FAO FOOD PRICE INDEX \u2014 OSTATNIE 3 MIESIACE")
        fao_sorted = fao_df.sort_values("Date").tail(3)
        categories = ["Food Price Index", "Cereals", "Oils", "Dairy", "Meat", "Sugar"]
        # 182mm total: 28 + 25.67*6 ≈ 28+154 = 182 → use 28+[26,26,26,26,25,25]=182
        date_w = 28
        cat_w  = [26, 26, 26, 26, 25, 25]
        pdf.table_header(["Data"] + [c[:10] for c in categories], [date_w] + cat_w)

        prev_row = None
        for _, row in fao_sorted.iterrows():
            date_str = pd.Timestamp(row["Date"]).strftime("%b %Y")
            row_vals = [date_str]
            row_colors = [DARK]
            for cat, cw in zip(categories, cat_w):
                val = row.get(cat)
                if pd.notna(val):
                    row_vals.append(f"{val:.1f}")
                    if prev_row is not None and cat in prev_row and prev_row[cat] != 0:
                        chg = (val - prev_row[cat]) / prev_row[cat]
                        row_colors.append(GREEN if chg > 0.005 else (RED if chg < -0.005 else DARK))
                    else:
                        row_colors.append(DARK)
                else:
                    row_vals.append("N/A")
                    row_colors.append(GRAY)
            pdf.table_row(row_vals, [date_w] + cat_w, row_colors)
            prev_row = row
        pdf.ln(3)

    # ── Weather summary ──────────────────────────────────────────────────────
    if weather_data:
        pdf.check_page_break(30)
        pdf.section_title("WARUNKI POGODOWE \u2014 REGIONY UPRAW")
        any_weather = False
        for region, data in weather_data.items():
            cur = data.get("current")
            if not cur or "current" not in cur:
                continue
            any_weather = True
            c = cur["current"]
            temp  = c.get("temperature_2m", "N/A")
            prec  = c.get("precipitation", 0)
            humid = c.get("relative_humidity_2m", "N/A")
            wind  = c.get("wind_speed_10m", "N/A")
            pdf.check_page_break(14)
            pdf._font("B", 8.5)
            pdf.set_text_color(*NAVY)
            pdf.cell(_PW, 5.5, pdf._txt(region), new_x="LMARGIN", new_y="NEXT")
            pdf._font("", 8)
            pdf.set_text_color(*DARK)
            pdf.cell(_PW, 5,
                     pdf._txt(f"Temp: {temp} \u00b0C  |  Opady: {prec} mm  |  Wilgotnosc: {humid}%  |  Wiatr: {wind} km/h"),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)
        if not any_weather:
            pdf._font("", 9)
            pdf.set_text_color(*GRAY)
            pdf.cell(0, 5, pdf._txt("Brak danych pogodowych."), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # ── Disclaimer ───────────────────────────────────────────────────────────
    pdf.check_page_break(14)
    pdf.ln(4)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.4)
    pdf.line(14, pdf.get_y(), 196, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(3)
    pdf._font("I", 7)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(_PW, 4, pdf._txt(
        "Raport wygenerowany automatycznie przez Agri Market Monitor. "
        "Dane maja charakter wylacznie informacyjny i nie stanowia rekomendacji inwestycyjnej. "
        "Zrodla: USDA WASDE, FAO Food Price Index, CBOT via yfinance, Open-Meteo."
    ))

    return bytes(pdf.output())
