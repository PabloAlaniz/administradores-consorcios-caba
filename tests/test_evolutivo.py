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
        'COMUNAUSIGADMINISTRADOR': ['Comuna 1', 'Comuna 1', '', None],
        'CPADMINISTRADOR': ['1437', '1437', '1049', ''],
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


class TestAgregadosGeograficos:

    def test_comuna_normaliza_vacios_y_nan(self, df_crudo):
        df = df_crudo.drop_duplicates('MATRICULAID')
        tabla = generar_agregados.comuna_administrador(df)
        conteo = dict(zip(tabla['comuna'], tabla['cantidad']))
        assert conteo == {'Comuna 1': 1, 'Sin dato': 2}

    def test_cp_extrae_4_digitos(self, df_crudo):
        df = df_crudo.drop_duplicates('MATRICULAID')
        tabla = generar_agregados.cp_administrador(df)
        conteo = dict(zip(tabla['codigo_postal'], tabla['cantidad']))
        assert conteo == {'1049': 1, '1437': 1, 'Sin dato': 1}

    def test_sin_columnas_geo_devuelve_none(self, df_crudo):
        df = df_crudo.drop(columns=['COMUNAUSIGADMINISTRADOR', 'CPADMINISTRADOR'])
        assert generar_agregados.comuna_administrador(df) is None
        assert generar_agregados.cp_administrador(df) is None
        # ...y generar_agregados() simplemente omite esas tablas.
        assert 'comuna_administrador' not in generar_agregados.generar_agregados(df)


class TestPanelMatriculas:

    def test_hash_estable_y_sin_pii(self, df_crudo):
        df = df_crudo.drop_duplicates('MATRICULAID')
        panel1 = generar_agregados.panel_matriculas(df)
        panel2 = generar_agregados.panel_matriculas(df)
        assert list(panel1['matricula_hash']) == list(panel2['matricula_hash'])
        assert panel1['matricula_hash'].nunique() == 3
        assert set(panel1.columns) == {'matricula_hash', 'estado', 'cantidad_consorcios', 'tiene_sanciones'}


class TestIndicesConcentracion:

    def test_gini_reparto_igualitario_es_cero(self):
        dist = pd.DataFrame({'cantidad_consorcios': [3], 'administradores': [10]})
        assert generar_evolutivo.gini_desde_distribucion(dist) == 0.0

    def test_gini_maxima_desigualdad(self):
        # 9 admins con 0 y 1 con todo: G = (n-1)/n = 0.9
        dist = pd.DataFrame({'cantidad_consorcios': [0, 100], 'administradores': [9, 1]})
        assert generar_evolutivo.gini_desde_distribucion(dist) == 0.9

    def test_hhi_monopolio_es_10000(self):
        dist = pd.DataFrame({'cantidad_consorcios': [0, 50], 'administradores': [4, 1]})
        assert generar_evolutivo.hhi_desde_distribucion(dist) == 10_000.0

    def test_hhi_reparto_uniforme(self):
        # 4 admins con 25% cada uno -> HHI = 4 * 25^2 = 2500
        dist = pd.DataFrame({'cantidad_consorcios': [10], 'administradores': [4]})
        assert generar_evolutivo.hhi_desde_distribucion(dist) == 2_500.0

    def test_sin_consorcios_devuelve_none(self):
        dist = pd.DataFrame({'cantidad_consorcios': [0], 'administradores': [5]})
        assert generar_evolutivo.gini_desde_distribucion(dist) is None
        assert generar_evolutivo.hhi_desde_distribucion(dist) is None


