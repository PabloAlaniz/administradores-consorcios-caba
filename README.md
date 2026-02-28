# Administradores de Consorcios - CABA Scraper

Scraper del [buscador oficial de administradores de consorcios](https://buscador-admin-consorcio.buenosaires.gob.ar/administradores) de la Ciudad de Buenos Aires.

## 📋 ¿Qué es esto?

Este proyecto extrae datos del Gobierno de la Ciudad de Buenos Aires (GCBA) sobre administradores de consorcios registrados, convirtiendo datos públicos en formato estructurado (CSV/Pandas DataFrame) para análisis.

**Funcionalidad:**
- Extrae token CSRF dinámicamente del sitio
- Realiza búsquedas por matrícula, CUIT, razón social, nombre, apellido, dirección
- Procesa respuestas JSON de la API interna del buscador
- Exporta resultados a CSV con formato limpio
- Arquitectura modular y simple (monolítica)

**Casos de uso:**
- Análisis de mercado inmobiliario
- Verificación de administradores activos
- Auditorías de consorcios
- Investigación académica sobre gestión de consorcios

## 🚀 Quick Start

```bash
# 1. Clonar repositorio
git clone https://github.com/PabloAlaniz/Administradores-Consorcios.git
cd Administradores-Consorcios

# 2. Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar scraper
python administradores_scraper.py

# 5. Ver resultados
cat administradores.csv
# O abrirlo en Excel/LibreOffice
```

**Resultado:** archivo `administradores.csv` con datos de administradores.

### Primera búsqueda personalizada

Editar `administradores_scraper.py` en la función `build_post_data()`:

```python
def build_post_data(csrf_token, matricula='1234'):  # Cambiar matrícula aquí
    return {
        '_token': csrf_token,
        'matricula': matricula,  # Matrícula a buscar
        'razonSocial': '',       # O buscar por razón social
        'nombre': '',            # O por nombre
        'apellido': '',          # O por apellido
        # ... más filtros disponibles
    }
```

Luego ejecutar de nuevo:
```bash
python administradores_scraper.py
```

## 🛠️ Arquitectura

El proyecto incluye **dos versiones** del scraper:

### 1. `administradores_scraper.py` (Recomendado)

Versión refactorizada con funciones separadas para cada paso:

```python
# Flujo del scraper modular
csrf_token = get_csrf_token(url)              # 1. Obtener token
data = build_post_data(csrf_token)            # 2. Construir payload
headers = build_headers()                     # 3. Construir headers
json_data = fetch_administradores_data(...)   # 4. Fetch de datos
df = process_data_to_dataframe(json_data)     # 5. Procesar a DataFrame
filename = save_to_csv(df)                    # 6. Exportar CSV
```

**Ventajas:**
- ✅ Funciones pequeñas y testeables
- ✅ Fácil de mantener y extender
- ✅ Docstrings en todas las funciones
- ✅ Separación de responsabilidades

**Funciones principales:**
- `get_csrf_token(url)` — Extrae token CSRF del HTML con BeautifulSoup
- `build_post_data(csrf_token, matricula)` — Construye payload de búsqueda
- `build_headers()` — Headers HTTP que emulan navegador móvil
- `fetch_administradores_data(url, data, headers)` — POST a API interna
- `process_data_to_dataframe(data)` — Convierte JSON a DataFrame
- `save_to_csv(df, filename)` — Exporta DataFrame a CSV UTF-8

### 2. `main.py` (Legacy)

Versión monolítica original (todo en un archivo secuencial).

**Cuándo usar:**
- Scripts rápidos one-off
- Debugging visual del flujo completo
- Referencia de implementación simple

**⚠️ Recomendación:** usar `administradores_scraper.py` para desarrollo activo.

### Estructura del proyecto

```
Administradores-Consorcios/
├── administradores_scraper.py  # Scraper modular (recomendado)
├── main.py                     # Scraper monolítico (legacy)
├── requirements.txt            # Dependencias
├── tests/                      # Tests unitarios
│   ├── __init__.py
│   └── test_main.py
├── .coverage                   # Coverage report (gitignore)
├── administradores.csv         # Output generado (gitignore)
└── README.md
```

## 📊 Output Format

El scraper genera un archivo `administradores.csv` con los siguientes campos (extraídos del endpoint JSON del GCBA):

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `MATRICULAID` | int | ID único de matrícula | `3502` |
| `CUIT` | str | CUIT del administrador | `20-12345678-9` |
| `RAZONSOCIAL` | str | Razón social (empresa) | `Administración S.A.` |
| `NOMBRE` | str | Nombre (persona física) | `Juan` |
| `APELLIDO` | str | Apellido (persona física) | `Pérez` |
| `FECHAALTA` | str | Fecha de inscripción | `2020-03-15` |
| `DOMICILIOADMINISTRADOR` | str | Dirección completa | `Av. Corrientes 1234, CABA` |
| `TELEFONO` | str | Teléfono de contacto | `011-4567-8901` |
| `EMAIL` | str | Email de contacto | `admin@ejemplo.com` |
| `CANTIDADCONSORCIOS` | int | Consorcios administrados | `15` |

**Campos adicionales** (pueden variar según la respuesta de la API):
- `BARRIO` — Barrio del domicilio
- `CODIGOPOSTAL` — Código postal
- `OBSERVACIONES` — Notas adicionales

**Formato de export:**
- CSV UTF-8 sin BOM (compatible con Excel/LibreOffice)
- Header row incluida
- Sin index de pandas
- Separador: `,` (coma)

### Ejemplo de output

```csv
MATRICULAID,CUIT,RAZONSOCIAL,NOMBRE,APELLIDO,FECHAALTA,DOMICILIOADMINISTRADOR,CANTIDADCONSORCIOS
3502,20-12345678-9,Administración S.A.,Juan,Pérez,2020-03-15,Av. Corrientes 1234,15
3503,30-98765432-1,Consorcio Pro S.R.L.,María,González,2019-07-22,Av. Santa Fe 5678,8
```

## 📦 Dependencias

```bash
requests==2.31.0       # HTTP client (GET/POST a la API del GCBA)
beautifulsoup4==4.12.3 # Parsing HTML para extraer CSRF token
pandas==2.2.0          # Procesamiento de datos y export CSV
pytest==8.0.0          # Testing framework (dev dependency)
```

**Instalación:**
```bash
pip install -r requirements.txt
```

**Sin entorno virtual:**
```bash
pip install requests beautifulsoup4 pandas
```

## 🔧 Configuración

### Variables de entorno (opcional)

Por defecto, el scraper no requiere configuración. Para avanzado:

```bash
export GCBA_BASE_URL="https://buscador-admin-consorcio.buenosaires.gob.ar"
export LOG_LEVEL="DEBUG"  # DEBUG | INFO | WARNING | ERROR
export OUTPUT_FILE="mi_archivo.csv"
```

**Nota:** actualmente el scraper usa valores hardcoded. Para usar env vars, modificar `administradores_scraper.py`.

### Personalizar búsqueda

Todos los filtros disponibles están en `build_post_data()`:

```python
def build_post_data(csrf_token, matricula='3502'):
    return {
        '_token': csrf_token,
        'cuit': '',            # CUIT del administrador
        'matricula': matricula,# Matrícula (requerido o vacío)
        'tipo_filtro': '1',    # Tipo de búsqueda (1 = matrícula)
        'razonSocial': '',     # Razón social (empresa)
        'nombre': '',          # Nombre (persona física)
        'apellido': '',        # Apellido (persona física)
        'calle': '',           # Calle del domicilio
        'altura': '',          # Altura de la calle
        'cuitConsorcio': '',   # CUIT del consorcio
        'isadmin': 'False'     # Es admin (siempre False)
    }
```

**Búsqueda por razón social:**
```python
return {
    '_token': csrf_token,
    'matricula': '',
    'razonSocial': 'Administración S.A.',
    # ... resto vacío
}
```

**Búsqueda por apellido:**
```python
return {
    '_token': csrf_token,
    'apellido': 'Pérez',
    # ... resto vacío
}
```

## 🧪 Testing

El proyecto incluye tests unitarios con `pytest`:

```bash
# Ejecutar tests
pytest

# Con coverage
pytest --cov=. --cov-report=html

# Ver coverage report
open htmlcov/index.html
```

### Tests disponibles

```
tests/
└── test_main.py  # Tests del scraper monolítico (main.py)
```

**TODO:**
- [ ] Tests para `administradores_scraper.py`
- [ ] Mocks de requests HTTP
- [ ] Tests de integración con sitio real
- [ ] Coverage target: >80%

### Ejecutar tests manualmente

```python
# Test de extracción de CSRF token
from administradores_scraper import get_csrf_token
token = get_csrf_token('https://buscador-admin-consorcio.buenosaires.gob.ar/administradores')
print(f"Token: {token}")

# Test de construcción de headers
from administradores_scraper import build_headers
headers = build_headers()
assert 'User-Agent' in headers
assert 'X-Requested-With' in headers
```

## 🔍 Cómo funciona

### Paso 1: Extraer CSRF token

El sitio del GCBA usa protección CSRF. Antes de hacer POST, necesitamos extraer el token del HTML:

```python
# GET a la página principal
response = requests.get(url)

# Parsear HTML con BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Extraer token de meta tag
csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
```

### Paso 2: Construir POST request

El formulario del buscador envía datos vía POST AJAX:

```python
data = {
    '_token': csrf_token,  # Token CSRF extraído
    'matricula': '3502',   # Criterio de búsqueda
    # ... otros filtros
}

headers = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'X-Requested-With': 'XMLHttpRequest',  # AJAX request
    'User-Agent': 'Mozilla/5.0 ...',       # Emular navegador
    # ... otros headers
}
```

### Paso 3: Fetch de datos

```python
session = requests.Session()  # Mantiene cookies automáticamente
response = session.post(url_post, data=data, headers=headers)
json_data = json.loads(response.text)
```

**Respuesta JSON del GCBA:**
```json
{
  "Objeto": [
    {
      "MATRICULAID": 3502,
      "CUIT": "20-12345678-9",
      "RAZONSOCIAL": "Administración S.A.",
      // ... más campos
    }
  ]
}
```

### Paso 4: Procesar y exportar

```python
# Convertir JSON a DataFrame
df = pd.json_normalize(json_data['Objeto'])

# Exportar a CSV UTF-8
df.to_csv('administradores.csv', index=False, encoding='utf-8')
```

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'pandas'"

**Solución:**
```bash
pip install -r requirements.txt
```

Si persiste, instalar pandas manualmente:
```bash
pip install pandas
```

### Error: "KeyError: 'csrf-token'"

**Causa:** el sitio del GCBA cambió su estructura HTML.

**Solución:**
1. Verificar que el sitio esté accesible:
   ```bash
   curl https://buscador-admin-consorcio.buenosaires.gob.ar/administradores
   ```
2. Inspeccionar el HTML manualmente:
   ```python
   import requests
   from bs4 import BeautifulSoup
   
   response = requests.get('https://buscador-admin-consorcio.buenosaires.gob.ar/administradores')
   soup = BeautifulSoup(response.text, 'html.parser')
   print(soup.find('meta', {'name': 'csrf-token'}))
   ```
3. Ajustar el selector en `get_csrf_token()` si cambió la estructura.

### Error: "JSONDecodeError: Expecting value"

**Causa:** la API del GCBA retornó HTML de error en lugar de JSON.

**Solución:**
1. Verificar respuesta HTTP:
   ```python
   print(f"Status Code: {response.status_code}")
   print(f"Response Text: {response.text[:500]}")  # Primeros 500 chars
   ```
2. Verificar que headers sean correctos (emular navegador).
3. El sitio puede estar bloqueando requests (rate limiting).

### CSV vacío o sin resultados

**Causa:** la búsqueda no retornó resultados.

**Solución:**
- Cambiar criterio de búsqueda (matrícula, razón social, etc.)
- Verificar que la matrícula exista:
  ```bash
  # Buscar matrícula 1 (probablemente exista)
  # Editar build_post_data(csrf_token, matricula='1')
  python administradores_scraper.py
  ```

### Headers rechazan request (403/401)

**Causa:** headers no emulan correctamente un navegador.

**Solución:**
1. Inspeccionar request real del navegador (DevTools → Network → Headers)
2. Actualizar `build_headers()` con valores actuales
3. Verificar que `Referer`, `Origin`, `User-Agent` coincidan

### Timeout en requests

**Solución:**
```python
# En fetch_administradores_data(), agregar timeout
response = session.post(url_post, data=data, headers=headers, timeout=30)
```

## 💻 Uso Avanzado

### Búsqueda batch (múltiples matrículas)

```python
from administradores_scraper import *

url_get = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
url_post = url_get
csrf_token = get_csrf_token(url_get)

matriculas = ['1', '2', '3', '3502', '100']  # Lista de matrículas
all_results = []

for mat in matriculas:
    data = build_post_data(csrf_token, matricula=mat)
    headers = build_headers()
    json_data = fetch_administradores_data(url_post, data, headers)
    df = process_data_to_dataframe(json_data)
    all_results.append(df)
    print(f"Matrícula {mat}: {len(df)} resultados")

# Concatenar todos los DataFrames
import pandas as pd
final_df = pd.concat(all_results, ignore_index=True)
final_df.to_csv('administradores_batch.csv', index=False, encoding='utf-8')
print(f"Total: {len(final_df)} administradores")
```

### Exportar a Excel

```python
# Después de obtener el DataFrame
df.to_excel('administradores.xlsx', index=False, sheet_name='Administradores')
```

**Requiere:** `pip install openpyxl`

### Exportar a JSON

```python
# Exportar como JSON lines
df.to_json('administradores.jsonl', orient='records', lines=True, force_ascii=False)

# Exportar como JSON array
df.to_json('administradores.json', orient='records', force_ascii=False, indent=2)
```

### Rate limiting (buenas prácticas)

```python
import time

for mat in matriculas:
    # ... fetch data ...
    time.sleep(2)  # Esperar 2 segundos entre requests
```

Esto evita sobrecargar el servidor del GCBA y posibles bloqueos.

## 📚 Recursos

- **Sitio oficial:** [Buscador GCBA](https://buscador-admin-consorcio.buenosaires.gob.ar/administradores)
- **Documentación BeautifulSoup:** [crummy.com/software/BeautifulSoup/](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- **Documentación Pandas:** [pandas.pydata.org](https://pandas.pydata.org/docs/)
- **Requests docs:** [requests.readthedocs.io](https://requests.readthedocs.io/)

## 📝 Roadmap

- [x] Scraper funcional con búsqueda por matrícula
- [x] Export a CSV
- [x] Refactorización modular
- [x] Docstrings en funciones
- [x] Tests básicos
- [x] Actualizar `requirements.txt` (pandas incluido)
- [ ] CLI con argparse (búsqueda desde terminal)
- [ ] Manejo de errores robusto (reintentos, exponential backoff)
- [ ] Export a múltiples formatos (Excel, JSON, SQLite)
- [ ] Búsqueda batch automatizada
- [ ] Coverage >80%
- [ ] GitHub Actions CI/CD
- [ ] Logging configurable (archivo + consola)
- [ ] Scraper asíncrono (aiohttp)

## ⚠️ Disclaimer

Este proyecto es para **uso educativo y análisis de datos públicos**.

**Responsabilidades:**
- ✅ Los datos son públicos y accesibles en el sitio del GCBA
- ✅ No se accede a información privada o protegida
- ⚠️ Respetar términos de uso del sitio oficial
- ⚠️ No hacer scraping masivo que afecte el servicio

**Uso bajo tu propia responsabilidad.**

## 📄 Licencia

MIT License

Copyright (c) 2024 Pablo Alaniz

Se permite uso, copia, modificación y distribución con atribución.

## 🤝 Contribución

Contribuciones bienvenidas! Si tenés ideas o mejoras:

1. Fork el proyecto
2. Crea un branch (`git checkout -b feature/nueva-feature`)
3. Commit con convenciones (`git commit -m 'feat: nueva feature'`)
4. Push al branch (`git push origin feature/nueva-feature`)
5. Abre un Pull Request

### Reportar bugs

[Abrí un issue](https://github.com/PabloAlaniz/Administradores-Consorcios/issues) con:
- Descripción del bug
- Pasos para reproducir
- Output esperado vs actual
- Versión de Python y dependencias

---

**Hecho por [@PabloAlaniz](https://github.com/PabloAlaniz)**  
**Repo:** https://github.com/PabloAlaniz/Administradores-Consorcios
