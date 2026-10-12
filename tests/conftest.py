import pytest


@pytest.fixture(autouse=True)
def clave_panel(monkeypatch):
    """Clave del HMAC del panel para los tests (en CI real es un secret)."""
    monkeypatch.setenv('PANEL_HMAC_KEY', 'clave-de-test')
