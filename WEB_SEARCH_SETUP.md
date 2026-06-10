# Web Search Setup Guide

## Overview

The chatbot uses **Serper.dev** for web search functionality, which provides fast and reliable Google search results via API.

## Setup Instructions

### 1. Get Your Serper API Key

1. Go to [https://serper.dev/dashboard](https://serper.dev/dashboard)
2. Sign up or log in to your account
3. Copy your API key from the dashboard
4. Serper.dev offers:
   - **2,500 free searches** to start
   - No credit card required for free tier
   - Fast response times (~0.5 seconds)

### 2. Configure Your API Key

1. Open the `.env` file in the project root
2. Replace `your_serper_api_key_here` with your actual API key:
   ```
   SERPER_API_KEY=your_actual_api_key_here
   ```
3. Save the file

### 3. Install Dependencies

If you haven't already installed the dependencies, run:

```bash
pip install -r requirements.txt
```

This will install `python-dotenv` which loads environment variables from the `.env` file.

### 4. Test Web Search

1. Start your Flask application:
   ```bash
   python app_refactored.py
   ```

2. In the chat interface:
   - Enable the **Web Search** toggle (🌐)
   - Send a query like: "what is the latest Python version"
   - The AI will fetch real-time web results

## Features

### Search Result Format

The web search returns:
- **Title** - Page title from Google search results
- **Snippet** - Description/preview text
- **Source URL** - Direct link to the webpage

### Example Output

```
[Web Search Results]

1. Python Release Python 3.12.0
   Python 3.12.0 is the newest major release of the Python programming language, and it contains many new features and optimizations...
   Source: https://www.python.org/downloads/release/python-3120/

2. What's New In Python 3.12
   This article explains the new features in Python 3.12, compared to 3.11...
   Source: https://docs.python.org/3.12/whatsnew/3.12.html
```

## Configuration

### Search Parameters

You can adjust search parameters in `services/websearch.py`:

- `max_results` - Number of search results to fetch (default: 3)
- `timeout` - Request timeout in seconds (default: 10.0)

### Error Handling

The web search includes automatic error handling:
- **Missing API key** - Shows helpful error message
- **Invalid API key** - Detects authentication errors
- **Network timeout** - Returns empty results gracefully
- **No results found** - Handles edge cases

## Troubleshooting

### "SERPER_API_KEY not configured"

**Problem**: The API key is not set or still has the default value.

**Solution**:
1. Open `.env` file
2. Replace `your_serper_api_key_here` with your actual key
3. Restart the Flask application

### "Invalid SERPER_API_KEY"

**Problem**: The API key is incorrect or expired.

**Solution**:
1. Go to [https://serper.dev/dashboard](https://serper.dev/dashboard)
2. Verify your API key is correct
3. Generate a new key if needed
4. Update `.env` file with the new key

### Web Search Not Working

**Problem**: Web search toggle is enabled but no results appear.

**Solution**:
1. Check console logs for error messages
2. Verify you have internet connectivity
3. Check if you've exceeded your free tier limit (2,500 searches)
4. Make sure `python-dotenv` is installed: `pip install python-dotenv`

## Security Notes

- **Never commit `.env` to Git** - The `.gitignore` file already excludes it
- **Keep your API key private** - Don't share it publicly
- **Regenerate if exposed** - If you accidentally expose your key, regenerate it immediately at [serper.dev/dashboard](https://serper.dev/dashboard)

## API Limits

### Free Tier
- **2,500 searches/month** - Free forever
- **No credit card required**
- Perfect for testing and development

### Paid Plans
If you need more searches, Serper offers affordable paid plans starting at $50/month for 5,000 searches. Check [https://serper.dev/pricing](https://serper.dev/pricing) for details.

## Technical Details

### Implementation

The web search is implemented in `services/websearch.py` using:
- **httpx** - Modern HTTP client for Python
- **Serper.dev API** - Google search results via REST API
- **Environment variables** - Secure API key management

### Integration

Web search is integrated into the chat flow:
1. User enables web search toggle
2. User sends a query
3. System detects if web search is needed
4. Fetches 3 search results from Serper
5. Injects results into AI context
6. AI generates response using web data

### Performance

- **Average latency**: ~500ms per search
- **Concurrent requests**: Supported
- **Caching**: Not implemented (can be added if needed)

## Next Steps

After setting up web search, you can:

1. **Test different queries** - Try technical questions, current events, etc.
2. **Adjust result count** - Modify `max_results` parameter
3. **Add search filters** - Serper supports date ranges, language filters, etc.
4. **Implement caching** - Cache frequent queries to save API calls

For more API features, check the [Serper.dev documentation](https://serper.dev/docs).
