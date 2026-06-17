# ORACLE AI Chat with Skin Lesion Classifier

A Flask-based AI chatbot with AWS Bedrock integration, featuring dual memory system, model fallback, real-time streaming responses, and **AI-powered skin lesion classification**.

## ✨ Features

### Core Chatbot Features
- 🤖 **Multi-Model Support**: Claude 3 Haiku + NVIDIA Nemotron with automatic fallback
- 🧠 **Dual Memory System**: Short-term (10 messages) + long-term (AI-generated summaries)
- ⚡ **Real-time Streaming**: Server-sent events for token-by-token responses
- 📊 **Token Analytics**: Track input/output tokens per message and session
- 🎨 **Beautiful UI**: Space-themed interface with animated background
- 🔒 **Rate Limiting**: 200 requests/day, 20/minute per IP
- 📱 **Responsive Design**: Works on desktop and mobile

### 🔬 Skin Lesion Classifier (NEW)
- 🎯 **81.73% Accuracy**: EfficientNet-B0 model trained on HAM10000 dataset
- ⚡ **Fast Inference**: ~40ms on CPU, real-time classification
- 🏥 **7 Disease Classes**: Melanoma, Basal Cell Carcinoma, Melanocytic Nevi, and more
- 🤖 **Auto-Detection**: Upload image + ask "What is this?" → Automatic classification
- 📚 **Educational**: Comprehensive disease information and medical guidance
- ⚠️ **Safe**: Medical disclaimer on all outputs, not for clinical diagnosis
- 🔐 **Privacy-First**: No image storage, all processing in-memory

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- AWS Account with Bedrock access
- AWS credentials configured
- PyTorch 2.12.0+ (for skin classifier)

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Chatbot
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables (REQUIRED):**
```bash
# Windows (CMD)
set SECRET_KEY=your-secret-key-here
set AWS_REGION=us-east-1

# Windows (PowerShell)
$env:SECRET_KEY="your-secret-key-here"
$env:AWS_REGION="us-east-1"

# Linux/Mac
export SECRET_KEY=your-secret-key-here
export AWS_REGION=us-east-1
```

4. **Run the application:**
```bash
python app_refactored.py
```

5. **Open your browser:**
```
http://localhost:5000
```

## ⬇️ Large Files (Not in Repository)

The following large files are **not included** in this repository due to GitHub size limits. Download them separately before running the app:

### Trained Model Weights (Required)
The EfficientNet model checkpoint (`best_efficientnet_ham10000.pth`, ~15.6 MB) must be placed in the project root.

Train it yourself using the training script:
```bash
# 1. Download the HAM10000 dataset first (see below)
# 2. Run training
cd datasets
python train_efficientnet.py
# Trained model will be saved as best_efficientnet_ham10000.pth in the project root
```

### HAM10000 Dataset (For Training Only)
The dataset is **not needed** to run the app — only if you want to retrain the model.

