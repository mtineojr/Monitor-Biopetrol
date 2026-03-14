import requests
import re
import csv
import os
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────
URL = "http://ec2-3-22-240-207.us-east-2.compute.amazonaws.com/guiasaldos/main/donde/134"
OUTPUT_CSV = "data/saldos.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BiopetrolMonitor/1.0)"}

# Umbral de alerta (litros)
UMBRAL_CRITICO = 500
# ──────────────────────────────────────────────────────────


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def parse_stations(html: str) -> list[dict]:
    """
    Extrae los bloques de cada estación del HTML.
    La página embebe un array PHP en texto plano con los campos clave.
    """
    stations = []
    bloques = re.split(r'(?=array\(5\))', html)

    for bloque in bloques:
        if 'array(5)' not in bloque:
            continue

        try:
            id_med     = re.search(r'"id"\]\s*=>\s*int\((\d+)\)', bloque)
            un         = re.search(r'"un"\]\s*=>\s*int\((\d+)\)', bloque)
            fecha      = re.search(r'"fecha"\]\s*=>\s*string\(\d+\)\s*"([^"]+)"', bloque)
            saldo      = re.search(r'"saldo"\]\s*=>\s*string\(\d+\)\s*"([^"]+)"', bloque)
            mangueras  = re.search(r'mangueras:\s*(\d+)', bloque)
            carga_prom = re.search(r'carga promedio:\s*(\d+)', bloque)
            vehiculos  = re.search(r'cantidad de vehiculos:\s*([\d.]+)', bloque)
            tiempo_mg  = re.search(r'tiempo de carga por manguera:\s*([\d.]+)', bloque)
            nombre     = re.search(r'\n([A-ZÁÉÍÓÚ][A-ZÁÉÍÓÚÑ\s]+)\n\nVolumen', bloque)

            if not (saldo and fecha):
                continue

            stations.append({
                "id_medicion":    id_med.group(1)    if id_med    else "",
                "unidad_id":      un.group(1)         if un        else "",
                "estacion":       nombre.group(1).strip() if nombre else f"UN-{un.group(1) if un else '?'}",
                "fecha":          fecha.group(1),
                "saldo_lts":      int(saldo.group(1).replace(",", "")),
                "mangueras":      int(mangueras.group(1))    if mangueras  else 0,
                "carga_prom_lts": int(carga_prom.group(1))   if carga_prom else 40,
                "vehiculos_est":  float(vehiculos.group(1))  if vehiculos  else 0,
                "min_x_manguera": float(tiempo_mg.group(1))  if tiempo_mg  else 0,
                "scrape_ts":      datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            })

        except Exception as e:
            print(f"[WARN] Error parseando bloque: {e}")
            continue

    return stations


def save_to_csv(records: list[dict], filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.isfile(filepath)

    fieldnames = [
        "id_medicion", "unidad_id", "estacion", "fecha",
        "saldo_lts", "mangueras", "carga_prom_lts",
        "vehiculos_est", "min_x_manguera", "scrape_ts"
    ]

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(records)

    print(f"[OK] {len(records)} registros guardados → {filepath}")


def check_alerts(records: list[dict]):
    """Imprime alertas en consola — GitHub Actions las registra en el log del workflow."""
    criticas = [r for r in records if r["saldo_lts"] < UMBRAL_CRITICO]

    if criticas:
        print(f"\n⚠️  ALERTA — {len(criticas)} estación(es) bajo {UMBRAL_CRITICO} Lts:")
        for r in criticas:
            print(f"   🔴 {r['estacion']}: {r['saldo_lts']} Lts (~{r['vehiculos_est']:.0f} vehículos)")
    else:
        print("\n✅ Todas las estaciones sobre el umbral crítico.")

    total_red = sum(r["saldo_lts"] for r in records)
    print(f"📊 Saldo total red: {total_red:,} Lts | {len(records)} estaciones reportando\n")


def main():
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Iniciando scrape Biopetrol...")
    html = fetch_page(URL)
    records = parse_stations(html)

    if not records:
        print("[ERROR] No se encontraron registros. Revisar estructura HTML.")
        raise SystemExit(1)

    save_to_csv(records, OUTPUT_CSV)
    check_alerts(records)


if __name__ == "__main__":
    main()
