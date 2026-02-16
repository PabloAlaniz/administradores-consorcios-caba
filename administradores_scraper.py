"""
Refactored scraper for Administradores de Consorcios
"""
import json
import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd


def get_csrf_token(url):
    """Extract CSRF token from the website"""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
    return csrf_token


def build_post_data(csrf_token, matricula='3502'):
    """Build POST data payload"""
    return {
        '_token': csrf_token,
        'cuit': '',
        'matricula': matricula,
        'tipo_filtro': '1',
        'razonSocial': '',
        'nombre': '',
        'apellido': '',
        'calle': '',
        'altura': '',
        'cuitConsorcio': '',
        'isadmin': 'False'
    }


def build_headers():
    """Build request headers"""
    return {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8,la;q=0.7,gl;q=0.6",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "buscador-admin-consorcio.buenosaires.gob.ar",
        "Origin": "https://buscador-admin-consorcio.buenosaires.gob.ar",
        "Referer": "https://buscador-admin-consorcio.buenosaires.gob.ar/administradores",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }


def fetch_administradores_data(url_post, data, headers):
    """Fetch data from the API"""
    session = requests.Session()
    response = session.post(url_post, data=data, headers=headers)
    return json.loads(response.text)


def process_data_to_dataframe(data):
    """Convert JSON data to DataFrame"""
    return pd.json_normalize(data['Objeto'])


def save_to_csv(df, filename='administradores.csv'):
    """Save DataFrame to CSV"""
    df.to_csv(filename, index=False, encoding='utf-8')
    return filename


def main():
    """Main scraper function"""
    logging.basicConfig(level=logging.DEBUG)
    
    url_get = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
    url_post = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
    
    # Get CSRF token
    csrf_token = get_csrf_token(url_get)
    logging.debug(f'CSRF Token: {csrf_token}')
    
    # Build request components
    data = build_post_data(csrf_token)
    headers = build_headers()
    
    # Fetch data
    json_data = fetch_administradores_data(url_post, data, headers)
    
    # Process data
    df = process_data_to_dataframe(json_data)
    print(df)
    
    # Save to file
    filename = save_to_csv(df)
    logging.info(f'Data saved to {filename}')
    
    return df


if __name__ == '__main__':
    main()