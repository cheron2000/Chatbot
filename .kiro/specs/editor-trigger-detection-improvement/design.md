# Editor Trigger Detection Improvement Bugfix Design

## Overview

The editor trigger detection system fails to recognize natural language code modification requests when Developer Mode is enabled. The current implementation uses only ~20 basic trigger phrases, loads limited file context (6000 chars per file), and hardcodes only 4 files for AI context. This causes the editor modal to fail triggering for common requests like "make the theme white in color" or "change background to blue".

The fix expands trigger detection to 30+ natural language patterns covering theme, layout, color, and code editing phrases. It increases file context from 6000 to 15000+ characters to capture complete CSS rules and Python functions. It dynamically loads all relevant Python files from routes/, services/, models/, and utils/ directories plus templates/index.html and style.css. Finally, it enhances the AI system prompt with better examples and improves error messages to show actual AI response formats when JSON parsing fails.

This approach ensures minimal changes to existing functionality while maximizing trigger coverage and context quality.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when natural language code modification requests fail to match EDITOR_TRIGGERS
- **Property (P)**: The desired behavior when natural language editing requests are made - the editor modal should appear
- **Preservation**: Existing non-editor chat behavior, file backup, syntax validation, and security protections that must remain unchanged
- **EDITOR_TRIGGERS**: The list in `routes/chat.py` that contains trigger phrases for detecting editor requests
- **developer_mode**: The session flag that enables code editing features
- **is_editor_request**: Boolean flag in chat route that determines if the editor modal should be triggered
- **editor_file_context**: String containing file contents injected into AI context for code generation
- **EDITOR_SYSTEM_PROMPT**: System prompt in `routes/editor.py` that instructs the AI how to generate JSON proposals
- **extract_json_proposal**: Function in `routes/editor.py` that parses AI responses to extract code change proposals

## Bug Details

### Bug Condition

The bug manifests when a user enables Developer Mode and makes a natural language request to modify code (theme changes, color changes, layout changes, CSS edits, HTML edits, or Python code edits), but the request does not match any phrase in the EDITOR_TRIGGERS list. The system treats the request as normal chat instead of triggering the editor modal, preventing the user from seeing or applying code changes.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type ChatRequest with fields {message: string, developer_mode: boolean}
  OUTPUT: boolean
  
  RETURN input.developer_mode == true
         AND isNaturalLanguageCodeRequest(input.message)
         AND NOT any(trigger IN EDITOR_TRIGGERS WHERE trigger IN input.message.toLowerCase())
         AND shouldTriggerEditor(input.message)
END FUNCTION

FUNCTION isNaturalLanguageCodeRequest(message)
  // Natural language patterns that indicate code editing intent
  RETURN contains_theme_words(message)
         OR contains_color_words(message)
         OR contains_layout_words(message)
         OR contains_style_words(message)
         OR contains_code_words(message)
