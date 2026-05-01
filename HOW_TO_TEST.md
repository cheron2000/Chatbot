# How to Test Vector Memory

## ✅ Automated Test (Already Passed!)

The automated test confirmed vector memory is working:
```bash
py -3.10 test_vector_memory.py
```

**Result**: ✅ ALL TESTS PASSED

## 🌐 Manual Browser Test (Recommended)

Follow these steps to see vector memory in action:

### Step 1: Make Sure Server is Running
Open terminal and check if you see:
```
[VECTOR] Initialized vector memory at vector_db
* Running on http://127.0.0.1:5000
```

If not running, start it:
```bash
py -3.10 app_refactored.py
```

### Step 2: Open Browser
Go to: **http://127.0.0.1:5000**

### Step 3: Test Semantic Memory

#### Test A: Topic Recall
1. **First message**: "What is Python programming?"
   - Wait for response
   - ✅ Check terminal: Should see `[VECTOR] Saved messages to vector database`

2. **Second message**: "Tell me about JavaScript"
   - Wait for response
   - ✅ Check terminal: Should see `[VECTOR] Saved messages to vector database`

3. **Third message**: "What did we discuss about programming languages?"
   - ✅ The AI should mention BOTH Python and JavaScript!
   - ✅ Check terminal: Should see `[VECTOR] Found X relevant messages`

#### Test B: Context Awareness
1. **First message**: "I'm learning web development"
   - Wait for response

2. **Second message**: "What's the weather like?" (different topic)
   - Wait for response

3. **Third message**: "Can you recommend resources for what I'm learning?"
   - ✅ AI should remember you're learning web development!
   - ✅ Check terminal for `[VECTOR] Found X relevant messages`

#### Test C: Long-term Memory
1. Send 5-10 messages on different topics
2. Clear your browser (but DON'T click "Clear History")
3. Open a new browser tab to http://127.0.0.1:5000
4. Ask about something from your earlier conversation
5. ✅ AI should still remember (vector memory persists!)

## 📊 What to Look For

### In Terminal (Server Logs):
```
✅ [VECTOR] Initialized vector memory at vector_db
✅ [VECTOR] Found 3 relevant messages          ← Semantic search working
✅ [VECTOR] Saved messages to vector database  ← Storage working
```

### In Browser (AI Responses):
- AI references previous conversations
- AI provides contextual answers based on past topics
- AI remembers your preferences/interests

### In File System:
Check if `vector_db/` directory exists and has files:
```
vector_db/
├── chroma.sqlite3           ← Database file
└── [uuid]/                  ← Index files
    ├── data_level0.bin
    ├── header.bin
    └── ...
```

## 🔍 Debugging

### If Vector Memory Isn't Working:

1. **Check Terminal Logs**
   ```bash
   # Should see this on startup:
   [VECTOR] Initialized vector memory at vector_db
   
   # Should see this after each message:
   [VECTOR] Saved messages to vector database
   ```

2. **Check Configuration**
   Open `config.py` and verify:
   ```python
   enable_vector_memory: bool = True  # Must be True
   ```

3. **Check Database**
   ```bash
   # Check if directory exists
   dir vector_db
   
   # Should show files inside
   ```

4. **Run Test Script**
   ```bash
   py -3.10 test_vector_memory.py
   ```

## 📈 Advanced Testing

### Test Semantic Similarity:
Ask these similar questions and see if AI connects them:
- "How do I learn Python?" 
- "What's the best way to study programming?"
- "Can you help me get started with coding?"

All three should trigger similar past conversations!

### Test Distance Threshold:
The lower the distance score, the more relevant:
- `0.0 - 0.3` = Very relevant
- `0.3 - 0.6` = Somewhat relevant  
- `0.6 - 1.0` = Less relevant

Check terminal logs to see distance scores.

## ✅ Success Indicators

You'll know it's working when:
1. ✅ Terminal shows `[VECTOR]` log messages
2. ✅ AI references past conversations naturally
3. ✅ `vector_db/` directory exists with files
4. ✅ Test script passes all checks
5. ✅ AI provides contextual responses based on history

## 🎯 Quick Verification

**Fastest way to verify:**
1. Open http://127.0.0.1:5000
2. Type: "My name is John and I love pizza"
3. Type: "What's 2+2?"
4. Type: "What's my name and favorite food?"
5. ✅ If AI says "John" and "pizza", vector memory works!

---

## 📞 Still Not Working?

Check these files:
- `VECTOR_MEMORY_STATUS.md` - Implementation details
- `analysis/PROJECT_STATUS.md` - Current status
- Terminal logs - Error messages

Run diagnostic:
```bash
py -3.10 test_vector_memory.py
```

If test passes but browser doesn't work, the issue is likely with session management, not vector memory.
