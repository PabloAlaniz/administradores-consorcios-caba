# 🏢 Administradores de Consorcios de CABA — Scraper & Análisis de datos

[![CI](https://github.com/PabloAlaniz/Administradores-Consorcios/actions/workflows/ci.yml/badge.svg)](https://github.com/PabloAlaniz/Administradores-Consorcios/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Scraper en **Python** del [buscador oficial de administradores de consorcios](https://buscador-admin-consorcio.buenosaires.gob.ar/administradores)
del Gobierno de la Ciudad de Buenos Aires, con un **análisis exploratorio** de los ~5.700 administradores registrados.

> **Stack:** Python · requests · BeautifulSoup · pandas · matplotlib · seaborn · pytest

---

## 📊 Análisis de datos

A partir de los datos públicos se construyó un dataset de **5.671 administradores únicos**. El análisis
completo, reproducible y narrado está en
[`notebooks/analisis_administradores.ipynb`](notebooks/analisis_administradores.ipynb).
Algunos hallazgos:

### El mercado está muy concentrado

![Concentración del mercado](docs/img/concentracion.png)

El **top 5% de los administradores (≈284 personas) maneja cerca del 67% de todos los consorcios**.
La mayoría administra 0 o 1, mientras que un puñado supera los **100 consorcios** a cargo.

![Distribución de consorcios por administrador](docs/img/distribucion_consorcios.png)

### Boom de inscripciones desde 2018

![Altas por año](docs/img/altas_por_anio.png)

Las altas se disparan a partir de **2018** (pico en 2018–2019) y se mantienen altas aún durante la pandemia.

### Padrón inflado y perfil de la actividad

![Estado de la matrícula](docs/img/estado_matricula.png)

Más del **60% de las matrículas están "sin actualizar"** y ~68% no administra ningún consorcio. Además:
~80% cobra honorarios, solo el **1,9% registra sanciones**, y la actividad está **equilibrada por género**
(estimado por prefijo de CUIT).

> 🔒 **Privacidad:** el análisis usa exclusivamente datos **agregados y anonimizados**
> (`data/agregados/`). El dataset crudo contiene datos personales (nombre, CUIT, domicilio) y **no se
> versiona ni se publica** — se genera localmente y se descarta. Ver [Privacidad y datos](#-privacidad-y-datos).

---

## 🚀 Quick Start

```bash
# 1. Clonar e instalar
git clone https://github.com/PabloAlaniz/Administradores-Consorcios.git
cd Administradores-Consorcios
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Reproducir el análisis (sin scrapear: usa los agregados versionados)
jupyter notebook notebooks/analisis_administradores.ipynb
```

Para **regenerar la data desde cero**:

```bash
python administradores_scraper.py       # 1. scrapea  -> administradores.csv (local, gitignored)
python generar_agregados.py --snapshot  # 2. anonimiza -> data/agregados/ + snapshot del mes
python generar_evolutivo.py             # 3. consolida los snapshots -> data/evolutivo/
```

---

## 🔁 Pipeline de datos

```
buscador GCBA
     │  administradores_scraper.py  (requests + BeautifulSoup + pandas)
     ▼
administradores.csv          ← crudo, con PII, LOCAL y gitignored
     │  generar_agregados.py --snapshot  (dedup por matrícula + anonimización)
     ▼
data/agregados/*.csv         ← foto ACTUAL sin PII, versionada
data/snapshots/YYYY-MM/      ← cortes mensuales fechados (mismos agregados + metadata.json)
     │  generar_evolutivo.py  (consolida todos los cortes)
     ▼
data/evolutivo/*.csv         ← series de tiempo: KPIs por mes + dimensiones en formato largo
     │  notebooks/analisis_administradores.ipynb  (matplotlib + seaborn)
     ▼
docs/img/*.png + insights    ← gráficos para el README
```

---

## 📈 Evolutivo: snapshots mensuales

El padrón cambia todos los meses (altas, bajas, matrículas que se actualizan, sanciones nuevas).
Para poder analizar esa **evolución en el tiempo**, cada corrida puede guardar un **snapshot fechado**:

```bash
python generar_agregados.py --snapshot           # snapshot del mes actual
python generar_agregados.py --snapshot 2026-07   # o con fecha explícita
python generar_evolutivo.py                      # reconstruye data/evolutivo/
```

- `data/snapshots/YYYY-MM/` — los mismos agregados anonimizados de siempre, congelados a la fecha
  del corte, más un `metadata.json` con los totales.
- `data/evolutivo/resumen.csv` — un registro por snapshot con los KPIs principales (total de
  administradores, matrículas activas, concentración del top 5%, sanciones…) y su **variación
  contra el mes anterior** (`var_*`).
- `data/evolutivo/evolucion_*.csv` — cada dimensión categórica en formato largo
  (`snapshot, categoría, cantidad`), lista para graficar líneas de tendencia.

La captura mensual está automatizada con **GitHub Actions**
([`.github/workflows/snapshot-mensual.yml`](.github/workflows/snapshot-mensual.yml)): el día 1 de
cada mes scrapea el padrón, genera el snapshot y commitea solo los agregados sin PII (el CSV crudo
vive únicamente en el runner efímero y se descarta). También se puede disparar a mano desde la
pestaña *Actions* (`workflow_dispatch`).

---

## 🛠️ Estructura del proyecto

```
Administradores-Consorcios/
├── administradores_scraper.py   # Scraper modular (recomendado)
├── main.py                      # Versión monolítica original (legacy)
├── generar_agregados.py         # Anonimiza y agrega el CSV crudo (--snapshot para corte mensual)
├── generar_evolutivo.py         # Consolida los snapshots en series de tiempo
├── notebooks/
│   └── analisis_administradores.ipynb
├── data/
│   ├── agregados/               # Foto actual (sin PII, versionada)
│   ├── snapshots/YYYY-MM/       # Cortes mensuales fechados
│   └── evolutivo/               # Series de tiempo consolidadas
├── docs/img/                    # Gráficos generados por el notebook
├── tests/                       # Tests unitarios (pytest)
├── .github/workflows/ci.yml     # CI: ruff + pytest
├── requirements.txt
├── LICENSE
└── README.md
```

### Cómo funciona el scraper

El buscador del GCBA usa protección CSRF y responde vía un endpoint AJAX que devuelve JSON.
El flujo (`administradores_scraper.py`):

```python
csrf_token = get_csrf_token(url)              # 1. token CSRF del <meta> del HTML
data       = build_post_data(csrf_token)      # 2. payload de búsqueda
headers    = build_headers()                  # 3. headers que emulan un navegador
json_data  = fetch_administradores_data(...)  # 4. POST al endpoint
df         = process_data_to_dataframe(...)   # 5. JSON -> DataFrame (pd.json_normalize)
save_to_csv(df)                               # 6. export a CSV UTF-8
```

Cada fila del endpoint es un par *(administrador, consorcio)*, por lo que una matrícula aparece
repetida; `generar_agregados.py` deduplica por `MATRICULAID`.

---

## 🧪 Testing & CI

```bash
pytest                              # corre los tests
pytest --cov=. --cov-report=html    # con coverage
```

El repo tiene **CI en GitHub Actions** (`.github/workflows/ci.yml`) que ejecuta linting con `ruff` y la
suite de `pytest` en cada push.

---

## 🔒 Privacidad y datos

- La fuente es un **portal público** del GCBA; aun así, el dataset crudo compila datos personales
  (nombre, CUIT, domicilio) de miles de personas.
- Por respeto a la privacidad (y a la Ley 25.326 de Protección de Datos Personales), **este repo no
  publica el dataset crudo**: está excluido por `.gitignore` y purgado del historial de git.
- Solo se versionan **agregados estadísticos anonimizados** (`data/agregados/`), de los que es imposible
  reconstruir individuos.
- Campos de contacto (teléfono, email) y documento **no son expuestos por el endpoint público**, por lo
  que no forman parte del análisis.

**Uso educativo y de análisis de datos públicos.** No hacer scraping masivo que afecte el servicio del GCBA.

---

## 📄 Licencia

[MIT](LICENSE) © 2026 Pablo Alaniz

---

**Hecho por [@PabloAlaniz](https://github.com/PabloAlaniz)**
