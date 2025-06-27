# D&D Crits & Fumbles API Documentation

## Overview

The D&D Crits & Fumbles application provides both legacy endpoints and a comprehensive RESTful API v1 for external integration. This API allows you to:

- Roll dice using various critical hit and fumble tables
- Manage custom dice tables
- Access roll statistics and analytics
- Export/import roll history
- Retrieve application health and cache status

## Base URL

```
Local Development: http://localhost:5000
Production: https://your-domain.com
```

## Authentication

Currently, no authentication is required for API access. Rate limiting may be implemented in future versions.

---

## API Endpoints

### Legacy Endpoints (Compatibility)

#### `POST /roll`
Roll dice using the main application interface.

**Request Body:**
```json
{
  "rollContext": "primary|secondary",
  "rollType": "crit|fumble|minor|major|insanity",
  "critSource": "Sterling Vermin|Questionable Arcana|BCoydog",
  "damageType": "slashing|piercing|bludgeoning|magic|etc",
  "magicSubtype": "fire|cold|lightning|etc",
  "fumbleType": "Questionable Arcana|BCoydog",
  "attackType": "Weapon|Magic|melee|ranged|magic"
}
```

**Response:**
```json
{
  "status": "success|error",
  "rollValue": 15,
  "dieType": "d20",
  "description": "Result description",
  "effect": "Mechanical effect",
  "isSecondaryPrompt": false,
  "errorMessage": null
}
```

#### `GET /get_roll_history`
Get recent roll history (legacy format).

#### `POST /share_discord`
Share roll result to Discord webhook.

---

### API v1 Endpoints

#### Health & Status

##### `GET /api/v1/health`
Get application health status.

**Response:**
```json
{
  "status": "healthy|unhealthy",
  "version": "1.0",
  "data_loaded": {
    "critical_hits": true,
    "fumbles": true
  },
  "cache_stats": {
    "crit_data_cached": true,
    "fumble_data_cached": true
  }
}
```

#### Dice Rolling

##### `POST /api/v1/roll`
General dice rolling endpoint.

**Request Body:**
```json
{
  "rollContext": "primary",
  "rollType": "crit",
  "critSource": "Sterling Vermin",
  "damageType": "slashing"
}
```

##### `POST /api/v1/roll/critical`
Simplified critical hit endpoint.

**Request Body:**
```json
{
  "source": "Sterling Vermin",
  "damage_type": "slashing",
  "magic_subtype": "fire"
}
```

##### `POST /api/v1/roll/fumble`
Simplified fumble endpoint.

**Request Body:**
```json
{
  "source": "BCoydog",
  "attack_type": "melee"
}
```

#### Table Management

##### `GET /api/v1/tables`
Get all available built-in tables.

**Response:**
```json
{
  "critical_hits": {
    "Sterling Vermin": {
      "damage_types": ["slashing", "piercing", "bludgeoning"],
      "total_tables": 15
    }
  },
  "fumbles": {
    "BCoydog": {
      "attack_types": ["melee", "ranged", "magic"],
      "total_tables": 3
    }
  }
}
```

##### `GET /api/v1/tables/{table_type}/{source}/{table_name}`
Get a specific built-in table.

**Parameters:**
- `table_type`: "critical" or "fumble"
- `source`: Table source (e.g., "Sterling Vermin")
- `table_name`: Specific table name (e.g., "slashing")

#### Custom Tables

##### `GET /api/v1/custom-tables`
List all custom tables.

**Response:**
```json
{
  "tables": [
    {
      "name": "my_custom_crit",
      "type": "critical",
      "description": "Custom critical hit table",
      "created": "2024-01-01T12:00:00Z",
      "usage_count": 5,
      "entry_count": 20
    }
  ]
}
```

##### `POST /api/v1/custom-tables`
Create a new custom table.

**Request Body:**
```json
{
  "name": "my_custom_table",
  "type": "critical",
  "description": "My awesome custom table",
  "data": {
    "1-5": "Minor effect",
    "6-10": "Moderate effect",
    "11-20": "Major effect"
  }
}
```

##### `GET /api/v1/custom-tables/{table_name}`
Get a specific custom table.

##### `PUT /api/v1/custom-tables/{table_name}`
Update a custom table.