END FUNCTION
```

### Examples

- **Example 1 (Theme)**: User says "make the theme white in color" → Current: No match in EDITOR_TRIGGERS → Expected: Should trigger editor modal
- **Example 2 (Color)**: User says "change background to blue" → Current: No match in EDITOR_TRIGGERS → Expected: Should trigger editor modal
- **Example 3 (Layout)**: User says "add dark mode toggle" → Current: Partial match with "add dark mode" but missing "toggle" variant → Expected: Should trigger editor modal
- **Example 4 (CSS)**: User says "update the color scheme" → Current: No match in EDITOR_TRIGGERS → Expected: Should trigger editor modal
- **Edge Case 1**: User says "adjust the padding on buttons" → Current: No match → Expected: Should trigger editor modal
- **Edge Case 2**: User says "make it responsive for mobile" → Current: No match → Expected: Should trigger editor modal
- **Edge Case 3**: User says "implement hover effects" → Current: No match → Expected: Should trigger editor modal

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Normal chat messages when Developer Mode is OFF must continue to work exactly as before
- File backup functionality using `backup_file()` must remain unchanged
- Python syntax validation using `validate_python()` must remain unchanged
- Protected file blocking (config.py, .env, requirements.txt, app_refactored.py) via `_safe_path()` must remain unchanged
- File upload processing for images and text files must remain unchanged
- Web search integration when enabled must remain unchanged
- Infiltration mode attack detection must remain unchanged
- Short-term and long-term memory management must remain unchanged
- Vector memory semantic search must remain unchanged
- User profile tracking must remain unchanged

**Scope:**
All inputs that do NOT involve Developer Mode being enabled should be completely unaffected by this fix. This includes:
- Normal chat conversations with Developer Mode OFF
- Web search queries
- File upload processing
- Infiltration mode testing
- Memory and profile management
- Rate limiting and session handling

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Insufficient Trigger Coverage**: The EDITOR_TRIGGERS list in `routes/chat.py` contains only ~20 phrases, mostly generic like "change the code", "edit the code", "modify the code". It's missing natural language variants like:
   - Theme-specific: "make the theme", "set theme to", "switch to dark/light mode", "toggle dark mode"
   - Color-specific: "change color scheme", "update colors to", "make background", "change text color"
   - Layout-specific: "adjust layout", "modify spacing", "change padding/margin", "make responsive"
   - Style-specific: "update styling", "add hover effects", "change font", "adjust shadows"

2. **Insufficient File Context**: The current implementation loads only 6000 characters per file (`content = f.read()[:6000]`), which truncates:
   - CSS rules in index.html (the `<style>` tag contains hundreds of lines of CSS)
   - Python functions that span multiple screens
   - Configuration and utility code that provides context

3. **Missing Files**: The hardcoded `key_files` list includes only:
   - templates/index.html
   - routes/chat.py
   - services/bedrock.py
   - config.py
   
   Missing files include:
   - style.css (if it exists, contains additional CSS context)
   - routes/editor.py (contains editor logic)
   - services/code_editor.py (contains apply_change, restore_file functions)
   - models/memory.py (context for memory-related changes)
   - utils/*.py (context for utility functions)

4. **Generic AI Prompt**: The EDITOR_SYSTEM_PROMPT in `routes/editor.py` provides only one example (changing background color). It doesn't show:
   - How to handle multi-line replacements
   - How to use "append" action
   - How to use "create" action
   - How to handle CSS class additions
   - How to handle Python function changes

5. **Unclear Error Messages**: The `extract_json_proposal` function prints generic error messages like "AI did not generate a valid code change proposal" without showing the actual AI response format, making debugging difficult.

## Correctness Properties

Property 1: Bug Condition - Natural Language Editor Triggers

_For any_ chat request where Developer Mode is enabled and the message contains natural language code editing intent (theme changes, color changes, layout changes, CSS/HTML edits, Python code edits), the enhanced EDITOR_TRIGGERS detection SHALL match the request and trigger the editor modal, allowing the AI to generate code change proposals with expanded file context (15000+ chars per file) and dynamically loaded files (all Python files in routes/, services/, models/, utils/ plus templates/index.html and style.css).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

Property 2: Preservation - Non-Editor Behavior

_For any_ chat request where Developer Mode is NOT enabled OR the message does NOT contain code editing intent, the fixed code SHALL produce exactly the same behavior as the original code, preserving normal chat functionality, file upload processing, web search integration, infiltration mode, memory management, and all other existing features.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10**

## Fix Implementation

### Changes Required

**File**: `routes/chat.py`

**Function**: `create_chat_blueprint` → specifically the `EDITOR_TRIGGERS` list and file loading logic

**Specific Changes**:

1. **Expand EDITOR_TRIGGERS List**: Replace the current ~20 trigger phrases with 30+ natural language patterns:
   - Add theme triggers: "make the theme", "set theme to", "switch to dark mode", "switch to light mode", "toggle dark mode", "enable dark mode", "disable dark mode"
   - Add color triggers: "change color scheme", "update colors", "make background", "change background color", "change text color", "update theme colors"
   - Add layout triggers: "adjust layout", "modify spacing", "change padding", "change margin", "add spacing", "update grid", "make responsive", "adjust for mobile"
   - Add style triggers: "update styling", "change style", "modify appearance", "add hover effect", "change font", "update font size", "adjust shadows", "add border"
   - Add CSS-specific: "update the css", "modify css rules", "change stylesheet", "edit styles"
   - Add HTML-specific: "update the html", "modify html structure", "change template", "edit html"
   - Add Python-specific: "update the python", "modify python code", "change logic", "fix the function"

2. **Increase File Context Limit**: Change the file reading cap from 6000 to 15000+ characters:
   ```python
   # OLD: content = f.read()[:6000]
   # NEW: content = f.read()[:15000]
   ```

3. **Dynamic File Loading**: Replace hardcoded `key_files` list with dynamic directory scanning:
   - Scan routes/ directory for all .py files
   - Scan services/ directory for all .py files
   - Scan models/ directory for all .py files
   - Scan utils/ directory for all .py files
   - Include templates/index.html
   - Include style.css if it exists
   - Exclude __pycache__ directories and .pyc files

4. **File Loading Logic**:
   ```python
   # Dynamically load all Python files from key directories
   key_dirs = ["routes", "services", "models", "utils"]
   key_files = [("templates/index.html", "templates/index.html")]
   
   # Add style.css if it exists
   if os.path.exists(os.path.join(PROJECT_ROOT, "style.css")):
       key_files.append(("style.css", "style.css"))
   
   # Scan directories for Python files
   for dir_name in key_dirs:
       dir_path = os.path.join(PROJECT_ROOT, dir_name)
       if os.path.exists(dir_path):
           for filename in os.listdir(dir_path):
               if filename.endswith(".py") and not filename.startswith("__"):
                   rel_path = f"{dir_name}/{filename}"
                   key_files.append((rel_path, rel_path))
   ```

5. **Enhanced EDITOR_SYSTEM_PROMPT**: Add more examples showing different action types:
   - Example 1: Replace action (already exists)
   - Example 2: Append action (add new CSS class to existing style block)
   - Example 3: Create action (create new file)
   - Example 4: Multi-line replace (change entire function)
   - Example 5: HTML structure change

**File**: `routes/editor.py`

**Function**: `extract_json_proposal`

**Specific Changes**:

1. **Better Error Messages**: When JSON parsing fails, include the actual AI response in the error message (truncated to 300 chars for readability):
   ```python
   # OLD: print(f"[EDITOR] No valid JSON proposal found in response")
   # NEW: 
   print(f"[EDITOR] No valid JSON proposal found in response")
   print(f"[EDITOR] AI response (first 300 chars): {text[:300]}")
   if "CODE_EDITOR_MODE" in text:
       print(f"[EDITOR] ERROR: AI used wrong format with 'CODE_EDITOR_MODE' key")
   ```

2. **Detailed Error Response**: Return more helpful error messages to the frontend:
   ```python
   if not proposal:
       error_msg = "AI did not generate a valid code change proposal.\n"
       error_msg += f"Response preview: {ai_response[:200]}...\n"
       if "CODE_EDITOR_MODE" in ai_response:
           error_msg += "Error: AI used incorrect JSON format. Expected 'changes' array."
       else:
           error_msg += "Error: No JSON found. Try rephrasing your request."
       return jsonify({"error": error_msg}), 400
   ```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code by showing natural language requests that fail to trigger the editor, then verify the fix works correctly across 30+ trigger patterns and preserves existing chat behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that natural language requests fail to trigger the editor modal. If we observe different failures, we will re-hypothesize.

**Test Plan**: Create a test script that simulates Developer Mode enabled and sends natural language editing requests. Check if `is_editor_request` flag is set to True. Run on UNFIXED code to observe failures.

**Test Cases**:
1. **Theme Request Test**: Send "make the theme white in color" with developer_mode=True → Verify is_editor_request=False on unfixed code
2. **Color Request Test**: Send "change background to blue" with developer_mode=True → Verify is_editor_request=False on unfixed code
3. **Layout Request Test**: Send "adjust the padding on buttons" with developer_mode=True → Verify is_editor_request=False on unfixed code
4. **Style Request Test**: Send "add hover effects to links" with developer_mode=True → Verify is_editor_request=False on unfixed code
5. **CSS Request Test**: Send "update the color scheme" with developer_mode=True → Verify is_editor_request=False on unfixed code
6. **Responsive Request Test**: Send "make it responsive for mobile" with developer_mode=True → Verify is_editor_request=False on unfixed code
7. **File Context Test**: Send "change the background" and check loaded file context → Verify index.html is truncated at 6000 chars
8. **Missing Files Test**: Check editor_file_context string → Verify style.css and routes/editor.py are NOT included

**Expected Counterexamples**:
- Natural language requests fail to match EDITOR_TRIGGERS list
- File context is truncated at 6000 characters, missing CSS rules
- Only 4 hardcoded files are loaded, missing style.css and Python utility files
- Error messages don't show actual AI response format

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (natural language editing requests with Developer Mode enabled), the fixed function produces the expected behavior (triggers editor modal, loads 15000+ chars, loads all relevant files).

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  // Test expanded EDITOR_TRIGGERS
  is_editor_request := check_editor_triggers_fixed(input.message)
  ASSERT is_editor_request == True
  
  // Test increased file context
  file_context := load_file_context_fixed(input)
  ASSERT length(file_context) >= 15000 * 4  // At least 4 files with 15000 chars each
  
  // Test dynamic file loading
  loaded_files := extract_file_list(file_context)
  ASSERT "templates/index.html" IN loaded_files
  ASSERT "routes/chat.py" IN loaded_files
  ASSERT "routes/editor.py" IN loaded_files
  ASSERT "services/code_editor.py" IN loaded_files
  ASSERT "models/memory.py" IN loaded_files
  ASSERT "utils/validators.py" IN loaded_files
  ASSERT count(loaded_files) >= 10  // At least 10 Python files loaded
  
  // Test enhanced error messages
  IF json_parsing_fails(input) THEN
    error_msg := extract_error_message()
    ASSERT "Response preview:" IN error_msg
    ASSERT length(error_msg) > 100  // Detailed error message
  END IF
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (Developer Mode OFF or non-editing requests), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  // Test with Developer Mode OFF
  IF input.developer_mode == false THEN
    result_original := handle_chat_original(input)
    result_fixed := handle_chat_fixed(input)
    ASSERT result_original == result_fixed
  END IF
  
  // Test non-editing requests
  IF NOT isNaturalLanguageCodeRequest(input.message) THEN
    result_original := handle_chat_original(input)
    result_fixed := handle_chat_fixed(input)
    ASSERT result_original == result_fixed
  END IF
  
  // Test file backup functionality
  IF file_modification_occurs(input) THEN
    ASSERT backup_file_called()
  END IF
  
  // Test protected file blocking
  IF protected_file_referenced(input) THEN
    ASSERT safe_path_validation_called()
    ASSERT modification_blocked()
  END IF
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (chat messages with/without developer mode, various file contexts, different user scenarios)
- It catches edge cases that manual unit tests might miss (special characters in messages, very long messages, file path edge cases)
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Write property-based tests that generate random chat messages and verify behavior is preserved when Developer Mode is OFF or when messages don't contain editing intent.

**Test Cases**:
1. **Normal Chat Preservation**: Generate 100 random chat messages with developer_mode=False → Verify is_editor_request=False for all
2. **Non-Editing Preservation**: Generate 100 chat messages without code editing keywords → Verify is_editor_request=False for all
3. **File Backup Preservation**: Send editor requests and verify backup_file() is called before modifications
4. **Protected File Preservation**: Try to modify config.py → Verify _safe_path() blocks the modification
5. **Web Search Preservation**: Send chat with web_search=True and developer_mode=False → Verify web search works normally
6. **Memory Preservation**: Send multiple chats → Verify short-term and long-term memory work normally
7. **Upload Preservation**: Upload image/PDF with developer_mode=False → Verify file processing works normally

### Unit Tests

- Test expanded EDITOR_TRIGGERS with 30+ phrases covering theme, color, layout, style, CSS, HTML, Python keywords
- Test file context loading with increased 15000 char limit per file
- Test dynamic file loading from routes/, services/, models/, utils/ directories
- Test error message generation when JSON parsing fails
- Test edge cases: very short messages, very long messages, messages with special characters
- Test that Developer Mode toggle works correctly
- Test that non-editor chats are not affected

### Property-Based Tests

**Property 1 - Trigger Coverage**: _For any_ natural language editing request containing theme/color/layout/style keywords, the expanded EDITOR_TRIGGERS SHALL match at least one phrase.

**Property 2 - File Context Completeness**: _For any_ file loaded for editor context, the content SHALL include at least 15000 characters (or entire file if smaller).

**Property 3 - Dynamic File Loading**: _For any_ Python file in routes/, services/, models/, utils/ directories (excluding __pycache__), the file SHALL be included in editor_file_context.

**Property 4 - Preservation**: _For any_ chat request where developer_mode=False OR message does not contain editing keywords, the behavior SHALL be identical to the original implementation.

### Integration Tests

- Test full editor flow: Enable Developer Mode → Send "make theme white" → Verify editor modal appears → Verify file context includes all Python files → Verify AI generates valid JSON → Apply changes → Verify file is modified and backed up
- Test error handling: Send malformed request → Verify detailed error message with AI response preview
- Test file context quality: Send CSS change request → Verify complete CSS rules are included (not truncated at 6000 chars)
- Test cross-feature compatibility: Enable Developer Mode + Web Search + Infiltration Mode → Verify all features work independently
- Test protected file blocking: Send request to modify config.py → Verify modification is blocked
- Test responsive behavior: Send requests from different sessions → Verify each session has independent developer_mode state