Download from Kaggle:
- [HAM10000 Skin Lesion Dataset](https://www.kaggle.com/datasets/kmader/skin-cancer-mnist-ham10000)
- Place the image folders in `datasets/dataset/HAM10000_images_part_1/` and `datasets/dataset/HAM10000_images_part_2/`
- The metadata files (`HAM10000_metadata.tab`, etc.) are already included in the repo

---

## 📁 Project Structure

```
Chatbot/
├── app_refactored.py              # Application entry point
├── config.py                      # Configuration management
├── requirements.txt               # Python dependencies
├── best_efficientnet_ham10000.pth # Trained model checkpoint (NOT in repo - train or download separately)
│
├── models/
│   ├── memory.py                 # Conversation memory
│   └── classification.py         # Classification data models
│
├── services/
│   ├── bedrock.py                # AWS Bedrock client
│   ├── streaming.py              # Streaming with fallback
│   └── skin_classifier.py        # Skin lesion classifier service
│
├── routes/
│   ├── main.py                   # Home page
│   ├── chat.py                   # Chat endpoints + classification
│   └── editor.py                 # Editor routes
│
├── utils/
│   ├── formatting.py             # Text formatting
│   └── validators.py             # Input validation
│
├── templates/
│   └── index.html                # Frontend interface
│
├── data/
│   └── diseases.json             # Disease information database
│
├── tests/
│   ├── test_model_accuracy.py    # Model accuracy testing (500 samples)
│   ├── test_classifier_integration.py  # Integration tests
│   ├── check_model.py            # Model validation
│   ├── model_accuracy_test_results.csv
│   └── model_accuracy_summary.txt
│
├── docs/
│   ├── SKIN_CLASSIFIER_DEPLOYMENT_GUIDE.md
│   └── MODEL_ACCURACY_TEST_FINAL_REPORT.md
│
└── datasets/
    ├── train_efficientnet.py     # Model training script
    └── dataset/                  # HAM10000 dataset (10,015 images)
```

## 🔬 Using the Skin Lesion Classifier

### Method 1: Chat Integration (Recommended)

1. Upload a skin lesion image using the 📎 button
2. Ask a question with keywords like:
   - "What is this?"
   - "Diagnose this skin lesion"
   - "Should I be worried about this mole?"
3. Get instant AI classification with educational information

### Method 2: Direct API

**Endpoint:** `POST /classify`

**Request:**
```bash
curl -X POST http://localhost:5000/classify \
  -F "image=@skin_lesion.jpg" \
  -F "top_k=3"
```

**Response:**
```json
{
  "predictions": [
    {
      "disease_code": "nv",
      "disease_name": "Melanocytic Nevi (Moles)",
      "confidence": 0.9992,
      "disease_info": {
        "description": "Benign skin growths...",
        "severity": "benign",
        "risk_factors": [...],
        "treatment": "...",
        "prognosis": "..."
      }
    }
  ],
  "processing_time_ms": 42.5,
  "model_info": {
    "model_name": "efficientnet_b0",
    "accuracy": 81.73
  }
}
```

### Supported Disease Classes

| Code | Disease | Type |
|------|---------|------|
| **nv** | Melanocytic Nevi (Moles) | Benign |
| **bkl** | Benign Keratosis | Benign |
| **vasc** | Vascular Lesions | Benign |
| **df** | Dermatofibroma | Benign |
| **akiec** | Actinic Keratoses | Pre-cancerous |
| **bcc** | Basal Cell Carcinoma | Malignant |
| **mel** | Melanoma | Malignant |

## 🧪 Testing

### Run Model Accuracy Test (500 samples)
```bash
cd tests
python test_model_accuracy.py
```

**Expected Results:**
- Overall Accuracy: ~83%
- Average Inference: ~40ms
- Detailed per-class performance report

### Run Integration Tests
```bash
cd tests
python test_classifier_integration.py
```

**Tests:**
- ✅ Health check endpoint
- ✅ Direct classification API
- ✅ Chat integration with auto-detection

### Validate Model Checkpoint
```bash
cd tests
python check_model.py
```

## ⚙️ Configuration

Edit `config.py` to customize:

### Chatbot Settings
```python
@dataclass
class AppConfig:
    max_message_length: int = 4000
    max_tokens: int = 4096
    enable_infiltration_mode: bool = False
```

### Classifier Settings
```python
@dataclass
class ClassifierConfig:
    model_path: str = "best_efficientnet_ham10000.pth"
    device: str = "auto"  # 'cpu', 'cuda', or 'auto'
    max_image_size_mb: int = 10
    rate_limit: str = "10 per minute"
```

## 🔒 Security & Privacy

### Data Privacy (Skin Classifier)
- ✅ **No image storage** - All processing in-memory
- ✅ **Immediate disposal** - Images deleted after classification
- ✅ **No PII collection** - No personal data logged
- ✅ **Session isolation** - Each user's data is separate

### Security Measures
- ✅ Rate limiting (10 classifications/minute)
- ✅ File size validation (max 10MB)
- ✅ MIME type validation
- ✅ Input sanitization
- ✅ Medical disclaimer enforcement

### Medical Safety
⚠️ **IMPORTANT MEDICAL DISCLAIMER**

This AI classification is for **educational purposes only** and should NOT be used as a substitute for professional medical advice, diagnosis, or treatment.

**Always consult a qualified dermatologist** for any concerns about skin lesions.

## 📊 Model Performance

| Metric | Value |
|--------|-------|
| **Validation Accuracy** | 81.73% |
| **Test Accuracy (500 samples)** | ~83% |
| **Inference Time (CPU)** | 40ms average |
| **Model Size** | 15.61 MB |
| **Architecture** | EfficientNet-B0 |
| **Training Dataset** | HAM10000 (10,015 images) |
| **Training Epochs** | 10 |

### Comparison with Research
- Human Dermatologists: 86.6% (Tschandl et al. 2018)
- Our Model: 81.73% (within 5% of experts)
- ResNet-50: ~80% (literature)
- Inception-V3: ~82% (literature)

## 🌐 API Endpoints

### Chat Endpoints

#### `GET /`
Render the chat interface.

#### `POST /chat`
Send a message and receive streaming response with auto-classification.

**Request:**
```json
{
  "message": "What is this skin lesion?"
}
```

**Response:** Server-sent events stream with classification context

#### `POST /clear`
Clear conversation history.

### Classifier Endpoints

#### `POST /classify`
Direct image classification.

**Parameters:**
- `image` (file, required): Skin lesion image (JPEG/PNG, max 10MB)
- `top_k` (int, optional): Number of predictions (default: 3)

#### `GET /health/classifier`
Check classifier service status.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cpu",
  "model_name": "efficientnet_b0"
}
```

## 🚀 Deployment

### Production Setup

1. **Use a production WSGI server:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app_refactored:create_app()"
```

