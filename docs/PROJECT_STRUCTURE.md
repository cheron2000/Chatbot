# Project Structure

## Directory Overview

```
Chatbot/
├── 📄 Core Application Files
│   ├── app_refactored.py              # Main application entry point
│   ├── config.py                      # Configuration management
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment variables template
│   └── best_efficientnet_ham10000.pth # Trained model (15.61 MB)
│
├── 🧠 Models & Data Structures
│   ├── models/
│   │   ├── memory.py                  # Conversation memory management
│   │   └── classification.py          # Classification data models
│   │
│   └── data/
│       └── diseases.json              # Disease information database
│
├── ⚙️ Services (Business Logic)
│   ├── services/
│   │   ├── bedrock.py                 # AWS Bedrock client
│   │   ├── streaming.py               # Streaming with fallback
│   │   └── skin_classifier.py         # Skin lesion classifier (singleton)
│
├── 🌐 Routes (API Endpoints)
│   ├── routes/
│   │   ├── main.py                    # Home page
│   │   ├── chat.py                    # Chat + classification endpoints
│   │   └── editor.py                  # Editor routes
│
├── 🛠️ Utilities
│   ├── utils/
│   │   ├── formatting.py              # Text formatting helpers
│   │   └── validators.py              # Input validation
│
├── 🎨 Frontend
│   ├── templates/
│   │   └── index.html                 # Main chat interface
│   │
│   └── static/                        # (if any) CSS, JS, images
│
├── 🧪 Tests
│   ├── tests/
│   │   ├── test_model_accuracy.py     # Model accuracy test (500 samples)
│   │   ├── test_classifier_integration.py  # Integration tests
│   │   ├── check_model.py             # Model validation
│   │   ├── model_accuracy_test_results.csv
│   │   └── model_accuracy_summary.txt
│
├── 📚 Documentation
│   ├── docs/
│   │   ├── SKIN_CLASSIFIER_DEPLOYMENT_GUIDE.md
│   │   ├── MODEL_ACCURACY_TEST_FINAL_REPORT.md
│   │   └── PROJECT_STRUCTURE.md       # This file
│
├── 🗄️ Data & Training
│   ├── datasets/
│   │   ├── train_efficientnet.py      # Model training script
│   │   ├── requirements.txt           # Training dependencies
│   │   ├── dataset/                   # HAM10000 dataset
│   │   │   ├── HAM10000_metadata.tab
│   │   │   ├── HAM10000_images_part_1/ (5,001 images)
│   │   │   └── HAM10000_images_part_2/ (5,015 images)
│
├── 💾 Runtime Data
│   ├── memory/                        # Long-term conversation memory
│   ├── vector_db/                     # ChromaDB vector memory
│   ├── user_profiles/                 # User session data
│   └── .flask_sessions/               # Flask session files
│
├── 📦 Archive/Legacy
│   ├── achivementfolder/              # Achievement docs
│   ├── analysis/                      # Project analysis
│   ├── backups/                       # File backups
│   └── .kiro/                         # Kiro AI specs
│
└── 📋 Configuration
    ├── .gitignore                     # Git ignore rules
    ├── .env                           # Environment variables (DO NOT COMMIT)
    ├── CHANGELOG.md                   # Project changelog
    └── README.md                      # Main documentation
```

## Key Components

### Application Layer

#### `app_refactored.py`
- Flask application factory
- Blueprint registration
- Middleware configuration
- Error handlers
- Initializes classifier service

#### `config.py`
- Centralized configuration
- Environment variable management
- Dataclass-based configs:
  - `AppConfig`: General app settings
  - `BedrockConfig`: AWS Bedrock settings
  - `MemoryConfig`: Conversation memory
  - `RateLimitConfig`: Rate limiting
  - `ClassifierConfig`: Skin classifier settings

### Service Layer

#### `services/skin_classifier.py`
- Singleton pattern for model management
- Lazy loading (model loaded on first use)
- Thread-safe implementation
- Device auto-detection (CPU/CUDA)
- Image preprocessing & inference
- Error handling & validation

#### `services/bedrock.py`
- AWS Bedrock API client
- Model invocation with streaming
- Token counting
- Error handling

#### `services/streaming.py`
- Multi-model fallback logic
- Stream parsing and formatting
- Token-by-token delivery

### Model Layer

#### `models/classification.py`
```python
@dataclass
class Prediction:
    disease_code: str
    disease_name: str
    confidence: float
    disease_info: DiseaseInfo

@dataclass
class ClassificationResult:
    predictions: List[Prediction]
    processing_time_ms: float
    model_info: ModelInfo
```

#### `models/memory.py`
- Short-term memory (last 10 messages)
- Long-term memory (AI summaries)
- Vector memory (semantic search)

### Routes Layer

#### `routes/chat.py`
- `POST /chat`: Main chat endpoint with streaming
- `POST /classify`: Direct image classification
- `GET /health/classifier`: Classifier health check
- Auto-detection logic for classification keywords
- Classification context injection

#### `routes/main.py`
- `GET /`: Render chat interface
- `POST /clear`: Clear conversation history

### Data Layer

