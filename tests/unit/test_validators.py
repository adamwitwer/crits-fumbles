"""Unit tests for validators"""

import pytest
from app.utils.validators import (
    validate_roll_payload, 
    validate_discord_message, 
    ValidationError
)

class TestValidators:
    """Test cases for validation functions"""
    
    def test_validate_roll_payload_valid_primary_crit(self):
        """Test valid primary crit payload"""
        payload = {
            "rollContext": "primary",
            "rollType": "crit",
            "critSource": "Sterling Vermin",
            "damageType": "slashing"
        }
        
        # Should not raise exception
        validate_roll_payload(payload)
    
    def test_validate_roll_payload_valid_secondary(self):
        """Test valid secondary payload"""
        payload = {
            "rollContext": "secondary",
            "rollType": "minor"
        }
        
        # Should not raise exception
        validate_roll_payload(payload)
    
    def test_validate_roll_payload_missing_context(self):
        """Test payload missing roll context"""
        payload = {"rollType": "crit"}
        
        with pytest.raises(ValidationError, match="Missing required fields"):
            validate_roll_payload(payload)
    
    def test_validate_roll_payload_invalid_context(self):
        """Test payload with invalid roll context"""
        payload = {"rollContext": "invalid"}
        
        with pytest.raises(ValidationError, match="Invalid roll context"):
            validate_roll_payload(payload)
    
    def test_validate_roll_payload_invalid_primary_type(self):
        """Test primary payload with invalid roll type"""
        payload = {
            "rollContext": "primary",
            "rollType": "invalid"
        }
        
        with pytest.raises(ValidationError, match="Invalid roll type"):
            validate_roll_payload(payload)
    
    def test_validate_roll_payload_invalid_secondary_type(self):
        """Test secondary payload with invalid roll type"""
        payload = {
            "rollContext": "secondary",
            "rollType": "invalid"
        }
        
        with pytest.raises(ValidationError, match="Invalid secondary roll type"):
            validate_roll_payload(payload)
    
    def test_validate_roll_payload_not_dict(self):
        """Test payload that is not a dictionary"""
        with pytest.raises(ValidationError, match="Payload must be a dictionary"):
            validate_roll_payload("not a dict")
    
    def test_validate_discord_message_valid(self):
        """Test valid Discord message"""
        message = "Test message"
        
        # Should not raise exception
        validate_discord_message(message)
    
    def test_validate_discord_message_empty(self):
        """Test empty Discord message"""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_discord_message("")
    
    def test_validate_discord_message_not_string(self):
        """Test non-string Discord message"""
        with pytest.raises(ValidationError, match="must be a string"):
            validate_discord_message(123)
    
    def test_validate_discord_message_too_long(self):
        """Test Discord message that's too long"""
        long_message = "x" * 2001
        
        with pytest.raises(ValidationError, match="exceeds 2000 character limit"):
            validate_discord_message(long_message)