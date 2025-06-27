"""Input validation utilities"""

from .exceptions import ValidationError

def validate_roll_payload(payload):
    """Validate roll payload structure and values"""
    if not isinstance(payload, dict):
        raise ValidationError("Payload must be a dictionary")
    
    # Required fields
    required_fields = ['rollContext']
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        raise ValidationError(f"Missing required fields: {missing_fields}")
    
    # Validate roll context
    valid_contexts = ['primary', 'secondary']
    if payload['rollContext'] not in valid_contexts:
        raise ValidationError(f"Invalid roll context: {payload['rollContext']}. Must be one of: {valid_contexts}")
    
    # Context-specific validation
    if payload['rollContext'] == 'primary':
        _validate_primary_roll(payload)
    elif payload['rollContext'] == 'secondary':
        _validate_secondary_roll(payload)

def _validate_primary_roll(payload):
    """Validate primary roll payload"""
    roll_type = payload.get('rollType')
    valid_roll_types = ['crit', 'fumble']
    
    if not roll_type:
        raise ValidationError("rollType is required for primary rolls")
    
    if roll_type not in valid_roll_types:
        raise ValidationError(f"Invalid roll type: {roll_type}. Must be one of: {valid_roll_types}")
    
    if roll_type == 'crit':
        _validate_crit_payload(payload)
    elif roll_type == 'fumble':
        _validate_fumble_payload(payload)

def _validate_secondary_roll(payload):
    """Validate secondary roll payload"""
    roll_type = payload.get('rollType')
    valid_secondary_types = ['minor', 'major', 'insanity']
    
    if not roll_type:
        raise ValidationError("rollType is required for secondary rolls")
    
    if roll_type not in valid_secondary_types:
        raise ValidationError(f"Invalid secondary roll type: {roll_type}. Must be one of: {valid_secondary_types}")

def _validate_crit_payload(payload):
    """Validate critical hit payload"""
    crit_source = payload.get('critSource')
    valid_sources = ['Sterling Vermin', 'Questionable Arcana', 'BCoydog']
    
    if crit_source and crit_source not in valid_sources:
        raise ValidationError(f"Invalid crit source: {crit_source}. Must be one of: {valid_sources}")

def _validate_fumble_payload(payload):
    """Validate fumble payload"""
    fumble_type = payload.get('fumbleType')
    valid_fumble_types = ['Questionable Arcana', 'BCoydog']
    
    if fumble_type and fumble_type not in valid_fumble_types:
        raise ValidationError(f"Invalid fumble type: {fumble_type}. Must be one of: {valid_fumble_types}")
    
    attack_type = payload.get('attackType')
    if fumble_type == 'BCoydog' and attack_type:
        valid_attack_types = ['melee', 'ranged', 'magic', 'Weapon', 'Magic']  # Support both formats
        if attack_type not in valid_attack_types:
            raise ValidationError(f"Invalid attack type for {fumble_type}: {attack_type}")

def validate_discord_message(message):
    """Validate Discord message content"""
    if not message:
        raise ValidationError("Discord message content cannot be empty")
    
    if not isinstance(message, str):
        raise ValidationError("Discord message must be a string")
    
    if len(message) > 2000:  # Discord character limit
        raise ValidationError("Discord message exceeds 2000 character limit")