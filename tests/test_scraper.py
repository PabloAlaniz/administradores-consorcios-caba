"""Tests del scraper con una sesión HTTP falsa (sin red)."""
from unittest.mock import Mock

import pytest
import requests

import administradores_scraper as scraper

HTML = '<html><head><meta name="csrf-token" content="tok-123"></head></html>'


def _fila(**extra):
    fila = {col: 'x' for col in scraper.COLUMNAS_REQUERIDAS}
    fila.update(MATRICULAID=1, CANTIDADCONSORCIOS=0)
    fila.update(extra)
    return fila


def _respuesta(texto='', json_data=None, status=200):
    resp = Mock()
    resp.text = texto
    resp.json.return_value = json_data
    resp.raise_for_status.side_effect = (
        requests.HTTPError(f'{status}') if status >= 400 else None)
    return resp


def _sesion(get_resps, post_resps):
    sesion = Mock()
    sesion.headers = {}
    sesion.get.side_effect = get_resps
    sesion.post.side_effect = post_resps
    return sesion


def test_get_y_post_usan_la_misma_sesion_con_timeout():
    sesion = _sesion([_respuesta(HTML)], [_respuesta(json_data={'Objeto': [_fila()]})])
    df = scraper.scrapear(sesion, reintentos=1)

    assert len(df) == 1
    assert sesion.get.call_args.kwargs['timeout'] == scraper.TIMEOUT
    post = sesion.post.call_args
    assert post.kwargs['timeout'] == scraper.TIMEOUT
    assert post.kwargs['data']['_token'] == 'tok-123'
    assert 'administradores-consorcios-caba' in sesion.headers['User-Agent']


def test_reintenta_ante_error_http(monkeypatch):
    monkeypatch.setattr(scraper.time, 'sleep', lambda s: None)
    sesion = _sesion(
        [_respuesta(HTML), _respuesta(HTML)],
        [_respuesta(status=503), _respuesta(json_data={'Objeto': [_fila()]})],
    )
    df = scraper.scrapear(sesion, reintentos=2)
    assert len(df) == 1
    assert sesion.post.call_count == 2


def test_falla_despues_del_ultimo_reintento(monkeypatch):
    monkeypatch.setattr(scraper.time, 'sleep', lambda s: None)
    sesion = _sesion([_respuesta(HTML)] * 2, [_respuesta(status=500)] * 2)
    with pytest.raises(requests.HTTPError):
        scraper.scrapear(sesion, reintentos=2)


def test_sin_token_csrf():
    sesion = _sesion([_respuesta('<html></html>')], [])
    with pytest.raises(scraper.ScraperError, match='CSRF'):
        scraper.get_csrf_token(sesion)


def test_respuesta_no_json():
    resp = _respuesta('<html>error</html>')
    resp.json.side_effect = ValueError('no json')
    sesion = _sesion([], [resp])
    with pytest.raises(scraper.ScraperError, match='JSON'):
        scraper.fetch_administradores_data(sesion, {}, {})


@pytest.mark.parametrize('data, mensaje', [
    ({'otra': []}, 'Objeto'),
    ({'Objeto': []}, 'vacío'),
    ({'Objeto': [{'MATRICULAID': 1}]}, 'Faltan columnas'),
])
def test_valida_forma_del_padron(data, mensaje):
    with pytest.raises(scraper.ScraperError, match=mensaje):
        scraper.process_data_to_dataframe(data)


def test_payload_replica_el_formulario():
    data = scraper.build_post_data('tok')
    assert data['_token'] == 'tok'
    assert data['isadmin'] == 'False'
