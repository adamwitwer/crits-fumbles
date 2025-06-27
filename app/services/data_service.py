"""Data loading and management service"""

import json
import os
from flask import current_app
from ..utils.exceptions import DataLoadError

class DataService:
    """Service for loading and managing JSON data files"""
    
    def __init__(self):
        self._crit_data = None
        self._fumble_data = None
    
    def load_json(self, filename):
        """Load JSON data from file"""
        json_path = os.path.join(os.path.dirname(__file__), '..', filename)
        try:
            with open(json_path) as f:
                return json.load(f)
        except FileNotFoundError:
            current_app.logger.error(f"Error: JSON file not found at {json_path}")
            raise DataLoadError(f"JSON file not found: {filename}")
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Error: Could not decode JSON from {json_path}: {e}")
            raise DataLoadError(f"Could not decode JSON from {filename}: {e}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error loading {json_path}: {e}")
            raise DataLoadError(f"Unexpected error loading {filename}: {e}")
    
    @property
    def crit_data(self):
        """Get critical hits data, loading if necessary"""
        if self._crit_data is None:
            self._crit_data = self.load_json("critical_hits_master.json")
            if not self._crit_data:
                current_app.logger.warning("CRIT_DATA is empty or failed to load.")
        return self._crit_data
    
    @property
    def fumble_data(self):
        """Get fumble data, loading if necessary"""
        if self._fumble_data is None:
            self._fumble_data = self.load_json("fumbles_master.json")
            if not self._fumble_data:
                current_app.logger.warning("FUMBLE_DATA is empty or failed to load.")
        return self._fumble_data
    
    def reload_data(self):
        """Force reload of all data files"""
        self._crit_data = None
        self._fumble_data = None
        # Trigger loading
        _ = self.crit_data
        _ = self.fumble_data