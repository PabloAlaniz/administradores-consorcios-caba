"""Tests de la reconciliación contra el CSV de BA Data."""
import pandas as pd
import pytest

import datos_abiertos

CSV = (
    'Nro. Matrícula;Nombre Administrador al 25/02/2026 (ACTIVOS);Fecha Inscripción;Oneroso;'
    'Correo Electronico;Sanciones\r\n'
    '5;PEREZ JUAN;11/08/2003;Si;juan@example.com;No Registra\r\n'
    '7;GOMEZ ANA;15/03/2025;Si;ana@example.com;No Registra\r\n'
    '20393;LOPEZ EVA;02/01/2026;No;eva@example.com;No Registra\r\n'
)


@pytest.fixture
def registro(tmp_path):
    path = tmp_path / 'registro.csv'
    path.write_bytes(CSV.encode('latin-1'))
    return datos_abiertos.cargar_registro(path)


def test_carga_descarta_nombre_y_correo(registro):
    df, fecha = registro
    assert fecha == '2026-02-25'
    assert list(df.columns) == ['matricula', 'fecha_inscripcion']
    assert list(df['matricula']) == [5, 7, 20393]


def test_resumen_cobertura(registro):
    df, fecha = registro
    resumen = datos_abiertos.resumen_cobertura(pd.Series([5, 99]), df, fecha)
    assert resumen == {
        'datos_abiertos_fecha_corte': '2026-02-25',
        'datos_abiertos_total': 3,
        'cobertura_en_ambos': 1,
        'cobertura_solo_buscador': 1,
        'cobertura_solo_datos_abiertos': 2,
    }


def test_cobertura_por_tramo(registro):
    df, _ = registro
    tabla = datos_abiertos.cobertura_por_tramo(pd.Series([5, 99]), df).set_index('tramo_matricula')
    assert tabla.loc['1-4999', 'en_ambos'] == 1
    assert tabla.loc['1-4999', 'solo_datos_abiertos'] == 1
    assert tabla.loc['1-4999', 'solo_buscador'] == 1
    assert tabla.loc['20000+', 'solo_datos_abiertos'] == 1


def test_cobertura_por_anio_alta(registro):
    df, _ = registro
    tabla = datos_abiertos.cobertura_por_anio_alta(pd.Series([5]), df).set_index('anio_alta')
    assert tabla.loc[2003, 'en_ambos'] == 1
    assert tabla.loc[2026, 'solo_datos_abiertos'] == 1
