"""
Scraper del buscador oficial de administradores de consorcios (GCBA).

Hace un GET para obtener el token CSRF y un POST al endpoint AJAX que
devuelve el padrón completo en JSON. Ambos pedidos van por la misma
`requests.Session`, para que la cookie de sesión del GET viaje en el POST.

El resultado (`administradores.csv`) tiene datos personales: es local,
está en `.gitignore` y nunca se commitea.

Uso:
    python administradores_scraper.py [--salida administradores.csv]
"""
import argparse
import logging
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
USER_AGENT = (
    'administradores-consorcios-caba/1.0 '
    '(+https://github.com/PabloAlaniz/administradores-consorcios-caba)'
)
TIMEOUT = 60
REINTENTOS = 3
ESPERA_BASE = 5  # segundos; se duplica en cada reintento

# Columnas que el pipeline necesita. Si el endpoint deja de mandarlas,
# el scrape falla en vez de producir un snapshot roto.
COLUMNAS_REQUERIDAS = {
    'MATRICULAID', 'CUIT', 'ONEROSO', 'ESTADOMATRICULADESC', 'FECHAALTA',
    'FECHAACTUALIZACION', 'TIENESANCIONES', 'CANTIDADCONSORCIOS',
    'TIPOPERSONADESC', 'CPADMINISTRADOR', 'COMUNAUSIGADMINISTRADOR',
    'DISPOSICION',
}

log = logging.getLogger(__name__)


class ScraperError(RuntimeError):
    """El endpoint respondió algo que no se puede usar como padrón."""


def get_csrf_token(session, url=URL):
    """Extrae el token CSRF del <meta name="csrf-token"> de la página."""
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    meta = BeautifulSoup(response.text, 'html.parser').find('meta', {'name': 'csrf-token'})
    if meta is None or not meta.get('content'):
        raise ScraperError('No se encontró el token CSRF en la página del buscador')
    return meta['content']


def build_post_data(csrf_token):
    """Payload del POST.

    El endpoint ignora los filtros y devuelve siempre el padrón completo
    (verificado en julio 2026); se manda igual una matrícula para replicar
    lo que envía el formulario.
    """
    return {
        '_token': csrf_token,
        'cuit': '',
        'matricula': '3502',
        'tipo_filtro': '1',
        'razonSocial': '',
        'nombre': '',
        'apellido': '',
        'calle': '',
        'altura': '',
        'cuitConsorcio': '',
        'isadmin': 'False',
    }


def build_headers(url=URL):
    """Headers del POST AJAX."""
    return {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://buscador-admin-consorcio.buenosaires.gob.ar',
        'Referer': url,
        'X-Requested-With': 'XMLHttpRequest',
    }


def fetch_administradores_data(session, data, headers, url=URL):
    """POST al endpoint; devuelve el JSON decodificado."""
    response = session.post(url, data=data, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:
        raise ScraperError(f'El endpoint no devolvió JSON: {response.text[:200]!r}') from exc


def process_data_to_dataframe(data):
    """Convierte el JSON a DataFrame y valida que tenga forma de padrón."""
    if not isinstance(data, dict) or 'Objeto' not in data:
        raise ScraperError("La respuesta no tiene la clave 'Objeto'")
    df = pd.json_normalize(data['Objeto'])
    if df.empty:
        raise ScraperError('El endpoint devolvió un padrón vacío')
    faltantes = COLUMNAS_REQUERIDAS - set(df.columns)
    if faltantes:
        raise ScraperError(f'Faltan columnas en la respuesta: {sorted(faltantes)}')
    return df


def scrapear(session=None, reintentos=REINTENTOS, espera_base=ESPERA_BASE):
    """Corre GET + POST con reintentos y backoff exponencial."""
    session = session or requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    for intento in range(1, reintentos + 1):
        try:
            token = get_csrf_token(session)
            data = fetch_administradores_data(session, build_post_data(token), build_headers())
            return process_data_to_dataframe(data)
        except (requests.RequestException, ScraperError) as exc:
            if intento == reintentos:
                raise
            espera = espera_base * 2 ** (intento - 1)
            log.warning('Intento %d/%d falló (%s); reintento en %ds', intento, reintentos, exc, espera)
            time.sleep(espera)
    raise AssertionError('inalcanzable')


def save_to_csv(df, filename='administradores.csv'):
    df.to_csv(filename, index=False, encoding='utf-8')
    return filename


def main(salida='administradores.csv'):
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    df = scrapear()
    save_to_csv(df, salida)
    log.info('%d filas (%d matrículas únicas) → %s', len(df), df['MATRICULAID'].nunique(), salida)
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--salida', default='administradores.csv', help='CSV de salida (default: administradores.csv)')
    main(parser.parse_args().salida)
