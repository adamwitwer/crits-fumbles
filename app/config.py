import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask settings
    FLASK_APP = 'app.app'
    
    # Discord integration
    DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
    
    # Logging configuration
    LOG_STORAGE_DIR = os.environ.get('LOG_STORAGE_DIR', '.')
    LOG_FILENAME = "narrative_dice_log.jsonl"
    
    # Security headers
    CSP_POLICY = (
        "default-src 'none';"
        "script-src 'self' 'sha256-xkCWla5qon65vOIHCOs7ZCr8zHIHr0UgJN5eX5r7PXU=';"
        "style-src 'self' 'unsafe-inline';"
        "img-src 'self' data:;"
        "media-src 'self';"
        "font-src 'self';"
        "connect-src 'self' http://ip-api.com;"
        "form-action 'self';"
        "frame-ancestors 'none';"
        "base-uri 'self';"
        "object-src 'none';"
        "worker-src 'self';"
        "manifest-src 'self';"
    )
    
    # Narrative logging descriptors
    RANDOM_DESCRIPTORS = [
        "an intrepid adventurer", "a curious scholar", "a daring rogue",
        "a wise wizard", "a valiant knight", "a mysterious stranger",
        "a lucky gambler", "an unfortunate soul", "a cautious traveler",
        "a brave hero", "a cunning strategist", "a wandering minstrel",
        "a forgotten deity", "a mischievous sprite", "a stoic guardian"
    ]
    
    # Data file paths
    CRIT_DATA_FILE = "critical_hits_master.json"
    FUMBLE_DATA_FILE = "fumbles_master.json"
    
    @property
    def log_file_path(self):
        """Get the full path to the log file"""
        return os.path.join(self.LOG_STORAGE_DIR, self.LOG_FILENAME)