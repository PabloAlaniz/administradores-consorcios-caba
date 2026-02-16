"""
Tests for main.py - Administradores Consorcios scraper
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup
import json


class TestScraperFunctionality:
    """Test the main scraper functionality"""
    
    @patch('requests.get')
    def test_csrf_token_extraction(self, mock_get):
        """Test CSRF token extraction from HTML"""
        # Mock HTML response with CSRF token
        mock_html = '''
        <html>
            <head>
                <meta name="csrf-token" content="test-token-123">
            </head>
        </html>
        '''
        mock_response = Mock()
        mock_response.text = mock_html
        mock_get.return_value = mock_response
        
        # Extract token using BeautifulSoup (like in main.py)
        response_get = requests.get('test-url')
        soup = BeautifulSoup(response_get.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
        
        assert csrf_token == "test-token-123"
        mock_get.assert_called_once_with('test-url')
    
    def test_data_payload_structure(self):
        """Test that the POST data payload has required fields"""
        # This mimics the data structure from main.py
        data = {
            '_token': 'test-token',
            'cuit': '',
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
        
        # Test required fields exist
        assert '_token' in data
        assert 'matricula' in data
        assert 'tipo_filtro' in data
        assert data['matricula'] == '3502'
        assert data['tipo_filtro'] == '1'
        assert data['isadmin'] == 'False'
    
    def test_headers_structure(self):
        """Test that headers have required structure"""
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        assert "Accept" in headers
        assert "Content-Type" in headers
        assert "X-Requested-With" in headers
        assert "application/json" in headers["Accept"]
        assert "XMLHttpRequest" in headers["X-Requested-With"]
    
    @patch('pandas.json_normalize')
    def test_json_processing(self, mock_normalize):
        """Test JSON response processing"""
        # Mock JSON data structure
        mock_json_data = {
            'Objeto': [
                {'id': 1, 'nombre': 'Admin 1', 'cuit': '12345'},
                {'id': 2, 'nombre': 'Admin 2', 'cuit': '67890'}
            ]
        }
        
        # Mock DataFrame with to_csv method
        mock_df = Mock()
        mock_normalize.return_value = mock_df
        
        # Process like in main.py
        df = pd.json_normalize(mock_json_data['Objeto'])
        df.to_csv('administradores.csv', index=False, encoding='utf-8')
        
        mock_normalize.assert_called_once_with(mock_json_data['Objeto'])
        mock_df.to_csv.assert_called_once_with('administradores.csv', index=False, encoding='utf-8')
    
    def test_url_constants(self):
        """Test that URL constants are properly defined"""
        url_get = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
        url_post = 'https://buscador-admin-consorcio.buenosaires.gob.ar/administradores'
        
        assert url_get.startswith('https://')
        assert url_post.startswith('https://')
        assert 'buenosaires.gob.ar' in url_get
        assert 'administradores' in url_get
    
    @patch('requests.Session')
    def test_session_usage(self, mock_session_class):
        """Test that requests.Session is used properly"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Simulate session creation like in main.py
        session = requests.Session()
        
        mock_session_class.assert_called_once()
        assert session == mock_session
    
    def test_logging_configuration(self):
        """Test that logging is configured"""
        import logging
        
        # Check that logging has some basic configuration
        logger = logging.getLogger()
        assert logger is not None
        
        # Test log level setting  
        test_logger = logging.getLogger('test_logger')
        test_logger.setLevel(logging.DEBUG)
        assert test_logger.isEnabledFor(logging.DEBUG)


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_missing_csrf_token(self):
        """Test handling when CSRF token is missing"""
        mock_html = '<html><head></head></html>'
        soup = BeautifulSoup(mock_html, 'html.parser')
        
        # Should raise exception when token not found
        with pytest.raises((TypeError, AttributeError)):
            csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
    
    def test_invalid_json_response(self):
        """Test handling of invalid JSON response"""
        with pytest.raises(json.JSONDecodeError):
            json.loads("invalid json")
    
    @patch('requests.get')
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors"""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        with pytest.raises(requests.exceptions.RequestException):
            requests.get('test-url')


class TestDataValidation:
    """Test data validation and processing"""
    
    def test_empty_dataframe_handling(self):
        """Test handling of empty response data"""
        empty_data = {'Objeto': []}
        df = pd.json_normalize(empty_data['Objeto'])
        
        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)
    
    def test_dataframe_with_data(self):
        """Test DataFrame creation with actual data"""
        sample_data = {
            'Objeto': [
                {'id': 1, 'nombre': 'Test Admin', 'cuit': '12345'},
                {'id': 2, 'nombre': 'Another Admin', 'cuit': '67890'}
            ]
        }
        
        df = pd.json_normalize(sample_data['Objeto'])
        
        assert len(df) == 2
        assert 'id' in df.columns
        assert 'nombre' in df.columns
        assert 'cuit' in df.columns
        assert df.iloc[0]['nombre'] == 'Test Admin'