import json
import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd

logging.basicConfig(level=logging.DEBUG)

session = requests.Session()

# URL del sitio al que quieres hacer las solicitudes
url_get = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
url_post = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'

# Realiza la solicitud GET para obtener la página y el token CSRF
response_get = requests.get(url_get)

# Utiliza BeautifulSoup para analizar el HTML y extraer el token CSRF
soup = BeautifulSoup(response_get.text, 'html.parser')
csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
logging.debug(f'CSRF Token: {csrf_token}')
# Datos que enviarás en la solicitud POST
data = {
    '_token': csrf_token,  # Usa el token CSRF extraído
    'cuit': '',  # Añade el valor correspondiente
    'matricula': '3502',
    'tipo_filtro': '1',
    'razonSocial': '',
    'nombre': '',
    'apellido': '',
    'calle': '',
    'altura': '',
    'cuitConsorcio': '',
    'isadmin': 'False'
}

headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8,la;q=0.7,gl;q=0.6",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Host": "buscador-admin-consorcio.buenosaires.gob.ar",
    "Origin": "https://buscador-admin-consorcio.buenosaires.gob.ar",
    "Referer": "https://buscador-admin-consorcio.buenosaires.gob.ar/administradores",
    "Sec-Ch-Ua": "\"Not A(Brand\";v=\"99\", \"Google Chrome\";v=\"121\", \"Chromium\";v=\"121\"",
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": "\"Android\"",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}


# Las cookies obtenidas en la solicitud GET ya están almacenadas en la sesión,
# por lo que se enviarán automáticamente en la solicitud POST.
response_post = session.post(url_post, data=data, headers=headers)

# Convertimos el JSON en un objeto de Python
datos = json.loads(response_post.text)

# Creamos un DataFrame a partir del objeto de Python
df = pd.json_normalize(datos['Objeto'])

# Mostramos el DataFrame resultante
print(df)

# Guardamos el DataFrame en un archivo CSV
df.to_csv('administradores.csv', index=False, encoding='utf-8')