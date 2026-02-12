# Administradores de Consorcios - CABA Scraper

Scraper del buscador oficial de administradores de consorcios de la Ciudad de Buenos Aires.

## 📋 Descripción

Este script extrae datos del [buscador de administradores de consorcios](https://buscador-admin-consorcio.buenosaires.gob.ar/administradores) del Gobierno de la Ciudad de Buenos Aires (GCBA).

**Funcionalidad:**
- Obtiene el token CSRF del sitio
- Realiza búsquedas por matrícula
- Extrae datos de administradores en formato JSON
- Exporta resultados a CSV

## 🚀 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/PabloAlaniz/Administradores-Consorcios.git
cd Administradores-Consorcios

# Instalar dependencias
pip install -r requirements.txt
```

## 📦 Dependencias

- `requests` — HTTP requests
- `beautifulsoup4` — Parsing HTML
- `pandas` — Procesamiento de datos

## 💻 Uso

```bash
python main.py
```

El script generará un archivo `administradores.csv` con los datos extraídos.

### Personalizar búsqueda

Editar los parámetros del `data` dict en `main.py`:

```python
data = {
    'matricula': '3502',    # Matrícula a buscar
    'razonSocial': '',      # Razón social
    'nombre': '',           # Nombre
    'apellido': '',         # Apellido
    # ... otros filtros
}
```

## 📊 Estructura de datos

El CSV resultante incluye campos como:
- `MATRICULAID` — ID de matrícula
- `CUIT` — CUIT del administrador
- `RAZONSOCIAL` — Razón social
- `FECHAALTA` — Fecha de alta
- `DOMICILIOADMINISTRADOR` — Dirección
- `CANTIDADCONSORCIOS` — Cantidad de consorcios administrados
- Y más...

## 🔍 Notas

- El script incluye logging en nivel DEBUG
- Utiliza sesiones para manejar cookies automáticamente
- Headers configurados para emular navegador móvil

## ⚠️ Disclaimer

Este script es para uso educativo y de análisis de datos públicos. Respetar los términos de uso del sitio oficial del GCBA.

## 📝 TODO

- [ ] Agregar `pandas` a `requirements.txt`
- [ ] Parametrizar búsqueda via CLI args
- [ ] Agregar manejo de errores y reintentos
- [ ] Exportar a múltiples formatos (JSON, Excel)
- [ ] Tests unitarios

## 📄 Licencia

MIT

---

**Autor:** Pablo Alaniz  
**Repo:** https://github.com/PabloAlaniz/Administradores-Consorcios
