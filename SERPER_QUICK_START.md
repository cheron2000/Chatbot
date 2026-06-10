# Serper Web Search - Quick Start

## 🚀 3 Steps to Enable Web Search

### Step 1: Get Your API Key
Go to [https://serper.dev/dashboard](https://serper.dev/dashboard) and copy your API key.

### Step 2: Add to .env File
Open `.env` and replace the default value:
```
SERPER_API_KEY=your_actual_api_key_here
```

### Step 3: Test It
Run the test script:
```bash
python test_websearch.py
```

## ✅ Verify It Works

You should see:
```
✅ API key found: 1234567890...abcd
✅ Search successful!

[Web Search Results]

1. What's New In Python 3.12
   This article explains the new features...
   Source: https://docs.python.org/3.12/whatsnew/3.12.html

✅ Web search is working correctly!
```

## 🎯 Usage in Chatbot

1. Start your app: `python app_refactored.py`
2. Open http://localhost:5000
3. Enable the 🌐 **Web Search** toggle
4. Ask questions like:
   - "What is the latest Python version?"
   - "What are the new features in React 19?"
   - "How to use async/await in JavaScript?"

## 📊 Your Free Tier

- ✅ **2,500 free searches per month**
- ✅ No credit card required
- ✅ ~0.5 second response time
- ✅ Google search quality results

## 🔧 Files Changed

| File | What Changed |
|------|--------------|
| `.env` | ✅ Created - Add your API key here |
| `services/websearch.py` | ✅ Updated - Now uses Serper API |
| `config.py` | ✅ Updated - Loads .env variables |
| `requirements.txt` | ✅ Updated - Added python-dotenv |
| `WEB_SEARCH_SETUP.md` | ✅ Created - Full documentation |
| `test_websearch.py` | ✅ Created - Test script |

## ❓ Troubleshooting

### Error: "SERPER_API_KEY not configured"
**Fix**: Edit `.env` and add your API key

### Error: "Invalid SERPER_API_KEY"
**Fix**: Check your key at https://serper.dev/dashboard

### No results in chat
**Fix**: 
1. Make sure web search toggle is ON (🌐)
2. Restart Flask app after editing `.env`
3. Check console for error messages

## 🎉 Done!

Your web search is now powered by Serper.dev with reliable Google search results!

For more details, see `WEB_SEARCH_SETUP.md`
