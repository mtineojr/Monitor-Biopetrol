"""
scraper_empacar.py
------------------
Scraper diario de Empacar Energy + indicadores de mercado.
Guarda en data/empacar.csv con una fila por ejecución.

Indicadores que captura:
  - Precio gasolina y diesel Empacar (scraping directo)
  - Brent USD/barril (fuente: EIA o Yahoo Finance fallback)
  - USDT/BOB paralelo (fuente: dolarparalelobolivia.net)
  - Heating Oil USD/galón (referencial fijo EIA semanal)
"""

import requests
import re
import csv
import os
import json
from datetime import datetime, timezone

OUTPUT_CSV = "data/empacar.csv"
EMPACAR_URL = "https://energy.empacar.com.bo/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BiopetrolMonitor/1.0)"}

FIELDNAMES = [
    "scrape_ts",
    "precio_gasolina", "precio_diesel",
    "brent_usd", "usdt_bob", "heating_oil",
    "fuente_brent", "fuente_usdt"
]


def scrape_empacar() -> dict:
    """Extrae precios de gasolina y diésel de Empacar."""
    result = {"precio_gasolina": None, "precio_diesel": None}
    try:
        resp = requests.get(EMPACAR_URL, headers=HEADERS, timeout=15)
        html = resp.text

        # La página carga precios via JS — buscar en el HTML o en scripts embebidos
        # Patrones posibles: "12.6", "12,6", "precio":12.6
        pat_gas = re.search(
            r'[Gg]asolina[^<]{0,200}?(\d{1,2}[.,]\d{1,2})\s*(?:Bs|bs|bolivianos)?',
            html
        )
        pat_die = re.search(
            r'[Dd]i[eé]sel[^<]{0,200}?(\d{1,2}[.,]\d{1,2})\s*(?:Bs|bs|bolivianos)?',
            html
        )

        # Buscar también en JSON embebido (wp_data, etc.)
        json_prices = re.findall(r'"precio[_\s]?(?:gasolina|combustible)"[:\s]+"?([\d.,]+)"?', html, re.I)

        if pat_gas:
            result["precio_gasolina"] = float(pat_gas.group(1).replace(',', '.'))
        if pat_die:
            result["precio_diesel"] = float(pat_die.group(1).replace(',', '.'))

        print(f"[Empacar] Gasolina: {result['precio_gasolina']} | Diésel: {result['precio_diesel']}")
    except Exception as e:
        print(f"[WARN] Empacar scrape falló: {e}")
    return result


def get_brent() -> tuple[float | None, str]:
    """Obtiene precio Brent desde Yahoo Finance API (sin key)."""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?interval=1d&range=1d"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        print(f"[Brent] ${price:.2f}/bbl (Yahoo Finance)")
        return round(price, 2), "yahoo_finance"
    except Exception as e:
        print(f"[WARN] Brent Yahoo falló: {e}")

    # Fallback: EIA API (sin key, endpoint público)
    try:
        url = "https://api.eia.gov/v2/petroleum/pri/spt/data/?frequency=daily&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1&api_key=DEMO"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        price = float(data["response"]["data"][0]["value"])
        print(f"[Brent] ${price:.2f}/bbl (EIA fallback)")
        return round(price, 2), "eia"
    except Exception as e:
        print(f"[WARN] Brent EIA falló: {e}")

    return None, "no_data"


def get_usdt_bob() -> tuple[float | None, str]:
    """Obtiene cotización USDT/BOB del mercado paralelo boliviano."""
    # Fuente 1: CriptoYa (agrega P2P Bolivia)
    try:
        url = "https://criptoya.com/api/usdt/bob/1"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        # Buscar primera entrada con totalAsk
        for exchange, vals in data.items():
            if isinstance(vals, dict) and "totalAsk" in vals:
                price = float(vals["totalAsk"])
                print(f"[USDT/BOB] Bs {price:.2f} (CriptoYa/{exchange})")
                return round(price, 4), f"criptoya_{exchange}"
    except Exception as e:
        print(f"[WARN] USDT CriptoYa falló: {e}")

    # Fallback: usar tipo oficial BCB como mínimo
    print("[USDT/BOB] Usando tipo oficial BCB 6.96 como fallback")
    return 6.96, "bcb_oficial_fallback"


def get_heating_oil() -> float:
    """Heating Oil — valor EIA semanal (actualizado manualmente o referencial)."""
    # En producción podría scrapear https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=pet&s=ema_epmrh_ppt_nus_dpg&f=w
    # Por ahora retornamos el último valor conocido
    return 2.89


def save_to_csv(record: dict):
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    file_exists = os.path.isfile(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)
    print(f"[OK] Registro guardado → {OUTPUT_CSV}")


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts} UTC] Iniciando scrape Empacar + indicadores...\n")

    empacar         = scrape_empacar()
    brent, f_brent  = get_brent()
    usdt, f_usdt    = get_usdt_bob()
    heating         = get_heating_oil()

    record = {
        "scrape_ts":       ts,
        "precio_gasolina": empacar["precio_gasolina"],
        "precio_diesel":   empacar["precio_diesel"],
        "brent_usd":       brent,
        "usdt_bob":        usdt,
        "heating_oil":     heating,
        "fuente_brent":    f_brent,
        "fuente_usdt":     f_usdt,
    }

    print(f"\n📊 Resumen:")
    for k, v in record.items():
        print(f"   {k:<20} {v}")

    save_to_csv(record)

    # Alerta si Empacar no pudo extraer precio
    if not record["precio_gasolina"]:
        print("\n⚠️  ALERTA: No se pudo extraer precio de Empacar. Revisar estructura HTML.")


if __name__ == "__main__":
    main()