class TestEvolutivo:

    @pytest.fixture
    def snapshots_dir(self, df_crudo, tmp_path):
        """Dos snapshots con movimientos conocidos entre cortes.

        2026-07: matrículas 1 (ACTIVA, 2 consorcios), 2 (SIN ACTUALIZAR,
        sancionada), 3 (ACTIVA, 5 consorcios).
        2026-08: la 1 se desactiva, pierde un consorcio y suma una sanción;
        la 2 se da de baja; la 3 sigue igual; entra la 4 (alta, ACTIVA).
        """
        snapshots_dir = tmp_path / 'snapshots'
        _crear_snapshot(df_crudo, snapshots_dir, '2026-07')

        df_agosto = pd.DataFrame({
            'MATRICULAID': [1, 3, 4],
            'CUIT': ['20-11111111-1', '30-33333333-3', '20-44444444-4'],
            'RAZONSOCIAL': ['A', 'C', 'D'],
            'ESTADOMATRICULADESC': ['SIN ACTUALIZAR', 'ACTIVA', 'ACTIVA'],
            'TIPOPERSONADESC': ['HUMANA', 'JURIDICA', 'HUMANA'],
            'ONEROSO': ['Si', 'Si', 'Si'],
            'TIENESANCIONES': ['Si', 'No', 'No'],
            'CANTIDADCONSORCIOS': [1, 5, 3],
            'FECHAALTA': ['2018-05-01', '2003-09-09', '2026-08-01'],
            'COMUNAUSIGADMINISTRADOR': ['Comuna 1', None, 'Comuna 4'],
            'CPADMINISTRADOR': ['1437', '', '1207'],
        })
        _crear_snapshot(df_agosto, snapshots_dir, '2026-08')
        return snapshots_dir

    def test_listar_snapshots_ordenados(self, snapshots_dir):
        (snapshots_dir / 'basura').mkdir()
        assert generar_evolutivo.listar_snapshots(str(snapshots_dir)) == ['2026-07', '2026-08']

    def test_resumen_kpis_y_variaciones(self, snapshots_dir):
        resumen = generar_evolutivo.construir_resumen(['2026-07', '2026-08'], str(snapshots_dir))

        assert list(resumen['snapshot']) == ['2026-07', '2026-08']
        assert list(resumen['total_administradores']) == [3, 3]
        assert list(resumen['total_consorcios']) == [7, 9]
        assert list(resumen['matriculas_activas']) == [2, 2]
        assert list(resumen['sancionados']) == [1, 1]
        assert resumen['gini'].notna().all()
        assert resumen['hhi'].notna().all()
        # Variaciones: primer corte sin dato, segundo con el delta.
        assert pd.isna(resumen['var_total_administradores'].iloc[0])
        assert resumen['var_total_administradores'].iloc[1] == 0
        assert resumen['var_total_consorcios'].iloc[1] == 2

    def test_flujos_entre_cortes(self, snapshots_dir):
        flujos = generar_evolutivo.construir_flujos(['2026-07', '2026-08'], str(snapshots_dir))

        assert len(flujos) == 1
        f = flujos.iloc[0]
        assert f['snapshot'] == '2026-08' and f['vs_snapshot'] == '2026-07'
        assert f['altas'] == 1          # matrícula 4
        assert f['bajas'] == 1          # matrícula 2
        assert f['activaciones'] == 0
        assert f['desactivaciones'] == 1   # matrícula 1: ACTIVA -> SIN ACTUALIZAR
        assert f['sancionados_nuevos'] == 1  # matrícula 1
        assert f['perdieron_consorcios'] == 1 and f['ganaron_consorcios'] == 0
        assert f['consorcios_netos'] == -1

    def test_flujos_sin_panel_devuelve_none(self, snapshots_dir):
        (snapshots_dir / '2026-07' / 'matriculas.csv').unlink()
        flujos = generar_evolutivo.construir_flujos(['2026-07', '2026-08'], str(snapshots_dir))
        assert flujos is None

    def test_reporte_incluye_kpis_y_flujos(self, snapshots_dir, tmp_path):
        snaps = ['2026-07', '2026-08']
        resumen = generar_evolutivo.construir_resumen(snaps, str(snapshots_dir))
        flujos = generar_evolutivo.construir_flujos(snaps, str(snapshots_dir))
        path = generar_evolutivo.generar_reporte(resumen, flujos, str(tmp_path))

        texto = open(path, encoding='utf-8').read()
        assert '2026-08' in path and '# Reporte del padrón — 2026-08' in texto
        assert 'vs corte 2026-07' in texto
        assert 'Flujos del mes (vs 2026-07)' in texto
        assert 'Altas al padrón: **1**' in texto

    def test_reporte_incluye_nota_metodologica(self, snapshots_dir, tmp_path):
        resumen = generar_evolutivo.construir_resumen(['2026-07', '2026-08'], str(snapshots_dir))
        path = generar_evolutivo.generar_reporte(
            resumen, None, str(tmp_path), nota='El endpoint cambió de semántica.')
        texto = open(path, encoding='utf-8').read()
        assert '## Nota metodológica' in texto
        assert '> El endpoint cambió de semántica.' in texto

    def test_series_formato_largo(self, snapshots_dir):
        series = generar_evolutivo.construir_series(['2026-07', '2026-08'], str(snapshots_dir))

        estado = series['evolucion_estado_matricula']
        assert set(estado.columns) == {'snapshot', 'estado', 'cantidad'}
        assert set(estado['snapshot']) == {'2026-07', '2026-08'}
        activa = estado[(estado['snapshot'] == '2026-08') & (estado['estado'] == 'ACTIVA')]
        assert activa['cantidad'].iloc[0] == 2
        # Las dimensiones geográficas también entran en el evolutivo.
        assert 'evolucion_comuna_administrador' in series
        assert 'evolucion_cp_administrador' in series

    def test_main_escribe_salidas(self, snapshots_dir, tmp_path, capsys):
        output_dir = tmp_path / 'evolutivo'
        generar_evolutivo.main(str(snapshots_dir), str(output_dir))
        assert (output_dir / 'resumen.csv').exists()
        assert (output_dir / 'evolucion_estado_matricula.csv').exists()

    def test_main_sin_snapshots_falla(self, tmp_path):
        with pytest.raises(SystemExit, match='No hay snapshots'):
            generar_evolutivo.main(str(tmp_path / 'vacio'), str(tmp_path / 'out'))
