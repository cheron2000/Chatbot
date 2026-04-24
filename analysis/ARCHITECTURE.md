# Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│                    (templates/index.html)                    │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Chat UI  │  │ Token Panel  │  │  Space Canvas    │   │
│  └────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/SSE
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Application                         │
│                   (app_refactored.py)                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Application Factory                      │  │
│  │              create_app()                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐            │
│         ▼                  ▼                   ▼            │
│  ┌────────────┐    ┌────────────┐     ┌────────────┐      │
│  │   Config   │    │  Services  │     │   Routes   │      │
│  │ (config.py)│    │            │     │            │      │
│  └────────────┘    └────────────┘     └────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Configuration Layer                     │
│                        (config.py)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Bedrock    │  │    Memory    │  │  Rate Limit  │     │
│  │    Config    │  │    Config    │  │    Config    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Service Layer                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           BedrockService (services/bedrock.py)       │  │
│  │  ┌────────────────┐        ┌────────────────┐       │  │
│  │  │ stream_anthropic│        │ stream_nvidia  │       │  │
│  │  │   (Claude)      │        │  (Nemotron)    │       │  │
│  │  └────────────────┘        └────────────────┘       │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      StreamingService (services/streaming.py)        │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │       stream_with_fallback()                   │ │  │
│  │  │  • Try primary model                           │ │  │
│  │  │  • Fallback on failure                         │ │  │
│  │  │  • Format responses                            │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Model Layer                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         MemoryManager (models/memory.py)             │  │
│  │  ┌────────────────┐        ┌────────────────┐       │  │
│  │  │  Short-term    │        │  Long-term     │       │  │
│  │  │  (Session)     │        │  (JSON files)  │       │  │
│  │  │  Last 10 msgs  │        │  AI summaries  │       │  │
│  │  └────────────────┘        └────────────────┘       │  │
│  │                                                       │  │
│  │  • load_longterm()                                   │  │
│  │  • save_longterm()                                   │  │
│  │  • generate_summary_async()                          │  │
│  │  • delete_longterm()                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Route Layer                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Main Blueprint (routes/main.py)              │  │
│  │  GET /  →  Render chat interface                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Chat Blueprint (routes/chat.py)              │  │
│  │  POST /chat   →  Stream AI response                  │  │
│  │  POST /clear  →  Clear conversation                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Utility Layer                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      Formatting (utils/formatting.py)                │  │
│  │  • format_response()                                 │  │
│  │  • Markdown → HTML conversion                        │  │
│  │  • Code block handling                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │      Validators (utils/validators.py)                │  │
│  │  • validate_message()                                │  │
│  │  • Length checks                                     │  │
│  │  • Empty message detection                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow

### Chat Request Flow

```
1. User sends message
   │
   ▼
2. Browser → POST /chat
   │
   ▼
3. routes/chat.py
   │
   ├─→ validate_message() [utils/validators.py]
   │   └─→ Check length, empty
   │
   ├─→ Get/Create session_id
   │
   ├─→ MemoryManager [models/memory.py]
   │   ├─→ load_longterm() → Read JSON file
   │   └─→ Get session history
   │
   ├─→ Add user message to history
   │
   ├─→ Trim history to MAX_SHORT_TERM
   │
   ▼
4. StreamingService.stream_with_fallback()
   │
   ├─→ Try Model 1 (Claude)
   │   │
   │   ├─→ BedrockService.stream_anthropic()
   │   │   │
   │   │   ├─→ Inject long-term summary as system prompt
   │   │   │
   │   │   ├─→ AWS Bedrock API call
   │   │   │
   │   │   └─→ Stream tokens
   │   │
   │   └─→ Success? → Format & send
   │
   ├─→ Failure? Try Model 2 (NVIDIA)
   │   │
   │   └─→ BedrockService.stream_nvidia()
   │       └─→ Same process
   │
   ▼
5. For each token:
   │
   ├─→ format_response() [utils/formatting.py]
   │   └─→ Markdown → HTML
   │
   └─→ Send SSE event to browser
       └─→ data: {"type": "token", "text": "..."}
   │
   ▼
6. On completion:
   │
   ├─→ Send final event
   │   └─→ data: {"type": "done", "html": "...", "tokens": ...}
   │
   ├─→ Save assistant reply to session
   │
   └─→ Background thread:
       └─→ MemoryManager.generate_summary_async()
           │
           ├─→ Call Claude for summary
           │
           └─→ save_longterm() → Write JSON file
```

### Clear Request Flow

```
1. User clicks "Clear Chat"
   │
   ▼
2. Browser → POST /clear
   │
   ▼
3. routes/chat.py
   │
   ├─→ Clear session history
   │
   └─→ MemoryManager.delete_longterm()
       └─→ Delete JSON file
   │
   ▼
4. Return {"status": "cleared"}
```

## Data Flow

### Session Data (Short-term Memory)

```
Flask Session (Server-side)
├── session_id: "uuid-string"
└── history: [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
    ...
    (max 10 messages)
]

Stored in: .flask_sessions/
Format: Pickle files
Lifetime: Until cleared or expired
```

### Long-term Memory

