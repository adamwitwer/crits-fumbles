"""Unit tests for dice service"""

import pytest
from unittest.mock import patch
from app.services.dice_service import DiceService
from app.utils.exceptions import InvalidTableError, InvalidRollValueError

class TestDiceService:
    """Test cases for DiceService"""
    
    def test_resolve_roll_with_single_value(self, data_service_with_mocks):
        """Test resolving roll with single value match"""
        service = DiceService(data_service_with_mocks)
        table = {"5": "Success", "10": "Critical"}
        
        result = service.resolve_roll(5, table)
        assert result == "Success"
    
    def test_resolve_roll_with_range(self, data_service_with_mocks):
        """Test resolving roll with range match"""
        service = DiceService(data_service_with_mocks)
        table = {"1-5": "Low", "6-10": "High"}
        
        result = service.resolve_roll(3, table)
        assert result == "Low"
        
        result = service.resolve_roll(8, table)
        assert result == "High"
    
    def test_resolve_roll_invalid_table(self, data_service_with_mocks):
        """Test resolve_roll with invalid table"""
        service = DiceService(data_service_with_mocks)
        
        with pytest.raises(InvalidTableError):
            service.resolve_roll(5, "not a dict")
    
    def test_resolve_roll_invalid_value(self, data_service_with_mocks):
        """Test resolve_roll with invalid roll value"""
        service = DiceService(data_service_with_mocks)
        table = {"1-5": "Success"}
        
        with pytest.raises(InvalidRollValueError):
            service.resolve_roll("invalid", table)
    
    def test_resolve_roll_no_match(self, data_service_with_mocks):
        """Test resolve_roll with no matching entry"""
        service = DiceService(data_service_with_mocks)
        table = {"1-5": "Success"}
        
        with pytest.raises(InvalidRollValueError):
            service.resolve_roll(10, table)
    
    @patch('random.randint')
    def test_roll_critical_hit_sterling_vermin(self, mock_random, data_service_with_mocks):
        """Test critical hit roll for Sterling Vermin"""
        mock_random.return_value = 3
        service = DiceService(data_service_with_mocks)
        
        result = service.roll_critical_hit("Sterling Vermin", "slashing")
        
        assert result["die_type"] == "d20"
        assert result["roll_value"] == 3
        assert result["result_text"] == "Minor cut"
    
    @patch('random.randint')
    def test_roll_fumble_bcoydog(self, mock_random, data_service_with_mocks):
        """Test fumble roll for BCoydog"""
        mock_random.return_value = 15
        service = DiceService(data_service_with_mocks)
        
        result = service.roll_fumble("BCoydog", "melee")
        
        assert result["die_type"] == "d100"
        assert result["roll_value"] == 15
        assert result["description"] == "Weapon slips"
        assert result["effect"] == "Drop weapon"
    
    def test_check_secondary_effects_minor_injury(self, data_service_with_mocks):
        """Test secondary effect detection for minor injury"""
        service = DiceService(data_service_with_mocks)
        
        result = service._check_secondary_effects("This causes a minor injury")
        
        assert result is not None
        assert result["type"] == "minor"
        assert result["prompt"] == "Minor Injury!"
    
    def test_check_secondary_effects_none(self, data_service_with_mocks):
        """Test no secondary effects detected"""
        service = DiceService(data_service_with_mocks)
        
        result = service._check_secondary_effects("Normal damage")
        
        assert result is None