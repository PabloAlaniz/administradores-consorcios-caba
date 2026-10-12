"""
Migración única de los paneles de matrículas: SHA-256 sin clave → HMAC.

Los snapshots anteriores a esta migración publicaban `matricula_hash` como
SHA-256 truncado del número de matrícula, reversible por fuerza bruta. Este
script recupera la matrícula de cada hash viejo (justamente por fuerza bruta,
dentro del runner o la máquina local) y la vuelve a seudonimizar con
`generar_agregados.hash_matricula`, para no cortar la continuidad de los flujos.

Los hashes viejos siguen en el historial de git: la migración protege los
cortes nuevos, no los ya publicados.

Uso (una sola vez, con la misma clave que el secret del repo):
    PANEL_HMAC_KEY=... python migrar_panel_hmac.py
"""
import glob
import hashlib
import os

import pandas as pd

from generar_agregados import SNAPSHOTS_DIR, clave_panel, hash_matricula

MATRICULA_MAXIMA = 100_000


def hash_viejo(matricula):
    return hashlib.sha256(str(matricula).encode('utf-8')).hexdigest()[:16]


def indice_inverso(maximo=MATRICULA_MAXIMA):
    return {hash_viejo(m): m for m in range(1, maximo)}


def migrar_panel(path, clave, inverso):
    """Reescribe un matriculas.csv. Devuelve False si ya estaba migrado."""
    panel = pd.read_csv(path, dtype={'matricula_hash': str})
    matriculas = panel['matricula_hash'].map(inverso)
    if matriculas.isna().all():
        return False
    if matriculas.isna().any():
        raise SystemExit(f'ERROR: {path} mezcla hashes viejos y nuevos ({matriculas.isna().sum()} sin resolver)')
    panel['matricula_hash'] = matriculas.astype(int).map(lambda m: hash_matricula(m, clave))
    panel.to_csv(path, index=False, encoding='utf-8')
    return True


def main(snapshots_dir=SNAPSHOTS_DIR):
    clave = clave_panel()
    inverso = indice_inverso()
    for path in sorted(glob.glob(os.path.join(snapshots_dir, '*', 'matriculas.csv'))):
        estado = 'migrado' if migrar_panel(path, clave, inverso) else 'ya estaba migrado'
        print(f'  ✓ {path}: {estado}')


if __name__ == '__main__':
    main()