**Request Body:**
```json
{
  "data": {
    "1-5": "Updated minor effect",
    "6-15": "Updated major effect",
    "16-20": "Critical effect"
  },
  "description": "Updated description"
}
```

##### `DELETE /api/v1/custom-tables/{table_name}`
Delete a custom table.

##### `GET /api/v1/custom-tables/{table_name}/export`
Export a custom table to JSON.

##### `POST /api/v1/custom-tables/import`
Import a custom table from JSON.

**Request Body:**
```json
{
  "name": "imported_table",
  "table_data": {
    "type": "critical",
    "description": "Imported from another source",
    "data": {
      "1-10": "Light wound",
      "11-20": "Serious wound"
    }
  }
}
```

#### Statistics & Analytics

##### `GET /api/v1/statistics`
Get comprehensive roll statistics.

**Response:**
```json
{
  "total_rolls": 150,
  "roll_distribution": {
    "1": 8,
    "2": 7,
    "20": 9
  },
  "table_usage": {
    "Sterling Vermin Crit (slashing)": 45,
    "BCoydog Fumble (melee)": 23
  },
  "time_analysis": {
    "hourly_distribution": {
      "14": 15,
      "15": 23,
      "20": 18
    },
    "daily_distribution": {
      "Monday": 25,
      "Friday": 40
    }
  },
  "dice_analysis": {
    "d20_analysis": {
      "count": 75,
      "average": 10.5,
      "crits": 4,
      "fumbles": 3,
      "streaks": {
        "longest_high": 3,
        "longest_low": 2
      }
    }
  }
}
```

#### Data Export

##### `GET /api/v1/export/history?format=json|csv`
Export roll history in JSON or CSV format.

**Query Parameters:**
- `format`: "json" or "csv" (default: "json")

**Response:** File download with appropriate content type.

##### `GET /api/v1/export/statistics`
Export statistics data as JSON file.

#### Cache Management

##### `GET /api/v1/cache/stats`
Get caching statistics.

##### `POST /api/v1/cache/reload`
Force reload of data cache.

---

## Data Formats

### Custom Table Data Formats

#### Critical Hit Tables (Dictionary Format)
```json
{
  "1-5": "Minor cut, no additional effect",
  "6-10": "Deep gash, bleeding for 1 round",
  "11-15": "Severe wound, disadvantage on next attack",
  "16-20": "Critical injury, major injury roll"
}
```

#### Fumble Tables (List Format)
```json
[
  {
    "roll": "1-25",
    "description": "Weapon flies from grip",
    "effect": "Drop weapon, move 10 feet in random direction"
  },
  {
    "roll": "26-50", 
    "description": "Stumble forward",
    "effect": "Move 5 feet toward target, fall prone"
  }
]
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error description",
  "status": "error"
}
```

### Common HTTP Status Codes

- `200`: Success
- `201`: Created (for POST operations)
- `400`: Bad Request (validation error)
- `404`: Not Found
- `500`: Internal Server Error

---

## Examples

### Rolling a Critical Hit
```bash
curl -X POST http://localhost:5000/api/v1/roll/critical \
  -H "Content-Type: application/json" \
  -d '{
    "source": "Sterling Vermin",
    "damage_type": "slashing"
  }'
```

### Creating a Custom Table
```bash
curl -X POST http://localhost:5000/api/v1/custom-tables \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_poison_crits",
    "type": "critical", 
    "description": "Critical hits for poison damage",
    "data": {
      "1-10": "Target is poisoned for 1 round",
      "11-15": "Target is poisoned for 1 minute", 
      "16-20": "Target is poisoned and paralyzed for 1 round"
    }
  }'
```

### Exporting Roll History as CSV
```bash
curl -o roll_history.csv \
  "http://localhost:5000/api/v1/export/history?format=csv"
```

### Getting Statistics
```bash
curl http://localhost:5000/api/v1/statistics
```

---

## Rate Limiting

Currently no rate limiting is implemented. Future versions may include:
- 100 requests per minute per IP
- 1000 requests per hour per IP
- Custom table operations limited to 10 per minute

---

## Changelog

### Version 1.0 (Current)
- Initial API release
- Full CRUD operations for custom tables
- Statistics and analytics endpoints
- Export/import functionality
- Health monitoring
- Cache management

---

## Support

For API support, please:
1. Check this documentation
2. Review the application logs
3. Create an issue in the project repository
4. Include request/response examples and error messages