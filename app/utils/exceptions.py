"""Custom exception classes for the dice rolling application"""

class DiceRollError(Exception):
    """Base exception for dice rolling errors"""
    pass

class InvalidTableError(DiceRollError):
    """Raised when an invalid table is accessed"""
    pass

class InvalidRollValueError(DiceRollError):
    """Raised when an invalid roll value is provided"""
    pass

class DataLoadError(DiceRollError):
    """Raised when JSON data files cannot be loaded"""
    pass

class GeolocationError(Exception):
    """Raised when geolocation services fail"""
    pass

class ValidationError(Exception):
    """Raised when input validation fails"""
    pass