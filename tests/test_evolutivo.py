"""
Tests del sistema de snapshots (generar_agregados --snapshot) y del
consolidado evolutivo (generar_evolutivo.py).
"""
import json

import pandas as pd
import pytest

import generar_agregados
import generar_evolutivo


@pytest.fixture
def df_crudo():
    """Mini dataset crudo con la misma forma que el CSV del scraper."""
    return pd.DataFrame({
        'MATRICULAID': [1, 1, 2, 3],
        'CUIT': ['20-11111111-1', '20-11111111-1', '27-22222222-2', '30-33333333-3'],
        'RAZONSOCIAL': ['A', 'A', 'B', 'C'],
        'ESTADOMATRICULADESC': ['ACTIVA', 'ACTIVA', 'SIN ACTUALIZAR', 'ACTIVA'],
        'TIPOPERSONADESC': ['HUMANA', 'HUMANA', 'HUMANA', 'JURIDICA'],
        'ONEROSO': ['Si', 'Si', 'NO', 'Si'],
        'TIENESANCIONES': ['No', 'No', 'Si', 'No'],
        'CANTIDADCONSORCIOS': [2, 2, 0, 5],
        'FECHAALTA': ['2018-05-01', '2018-05-01', '2020-01-15', '2003-09-09'],
    })


def _crear_snapshot(df_crudo, snapshots_dir, snapshot):
    df = df_crudo.drop_duplicates('MATRICULAID').reset_index(drop=True)
    agregados = generar_agregados.generar_agregados(df)
    generar_agregados.escribir_snapshot(agregados, df, snapshot, snapshots_dir=str(snapshots_dir))
    return df


class TestEscribirSnapshot:

    def test_crea_csvs_y_metadata(self, df_crudo, tmp_path):
        snapshots_dir = tmp_path / 'snapshots'
        df = _crear_snapshot(df_crudo, snapshots_dir, '2026-07')

        snapshot_dir = snapshots_dir / '2026-07'
        assert (snapshot_dir / 'estado_matricula.csv').exists()
        assert (snapshot_dir / 'concentracion.csv').exists()

        meta = json.loads((snapshot_dir / 'metadata.json').read_text(encoding='utf-8'))
        assert meta['snapshot'] == '2026-07'
        assert meta['total_administradores'] == len(df) == 3
        assert meta['total_consorcios'] == 7

    def test_rechaza_formato_invalido(self, df_crudo, tmp_path):
        df = df_crudo.drop_duplicates('MATRICULAID')
        agregados = generar_agregados.generar_agregados(df)
        with pytest.raises(SystemExit, match='YYYY-MM'):
            generar_agregados.escribir_snapshot(agregados, df, 'julio-2026', snapshots_dir=str(tmp_path))

    def test_snapshot_sin_pii(self, df_crudo, tmp_path):
        snapshots_dir = tmp_path / 'snapshots'
        _crear_snapshot(df_crudo, snapshots_dir, '2026-07')
        pii = {c.upper() for c in generar_agregados.PII_COLS}
        for csv in (snapshots_dir / '2026-07').glob('*.csv'):
            cols = {c.upper() for c in pd.read_csv(csv, nrows=0).columns}
            assert not cols & pii, f'{csv.name} contiene PII'


class TestEvolutivo:

    @pytest.fixture
    def snapshots_dir(self, df_crudo, tmp_path):
        """Dos snapshots: el segundo con un administrador y consorcios extra."""
        snapshots_dir = tmp_path / 'snapshots'
        _crear_snapshot(df_crudo, snapshots_dir, '2026-07')

        fila_nueva = df_crudo.iloc[[2]].assign(
            MATRICULAID=4, CUIT='20-44444444-4', ESTADOMATRICULADESC='ACTIVA',
            CANTIDADCONSORCIOS=3, TIENESANCIONES='No',
        )
        _crear_snapshot(pd.concat([df_crudo, fila_nueva]), snapshots_dir, '2026-08')
        return snapshots_dir

    def test_listar_snapshots_ordenados(self, snapshots_dir):
        (snapshots_dir / 'basura').mkdir()
        assert generar_evolutivo.listar_snapshots(str(snapshots_dir)) == ['2026-07', '2026-08']

    def test_resumen_kpis_y_variaciones(self, snapshots_dir):
        resumen = generar_evolutivo.construir_resumen(['2026-07', '2026-08'], str(snapshots_dir))

        assert list(resumen['snapshot']) == ['2026-07', '2026-08']
        assert list(resumen['total_administradores']) == [3, 4]
        assert list(resumen['total_consorcios']) == [7, 10]
        assert list(resumen['matriculas_activas']) == [2, 3]
        assert list(resumen['sancionados']) == [1, 1]
        # Variaciones: primer corte sin dato, segundo con el delta.
        assert pd.isna(resumen['var_total_administradores'].iloc[0])
        assert resumen['var_total_administradores'].iloc[1] == 1
        assert resumen['var_total_consorcios'].iloc[1] == 3

    def test_series_formato_largo(self, snapshots_dir):
        series = generar_evolutivo.construir_series(['2026-07', '2026-08'], str(snapshots_dir))

        estado = series['evolucion_estado_matricula']
        assert set(estado.columns) == {'snapshot', 'estado', 'cantidad'}
        assert set(estado['snapshot']) == {'2026-07', '2026-08'}
        activa = estado[(estado['snapshot'] == '2026-08') & (estado['estado'] == 'ACTIVA')]
        assert activa['cantidad'].iloc[0] == 3

    def test_main_escribe_salidas(self, snapshots_dir, tmp_path, capsys):
        output_dir = tmp_path / 'evolutivo'
        generar_evolutivo.main(str(snapshots_dir), str(output_dir))
        assert (output_dir / 'resumen.csv').exists()
        assert (output_dir / 'evolucion_estado_matricula.csv').exists()

    def test_main_sin_snapshots_falla(self, tmp_path):
        with pytest.raises(SystemExit, match='No hay snapshots'):
            generar_evolutivo.main(str(tmp_path / 'vacio'), str(tmp_path / 'out'))
