"""Pytest configuration and fixtures"""

import pytest
import json
import tempfile
import os
from app.app_refactored import create_app
from app.config import Config
from app.services.data_service import DataService

class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    LOG_STORAGE_DIR = tempfile.gettempdir()

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app(TestConfig)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def mock_crit_data():
    """Mock critical hit data"""
    return {
        "Sterling Vermin": {
            "slashing": {
                "1-5": "Minor cut",
                "6-10": "Deep gash",
                "11-20": "Severe laceration"
            }
        },
        "effects_tables": {
            "minor_injuries": {
                "1-10": "Bruised",
                "11-20": "Winded"
            }
        }
    }

@pytest.fixture
def mock_fumble_data():
    """Mock fumble data"""
    return {
        "BCoydog": {
            "melee": [
                {"roll": "1-25", "description": "Weapon slips", "effect": "Drop weapon"},
                {"roll": "26-50", "description": "Poor footing", "effect": "Fall prone"}
            ]
        }
    }

@pytest.fixture
def data_service_with_mocks(mock_crit_data, mock_fumble_data, monkeypatch):
    """Data service with mocked data"""
    service = DataService()
    monkeypatch.setattr(service, '_crit_data', mock_crit_data)
    monkeypatch.setattr(service, '_fumble_data', mock_fumble_data)
    return service