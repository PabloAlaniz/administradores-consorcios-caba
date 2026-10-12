"""
Reconciliación del buscador contra el registro publicado en BA Data.

El GCBA publica en su portal de datos abiertos un CSV del Registro Público de
Administradores ("activos" a una fecha de corte que figura en el encabezado).
Este módulo lo descarga y lo compara, matrícula por matrícula, con lo que
devuelve el buscador, para medir qué parte del registro está viendo el scraper.

Solo se usan la matrícula y la fecha de inscripción del CSV oficial: el
nombre y el correo electrónico que también trae se descartan al cargarlo.

Uso:
    python datos_abiertos.py [--salida registro_oficial.csv]
"""
import argparse
import re
from datetime import datetime

import pandas as pd
import requests

URL_REGISTRO = (
    'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/jefatura-de-gabinete-de-ministros/'
    'registro-administradores-consorcio/registro-administradores-de-consorcio.csv'
)
TIMEOUT = 120

# Cortes de matrícula para leer la cobertura. El buscador oficial avisa que
# todavía no muestra las matrículas desde la 20.000 en adelante.
TRAMOS = [0, 5_000, 10_000, 15_000, 20_000, float('inf')]
ETIQUETAS_TRAMOS = ['1-4999', '5000-9999', '10000-14999', '15000-19999', '20000+']


def descargar_registro(salida='registro_oficial.csv', url=URL_REGISTRO):
    response = requests.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    with open(salida, 'wb') as fh:
        fh.write(response.content)
    return salida


def cargar_registro(path):
    """Devuelve (DataFrame[matricula, fecha_inscripcion], fecha_corte ISO o None)."""
    df = pd.read_csv(path, sep=';', encoding='latin-1', dtype=str)
    columnas = list(df.columns)
    fecha_corte = None
    for col in columnas:
        m = re.search(r'(\d{2}/\d{2}/\d{4})', col)
        if m:
            fecha_corte = datetime.strptime(m.group(1), '%d/%m/%Y').date().isoformat()
            break
    col_matricula = next(c for c in columnas if c.lower().startswith('nro'))
    col_alta = next(c for c in columnas if 'inscrip' in c.lower())
    out = pd.DataFrame({
        'matricula': pd.to_numeric(df[col_matricula], errors='coerce'),
        'fecha_inscripcion': pd.to_datetime(df[col_alta], dayfirst=True, errors='coerce'),
    }).dropna(subset=['matricula'])
    out['matricula'] = out['matricula'].astype(int)
    return out.drop_duplicates('matricula').reset_index(drop=True), fecha_corte


def _universo(matriculas_buscador, oficial):
    """Une ambas fuentes en un DataFrame con la categoría de cobertura de cada matrícula."""
    buscador = set(int(m) for m in matriculas_buscador)
    oficiales = set(oficial['matricula'])
    todas = pd.DataFrame({'matricula': sorted(buscador | oficiales)})
    todas['categoria'] = todas['matricula'].map(
        lambda m: 'en_ambos' if m in buscador and m in oficiales
        else 'solo_buscador' if m in buscador else 'solo_datos_abiertos'
    )
    return todas.merge(oficial, on='matricula', how='left')


def _pivot(universo, por):
    out = (universo.groupby([por, 'categoria'], observed=False).size()
           .unstack(fill_value=0)
           .reindex(columns=['en_ambos', 'solo_buscador', 'solo_datos_abiertos'], fill_value=0))
    return out.reset_index().rename_axis(columns=None)


def cobertura_por_tramo(matriculas_buscador, oficial):
    """Cobertura por tramo de número de matrícula."""
    u = _universo(matriculas_buscador, oficial)
    u['tramo_matricula'] = pd.cut(u['matricula'], TRAMOS, labels=ETIQUETAS_TRAMOS, right=False)
    return _pivot(u, 'tramo_matricula')


def cobertura_por_anio_alta(matriculas_buscador, oficial):
    """Cobertura por año de inscripción (solo matrículas presentes en el CSV oficial)."""
    u = _universo(matriculas_buscador, oficial).dropna(subset=['fecha_inscripcion'])
    u['anio_alta'] = u['fecha_inscripcion'].dt.year.astype(int)
    return _pivot(u, 'anio_alta')


def resumen_cobertura(matriculas_buscador, oficial, fecha_corte):
    u = _universo(matriculas_buscador, oficial)
    conteo = u['categoria'].value_counts()
    return {
        'datos_abiertos_fecha_corte': fecha_corte,
        'datos_abiertos_total': int(len(oficial)),
        'cobertura_en_ambos': int(conteo.get('en_ambos', 0)),
        'cobertura_solo_buscador': int(conteo.get('solo_buscador', 0)),
        'cobertura_solo_datos_abiertos': int(conteo.get('solo_datos_abiertos', 0)),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--salida', default='registro_oficial.csv',
                        help='dónde guardar el CSV oficial (default: registro_oficial.csv, gitignored)')
    path = descargar_registro(parser.parse_args().salida)
    df, fecha = cargar_registro(path)
    print(f'{len(df)} matrículas en el registro oficial (corte {fecha}) → {path}')