#### `data/diseases.json`
Comprehensive disease information:
```json
{
  "nv": {
    "name": "Melanocytic Nevi (Moles)",
    "description": "...",
    "severity": "benign",
    "risk_factors": [...],
    "treatment": "...",
    "prognosis": "..."
  }
}
```

## File Responsibilities

### Configuration Files

| File | Purpose |
|------|---------|
| `config.py` | All application configuration |
| `.env` | Environment-specific secrets (NOT in git) |
| `.env.example` | Template for environment variables |
| `requirements.txt` | Python dependencies |

### Test Files

| File | Purpose |
|------|---------|
| `test_model_accuracy.py` | Test model on 500 random images |
| `test_classifier_integration.py` | API integration tests |
| `check_model.py` | Validate model checkpoint |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation |
| `SKIN_CLASSIFIER_DEPLOYMENT_GUIDE.md` | Deployment instructions |
| `MODEL_ACCURACY_TEST_FINAL_REPORT.md` | Accuracy test results |
| `PROJECT_STRUCTURE.md` | This file |

## Data Flow

### Chat with Classification Flow

```
User uploads image + message
         ↓
routes/chat.py (POST /chat)
         ↓
Check for classification keywords
         ↓
services/skin_classifier.py
         ↓
Load model (if not loaded)
         ↓
Preprocess image (224x224, normalize)
         ↓
Run inference (EfficientNet-B0)
         ↓
Get top-K predictions
         ↓
Load disease info from data/diseases.json
         ↓
Inject classification context
         ↓
services/streaming.py
         ↓
Call AWS Bedrock with context
         ↓
Stream AI response to user
         ↓
Include medical disclaimer
```

### Direct Classification Flow

```
User sends image to /classify
         ↓
routes/chat.py (POST /classify)
         ↓
Validate image (size, format)
         ↓
services/skin_classifier.py
         ↓
Classify image
         ↓
Return JSON response
{
  "predictions": [...],
  "processing_time_ms": 42,
  "model_info": {...}
}
```

## Memory Storage

### Short-term Memory
- **Location**: Flask session (`.flask_sessions/`)
- **Scope**: Current conversation
- **Lifetime**: Session duration
- **Size**: Last 10 messages

### Long-term Memory
- **Location**: `memory/` directory
- **Scope**: Across sessions
- **Lifetime**: Persistent
- **Format**: JSON files with AI-generated summaries

### Vector Memory
- **Location**: `vector_db/` directory
- **Technology**: ChromaDB
- **Purpose**: Semantic search through past conversations
- **Lifetime**: Session-specific

## Dependencies

### Core Dependencies
```
flask>=3.0.0
boto3>=1.34.0
torch>=2.0.0
torchvision>=0.15.0
timm>=0.9.0
Pillow>=10.0.0
pandas>=2.0.0
```

### Development Dependencies
```
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
```

## Environment Variables

Required:
- `SECRET_KEY`: Flask secret key (REQUIRED in production)
- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)

Optional:
- `FLASK_ENV`: development/production
- `MODEL_PATH`: Path to trained model
- `ENABLE_DEBUG`: Enable debug mode

## Best Practices

### Adding New Features

1. **Service Layer**: Business logic goes in `services/`
2. **Routes Layer**: API endpoints go in `routes/`
3. **Models Layer**: Data structures go in `models/`
4. **Tests**: All tests go in `tests/`
5. **Docs**: Documentation goes in `docs/`

### Code Organization

- ✅ Keep routes thin (delegate to services)
- ✅ Use dataclasses for data structures
- ✅ Centralize configuration in `config.py`
- ✅ Write tests for all services
- ✅ Document complex logic

### File Naming

- Routes: `routes/<feature>.py`
- Services: `services/<feature>_service.py`
- Models: `models/<feature>.py`
- Tests: `tests/test_<feature>.py`
- Docs: `docs/<FEATURE>_<TYPE>.md`

## Git Workflow

### What to Commit

✅ Source code  
✅ Configuration templates (`.env.example`)  
✅ Documentation  
✅ Tests  
✅ Requirements files  

### What NOT to Commit

❌ `.env` (secrets)  
❌ `best_efficientnet_ham10000.pth` (large file - use Git LFS or download separately)  
❌ `memory/` (runtime data)  
❌ `vector_db/` (runtime data)  
❌ `.flask_sessions/` (temporary)  
❌ `__pycache__/` (Python cache)  

## Deployment Checklist

- [ ] Set `SECRET_KEY` environment variable
- [ ] Set `AWS_REGION` environment variable
- [ ] Ensure model checkpoint exists (`best_efficientnet_ham10000.pth`)
- [ ] Install all dependencies (`pip install -r requirements.txt`)
- [ ] Run tests (`python tests/test_classifier_integration.py`)
- [ ] Configure HTTPS (production)
- [ ] Set up monitoring
- [ ] Configure rate limiting
- [ ] Review medical disclaimer

## Support

For questions about the project structure:
1. Review this document
2. Check `README.md`
3. Review inline code documentation
4. Open a GitHub issue

---

**Last Updated**: June 18, 2026  
**Version**: 1.0
