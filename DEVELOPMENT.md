# Development Documentation

## Architecture Overview

The D&D Crits & Fumbles application follows a modular, service-oriented architecture:

```
app/
├── config.py                    # Application configuration
├── app_refactored.py           # Main application factory
├── services/                   # Business logic layer
│   ├── data_service.py         # JSON data loading with caching
│   ├── dice_service.py         # Core dice rolling logic
│   ├── geolocation_service.py  # IP geolocation resolution
│   ├── logging_service.py      # Narrative logging system
│   ├── statistics_service.py   # Roll analytics and statistics
│   ├── custom_tables_service.py # Custom table management
│   └── roll_service.py         # Main roll orchestration
├── routes/                     # HTTP endpoints
│   ├── main.py                 # Main application routes
│   ├── api.py                  # Legacy API endpoints
│   └── api_v1.py              # RESTful API v1
└── utils/                      # Utilities and helpers
    ├── exceptions.py           # Custom exception hierarchy
    └── validators.py           # Input validation logic
```

## Key Design Patterns

### 1. **Service Layer Pattern**
- Business logic encapsulated in service classes
- Services are injected into route handlers
- Clear separation of concerns

### 2. **Application Factory Pattern**
- Flask app created by `create_app()` function
- Configuration passed as parameter
- Enables easy testing with different configs

### 3. **Dependency Injection**
- Services passed to route registration functions
- Loose coupling between components
- Easy mocking for tests

### 4. **Error Handling Hierarchy**
- Custom exceptions for different error types
- Graceful degradation when services fail
- Consistent error responses

## Core Services

### DataService
**Purpose:** Manages JSON data loading with caching and file modification detection.

**Key Features:**
- Automatic cache invalidation based on file modification time
- Graceful handling of file system errors
- Thread-safe property-based access

**Usage Example:**
```python
data_service = DataService()
crit_data = data_service.crit_data  # Loads and caches if needed
fumble_data = data_service.fumble_data  # Loads and caches if needed
data_service.reload_data()  # Force reload
```

### DiceService  
**Purpose:** Core dice rolling logic and result resolution.

**Key Features:**
- Supports multiple table formats (range-based, list-based)
- Automatic secondary effect detection
- Extensible for new dice types and sources

**Roll Resolution Algorithm:**
1. Validate table data structure
2. Generate random value based on die type
3. Find matching entry in table
4. Parse result based on source format
5. Check for secondary effects (injuries, insanity)

### RollService
**Purpose:** Main orchestration service that coordinates all roll operations.

**Workflow:**
1. Validate input payload
2. Resolve geolocation for logging
3. Delegate to appropriate service (crit/fumble/secondary)
4. Log successful results
5. Return formatted response

### StatisticsService
**Purpose:** Analyzes roll patterns and generates analytics.

**Capabilities:**
- Roll distribution analysis
- Table usage tracking
- Temporal pattern detection
- Streak identification
- Export to multiple formats

## Database Schema (File-based)

### Log Files
- **narrative_dice_log.jsonl**: JSONL format for roll logs
- **roll_statistics.json**: Cached statistics data
- **custom_tables.json**: User-created custom tables

### Log Entry Format
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "narrative": "A brave hero from Seattle, WA rolled 15...",
  "raw_payload": {...},
  "raw_response": {...}
}
```

## Testing Strategy

### Unit Tests
- Service layer components tested in isolation
- Mock external dependencies (file system, HTTP)
- Validate business logic correctness

### Integration Tests  
- Full request/response cycles
- Real Flask application context
- API endpoint functionality

### Test Structure
```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── unit/
│   ├── test_dice_service.py
│   ├── test_validators.py
│   └── test_statistics_service.py
└── integration/
    └── test_roll_endpoints.py
