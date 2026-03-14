# 🛢️ Biopetrol Monitor — Fase 1

Scraper automático de saldos de combustible Biopetrol Santa Cruz.
Corre en **GitHub Actions** (gratis) y guarda los datos en `data/saldos.csv`.

---

## Estructura del repositorio

```
biopetrol-monitor/
├── .github/
│   └── workflows/
│       └── scraper.yml      ← automatización en la nube
├── data/
│   └── saldos.csv           ← histórico acumulado (auto-generado)
├── scraper.py               ← lógica de scraping y alertas
├── requirements.txt
└── README.md
```

---

## Setup en 5 minutos

### 1. Crear el repositorio en GitHub
- Ir a https://github.com/new
- Nombre sugerido: `biopetrol-monitor`
- Visibilidad: **Private** (recomendado, los datos son públicos pero el repo no necesita serlo)
- Crear sin README (lo sobreescribimos)

### 2. Subir estos archivos
```bash
git init
git add .
git commit -m "feat: setup inicial biopetrol monitor"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/biopetrol-monitor.git
git push -u origin main
```

### 3. Activar Actions
- Ir a la pestaña **Actions** del repo
- Click en **"I understand my workflows, go ahead and enable them"**
- El workflow se ejecutará automáticamente según el horario definido

### 4. Primera prueba manual
- Pestaña **Actions** → *Biopetrol Scraper* → **Run workflow** → Run
- Verificar que el log muestre estaciones y que aparezca `data/saldos.csv`

---

## Columnas del CSV

| Columna | Descripción |
|---|---|
| `id_medicion` | ID único de la medición en la fuente |
| `unidad_id` | ID interno de la estación |
| `estacion` | Nombre de la estación |
| `fecha` | Timestamp de la medición (según la fuente) |
| `saldo_lts` | Litros disponibles al momento del scrape |
| `mangueras` | Número de mangueras activas |
| `carga_prom_lts` | Litros promedio por carga (~40 Lts) |
| `vehiculos_est` | Vehículos estimados que puede atender |
| `min_x_manguera` | Minutos por vehículo por manguera |
| `scrape_ts` | Timestamp de cuando corrió el scraper (UTC) |

---

## Ajustar el umbral de alerta

En `scraper.py`, línea 12:
```python
UMBRAL_CRITICO = 500  # Lts — cambiar según criterio
```

---

## Conectar a Power BI

1. Descargar `data/saldos.csv` desde GitHub (o usar la URL raw del archivo)
2. Power BI Desktop → **Obtener datos** → **Web**
3. URL raw: `https://raw.githubusercontent.com/TU_USUARIO/biopetrol-monitor/main/data/saldos.csv`
4. Configurar refresco programado cada hora

---

## Consumo estimado de GitHub Actions

- Frecuencia: cada 30 min × 17 horas/día = ~34 ejecuciones/día
- Duración por ejecución: ~1 minuto
- Total mensual: ~1,020 minutos → **dentro del free tier (2,000 min/mes)**
