"""
Consolida los snapshots mensuales en series de tiempo para el análisis evolutivo.

Lee todos los cortes guardados en `data/snapshots/YYYY-MM/` (generados con
`python generar_agregados.py --snapshot`) y produce en `data/evolutivo/`:

- `resumen.csv`: un registro por snapshot con los KPIs principales
  (total de administradores, matrículas activas, concentración top 5%,
  índices Gini y HHI, sanciones, etc.) y su variación contra el snapshot
  anterior.
- `evolucion_<dimension>.csv`: series en formato largo (snapshot, categoría,
  cantidad) para cada dimensión categórica, listas para graficar.
- `flujos.csv`: altas, bajas y transiciones de estado entre cortes
  consecutivos, calculadas a partir del panel pseudonimizado
  (`matriculas.csv`) de cada snapshot.
- `reporte_YYYY-MM.md`: reporte narrado del último corte, con las
  variaciones contra el mes anterior.

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
    'comuna_administrador': ('comuna', 'cantidad'),
    'cp_administrador': ('codigo_postal', 'cantidad'),
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


def gini_desde_distribucion(distribucion):
    """Índice de Gini (0 = reparto igualitario, 1 = un solo administrador con todo).

    Se calcula desde la distribución agrupada (cantidad_consorcios,
    administradores), por lo que funciona retroactivamente para cualquier
    snapshot ya guardado.
    """
    if distribucion is None or distribucion.empty:
        return None
    d = distribucion.sort_values('cantidad_consorcios')
    v = d['cantidad_consorcios'].astype(float).to_numpy()
    w = d['administradores'].astype(float).to_numpy()
    n = w.sum()
    total = (v * w).sum()
    if n == 0 or total == 0:
        return None
    # Suma de rank*valor con datos agrupados: dentro de un grupo los rangos
    # son consecutivos, así que se usa el rango medio del grupo.
    cum_w_prev = w.cumsum() - w
    suma_rangos = (v * w * (cum_w_prev + (w + 1) / 2)).sum()
    gini = 2 * suma_rangos / (n * total) - (n + 1) / n
    return round(float(gini), 4)


def hhi_desde_distribucion(distribucion):
    """Índice Herfindahl-Hirschman (0–10.000) sobre el share de consorcios por administrador."""
    if distribucion is None or distribucion.empty:
        return None
    v = distribucion['cantidad_consorcios'].astype(float)
    w = distribucion['administradores'].astype(float)
    total = (v * w).sum()
    if total == 0:
        return None
    hhi = (w * (v / total) ** 2).sum() * 10_000
    return round(float(hhi), 1)


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
        'gini': gini_desde_distribucion(distribucion),
        'hhi': hhi_desde_distribucion(distribucion),
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


def _leer_panel(snapshots_dir, snapshot):
    df = _leer_csv(os.path.join(snapshots_dir, snapshot), 'matriculas')
    if df is None:
        return None
    return df.set_index('matricula_hash')


def flujos_entre(panel_ant, panel_act):
    """Flujos brutos entre dos paneles consecutivos de matrículas."""
    ant, act = set(panel_ant.index), set(panel_act.index)
    comunes = list(ant & act)
    a, b = panel_ant.loc[comunes], panel_act.loc[comunes]

    era_activa = a['estado'].str.upper() == 'ACTIVA'
    es_activa = b['estado'].str.upper() == 'ACTIVA'
    delta_consorcios = b['cantidad_consorcios'] - a['cantidad_consorcios']

    return {
        'altas': len(act - ant),
        'bajas': len(ant - act),
        'activaciones': int((~era_activa & es_activa).sum()),
        'desactivaciones': int((era_activa & ~es_activa).sum()),
        'sancionados_nuevos': int(((a['tiene_sanciones'] != 'Sí') & (b['tiene_sanciones'] == 'Sí')).sum()),
        'ganaron_consorcios': int((delta_consorcios > 0).sum()),
        'perdieron_consorcios': int((delta_consorcios < 0).sum()),
        'consorcios_netos': int(delta_consorcios.sum()),
    }


def construir_flujos(snapshots, snapshots_dir=SNAPSHOTS_DIR):
    """Flujos para cada par de snapshots consecutivos que tengan panel de matrículas.

    Devuelve None si ningún par lo tiene (p. ej. snapshots viejos, anteriores
    a la incorporación del panel).
    """
    filas = []
    for anterior, actual in zip(snapshots, snapshots[1:]):
        panel_ant = _leer_panel(snapshots_dir, anterior)
        panel_act = _leer_panel(snapshots_dir, actual)
        if panel_ant is None or panel_act is None:
            continue
        filas.append({'snapshot': actual, 'vs_snapshot': anterior,
                      **flujos_entre(panel_ant, panel_act)})
    return pd.DataFrame(filas) if filas else None


def _fmt_delta(actual, anterior, sufijo='', vs='corte anterior'):
    if actual is None or anterior is None or pd.isna(actual) or pd.isna(anterior):
        return ''
    delta = actual - anterior
    signo = '+' if delta >= 0 else ''
    return f' ({signo}{delta:g}{sufijo} vs {vs})'


def generar_reporte(resumen, flujos, output_dir, nota=None):
    """Escribe reporte_<ultimo-snapshot>.md con el diff narrado del último corte.

    Si el snapshot tiene una nota metodológica en su metadata.json (p. ej. un
    cambio observado en el endpoint), se incluye en el reporte para que la
    advertencia viaje junto con el dato.
    """
    actual = resumen.iloc[-1]
    anterior = resumen.iloc[-2] if len(resumen) > 1 else None

    def delta(col, sufijo=''):
        return _fmt_delta(actual.get(col), anterior.get(col) if anterior is not None else None,
                          sufijo, vs=f"corte {anterior['snapshot']}" if anterior is not None else '')

    lineas = [
        f"# Reporte del padrón — {actual['snapshot']}",
        '',
        f"- **Administradores registrados:** {actual['total_administradores']:g}{delta('total_administradores')}",
        f"- **Consorcios administrados:** {actual['total_consorcios']:g}{delta('total_consorcios')}",
        f"- **Matrículas activas:** {actual['matriculas_activas']:g}{delta('matriculas_activas')}",
        f"- **Sin actualizar:** {actual['matriculas_sin_actualizar']:g}{delta('matriculas_sin_actualizar')}",
        f"- **Con sanciones:** {actual['sancionados']:g}{delta('sancionados')}",
        '',
        '## Concentración del mercado',
        '',
        f"- Top 5% concentra el **{actual['pct_top_5']:g}%** de los consorcios{delta('pct_top_5', ' pp')}",
        f"- Índice de Gini: **{actual['gini']:g}**{delta('gini')}",
        f"- HHI: **{actual['hhi']:g}**{delta('hhi')}",
    ]

    if flujos is not None and flujos.iloc[-1]['snapshot'] == actual['snapshot']:
        f = flujos.iloc[-1]
        lineas += [
            '',
            f"## Flujos del mes (vs {f['vs_snapshot']})",
            '',
            f"- Altas al padrón: **{f['altas']}** · Bajas: **{f['bajas']}**",
            f"- Matrículas que se activaron: **{f['activaciones']}** · que dejaron de estar activas: **{f['desactivaciones']}**",
            f"- Sancionados nuevos: **{f['sancionados_nuevos']}**",
            f"- Administradores que ganaron consorcios: **{f['ganaron_consorcios']}** · que perdieron: **{f['perdieron_consorcios']}** (neto: {f['consorcios_netos']:+d})",
        ]

    if nota:
        lineas += ['', '## Nota metodológica', '', f'> {nota}']

    if anterior is None:
        lineas += ['', '_Primer corte disponible: las variaciones aparecerán a partir del próximo snapshot._']

    lineas += ['', '---', '_Generado automáticamente por `generar_evolutivo.py` a partir de datos agregados y anonimizados._', '']
    path = os.path.join(output_dir, f"reporte_{actual['snapshot']}.md")
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lineas))
    return path


def main(snapshots_dir=SNAPSHOTS_DIR, output_dir=OUTPUT_DIR):
    snapshots = listar_snapshots(snapshots_dir)
    if not snapshots:
        raise SystemExit(
            f'No hay snapshots en {snapshots_dir}/. '
            'Generá el primero con: python generar_agregados.py --snapshot'
        )

    print(f'Snapshots encontrados: {", ".join(snapshots)}')
    os.makedirs(output_dir, exist_ok=True)

    resumen = construir_resumen(snapshots, snapshots_dir)
    tablas = {'resumen': resumen}
    tablas.update(construir_series(snapshots, snapshots_dir))

    flujos = construir_flujos(snapshots, snapshots_dir)
    if flujos is not None:
        tablas['flujos'] = flujos

    for nombre, tabla in tablas.items():
        path = os.path.join(output_dir, f'{nombre}.csv')
        tabla.to_csv(path, index=False, encoding='utf-8')
        print(f'  ✓ {path} ({len(tabla)} filas)')

    nota = _leer_metadata(os.path.join(snapshots_dir, snapshots[-1])).get('nota')
    reporte = generar_reporte(resumen, flujos, output_dir, nota=nota)
    print(f'  ✓ {reporte}')

    if len(snapshots) < 2:
        print('\nNota: hay un solo snapshot; el evolutivo cobra sentido a partir del segundo corte mensual.')
    print(f'\nListo: {len(snapshots)} snapshots consolidados → {output_dir}/')


if __name__ == '__main__':
    main()
