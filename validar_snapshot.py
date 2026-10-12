"""
Control de calidad de un snapshot antes de commitearlo.

Compara el snapshot nuevo contra el anterior y falla (exit 1) si algo indica
que el endpoint cambió o devolvió basura. El workflow mensual no commitea y
abre un issue cuando este script falla.

Uso:
    python validar_snapshot.py YYYY-MM
"""
import argparse
import json
import os
import sys

from generar_evolutivo import SNAPSHOTS_DIR, listar_snapshots

ARCHIVOS_REQUERIDOS = [
    'metadata.json', 'matriculas.csv', 'estado_matricula.csv', 'distribucion_consorcios.csv',
    'concentracion.csv', 'sanciones.csv',
]
# Caída o suba máxima tolerada del total de administradores entre cortes.
VARIACION_MAXIMA = 0.15


def _metadata(snapshots_dir, snapshot):
    with open(os.path.join(snapshots_dir, snapshot, 'metadata.json'), encoding='utf-8') as fh:
        return json.load(fh)


def validar(snapshot, snapshots_dir=SNAPSHOTS_DIR, variacion_maxima=VARIACION_MAXIMA):
    """Devuelve la lista de problemas encontrados (vacía si el snapshot está sano)."""
    directorio = os.path.join(snapshots_dir, snapshot)
    faltantes = [a for a in ARCHIVOS_REQUERIDOS if not os.path.exists(os.path.join(directorio, a))]
    if faltantes:
        return [f'faltan archivos en {directorio}: {faltantes}']

    problemas = []
    actual = _metadata(snapshots_dir, snapshot)
    total = actual.get('total_administradores') or 0
    if total == 0:
        problemas.append('el snapshot no tiene administradores')

    anteriores = [s for s in listar_snapshots(snapshots_dir) if s < snapshot]
    if anteriores and total:
        previo = _metadata(snapshots_dir, anteriores[-1])
        total_previo = previo.get('total_administradores') or 0
        if total_previo:
            variacion = (total - total_previo) / total_previo
            if abs(variacion) > variacion_maxima:
                problemas.append(
                    f'el total de administradores pasó de {total_previo} ({anteriores[-1]}) '
                    f'a {total} ({variacion:+.0%}), más que el ±{variacion_maxima:.0%} tolerado'
                )
    return problemas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('snapshot', help='snapshot a validar (YYYY-MM)')
    args = parser.parse_args(argv)
    problemas = validar(args.snapshot)
    for problema in problemas:
        print(f'✗ {problema}')
    if problemas:
        return 1
    print(f'✓ snapshot {args.snapshot} sano')
    return 0


if __name__ == '__main__':
    sys.exit(main())