```
memory/{session_id}_longterm.json
{
  "summary": "User asked about Python. Discussed Flask...",
  "updated_at": "2024-01-15T10:30:00Z"
}

Created: After each conversation turn
Updated: Asynchronously in background
Used: Injected as system prompt in next request
```

## External Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock                               │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Claude 3 Haiku  │         │ NVIDIA Nemotron  │         │
│  │   (Primary)      │         │   (Fallback)     │         │
│  └──────────────────┘         └──────────────────┘         │
│                                                              │
│  Region: us-east-1                                          │
│  Protocol: HTTPS                                            │
│  Auth: AWS IAM                                              │
└─────────────────────────────────────────────────────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      Rate Limiting                           │
│  • 200 requests/day per IP                                  │
│  • 20 requests/minute per IP                                │
│  • In-memory storage                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Input Validation                          │
│  • Max 4000 characters per message                          │
│  • Empty message rejection                                  │
│  • XSS prevention (HTML escaping)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Session Management                         │
│  • Server-side sessions                                     │
│  • Secure session IDs (UUID)                                │
│  • Session isolation                                        │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Current Architecture (Single Server)

```
┌──────────────┐
│   Browser    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Flask Server │ ← Single instance
│  (Threaded)  │
└──────┬───────┘
       │
       ├─→ .flask_sessions/ (Local disk)
       ├─→ memory/ (Local disk)
       └─→ AWS Bedrock (Scalable)
```

### Recommended Production Architecture

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Browser 1   │  │  Browser 2   │  │  Browser N   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  ┌─────────────┐
                  │ Load Balancer│
                  └──────┬───────┘
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Server 1   │  │  Server 2   │  │  Server N   │
│  (Gunicorn) │  │  (Gunicorn) │  │  (Gunicorn) │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        ▼
              ┌──────────────────┐
              │  Redis (Sessions)│
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  S3 (Long-term)  │
              └──────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   AWS Bedrock    │
              └──────────────────┘
```

## Performance Characteristics

### Response Times

```
Component                    Typical Time
─────────────────────────────────────────
Input validation             < 1ms
Session lookup               < 5ms
Memory load (disk)           < 10ms
AWS Bedrock (first token)    200-500ms
Token streaming              ~50ms per token
Memory save (background)     100-200ms
Summary generation (async)   2-5 seconds
```

### Resource Usage

```
Component              Memory    Disk      Network
──────────────────────────────────────────────────
Flask app              ~50MB     -         -
Session storage        ~1KB/user ~10KB/user -
Long-term memory       -         ~2KB/user  -
Bedrock streaming      ~5MB      -         ~1KB/s
```

## Error Handling

```
┌─────────────────────────────────────────────────────────────┐
│                      Error Flow                              │
│                                                              │
│  User Request                                               │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────┐                                            │
│  │ Validation  │ ──Error──→ 400 Bad Request                │
│  └─────┬───────┘                                            │
│        │                                                     │
│        ▼                                                     │
│  ┌─────────────┐                                            │
│  │ Rate Limit  │ ──Error──→ 429 Too Many Requests          │
│  └─────┬───────┘                                            │
│        │                                                     │
│        ▼                                                     │
│  ┌─────────────┐                                            │
│  │  Model 1    │ ──Error──→ Try Model 2                    │
│  └─────┬───────┘                                            │
│        │                                                     │
│        ▼                                                     │
│  ┌─────────────┐                                            │
│  │  Model 2    │ ──Error──→ Return error message           │
│  └─────┬───────┘                                            │
│        │                                                     │
│        ▼                                                     │
│  Success Response                                           │
└─────────────────────────────────────────────────────────────┘
```

## Testing Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                      Test Pyramid                            │
│                                                              │
│                        ┌──────┐                             │
│                        │  E2E │ (Manual browser testing)    │
│                        └──────┘                             │
│                      ┌──────────┐                           │
│                      │Integration│ (API endpoint tests)     │
│                      └──────────┘                           │
│                  ┌──────────────────┐                       │
│                  │   Unit Tests     │ (Component tests)     │
│                  └──────────────────┘                       │
│                                                              │
│  test_refactored.py covers:                                 │
│  • Import validation                                        │
│  • Configuration                                            │
│  • Formatting logic                                         │
│  • Input validation                                         │
│  • App creation                                             │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
Development:
  py -3.10 app_refactored.py
  └─→ Flask dev server (single-threaded, auto-reload)

Production:
  gunicorn -w 4 -k gevent "app_refactored:create_app()"
  └─→ 4 worker processes, async I/O, no auto-reload
```

## Monitoring Points

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Targets                        │
│                                                              │
│  Application Level:                                         │
│  • Request rate                                             │
│  • Response times                                           │
│  • Error rates                                              │
│  • Active sessions                                          │
│                                                              │
│  Service Level:                                             │
│  • Bedrock API latency                                      │
│  • Model fallback frequency                                 │
│  • Token usage                                              │
│  • Memory generation time                                   │
│                                                              │
│  Infrastructure Level:                                      │
│  • CPU usage                                                │
│  • Memory usage                                             │
│  • Disk I/O (sessions, memory files)                        │
│  • Network I/O (Bedrock calls)                              │
└─────────────────────────────────────────────────────────────┘
```

This architecture provides a clear separation of concerns, making the system easy to understand, test, and scale.
