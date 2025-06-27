"""Integration tests for roll endpoints"""

import json
import pytest
from unittest.mock import patch

class TestRollEndpoints:
    """Test cases for roll API endpoints"""
    
    def test_index_route(self, client):
        """Test main index route"""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Crits' in response.data or b'crit' in response.data.lower()
    
    @patch('app.services.dice_service.random.randint')
    def test_roll_crit_endpoint(self, mock_random, client):
        """Test crit roll endpoint"""
        mock_random.return_value = 10
        
        payload = {
            "rollContext": "primary",
            "rollType": "crit",
            "critSource": "Sterling Vermin",
            "damageType": "slashing"
        }
        
        response = client.post('/roll', 
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["rollValue"] == 10
        assert data["selectedRollType"] == "crit"
    
    def test_roll_invalid_payload(self, client):
        """Test roll endpoint with invalid payload"""
        response = client.post('/roll',
                             data="invalid json",
                             content_type='application/json')
        
        assert response.status_code == 400
        # Flask returns HTML error page for bad JSON, not JSON response
        assert b'Bad Request' in response.data
    
    def test_roll_missing_context(self, client):
        """Test roll endpoint with missing context"""
        payload = {"rollType": "crit"}
        
        response = client.post('/roll',
                             data=json.dumps(payload),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Missing required fields" in data["errorMessage"]
    
    def test_get_roll_history(self, client):
        """Test roll history endpoint"""
        response = client.get('/get_roll_history')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)