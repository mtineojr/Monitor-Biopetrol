"""
fix_nombres.py
--------------
Script de ejecución única para corregir filas con estacion="UN-XXX (NUEVO)"
en data/saldos.csv usando la tabla estaciones.csv como referencia.

Uso:
    python fix_nombres.py

El script sobreescribe data/saldos.csv en el mismo lugar.
Genera una copia de respaldo en data/saldos_backup.csv antes de modificar.
"""

import csv
import os
import shutil
from datetime import datetime

SALDOS_CSV     = "data/saldos.csv"
ESTACIONES_CSV = "estaciones.csv"
BACKUP_CSV     = "data/saldos_backup.csv"


def load_estaciones(filepath: str) -> dict:
    tabla = {}
    with open(filepath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tabla[row["unidad_id"].strip()] = row["nombre"].strip()
    print(f"[OK] Tabla cargada: {len(tabla)} estaciones.")
    return tabla


def fix_nombres(saldos_path: str, backup_path: str, tabla: dict):
    # Backup antes de tocar nada
    shutil.copy2(saldos_path, backup_path)
    print(f"[OK] Backup guardado → {backup_path}")

    rows_total    = 0
    rows_fixed    = 0
    rows_no_map   = 0

    with open(saldos_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    for row in rows:
        rows_total += 1
        estacion = row.get("estacion", "")

        # Solo procesar filas con nombre sin resolver
        if "(NUEVO)" in estacion or estacion.startswith("UN-"):
            unidad_id = row.get("unidad_id", "").strip()
            if unidad_id in tabla:
                row["estacion"] = tabla[unidad_id]
                rows_fixed += 1
            else:
                rows_no_map += 1

    # Sobreescribir el CSV con los nombres corregidos
    with open(saldos_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n📊 Resumen:")
    print(f"   Total filas procesadas : {rows_total}")
    print(f"   ✅ Nombres corregidos   : {rows_fixed}")
    print(f"   ⚠️  Sin mapeo (revisar) : {rows_no_map}")
    if rows_no_map > 0:
        print(f"   → Agregar esos unidad_id a estaciones.csv y volver a correr.")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando fix de nombres...\n")

    if not os.path.isfile(SALDOS_CSV):
        print(f"[ERROR] No se encontró {SALDOS_CSV}")
        raise SystemExit(1)

    if not os.path.isfile(ESTACIONES_CSV):
        print(f"[ERROR] No se encontró {ESTACIONES_CSV}")
        raise SystemExit(1)

    tabla = load_estaciones(ESTACIONES_CSV)
    fix_nombres(SALDOS_CSV, BACKUP_CSV, tabla)
    print(f"\n[OK] {SALDOS_CSV} actualizado correctamente.")


if __name__ == "__main__":
    main()
