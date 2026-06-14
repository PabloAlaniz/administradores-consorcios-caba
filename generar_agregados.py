"""
Genera datasets agregados y anonimizados a partir del CSV crudo del scraper.

El CSV crudo (`administradores.csv`) contiene datos personales (nombre, CUIT,
domicilio) y NO se versiona ni se publica. Este script lo lee localmente y
produce únicamente agregados estadísticos (sin PII) en `data/agregados/`,
que son los que se publican y consume el notebook de análisis.

Uso:
    python generar_agregados.py [ruta_csv]   # default: administradores.csv
"""
import sys
import os
import pandas as pd

# Columnas con datos personales que NUNCA deben salir en los agregados.
PII_COLS = [
    'CUIT', 'RAZONSOCIAL', 'NRODOCUMENTO', 'TELEFONO', 'CELULAR',
    'CORREOELECTRONICO', 'CALLEADMINISTRADOR', 'ALTURAADMINISTRADOR',
    'PISOADMINISTRADOR', 'DEPARTAMENTOADMINISTRADOR', 'DOMICILIO',
    'DOMICILIOADMINISTRADOR',
]

OUTPUT_DIR = os.path.join('data', 'agregados')


def cargar_administradores(ruta_csv):
    """Carga el CSV crudo y deduplica a una fila por matrícula.

    El endpoint devuelve un par (administrador, consorcio) por fila, así que
    una misma matrícula aparece repetida. Para perfilar administradores nos
    quedamos con una fila por MATRICULAID.
    """
    df = pd.read_csv(ruta_csv)
    return df.drop_duplicates('MATRICULAID').reset_index(drop=True)


def _normalizar_si_no(serie):
    """Normaliza variantes 'Si'/'SI'/'No'/'NO' a 'Sí'/'No'."""
    mapa = {'si': 'Sí', 'no': 'No'}
    return serie.astype(str).str.strip().str.lower().map(mapa)


def estado_matricula(df):
    out = df['ESTADOMATRICULADESC'].value_counts(dropna=False).rename_axis('estado')
    return out.reset_index(name='cantidad')


def tipo_persona(df):
    out = df['TIPOPERSONADESC'].value_counts(dropna=False).rename_axis('tipo_persona')
    return out.reset_index(name='cantidad')


def onerosidad(df):
    out = _normalizar_si_no(df['ONEROSO']).value_counts(dropna=False).rename_axis('oneroso')
    return out.reset_index(name='cantidad')


def sanciones(df):
    out = _normalizar_si_no(df['TIENESANCIONES']).value_counts(dropna=False).rename_axis('tiene_sanciones')
    return out.reset_index(name='cantidad')


def distribucion_consorcios(df):
    """Distribución de cantidad de consorcios administrados por matrícula."""
    out = (df['CANTIDADCONSORCIOS']
           .value_counts()
           .sort_index()
           .rename_axis('cantidad_consorcios')
           .reset_index(name='administradores'))
    return out


def concentracion(df):
    """Métricas de concentración del mercado (qué % de consorcios concentra el top-N)."""
    s = df['CANTIDADCONSORCIOS'].sort_values(ascending=False).reset_index(drop=True)
    total_consorcios = int(s.sum())
    total_admins = len(s)
    filas = []
    for pct in (0.01, 0.05, 0.10):
        n = max(1, int(round(total_admins * pct)))
        filas.append({
            'top_pct': pct,
            'top_n_administradores': n,
            'consorcios_concentrados': int(s.head(n).sum()),
            'pct_del_total': round(s.head(n).sum() / total_consorcios * 100, 1),
        })
    filas.append({
        'top_pct': None,
        'top_n_administradores': total_admins,
        'consorcios_concentrados': total_consorcios,
        'pct_del_total': 100.0,
    })
    return pd.DataFrame(filas)


def altas_por_anio(df):
    anios = pd.to_datetime(df['FECHAALTA'], errors='coerce').dt.year
    out = anios.value_counts().sort_index().rename_axis('anio').reset_index(name='altas')
    out['anio'] = out['anio'].astype('Int64')
    return out.dropna(subset=['anio'])


def genero_estimado(df):
    """Estima género agregando por prefijo de CUIT (solo personas humanas).

    Convención AFIP: 20/23/24 -> masculino, 27 -> femenino, 30/33/34 -> jurídica.
    Es una *estimación* a nivel agregado; no se expone ningún CUIT individual.
    """
    humanas = df[df['TIPOPERSONADESC'] == 'HUMANA']
    prefijo = humanas['CUIT'].astype(str).str.replace(r'\D', '', regex=True).str[:2]
    mapa = {'20': 'Masculino', '23': 'Masculino', '24': 'Masculino', '27': 'Femenino'}
    genero = prefijo.map(mapa).fillna('Indeterminado')
    out = genero.value_counts().rename_axis('genero_estimado').reset_index(name='cantidad')
    return out


def _verificar_sin_pii(path):
    """Falla si algún agregado contiene columnas con PII."""
    cols = pd.read_csv(path, nrows=0).columns
    filtradas = [c for c in cols if c.upper() in {p.upper() for p in PII_COLS}]
    if filtradas:
        raise SystemExit(f'ERROR: {path} contiene columnas PII: {filtradas}')


def main(ruta_csv='administradores.csv'):
    if not os.path.exists(ruta_csv):
        raise SystemExit(
            f'No se encontró {ruta_csv}. Generalo primero con: python administradores_scraper.py'
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = cargar_administradores(ruta_csv)

    agregados = {
        'estado_matricula': estado_matricula(df),
        'tipo_persona': tipo_persona(df),
        'onerosidad': onerosidad(df),
        'sanciones': sanciones(df),
        'distribucion_consorcios': distribucion_consorcios(df),
        'concentracion': concentracion(df),
        'altas_por_anio': altas_por_anio(df),
        'genero_estimado': genero_estimado(df),
    }

    for nombre, tabla in agregados.items():
        path = os.path.join(OUTPUT_DIR, f'{nombre}.csv')
        tabla.to_csv(path, index=False, encoding='utf-8')
        _verificar_sin_pii(path)
        print(f'  ✓ {path} ({len(tabla)} filas)')

    print(f'\nListo: {len(df)} administradores únicos procesados → {OUTPUT_DIR}/')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'administradores.csv')
