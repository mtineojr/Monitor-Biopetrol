import requests
import re
import csv
import os
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────
URL = "http://ec2-3-22-240-207.us-east-2.compute.amazonaws.com/guiasaldos/main/donde/134"
OUTPUT_CSV     = "data/saldos.csv"
ESTACIONES_CSV = "estaciones.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BiopetrolMonitor/1.0)"}

UMBRAL_CRITICO = 500   # Lts — ajustar según criterio
# ──────────────────────────────────────────────────────────


def load_estaciones(filepath: str) -> dict:
    """
    Carga la tabla de equivalencias unidad_id → nombre comercial.
    Retorna dict: { "205": "BENI", "315": "BEREA", ... }
    Si el archivo no existe, retorna dict vacío (no rompe el scraper).
    """
    tabla = {}
    if not os.path.isfile(filepath):
        print(f"[WARN] No se encontró {filepath} — se usará solo auto-descubrimiento.")
        return tabla
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tabla[row["unidad_id"].strip()] = row["nombre"].strip()
    print(f"[OK] Tabla de estaciones cargada: {len(tabla)} registros.")
    return tabla


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def resolve_nombre(unidad_id: str, nombre_html: str, tabla: dict) -> tuple[str, str]:
    """
    Resuelve el nombre comercial de una estación usando 3 niveles:
      1. Nombre extraído del HTML  (fuente más fresca)
      2. Tabla de equivalencias    (fallback manual)
      3. "UN-XXX (NUEVO)"          (desconocida — dispara alerta)

    Retorna (nombre, fuente) donde fuente es "html" | "tabla" | "nuevo"
    """
    # Nivel 1: nombre del HTML limpio y válido
    if nombre_html and len(nombre_html) >= 3:
        return nombre_html.upper().strip(), "html"

    # Nivel 2: tabla de equivalencias
    if unidad_id in tabla:
        return tabla[unidad_id], "tabla"

    # Nivel 3: desconocida
    return f"UN-{unidad_id} (NUEVO)", "nuevo"


def parse_stations(html: str, tabla: dict) -> tuple[list[dict], list[str]]:
    """
    Extrae los bloques de cada estación del HTML.
    Retorna (registros, lista_de_ids_nuevos)
    """
    stations = []
    nuevos   = []

    bloques = re.split(r'(?=array\(5\)\s*\{)', html)

    for bloque in bloques:
        if 'array(5)' not in bloque:
            continue

        try:
            # ── Campos del array PHP ──────────────────────────────
            id_med     = re.search(r'"id"\]\s*=>\s*int\((\d+)\)',              bloque)
            un         = re.search(r'"un"\]\s*=>\s*int\((\d+)\)',              bloque)
            fecha      = re.search(r'"fecha"\]\s*=>\s*string\(\d+\)\s*"([^"]+)"', bloque)
            saldo      = re.search(r'"saldo"\]\s*=>\s*string\(\d+\)\s*"([^"]+)"', bloque)

            # ── Campos operativos ─────────────────────────────────
            mangueras  = re.search(r'mangueras:\s*(\d+)',                      bloque)
            carga_prom = re.search(r'carga promedio:\s*(\d+)',                 bloque)
            vehiculos  = re.search(r'cantidad de vehiculos:\s*([\d.]+)',       bloque)
            tiempo_mg  = re.search(r'tiempo de carga por manguera:\s*([\d.]+)',bloque)

            # ── Nombre desde HTML ─────────────────────────────────
            # Busca texto en mayúsculas que precede a "Volumen disponible"
            # Acepta nombres con espacios, tildes y Ñ
            nombre_raw = re.search(
                r'\n[ \t]*([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ\s\-\.]{2,}?)\s*\n+\s*Volumen',
                bloque, re.IGNORECASE
            )
            nombre_html = nombre_raw.group(1).strip() if nombre_raw else ""

            if not (saldo and fecha and un):
                continue

            unidad_id = un.group(1)
            nombre, fuente = resolve_nombre(unidad_id, nombre_html, tabla)

            if fuente == "nuevo":
                nuevos.append(unidad_id)
                print(f"[NUEVO] Estación desconocida detectada → unidad_id={unidad_id} | "
                      f"Agregar a estaciones.csv con su nombre comercial.")

            stations.append({
                "id_medicion":    id_med.group(1)         if id_med    else "",
                "unidad_id":      unidad_id,
                "estacion":       nombre,
                "fuente_nombre":  fuente,
                "fecha":          fecha.group(1),
                "saldo_lts":      int(saldo.group(1).replace(",", "")),
                "mangueras":      int(mangueras.group(1))   if mangueras  else 0,
                "carga_prom_lts": int(carga_prom.group(1))  if carga_prom else 40,
                "vehiculos_est":  float(vehiculos.group(1)) if vehiculos  else 0,
                "min_x_manguera": float(tiempo_mg.group(1)) if tiempo_mg  else 0,
                "scrape_ts":      datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            })

        except Exception as e:
            print(f"[WARN] Error parseando bloque: {e}")
            continue

    return stations, nuevos


def save_to_csv(records: list[dict], filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    file_exists = os.path.isfile(filepath)

    fieldnames = [
        "id_medicion", "unidad_id", "estacion", "fuente_nombre", "fecha",
        "saldo_lts", "mangueras", "carga_prom_lts",
        "vehiculos_est", "min_x_manguera", "scrape_ts"
    ]

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(records)

    print(f"[OK] {len(records)} registros guardados → {filepath}")


def check_alerts(records: list[dict], nuevos: list[str]):
    """Imprime resumen y alertas en consola (visible en el log de GitHub Actions)."""

    # Alertas de stock crítico
    criticas = [r for r in records if r["saldo_lts"] < UMBRAL_CRITICO]
    if criticas:
        print(f"\n⚠️  ALERTA STOCK — {len(criticas)} estación(es) bajo {UMBRAL_CRITICO} Lts:")
        for r in criticas:
            print(f"   🔴 {r['estacion']:20} | {r['saldo_lts']:>6,} Lts | ~{r['vehiculos_est']:.0f} vehículos")
    else:
        print("\n✅ Todas las estaciones sobre el umbral crítico.")

    # Alertas de estaciones nuevas
    if nuevos:
        print(f"\n🆕 ALERTA NUEVAS ESTACIONES — IDs sin mapear: {', '.join(nuevos)}")
        print("   → Identificar nombre comercial y agregar fila en estaciones.csv")

    # Resumen de red
    total_red = sum(r["saldo_lts"] for r in records)
    print(f"\n📊 Saldo total red Biopetrol: {total_red:,} Lts | {len(records)} estaciones\n")


def main():
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] Iniciando scrape Biopetrol...")

    tabla    = load_estaciones(ESTACIONES_CSV)
    html     = fetch_page(URL)
    records, nuevos = parse_stations(html, tabla)

    if not records:
        print("[ERROR] No se encontraron registros. Revisar estructura HTML.")
        raise SystemExit(1)

    save_to_csv(records, OUTPUT_CSV)
    check_alerts(records, nuevos)


if __name__ == "__main__":
    main()