2. **Set a strong secret key:**
```bash
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
```

3. **Configure AWS credentials** (IAM roles recommended)

4. **Set up HTTPS** (nginx or AWS ALB)

5. **Enable GPU for faster inference** (optional):
```python
# In config.py
device: str = "cuda"  # Requires CUDA-enabled GPU
```

6. **Set up monitoring:**
```bash
# Monitor accuracy, latency, error rates
# Set up CloudWatch or similar
```

### Performance Optimization

For production with high traffic:

1. **GPU Deployment**: 5-10x faster inference
2. **Result Caching**: Cache duplicate image classifications
3. **Load Balancing**: Distribute requests across multiple instances
4. **Model Quantization**: 2-4x faster CPU inference (optional)

## 🐛 Troubleshooting

### Classifier Issues

**Model not loading:**
- `best_efficientnet_ham10000.pth` is **not included in the repo** — you need to train it (see "Large Files" section above)
- After training, ensure the `.pth` file is in the project root directory
- Check file size: should be ~15.6 MB
- Verify PyTorch installation: `python -c "import torch; print(torch.__version__)"`

**Slow inference:**
- CPU inference: 40-60ms (normal)
- Check system resources (CPU usage)
- Consider GPU deployment for faster inference

**Classification errors:**
- Verify image format (JPEG/PNG only)
- Check image size (<10MB)
- Ensure image contains skin lesion
- Review rate limiting (10 req/min)

### Chatbot Issues

**App won't start:**
- Check Python version: `python --version` (requires 3.10+)
- Verify dependencies: `pip list`
- Check AWS credentials: `aws sts get-caller-identity`
- Set SECRET_KEY environment variable

**Models failing:**
- Verify Bedrock access in AWS region
- Check model IDs in config.py
- Ensure IAM permissions for Bedrock

## 📚 Documentation

- **Deployment Guide**: `docs/SKIN_CLASSIFIER_DEPLOYMENT_GUIDE.md`
- **Accuracy Report**: `docs/MODEL_ACCURACY_TEST_FINAL_REPORT.md`
- **Training Guide**: `datasets/MODEL_TESTING_GUIDE.md`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- **HAM10000 Dataset**: Tschandl et al. (2018)
- **EfficientNet**: Tan & Le (2019)
- **AWS Bedrock**: For AI models
- **PyTorch & timm**: For deep learning framework
- **Flask**: For web framework
- **Open-source community**

## 📞 Support

For issues and questions:
- Open a GitHub issue
- Check documentation in `docs/` folder
- Review test scripts in `tests/` folder

---

**Built with ❤️ for educational purposes in dermatology and AI**

⚠️ **Remember**: Always consult a qualified dermatologist for medical concerns. This tool is for education only.
