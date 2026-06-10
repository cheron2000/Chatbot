# Quick Reference Guide

## Common Commands

### Setup
```bash
# Install dependencies
py -3.10 -m pip install -r requirements.txt

# Clean up legacy files
cleanup.bat

# Set environment variables
set SECRET_KEY=your-secret-key
set AWS_REGION=us-east-1
```

### Running
```bash
# Development mode
py -3.10 app_refactored.py

# Production mode (with gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app_refactored:create_app()"
```

### Testing
```bash
# Test imports
py -3.10 -c "from app_refactored import create_app; print('OK')"

# Test AWS connection
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

## Configuration Quick Reference

### Security Settings (config.py)
```python
enable_infiltration_mode: bool = False  # Keep disabled in production
infiltration_auto_block: bool = True    # Keep enabled for security
```

### Memory Settings (config.py)
```python
max_short_term: int = 10                # Recent messages in session
max_summary_tokens: int = 200           # Long-term summary size
enable_vector_memory: bool = True       # Semantic search
vector_search_results: int = 3          # Results per search
```

### Rate Limiting (config.py)
```python
default_limit: str = "200 per day"      # Global limit
chat_limit: str = "20 per minute"       # Chat endpoint limit
```

## API Endpoints

### GET /
Home page with chat interface

### POST /chat
Send message and receive streaming response
```json
{
  "message": "Your message here"
}
```

### POST /clear
Clear conversation history
```json
{
  "status": "cleared"
}
```

### POST /infiltration/toggle
Toggle infiltration mode (if enabled)

### GET /infiltration/status
Get infiltration mode status

## File Structure

```
Chatbot/
├── app_refactored.py          # Main application
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
│
├── models/
│   ├── memory.py             # Long-term memory
│   └── vector_memory.py      # Vector search
│
├── services/
│   ├── bedrock.py            # AWS Bedrock client
│   └── streaming.py          # Streaming with fallback
│
├── routes/
│   ├── main.py               # Home route
│   └── chat.py               # Chat routes
│
├── utils/
│   ├── formatting.py         # Text formatting
│   ├── validators.py         # Input validation
│   ├── attack_detector.py    # Security detection
│   └── prompt_enhancer.py    # Prompt improvement
│
└── templates/
    └── index.html            # Frontend
```

## Environment Variables

### Required
```bash
SECRET_KEY=your-secret-key-here
```

### Optional
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## Troubleshooting Quick Fixes

### "Module not found" error
```bash
py -3.10 -m pip install -r requirements.txt
```

### "SECRET_KEY warning"
```bash
set SECRET_KEY=%RANDOM%%RANDOM%%RANDOM%
```

### "AWS credentials not found"
```bash
aws configure
```

### "Port already in use"
```bash
# Change port in app_refactored.py
app.run(host="0.0.0.0", port=5001, debug=True, threaded=True)
```

### "Vector DB error"
```bash
# Delete and recreate
rmdir /S /Q vector_db
# Restart application
```

### "Session error"
```bash
# Clear sessions
rmdir /S /Q .flask_sessions
# Restart application
```

## Security Checklist

- [ ] SECRET_KEY set via environment variable
- [ ] infiltration_mode disabled in production
- [ ] infiltration_auto_block enabled
- [ ] HTTPS configured (production)
- [ ] Rate limiting configured
- [ ] AWS credentials secured (IAM roles preferred)
- [ ] Dependencies pinned and up-to-date
- [ ] Logs monitored
- [ ] Backups configured

## Performance Tips

1. **Use Redis for sessions** (production)
   ```python
   app.config["SESSION_TYPE"] = "redis"
   ```

2. **Use Redis for rate limiting** (distributed)
   ```python
   storage_uri="redis://localhost:6379"
   ```

3. **Enable caching** for static assets

4. **Use CDN** for frontend resources

5. **Monitor memory usage** of vector DB

## Backup Commands

```bash
# Backup memory
xcopy memory memory_backup_%date% /E /I

# Backup vector DB
xcopy vector_db vector_db_backup_%date% /E /I

# Backup sessions
xcopy .flask_sessions sessions_backup_%date% /E /I
```

## Monitoring

### Check logs
```bash
# Application logs (if configured)
type app.log

# System logs
type nul > app.log  # Create log file
```

### Check memory usage
```bash
# Vector DB stats (add to code)
print(vector_memory.get_stats())
```

### Check rate limits
```bash
# Monitor rate limit hits in logs
# Look for 429 status codes
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Import errors | Run `pip install -r requirements.txt` |
| AWS errors | Check credentials with `aws sts get-caller-identity` |
| Memory errors | Clear `memory/` and `vector_db/` directories |
| Session errors | Clear `.flask_sessions/` directory |
| Port conflicts | Change port in `app_refactored.py` |
| SECRET_KEY warning | Set `SECRET_KEY` environment variable |

## Support

For issues:
1. Check `README.md` troubleshooting section
2. Review `CHANGELOG.md` for recent changes
3. Check `IMPROVEMENTS.md` for migration guide
4. Review application logs
5. Open GitHub issue

## Quick Links

- Main app: `app_refactored.py`
- Config: `config.py`
- Routes: `routes/chat.py`
- Memory: `models/memory.py`
- Vector: `models/vector_memory.py`
- Security: `utils/attack_detector.py`