```

## Performance Considerations

### Caching Strategy
- **JSON Data**: Cached in memory, reloaded on file modification
- **Statistics**: Computed on demand, optionally cached to disk
- **Geolocation**: Results not cached (privacy concern)

### Memory Usage
- JSON data kept in memory for fast access
- Log files streamed during statistics computation
- Custom tables stored separately to avoid bloat

### Scalability
- Stateless services enable horizontal scaling
- File-based persistence for simplicity
- Consider database migration for high volume

## Security Implementation

### Input Validation
- All payloads validated before processing
- Type checking and range validation
- Protection against injection attacks

### Data Privacy
- IP addresses redacted in logs
- No sensitive data persistence
- Optional Discord webhook integration

### Content Security Policy
- Strict CSP headers prevent XSS
- Script execution limited to known sources
- External resources restricted

## Error Handling Philosophy

### Exception Hierarchy
```python
DiceRollError              # Base dice rolling error
├── InvalidTableError      # Invalid table structure
├── InvalidRollValueError  # Invalid roll value
└── DataLoadError         # File loading error

ValidationError           # Input validation failure
GeolocationError         # Geolocation service error
```

### Error Response Strategy
1. **User Errors (400)**: Validation failures, bad input
2. **Not Found (404)**: Missing resources
3. **Server Errors (500)**: Unexpected failures, logged for debugging

## Deployment Considerations

### Environment Variables
```bash
FLASK_APP=app.app_refactored    # Use refactored version
FLASK_ENV=development           # Enable debug mode
LOG_STORAGE_DIR=/app/logs       # Custom log directory
DISCORD_WEBHOOK_URL=...         # Optional Discord integration
```

### Production Checklist
- [ ] Set `FLASK_ENV=production`
- [ ] Configure proper log directory with write permissions
- [ ] Set up log rotation for narrative logs
- [ ] Monitor disk usage for log files
- [ ] Configure reverse proxy with proper headers
- [ ] Set up health check monitoring (`/api/v1/health`)

### Docker Deployment
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.app_refactored:app"]
```

## Monitoring & Observability

### Health Checks
- **Endpoint**: `GET /api/v1/health`
- **Checks**: Data loading, cache status, disk space
- **Response Time**: < 100ms typical

### Logging Strategy
- **Application Logs**: Standard Python logging to stdout/stderr
- **Access Logs**: Handled by reverse proxy (nginx/apache)
- **Narrative Logs**: Custom JSONL format for roll tracking

### Metrics to Monitor
- Request rate and response time
- Error rate by endpoint
- Cache hit/miss ratio
- Log file size growth
- Custom table creation rate

## Contributing Guidelines

### Code Style
- Follow PEP 8 formatting
- Use type hints where beneficial
- Document complex algorithms
- Keep functions focused and small

### Testing Requirements
- All new features must include tests
- Maintain >90% test coverage
- Test both success and failure cases
- Include integration tests for new endpoints

### Pull Request Process
1. Create feature branch from main
2. Implement changes with tests
3. Update documentation as needed
4. Run full test suite
5. Submit PR with clear description

## Future Enhancements

### Planned Features
- Real-time roll sharing via WebSockets
- Roll replay and analysis tools
- Advanced statistics visualization
- Mobile app integration via API
- Multi-language support

### Technical Debt
- Consider migrating to proper database for high volume
- Implement rate limiting for API endpoints
- Add API versioning strategy
- Enhance error tracking and reporting

## Troubleshooting

### Common Issues

**"Working outside of application context" errors**
- Occurs when services try to use Flask's `current_app` outside request context
- Solution: Wrap Flask-dependent code in try/except blocks for graceful degradation

**Cache not updating after file changes**
- Check file modification time resolution on your system
- Force reload using `/api/v1/cache/reload` endpoint

**Large log files**
- Implement log rotation strategy
- Consider archiving old statistics data
- Monitor disk usage regularly

### Debug Mode
```bash
FLASK_ENV=development python -m flask run --debug
```

### Test Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_dice_service.py -v
```