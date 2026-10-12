"""
Genera datasets agregados y anonimizados a partir del CSV crudo del scraper.

El CSV crudo (`administradores.csv`) contiene datos personales (nombre, CUIT,
domicilio) y NO se versiona ni se publica. Este script lo lee localmente y
produce únicamente agregados estadísticos (sin PII) en `data/agregados/`,
que son los que se publican y consume el notebook de análisis.

Además de actualizar `data/agregados/` (la foto "actual"), puede guardar una
copia fechada en `data/snapshots/YYYY-MM/` para construir el análisis
evolutivo (ver `generar_evolutivo.py`).

Uso:
    python generar_agregados.py [ruta_csv]              # default: administradores.csv
    python generar_agregados.py --snapshot              # + snapshot del mes actual
    python generar_agregados.py --snapshot 2026-07      # + snapshot con fecha explícita
    python generar_agregados.py --snapshot --datos-abiertos registro_oficial.csv
                                                        # + cobertura vs BA Data

Generar un snapshot requiere la variable de entorno PANEL_HMAC_KEY.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
from datetime import date, datetime, timezone

import pandas as pd

import datos_abiertos

# Columnas con datos personales que NUNCA deben salir en los agregados.
PII_COLS = [
    'CUIT', 'RAZONSOCIAL', 'NRODOCUMENTO', 'TELEFONO', 'CELULAR',
    'CORREOELECTRONICO', 'CALLEADMINISTRADOR', 'ALTURAADMINISTRADOR',
    'PISOADMINISTRADOR', 'DEPARTAMENTOADMINISTRADOR', 'DOMICILIO',
    'DOMICILIOADMINISTRADOR',
]

# Clave del HMAC que seudonimiza las matrículas del panel. Vive como secret
# de GitHub; sin ella no se puede generar un snapshot (ver panel_matriculas).
ENV_CLAVE_PANEL = 'PANEL_HMAC_KEY'

OUTPUT_DIR = os.path.join('data', 'agregados')
SNAPSHOTS_DIR = os.path.join('data', 'snapshots')


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


def comuna_administrador(df):
    """Administradores por comuna (USIG) del domicilio del administrador.

    El campo lo carga el GCBA y hoy tiene poca cobertura; se agrega igual
    para poder seguir su evolución a medida que el padrón se actualiza.
    """
    if 'COMUNAUSIGADMINISTRADOR' not in df.columns:
        return None
    comuna = (df['COMUNAUSIGADMINISTRADOR'].fillna('').astype(str).str.strip()
              .replace('', 'Sin dato'))
    out = comuna.value_counts(dropna=False).rename_axis('comuna')
    return out.reset_index(name='cantidad')


def cp_administrador(df):
    """Administradores por código postal (4 dígitos) del domicilio del administrador."""
    if 'CPADMINISTRADOR' not in df.columns:
        return None
    cp = df['CPADMINISTRADOR'].astype(str).str.extract(r'(\d{4})', expand=False).fillna('Sin dato')
    out = cp.value_counts(dropna=False).rename_axis('codigo_postal')
    return out.reset_index(name='cantidad').sort_values('codigo_postal').reset_index(drop=True)


def barrio_administrador(df):
    """Administradores por barrio (USIG) del domicilio del administrador."""
    if 'BARRIOUSIGADMINISTRADOR' not in df.columns:
        return None
    barrio = (df['BARRIOUSIGADMINISTRADOR'].fillna('').astype(str).str.strip().str.upper()
              .replace('', 'Sin dato'))
    out = barrio.value_counts(dropna=False).rename_axis('barrio')
    return out.reset_index(name='cantidad')


def actualizaciones_por_mes(df):
    """Matrículas según el mes de su última actualización (renovación de la DDJJ).

    Muestra hasta cuándo el GCBA viene procesando renovaciones: si el último
    mes con actualizaciones queda quieto corte tras corte, las matrículas
    activas se van venciendo sin reemplazo.
    """
    if 'FECHAACTUALIZACION' not in df.columns:
        return None
    fechas = pd.to_datetime(df['FECHAACTUALIZACION'], errors='coerce')
    fechas = fechas[fechas.dt.year >= 2000]  # el padrón usa 1900-01-01 como "sin dato"
    out = (fechas.dt.to_period('M').astype(str).value_counts().sort_index()
           .rename_axis('mes').reset_index(name='matriculas'))
    return out


def _disposiciones(df):
    """Serie de listas de disposiciones (DI-AAAA-NNNN-GCABA-DGDYPC) por matrícula."""
    return (df['DISPOSICION'].fillna('').astype(str)
            .str.findall(r'DI-\d{4}-\d+-GCABA-[A-Z]+'))


def disposiciones_por_anio(df):
    """Disposiciones sancionatorias únicas por año de emisión."""
    if 'DISPOSICION' not in df.columns:
        return None
    unicas = pd.Series(sorted({d for lista in _disposiciones(df) for d in lista}), dtype=str)
    if unicas.empty:
        return pd.DataFrame({'anio': pd.Series(dtype='Int64'), 'disposiciones': pd.Series(dtype=int)})
    anios = unicas.str.extract(r'DI-(\d{4})-', expand=False).astype(int)
    return anios.value_counts().sort_index().rename_axis('anio').reset_index(name='disposiciones')


def disposiciones_por_administrador(df):
    """Cuántos sancionados tienen 1, 2, 3+ disposiciones vigentes en el buscador."""
    if 'DISPOSICION' not in df.columns:
        return None
    cantidad = _disposiciones(df).str.len()
    cantidad = cantidad[cantidad > 0].clip(upper=3)
    etiqueta = cantidad.map({1: '1', 2: '2', 3: '3+'})
    out = etiqueta.value_counts().sort_index().rename_axis('disposiciones').reset_index(name='administradores')
    return out


def hash_matricula(matricula, clave):
    """Seudónimo estable de una matrícula: HMAC-SHA256 truncado.

    Con un hash sin clave, las matrículas (enteros chicos y secuenciales) se
    recuperan por fuerza bruta en milisegundos. El HMAC con clave secreta lo
    impide mientras la clave no se publique.
    """
    return hmac.new(clave.encode('utf-8'), str(matricula).encode('utf-8'), hashlib.sha256).hexdigest()[:16]


def clave_panel():
    clave = os.environ.get(ENV_CLAVE_PANEL, '')
    if not clave:
        raise SystemExit(
            f'ERROR: falta la variable de entorno {ENV_CLAVE_PANEL} (clave del HMAC del panel). '
            'En CI es un secret del repo; localmente exportala antes de generar un snapshot.'
        )
    return clave


def panel_matriculas(df, clave):
    """Panel seudonimizado, una fila por matrícula, para calcular flujos entre cortes.

    La matrícula se publica como HMAC (ver `hash_matricula`). Solo se exponen
    atributos que ya son públicos en el buscador oficial (estado, cantidad de
    consorcios, sanciones, año de alta) — nunca nombre, CUIT ni domicilio. El
    seudónimo es estable entre snapshots, que es lo que permite calcular
    altas, bajas y transiciones de estado.
    """
    return pd.DataFrame({
        'matricula_hash': df['MATRICULAID'].map(lambda m: hash_matricula(m, clave)),
        'estado': df['ESTADOMATRICULADESC'].astype(str).str.strip(),
        'cantidad_consorcios': df['CANTIDADCONSORCIOS'].astype(int),
        'tiene_sanciones': _normalizar_si_no(df['TIENESANCIONES']),
        'anio_alta': pd.to_datetime(df['FECHAALTA'], errors='coerce').dt.year.astype('Int64'),
    }).reset_index(drop=True)


def _verificar_sin_pii(path):
    """Falla si algún agregado contiene columnas con PII."""
    cols = pd.read_csv(path, nrows=0).columns
    filtradas = [c for c in cols if c.upper() in {p.upper() for p in PII_COLS}]
    if filtradas:
        raise SystemExit(f'ERROR: {path} contiene columnas PII: {filtradas}')


def generar_agregados(df):
    """Devuelve el dict {nombre: DataFrame} con todos los agregados."""
    agregados = {
        'estado_matricula': estado_matricula(df),
        'tipo_persona': tipo_persona(df),
        'onerosidad': onerosidad(df),
        'sanciones': sanciones(df),
        'distribucion_consorcios': distribucion_consorcios(df),
        'concentracion': concentracion(df),
        'altas_por_anio': altas_por_anio(df),
        'genero_estimado': genero_estimado(df),
        # Geográficos: pueden faltar en CSVs crudos viejos sin esas columnas.
        'comuna_administrador': comuna_administrador(df),
        'cp_administrador': cp_administrador(df),
        'barrio_administrador': barrio_administrador(df),
        # Calendario de renovaciones y sanciones con número de disposición.
        'actualizaciones_por_mes': actualizaciones_por_mes(df),
        'disposiciones_por_anio': disposiciones_por_anio(df),
        'disposiciones_por_administrador': disposiciones_por_administrador(df),
    }
    return {nombre: tabla for nombre, tabla in agregados.items() if tabla is not None}


def escribir_agregados(agregados, output_dir):
    """Escribe cada agregado como CSV en `output_dir`, verificando que no haya PII."""
    os.makedirs(output_dir, exist_ok=True)
    for nombre, tabla in agregados.items():
        path = os.path.join(output_dir, f'{nombre}.csv')
        tabla.to_csv(path, index=False, encoding='utf-8')
        _verificar_sin_pii(path)
        print(f'  ✓ {path} ({len(tabla)} filas)')


def ultima_actualizacion(df):
    """Fecha (ISO) de la renovación más reciente registrada en el padrón, o None."""
    if 'FECHAACTUALIZACION' not in df.columns:
        return None
    fecha = pd.to_datetime(df['FECHAACTUALIZACION'], errors='coerce').max()
    return None if pd.isna(fecha) else fecha.date().isoformat()


def escribir_snapshot(agregados, df, snapshot, snapshots_dir=SNAPSHOTS_DIR, clave=None,
                      metadata_extra=None):
    """Guarda una copia fechada de los agregados en `data/snapshots/<snapshot>/`.

    Además escribe un `metadata.json` con los totales del corte, que usa
    `generar_evolutivo.py` para armar las series de tiempo.
    """
    if not re.fullmatch(r'\d{4}-\d{2}', snapshot):
        raise SystemExit(f"ERROR: snapshot inválido '{snapshot}' (formato esperado: YYYY-MM)")

    clave = clave or clave_panel()
    snapshot_dir = os.path.join(snapshots_dir, snapshot)
    escribir_agregados(agregados, snapshot_dir)

    # El panel pseudonimizado va solo en el snapshot (es propio de cada corte):
    # es lo que permite calcular flujos (altas/bajas/transiciones) entre meses.
    panel = panel_matriculas(df, clave)
    panel_path = os.path.join(snapshot_dir, 'matriculas.csv')
    panel.to_csv(panel_path, index=False, encoding='utf-8')
    _verificar_sin_pii(panel_path)
    print(f'  ✓ {panel_path} ({len(panel)} filas)')

    metadata = {
        'snapshot': snapshot,
        'generado': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'total_administradores': int(len(df)),
        'total_consorcios': int(df['CANTIDADCONSORCIOS'].sum()),
        'matricula_maxima': int(df['MATRICULAID'].max()),
        'ultima_actualizacion_padron': ultima_actualizacion(df),
        'fuente': 'buscador-admin-consorcio.buenosaires.gob.ar',
        **(metadata_extra or {}),
    }
    meta_path = os.path.join(snapshot_dir, 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f'  ✓ {meta_path}')
    return snapshot_dir


def agregados_cobertura(df, ruta_registro):
    """Agregados y metadata de la reconciliación contra el CSV de BA Data."""
    oficial, fecha_corte = datos_abiertos.cargar_registro(ruta_registro)
    matriculas = df['MATRICULAID']
    agregados = {
        'cobertura_por_tramo': datos_abiertos.cobertura_por_tramo(matriculas, oficial),
        'cobertura_por_anio_alta': datos_abiertos.cobertura_por_anio_alta(matriculas, oficial),
    }
    return agregados, datos_abiertos.resumen_cobertura(matriculas, oficial, fecha_corte)


def main(ruta_csv='administradores.csv', snapshot=None, ruta_registro=None):
    if not os.path.exists(ruta_csv):
        raise SystemExit(
            f'No se encontró {ruta_csv}. Generalo primero con: python administradores_scraper.py'
        )

    df = cargar_administradores(ruta_csv)
    agregados = generar_agregados(df)
    metadata_extra = {}
    if ruta_registro:
        cobertura, metadata_extra = agregados_cobertura(df, ruta_registro)
        agregados.update(cobertura)
    escribir_agregados(agregados, OUTPUT_DIR)

    if snapshot:
        snapshot_dir = escribir_snapshot(agregados, df, snapshot, metadata_extra=metadata_extra)
        print(f'\nSnapshot {snapshot} guardado en {snapshot_dir}/')

    print(f'\nListo: {len(df)} administradores únicos procesados → {OUTPUT_DIR}/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('ruta_csv', nargs='?', default='administradores.csv',
                        help='CSV crudo del scraper (default: administradores.csv)')
    parser.add_argument('--snapshot', nargs='?', const='__mes_actual__', default=None, metavar='YYYY-MM',
                        help='guarda además una copia fechada en data/snapshots/YYYY-MM/ '
                             '(sin valor: usa el mes actual)')
    parser.add_argument('--datos-abiertos', metavar='CSV', default=None,
                        help='CSV del registro oficial de BA Data (ver datos_abiertos.py) para '
                             'medir la cobertura del buscador')
    args = parser.parse_args()

    snapshot = args.snapshot
    if snapshot == '__mes_actual__':
        snapshot = date.today().strftime('%Y-%m')
    main(args.ruta_csv, snapshot=snapshot, ruta_registro=args.datos_abiertos)
