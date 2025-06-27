"""Service for managing custom dice tables"""

import json
import os
import datetime
from flask import current_app
from ..config import Config
from ..utils.exceptions import DataLoadError, ValidationError

class CustomTablesService:
    """Service for creating and managing custom dice tables"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.custom_tables_file = os.path.join(self.config.LOG_STORAGE_DIR, "custom_tables.json")
        self._custom_tables = None
    
    def load_custom_tables(self):
        """Load custom tables from file"""
        if not os.path.exists(self.custom_tables_file):
            return {"tables": {}, "metadata": {"created": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
        
        try:
            with open(self.custom_tables_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            try:
                current_app.logger.error(f"Error loading custom tables: {e}")
            except RuntimeError:
                pass
            return {"tables": {}, "metadata": {"created": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
    
    def save_custom_tables(self, tables_data):
        """Save custom tables to file"""
        try:
            tables_data["metadata"]["last_modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with open(self.custom_tables_file, "w", encoding="utf-8") as f:
                json.dump(tables_data, f, indent=2)
        except Exception as e:
            try:
                current_app.logger.error(f"Error saving custom tables: {e}")
            except RuntimeError:
                pass
            raise DataLoadError(f"Failed to save custom tables: {e}")
    
    @property
    def custom_tables(self):
        """Get custom tables, loading if necessary"""
        if self._custom_tables is None:
            self._custom_tables = self.load_custom_tables()
        return self._custom_tables
    
    def create_table(self, table_name, table_type, table_data, description=""):
        """Create a new custom table"""
        self.validate_table_data(table_data, table_type)
        
        tables = self.custom_tables
        
        if table_name in tables["tables"]:
            raise ValidationError(f"Table '{table_name}' already exists")
        
        new_table = {
            "type": table_type,
            "description": description,
            "data": table_data,
            "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "usage_count": 0
        }
        
        tables["tables"][table_name] = new_table
        self.save_custom_tables(tables)
        self._custom_tables = tables
        
        return new_table
    
    def update_table(self, table_name, table_data=None, description=None):
        """Update an existing custom table"""
        tables = self.custom_tables
        
        if table_name not in tables["tables"]:
            raise ValidationError(f"Table '{table_name}' does not exist")
        
        table = tables["tables"][table_name]
        
        if table_data is not None:
            self.validate_table_data(table_data, table["type"])
            table["data"] = table_data
        
        if description is not None:
            table["description"] = description
        
        table["last_modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        self.save_custom_tables(tables)
        self._custom_tables = tables
        
        return table
    
    def delete_table(self, table_name):
        """Delete a custom table"""
        tables = self.custom_tables
        
        if table_name not in tables["tables"]:
            raise ValidationError(f"Table '{table_name}' does not exist")
        
        deleted_table = tables["tables"].pop(table_name)
        self.save_custom_tables(tables)
        self._custom_tables = tables
        
        return deleted_table
    
    def get_table(self, table_name):
        """Get a specific custom table"""
        tables = self.custom_tables
        
        if table_name not in tables["tables"]:
            raise ValidationError(f"Table '{table_name}' does not exist")
        
        return tables["tables"][table_name]
    
    def list_tables(self):
        """List all custom tables"""
        tables = self.custom_tables
        
        table_list = []
        for name, table_data in tables["tables"].items():
            table_list.append({
                "name": name,
                "type": table_data["type"],
                "description": table_data["description"],
                "created": table_data["created"],
                "usage_count": table_data.get("usage_count", 0),
                "entry_count": len(table_data["data"])
            })
        
        return table_list
    
    def increment_usage(self, table_name):
        """Increment usage count for a table"""
        tables = self.custom_tables
        
        if table_name in tables["tables"]:
            tables["tables"][table_name]["usage_count"] = tables["tables"][table_name].get("usage_count", 0) + 1
            self.save_custom_tables(tables)
            self._custom_tables = tables
    
    def validate_table_data(self, table_data, table_type):
        """Validate table data structure"""
        if not isinstance(table_data, (dict, list)):
            raise ValidationError("Table data must be a dictionary or list")
        
        if table_type in ["critical", "fumble"] and isinstance(table_data, dict):
            # Validate range-based table (e.g., {"1-5": "result", "6-10": "other result"})
            for key, value in table_data.items():
                if not isinstance(value, str):
                    raise ValidationError(f"Table entry values must be strings, got {type(value)} for key '{key}'")
                
                # Validate range format
                if '-' in key:
                    try:
                        start, end = map(int, key.split('-'))
                        if start >= end:
                            raise ValidationError(f"Invalid range '{key}': start must be less than end")
                    except ValueError:
                        raise ValidationError(f"Invalid range format '{key}': must be 'start-end' or single number")
                else:
                    try:
                        int(key)
                    except ValueError:
                        raise ValidationError(f"Invalid key '{key}': must be a number or range")
        
        elif table_type == "fumble" and isinstance(table_data, list):
            # Validate fumble list format (e.g., [{"roll": "1-25", "description": "...", "effect": "..."}])
            for i, entry in enumerate(table_data):
                if not isinstance(entry, dict):
                    raise ValidationError(f"Fumble entry {i} must be a dictionary")
                
                required_fields = ["roll", "description", "effect"]
                for field in required_fields:
                    if field not in entry:
                        raise ValidationError(f"Fumble entry {i} missing required field '{field}'")
                    if not isinstance(entry[field], str):
                        raise ValidationError(f"Fumble entry {i} field '{field}' must be a string")
        
        else:
            raise ValidationError(f"Unsupported table type '{table_type}' or data format")
    
    def import_table_from_json(self, json_data, table_name=None):
        """Import a table from JSON data"""
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            # Extract table information
            table_name = table_name or data.get("name", "imported_table")
            table_type = data.get("type", "critical")
            description = data.get("description", "Imported table")
            table_data = data.get("data", data)  # If no 'data' key, use whole object
            
            return self.create_table(table_name, table_type, table_data, description)
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON data: {e}")
        except Exception as e:
            raise ValidationError(f"Failed to import table: {e}")
    
    def export_table_to_json(self, table_name):
        """Export a table to JSON format"""
        table = self.get_table(table_name)
        
        export_data = {
            "name": table_name,
            "type": table["type"],
            "description": table["description"],
            "data": table["data"],
            "created": table["created"],
            "exported": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        return export_data