"""Tests del control de calidad del snapshot y de la migración al HMAC."""
import hashlib
import json

import pandas as pd

import generar_agregados
import migrar_panel_hmac
import validar_snapshot


def _snapshot(directorio, nombre, total):
    d = directorio / nombre
    d.mkdir(parents=True)
    for archivo in validar_snapshot.ARCHIVOS_REQUERIDOS:
        (d / archivo).write_text('x\n', encoding='utf-8')
    (d / 'metadata.json').write_text(json.dumps({'total_administradores': total}), encoding='utf-8')


def test_snapshot_sano(tmp_path):
    _snapshot(tmp_path, '2026-09', 3836)
    _snapshot(tmp_path, '2026-10', 3829)
    assert validar_snapshot.validar('2026-10', str(tmp_path)) == []


def test_caida_brusca_falla(tmp_path):
    _snapshot(tmp_path, '2026-09', 3836)
    _snapshot(tmp_path, '2026-10', 1000)
    problemas = validar_snapshot.validar('2026-10', str(tmp_path))
    assert len(problemas) == 1 and '3836' in problemas[0]


def test_archivos_faltantes_fallan(tmp_path):
    _snapshot(tmp_path, '2026-10', 3829)
    (tmp_path / '2026-10' / 'matriculas.csv').unlink()
    assert 'matriculas.csv' in validar_snapshot.validar('2026-10', str(tmp_path))[0]


def test_primer_snapshot_sin_anterior(tmp_path):
    _snapshot(tmp_path, '2026-10', 3829)
    assert validar_snapshot.validar('2026-10', str(tmp_path)) == []


def test_migracion_preserva_continuidad(tmp_path):
    panel = pd.DataFrame({
        'matricula_hash': [hashlib.sha256(str(m).encode()).hexdigest()[:16] for m in (152, 3502)],
        'estado': ['ACTIVA', 'SIN ACTUALIZAR'],
    })
    path = tmp_path / 'matriculas.csv'
    panel.to_csv(path, index=False)
    inverso = migrar_panel_hmac.indice_inverso(maximo=5000)

    assert migrar_panel_hmac.migrar_panel(path, 'clave', inverso) is True
    migrado = pd.read_csv(path, dtype=str)
    esperado = [generar_agregados.hash_matricula(m, 'clave') for m in (152, 3502)]
    assert list(migrado['matricula_hash']) == esperado
    assert list(migrado['estado']) == ['ACTIVA', 'SIN ACTUALIZAR']
    # Correrla de nuevo no hace nada.
    assert migrar_panel_hmac.migrar_panel(path, 'clave', inverso) is False
