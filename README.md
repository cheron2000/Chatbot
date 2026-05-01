# ORACLE AI Chat

A Flask-based AI chatbot with AWS Bedrock integration, featuring dual memory system, model fallback, and real-time streaming responses.

## Features

-  **Multi-Model Support**: Claude 3 Haiku + NVIDIA Nemotron with automatic fallback
-  **Dual Memory System**: Short-term (10 messages) + long-term (AI-generated summaries)
-  **Real-time Streaming**: Server-sent events for token-by-token responses
-  **Token Analytics**: Track input/output tokens per message and session
-  **Beautiful UI**: Space-themed interface with animated background
-  **Rate Limiting**: 200 requests/day, 20/minute per IP
-  **Responsive Design**: Works on desktop and mobile

## Quick Start

### Prerequisites

- Python 3.10+
- AWS Account with Bedrock access
- AWS credentials configured

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Chatbot
```

2. Install dependencies:
```bash
py -3.10 -m pip install -r requirements.txt
```

3. Set environment variables (optional):
```bash
export SECRET_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

4. Run the application:
```bash
py -3.10 app_refactored.py
```

5. Open your browser:
```
http://localhost:5000
```

## Project Structure

```
Chatbot/
├── app_refactored.py          # Application entry point
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
│
├── models/
│   └── memory.py             # Conversation memory management
│
├── services/
│   ├── bedrock.py            # AWS Bedrock client
│   └── streaming.py          # Streaming with fallback
│
├── routes/
│   ├── main.py               # Home page
│   └── chat.py               # Chat endpoints
│
├── utils/
│   ├── formatting.py         # Text formatting
│   └── validators.py         # Input validation
│
└── templates/
    └── index.html            # Frontend interface
```

## Configuration

Edit `config.py` to customize:

```python
@dataclass
class AppConfig:
    max_message_length: int = 4000    # Max chars per message
    max_tokens: int = 4096            # Max tokens per response
    
    bedrock: BedrockConfig            # AWS Bedrock settings
    memory: MemoryConfig              # Memory settings
    rate_limit: RateLimitConfig       # Rate limiting
```

## API Endpoints

### `GET /`
Render the chat interface.

### `POST /chat`
Send a message and receive streaming response.

**Request:**
```json
{
  "message": "Hello, how are you?"
}
```

**Response:** Server-sent events stream
```
data: {"type": "token", "text": "Hello"}
data: {"type": "token", "text": "!"}
data: {"type": "done", "html": "<p>Hello!</p>", "input_tokens": 10, "output_tokens": 5}
```

### `POST /clear`
Clear conversation history.

**Response:**
```json
{
  "status": "cleared"
}
```

## Memory System

### Short-term Memory
- Stores last 10 messages in Flask session
- Fast access for recent context
- Cleared when session expires or manually cleared

### Long-term Memory
- AI-generated conversation summaries
- Stored as JSON files per session
- Updated asynchronously in background
- Persists across sessions

## Model Fallback

The application tries models in order:
1. **Anthropic Claude 3 Haiku** (primary)
2. **NVIDIA Nemotron Nano 12B** (fallback)

If a model fails before streaming starts, it automatically tries the next one.

## Testing

Run the test suite:
```bash
py -3.10 test_refactored.py
```

Expected output:
```
✓ Imports              PASSED
✓ Configuration        PASSED
✓ Formatting           PASSED
✓ Validators           PASSED
✓ App Creation         PASSED
```

## Development

### Running in Debug Mode
```bash
py -3.10 app_refactored.py
```
Debug mode is enabled by default. The app will auto-reload on code changes.

### Adding a New Model

1. Add model ID to `config.py`:
```python
models: List[str] = field(default_factory=lambda: [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "nvidia.nemotron-nano-12b-v2",
    "your-new-model-id",  # Add here
])
```

2. Add streaming method to `services/bedrock.py` if needed.

3. Update `services/streaming.py` to handle the new model.

### Adding a New Route

1. Create a new blueprint in `routes/`:
```python
# routes/your_route.py
from flask import Blueprint

your_bp = Blueprint('your_name', __name__)

@your_bp.route("/your-path")
def your_handler():
    return {"status": "ok"}
```

2. Register in `app_refactored.py`:
```python
from routes.your_route import your_bp
app.register_blueprint(your_bp)
```

## Deployment

### Production Considerations

1. **Use a production WSGI server**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app_refactored:create_app()"
```

2. **Set a strong secret key**:
```bash
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
```

3. **Configure AWS credentials** properly (IAM roles recommended)

4. **Set up HTTPS** (use nginx or AWS ALB)

5. **Enable logging**:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

6. **Use Redis for sessions** instead of filesystem:
```python
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.from_url("redis://localhost:6379")
```

## Troubleshooting

### App won't start
- Check Python version: `py -3.10 --version`
- Verify dependencies: `py -3.10 -m pip list`
- Check AWS credentials: `aws sts get-caller-identity`

### Models failing
- Verify Bedrock access in your AWS region
- Check model IDs are correct
- Ensure IAM permissions for Bedrock

### Memory issues
- Check `memory/` directory permissions
- Verify disk space available
- Check session directory: `.flask_sessions/`

### Rate limiting
- Adjust limits in `config.py`
- Use Redis for distributed rate limiting

## License

[Your License Here]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.

## Acknowledgments

- AWS Bedrock for AI models
- Flask for the web framework
- The open-source community
