# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Natural Language Editor Trigger Detection
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate natural language editing requests fail to trigger editor modal
  - **Scoped PBT Approach**: Scope the property to concrete failing cases - natural language editing requests with developer_mode enabled that should trigger editor but don't match current EDITOR_TRIGGERS
  - Test implementation details from Bug Condition in design:
    - Test with developer_mode=True and natural language editing requests
    - Test "make the theme white in color" → should set is_editor_request=True but doesn't
    - Test "change background to blue" → should set is_editor_request=True but doesn't
    - Test "adjust the padding on buttons" → should set is_editor_request=True but doesn't
    - Test "update the color scheme" → should set is_editor_request=True but doesn't
    - Test "make it responsive for mobile" → should set is_editor_request=True but doesn't
    - Test file context length → should be 15000+ chars per file but is only 6000
    - Test loaded files count → should include 10+ Python files but only includes 4 hardcoded files
  - The test assertions should match the Expected Behavior Properties from design:
    - Property 1: For any natural language editing request with theme/color/layout/style keywords, EDITOR_TRIGGERS should match
    - Property 1: File context should include 15000+ characters per file
    - Property 1: All Python files from routes/, services/, models/, utils/ should be loaded
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause:
    - Which natural language phrases fail to match EDITOR_TRIGGERS
    - How much file content is truncated at 6000 chars
    - Which files are missing from editor_file_context
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Editor Behavior Preservation
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Send normal chat messages with developer_mode=False
    - Send messages without code editing keywords
    - Test file backup functionality with existing code
    - Test protected file blocking with existing _safe_path()
    - Test web search integration with developer_mode=False
    - Test memory management across multiple chats
    - Test file upload processing with images and PDFs
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - Property 2: For any chat request where developer_mode=False, is_editor_request should remain False
    - Property 2: For any message without code editing keywords, is_editor_request should remain False
    - Property 2: File backup using backup_file() should be called before modifications
    - Property 2: Protected files should be blocked by _safe_path() validation
    - Property 2: Normal chat, web search, memory, and upload features should work unchanged
  - Property-based testing generates many test cases for stronger guarantees:
    - Generate 100 random chat messages with developer_mode=False
    - Generate 100 chat messages without editing keywords
    - Test various file modification scenarios
    - Test protected file access attempts
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [ ] 3. Fix for editor trigger detection improvement

  - [ ] 3.1 Expand EDITOR_TRIGGERS list with 30+ natural language patterns
    - Open routes/chat.py and locate the EDITOR_TRIGGERS list
    - Add theme triggers: "make the theme", "set theme to", "switch to dark mode", "switch to light mode", "toggle dark mode", "enable dark mode", "disable dark mode"
    - Add color triggers: "change color scheme", "update colors", "make background", "change background color", "change text color", "update theme colors"
    - Add layout triggers: "adjust layout", "modify spacing", "change padding", "change margin", "add spacing", "update grid", "make responsive", "adjust for mobile"
    - Add style triggers: "update styling", "change style", "modify appearance", "add hover effect", "change font", "update font size", "adjust shadows", "add border"
    - Add CSS-specific: "update the css", "modify css rules", "change stylesheet", "edit styles"
    - Add HTML-specific: "update the html", "modify html structure", "change template", "edit html"
    - Add Python-specific: "update the python", "modify python code", "change logic", "fix the function"
    - _Bug_Condition: isBugCondition(input) where input.developer_mode=true AND isNaturalLanguageCodeRequest(input.message) AND NOT any(trigger IN EDITOR_TRIGGERS)_
    - _Expected_Behavior: For all natural language editing requests, at least one trigger in expanded EDITOR_TRIGGERS should match_
    - _Preservation: Non-editor chat messages when developer_mode=false remain unchanged_
    - _Requirements: 1.1, 1.2, 1.5, 2.1, 2.2, 2.5, 3.1_

  - [ ] 3.2 Increase file context limit from 6000 to 15000+ characters
    - Open routes/chat.py and locate file reading logic for editor_file_context
    - Find the line: `content = f.read()[:6000]`
    - Change to: `content = f.read()[:15000]`
    - This ensures complete CSS rules and Python functions are included in AI context
    - _Bug_Condition: isBugCondition(input) where file context is truncated at 6000 chars_
    - _Expected_Behavior: File context includes at least 15000 characters per file or entire file if smaller_
    - _Preservation: File backup, syntax validation, and protected file blocking remain unchanged_
    - _Requirements: 1.3, 2.3, 3.2, 3.3_

  - [ ] 3.3 Implement dynamic file loading from routes/, services/, models/, utils/ directories
    - Open routes/chat.py and locate the key_files hardcoded list
    - Replace hardcoded list with dynamic directory scanning:
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
    - Ensure __pycache__ directories and .pyc files are excluded
    - _Bug_Condition: isBugCondition(input) where only 4 hardcoded files are loaded_
    - _Expected_Behavior: All Python files from routes/, services/, models/, utils/ plus templates/index.html and style.css are loaded_
    - _Preservation: Protected file blocking using _safe_path() remains unchanged_
    - _Requirements: 1.4, 2.4, 3.5_

  - [ ] 3.4 Enhance EDITOR_SYSTEM_PROMPT with multiple examples
    - Open routes/editor.py and locate the EDITOR_SYSTEM_PROMPT constant
    - Add Example 2 for append action: Show how to add new CSS class to existing style block
    - Add Example 3 for create action: Show how to create new file
    - Add Example 4 for multi-line replace: Show how to change entire Python function
    - Add Example 5 for HTML structure change: Show how to modify HTML layout
    - Each example should show proper JSON format with "action", "file", "old_content", "new_content"
    - _Bug_Condition: isBugCondition(input) where AI generates invalid JSON due to insufficient examples_
    - _Expected_Behavior: EDITOR_SYSTEM_PROMPT provides 5 examples covering replace, append, create actions_
    - _Preservation: Existing get_file_preview() diff generation remains unchanged_
    - _Requirements: 1.6, 2.6, 3.6_

  - [ ] 3.5 Improve error messages in extract_json_proposal function
    - Open routes/editor.py and locate the extract_json_proposal function
    - Find the error handling section where JSON parsing fails
    - Add detailed error messages showing actual AI response:
      ```python
      print(f"[EDITOR] No valid JSON proposal found in response")
      print(f"[EDITOR] AI response (first 300 chars): {text[:300]}")
      if "CODE_EDITOR_MODE" in text:
          print(f"[EDITOR] ERROR: AI used wrong format with 'CODE_EDITOR_MODE' key")
      ```
    - Update error response to frontend:
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
    - _Bug_Condition: isBugCondition(input) where JSON parsing fails with generic error message_
    - _Expected_Behavior: Error messages show actual AI response format to help debugging_
    - _Preservation: File upload processing and web search integration remain unchanged_
    - _Requirements: 1.7, 2.7, 3.7, 3.8_

  - [ ] 3.6 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Natural Language Editor Triggers Work
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - Verify natural language requests now match expanded EDITOR_TRIGGERS
    - Verify file context includes 15000+ characters per file
    - Verify 10+ Python files are loaded dynamically
    - Verify error messages show AI response preview
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ] 3.7 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Editor Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - Verify chat messages with developer_mode=False work unchanged
    - Verify messages without editing keywords work unchanged
    - Verify file backup functionality still works
    - Verify protected file blocking still works
    - Verify web search, memory, and upload features work unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Run full test suite including bug condition and preservation tests
  - Verify all natural language editing requests trigger editor modal
  - Verify file context is complete (15000+ chars per file, 10+ files loaded)
  - Verify enhanced error messages appear when JSON parsing fails
  - Verify normal chat, web search, memory, and upload features work unchanged
  - If any tests fail, investigate root cause and fix issues
  - If questions arise about edge cases or unexpected behavior, ask the user for guidance
  - Mark complete when all tests pass and bug is resolved
