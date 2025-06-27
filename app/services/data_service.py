"""Data loading and management service"""

import json
import os
import time
from flask import current_app
from ..utils.exceptions import DataLoadError

class DataService:
    """Service for loading and managing JSON data files with caching"""
    
    def __init__(self):
        self._crit_data = None
        self._fumble_data = None
        self._crit_data_mtime = None
        self._fumble_data_mtime = None
    
    def load_json(self, filename):
        """Load JSON data from file"""
        json_path = os.path.join(os.path.dirname(__file__), '..', filename)
        try:
            with open(json_path) as f:
                return json.load(f)
        except FileNotFoundError:
            try:
                current_app.logger.error(f"Error: JSON file not found at {json_path}")
            except RuntimeError:
                pass
            raise DataLoadError(f"JSON file not found: {filename}")
        except json.JSONDecodeError as e:
            try:
                current_app.logger.error(f"Error: Could not decode JSON from {json_path}: {e}")
            except RuntimeError:
                pass
            raise DataLoadError(f"Could not decode JSON from {filename}: {e}")
        except Exception as e:
            try:
                current_app.logger.error(f"Unexpected error loading {json_path}: {e}")
            except RuntimeError:
                pass
            raise DataLoadError(f"Unexpected error loading {filename}: {e}")
    
    def get_file_mtime(self, filename):
        """Get file modification time"""
        json_path = os.path.join(os.path.dirname(__file__), '..', filename)
        try:
            return os.path.getmtime(json_path)
        except OSError:
            return None
    
    def should_reload_data(self, filename, cached_mtime):
        """Check if data should be reloaded based on file modification time"""
        if cached_mtime is None:
            return True
        current_mtime = self.get_file_mtime(filename)
        return current_mtime is None or current_mtime > cached_mtime
    
    @property
    def crit_data(self):
        """Get critical hits data, loading if necessary"""
        filename = "critical_hits_master.json"
        if self.should_reload_data(filename, self._crit_data_mtime):
            self._crit_data = self.load_json(filename)
            self._crit_data_mtime = self.get_file_mtime(filename)
            if not self._crit_data:
                try:
                    current_app.logger.warning("CRIT_DATA is empty or failed to load.")
                except RuntimeError:
                    pass
        return self._crit_data
    
    @property
    def fumble_data(self):
        """Get fumble data, loading if necessary"""
        filename = "fumbles_master.json"
        if self.should_reload_data(filename, self._fumble_data_mtime):
            self._fumble_data = self.load_json(filename)
            self._fumble_data_mtime = self.get_file_mtime(filename)
            if not self._fumble_data:
                try:
                    current_app.logger.warning("FUMBLE_DATA is empty or failed to load.")
                except RuntimeError:
                    pass
        return self._fumble_data
    
    def reload_data(self):
        """Force reload of all data files"""
        self._crit_data = None
        self._fumble_data = None
        self._crit_data_mtime = None
        self._fumble_data_mtime = None
        # Trigger loading
        _ = self.crit_data
        _ = self.fumble_data
    
    def get_cache_stats(self):
        """Get caching statistics"""
        return {
            "crit_data_cached": self._crit_data is not None,
            "fumble_data_cached": self._fumble_data is not None,
            "crit_data_mtime": self._crit_data_mtime,
            "fumble_data_mtime": self._fumble_data_mtime
        }