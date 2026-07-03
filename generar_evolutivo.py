"""
Consolida los snapshots mensuales en series de tiempo para el análisis evolutivo.

Lee todos los cortes guardados en `data/snapshots/YYYY-MM/` (generados con
`python generar_agregados.py --snapshot`) y produce en `data/evolutivo/`:

- `resumen.csv`: un registro por snapshot con los KPIs principales
  (total de administradores, matrículas activas, concentración top 5%,
  sanciones, etc.) y su variación contra el snapshot anterior.
- `evolucion_<dimension>.csv`: series en formato largo (snapshot, categoría,
  cantidad) para cada dimensión categórica, listas para graficar.

Uso:
    python generar_evolutivo.py
"""
import json
import os
import re

import pandas as pd

SNAPSHOTS_DIR = os.path.join('data', 'snapshots')
OUTPUT_DIR = os.path.join('data', 'evolutivo')

# Dimensiones categóricas que se consolidan en formato largo:
# nombre del CSV -> (columna categoría, columna valor)
DIMENSIONES = {
    'estado_matricula': ('estado', 'cantidad'),
    'tipo_persona': ('tipo_persona', 'cantidad'),
    'onerosidad': ('oneroso', 'cantidad'),
    'sanciones': ('tiene_sanciones', 'cantidad'),
    'genero_estimado': ('genero_estimado', 'cantidad'),
    'distribucion_consorcios': ('cantidad_consorcios', 'administradores'),
}


def listar_snapshots(snapshots_dir=SNAPSHOTS_DIR):
    """Devuelve los nombres de snapshot (YYYY-MM) ordenados cronológicamente."""
    if not os.path.isdir(snapshots_dir):
        return []
    return sorted(
        d for d in os.listdir(snapshots_dir)
        if re.fullmatch(r'\d{4}-\d{2}', d) and os.path.isdir(os.path.join(snapshots_dir, d))
    )


def _leer_csv(snapshot_dir, nombre):
    path = os.path.join(snapshot_dir, f'{nombre}.csv')
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def _leer_metadata(snapshot_dir):
    path = os.path.join(snapshot_dir, 'metadata.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _valor_categoria(df, col_cat, categoria, col_valor):
    """Devuelve el valor de una categoría puntual, o 0 si no aparece en el corte."""
    if df is None:
        return None
    fila = df[df[col_cat].astype(str).str.strip().str.upper() == categoria.upper()]
    return int(fila[col_valor].sum()) if not fila.empty else 0


def _pct_top(concentracion, top_pct):
    if concentracion is None:
        return None
    fila = concentracion[concentracion['top_pct'] == top_pct]
    return float(fila['pct_del_total'].iloc[0]) if not fila.empty else None


def resumen_snapshot(snapshot, snapshot_dir):
    """Arma la fila de KPIs de un snapshot a partir de sus agregados."""
    meta = _leer_metadata(snapshot_dir)
    estado = _leer_csv(snapshot_dir, 'estado_matricula')
    sanciones = _leer_csv(snapshot_dir, 'sanciones')
    distribucion = _leer_csv(snapshot_dir, 'distribucion_consorcios')
    concentracion = _leer_csv(snapshot_dir, 'concentracion')

    total_admins = meta.get('total_administradores')
    if total_admins is None and estado is not None:
        total_admins = int(estado['cantidad'].sum())

    total_consorcios = meta.get('total_consorcios')
    if total_consorcios is None and concentracion is not None:
        total = concentracion[concentracion['top_pct'].isna()]
        if not total.empty:
            total_consorcios = int(total['consorcios_concentrados'].iloc[0])

    sin_consorcios = _valor_categoria(distribucion, 'cantidad_consorcios', '0', 'administradores')
    sancionados = _valor_categoria(sanciones, 'tiene_sanciones', 'Sí', 'cantidad')

    fila = {
        'snapshot': snapshot,
        'total_administradores': total_admins,
        'total_consorcios': total_consorcios,
        'matriculas_activas': _valor_categoria(estado, 'estado', 'ACTIVA', 'cantidad'),
        'matriculas_sin_actualizar': _valor_categoria(estado, 'estado', 'SIN ACTUALIZAR', 'cantidad'),
        'sancionados': sancionados,
        'sin_consorcios': sin_consorcios,
        'pct_top_1': _pct_top(concentracion, 0.01),
        'pct_top_5': _pct_top(concentracion, 0.05),
        'pct_top_10': _pct_top(concentracion, 0.10),
    }
    if total_admins:
        if sancionados is not None:
            fila['pct_sancionados'] = round(sancionados / total_admins * 100, 1)
        if sin_consorcios is not None:
            fila['pct_sin_consorcios'] = round(sin_consorcios / total_admins * 100, 1)
    return fila


def construir_resumen(snapshots, snapshots_dir=SNAPSHOTS_DIR):
    """Serie de KPIs por snapshot, con variaciones contra el corte anterior."""
    filas = [resumen_snapshot(s, os.path.join(snapshots_dir, s)) for s in snapshots]
    resumen = pd.DataFrame(filas)
    for col in ('total_administradores', 'total_consorcios', 'matriculas_activas'):
        if col in resumen.columns:
            resumen[f'var_{col}'] = resumen[col].diff().astype('Int64')
    return resumen


def construir_series(snapshots, snapshots_dir=SNAPSHOTS_DIR):
    """Series en formato largo por dimensión: {nombre: DataFrame(snapshot, cat, valor)}."""
    series = {}
    for nombre, (col_cat, col_valor) in DIMENSIONES.items():
        partes = []
        for snapshot in snapshots:
            df = _leer_csv(os.path.join(snapshots_dir, snapshot), nombre)
            if df is None or col_cat not in df.columns:
                continue
            parte = df[[col_cat, col_valor]].copy()
            parte.insert(0, 'snapshot', snapshot)
            partes.append(parte)
        if partes:
            series[f'evolucion_{nombre}'] = pd.concat(partes, ignore_index=True)
    return series


def main(snapshots_dir=SNAPSHOTS_DIR, output_dir=OUTPUT_DIR):
    snapshots = listar_snapshots(snapshots_dir)
    if not snapshots:
        raise SystemExit(
            f'No hay snapshots en {snapshots_dir}/. '
            'Generá el primero con: python generar_agregados.py --snapshot'
        )

    print(f'Snapshots encontrados: {", ".join(snapshots)}')
    os.makedirs(output_dir, exist_ok=True)

    tablas = {'resumen': construir_resumen(snapshots, snapshots_dir)}
    tablas.update(construir_series(snapshots, snapshots_dir))

    for nombre, tabla in tablas.items():
        path = os.path.join(output_dir, f'{nombre}.csv')
        tabla.to_csv(path, index=False, encoding='utf-8')
        print(f'  ✓ {path} ({len(tabla)} filas)')

    if len(snapshots) < 2:
        print('\nNota: hay un solo snapshot; el evolutivo cobra sentido a partir del segundo corte mensual.')
    print(f'\nListo: {len(snapshots)} snapshots consolidados → {output_dir}/')


if __name__ == '__main__':
    main()
