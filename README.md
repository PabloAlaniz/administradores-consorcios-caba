# 🏢 Administradores de Consorcios de CABA — Scraper & Análisis de datos

[![CI](https://github.com/PabloAlaniz/Administradores-Consorcios/actions/workflows/ci.yml/badge.svg)](https://github.com/PabloAlaniz/Administradores-Consorcios/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Scraper en **Python** del [buscador oficial de administradores de consorcios](https://buscador-admin-consorcio.buenosaires.gob.ar/administradores)
del Gobierno de la Ciudad de Buenos Aires, con un **análisis exploratorio** de los ~3.900 administradores
registrados (corte julio 2026) y un **evolutivo** con snapshots mensuales del padrón.

> **Stack:** Python · requests · BeautifulSoup · pandas · matplotlib · seaborn · pytest

---

## 📊 Análisis de datos

A partir de los datos públicos se construyó un dataset de **3.856 administradores únicos**
(corte **julio 2026**, verificado con un doble check contra el endpoint: devuelve el padrón
completo, sin paginación, estable entre requests). El análisis completo, reproducible y narrado
está en [`notebooks/analisis_administradores.ipynb`](notebooks/analisis_administradores.ipynb).

> 📉 **El padrón se achicó un tercio desde 2024.** El análisis original (corte ~marzo 2024)
> registraba 5.671 administradores. La historia completa del cambio, con hipótesis y evidencia,
> está en la sección [Evolutivo](#-evolutivo-snapshots-mensuales).

Algunos hallazgos del corte de julio 2026:

### Concentración moderada (según el endpoint actual)

![Concentración del mercado](docs/img/concentracion.png)

El **top 5% de los administradores (≈193 personas) maneja el 28,8% de los consorcios** y nadie
supera los **6** a cargo. El corte de 2024 mostraba otra escala (top 5% = 67%, administradores con
+100 consorcios): un cambio tan drástico sugiere que el campo `CANTIDADCONSORCIOS` del endpoint
cambió de semántica — está documentado en el evolutivo.

![Distribución de consorcios por administrador](docs/img/distribucion_consorcios.png)

### El boom de inscripciones se mudó a 2021–2024

![Altas por año](docs/img/altas_por_anio.png)

Las altas se aceleran desde **2021** y tocan su máximo en **2024** (595). En 2025 se frenan (237)
y **2026 aún no registra altas** pese a que el padrón tiene actualizaciones hasta mayo 2026.
Ojo con el sesgo de supervivencia: las cohortes viejas están subrepresentadas porque el corte
actual ya no incluye a quienes salieron del padrón.

### Padrón depurado pero aún inflado

![Estado de la matrícula](docs/img/estado_matricula.png)

El **72% de las matrículas están "sin actualizar"** y ~68% no administra ningún consorcio. Además:
~84% cobra honorarios, solo el **1,3% registra sanciones**, y la actividad está **equilibrada por
género con leve mayoría femenina** (estimado por prefijo de CUIT; en 2024 la mayoría era masculina).

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
python administradores_scraper.py         # 1. scrapea  -> administradores.csv (local, gitignored)
python generar_agregados.py --snapshot    # 2. anonimiza -> data/agregados/ + snapshot del mes
python generar_evolutivo.py               # 3. consolida los snapshots -> data/evolutivo/
python generar_graficos_evolutivo.py      # 4. gráficos de tendencia -> docs/img/evolucion_*.png
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
data/snapshots/YYYY-MM/      ← cortes mensuales fechados (agregados + panel pseudonimizado + metadata)
     │  generar_evolutivo.py  (consolida todos los cortes)
     ▼
data/evolutivo/*.csv + .md   ← series de tiempo, flujos, Gini/HHI y reporte mensual narrado
     │  generar_graficos_evolutivo.py / notebook  (matplotlib + seaborn)
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
python generar_graficos_evolutivo.py             # gráficos de tendencia en docs/img/
```

**Qué guarda cada snapshot** (`data/snapshots/YYYY-MM/`):

- Los agregados anonimizados de siempre, congelados a la fecha del corte, más un `metadata.json`
  con los totales.
- Dimensión **geográfica**: administradores por comuna (USIG) y por código postal del domicilio
  del administrador. La comuna todavía tiene poca cobertura en el padrón oficial; el CP cubre ~94%,
  y el evolutivo permite ver cómo mejora esa cobertura con el tiempo.
- `matriculas.csv`: un **panel pseudonimizado** (matrícula hasheada + estado + cantidad de
  consorcios + sanciones — todos atributos ya públicos en el buscador oficial; nunca nombre,
  CUIT ni domicilio). Es lo que permite calcular flujos reales entre meses.

**Qué produce el evolutivo** (`data/evolutivo/`):

- `resumen.csv` — un registro por snapshot con los KPIs principales (total de administradores,
  matrículas activas, concentración del top 1/5/10%, **índices de Gini y HHI**, sanciones…) y su
  **variación contra el mes anterior** (`var_*`). Gini y HHI se calculan desde la distribución
  agregada, así que funcionan retroactivamente para todos los snapshots.
- `flujos.csv` — movimientos **brutos** entre cortes consecutivos: altas y bajas del padrón,
  matrículas que se activaron o desactivaron, sancionados nuevos y administradores que ganaron
  o perdieron consorcios. Un +20 neto puede ser 25 altas y 5 bajas: esto lo hace visible.
- `evolucion_*.csv` — cada dimensión categórica (estado, tipo de persona, comuna, CP…) en formato
  largo (`snapshot, categoría, cantidad`), lista para graficar líneas de tendencia.
- `reporte_YYYY-MM.md` — **reporte narrado** del último corte con todas las variaciones,
  regenerado en cada corrida.

**Gráficos de tendencia**: `generar_graficos_evolutivo.py` produce `docs/img/evolucion_padron.png`
y `docs/img/evolucion_concentracion.png` a partir del resumen (con un solo snapshot son puntos;
las líneas aparecen a medida que se acumulan cortes).

### 🔍 El evolutivo en acción: el padrón se achicó un tercio entre 2024 y 2026

El primer corte scrapeado en vivo (julio 2026) devolvió un padrón **muy** distinto al del análisis
original. Lejos de esconder la discrepancia, es exactamente el tipo de cambio que este sistema
existe para registrar — ambos cortes están versionados como snapshots y el salto queda a la vista:

| Métrica | ~2024-03 | 2026-07 | Δ |
|---|---:|---:|---:|
| Administradores registrados | 5.671 | 3.856 | **−1.815 (−32%)** |
| Consorcios informados | 7.744 | 1.560 | **−6.184** |
| Matrículas activas | 2.184 | 1.071 | −1.113 |
| Máx. consorcios por administrador | 100+ | 6 | — |
| Top 5% concentra | 67,4% | 28,8% | −38,6 pp |

![Evolución del padrón](docs/img/evolucion_padron.png)

**El doble check que hicimos antes de creer los números:**

- El corte de julio 2026 se verificó contra el endpoint: **ignora todos los filtros del payload**
  y devuelve siempre el padrón completo — 3.856 matrículas únicas, sin paginación, estable en
  5 requests consecutivos. El número es real, no un truncamiento.
- La fecha del corte original estaba mal atribuida: el dataset entró al repo en junio 2026, pero
  la distribución de altas lo delata — su cohorte 2024 estaba ~19% completa (115 de 595 altas) y
  2025 no existía. **El scrape original es de ~marzo 2024**, así que la caída ocurrió a lo largo
  de ~2 años, no de un mes.

**Qué muestra la evidencia:**

1. **Depuración gradual del padrón**: la pérdida se concentra en las cohortes 2010–2020
   (−50/65%), mientras las recientes (2021–2023) apenas pierden 9–16% — consistente con bajas
   por falta de renovación anual acumuladas en dos años.
2. **Cambio de semántica del endpoint**: la respuesta pasó de pares *(administrador, consorcio)*
   a una fila por administrador, y `CANTIDADCONSORCIOS` cambió de escala (máx. 6 vs +100), algo
   que la depuración sola no explica — posiblemente ahora cuente solo consorcios con declaración
   vigente.

La política del repo es **documentar lo observado tal cual**: cada snapshot lleva su `nota`
metodológica en `metadata.json`, que se propaga automáticamente al reporte mensual
([`reporte_2026-07.md`](data/evolutivo/reporte_2026-07.md)). Los próximos cortes mensuales van a
mostrar si los números se estabilizan en el nuevo nivel o siguen moviéndose.

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
├── generar_evolutivo.py         # Series de tiempo, flujos, Gini/HHI y reporte mensual
├── generar_graficos_evolutivo.py # Gráficos de tendencia desde el evolutivo
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
