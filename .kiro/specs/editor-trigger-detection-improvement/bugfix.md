# Bugfix Requirements Document

## Introduction

The AI chatbot's code editor feature fails to trigger when users make natural language editing requests in Developer Mode. When users say phrases like "make the theme white in color" or "change background to blue", the system treats these as normal chat messages instead of code editing requests. This prevents the editor modal from appearing and blocks users from seeing proposed code changes.

The bug significantly degrades the user experience for the code editing feature, forcing users to use very specific trigger phrases instead of natural language. The root causes are:

1. **Insufficient Trigger Detection** - Only ~20 basic trigger phrases, missing common natural language patterns
2. **Limited File Context** - Only 6000 chars per file, truncating important CSS rules
3. **Missing Files** - style.css and other Python files not loaded for AI context
4. **Generic Triggers** - Not enough theme-specific, CSS-specific, or layout-specific phrases

This bugfix will expand trigger detection to handle 30+ natural language patterns, increase file context limits, dynamically load all relevant files, and improve AI prompts for better code generation.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user enables Developer Mode and says "make the theme white in color" THEN the system does not detect this as an editor trigger and treats it as normal chat

1.2 WHEN a user says "change the background to blue" or "update the color scheme" THEN the EDITOR_TRIGGERS list does not match these natural language patterns

1.3 WHEN the AI needs to generate code changes for CSS in index.html THEN only 6000 characters of index.html are loaded, truncating CSS rules at the end of the file

1.4 WHEN the AI needs context about the application structure THEN only 4 hardcoded files are loaded (index.html, chat.py, bedrock.py, config.py), missing style.css and other Python files

1.5 WHEN a user says theme-related requests like "make it dark mode" or "change colors to blue" THEN the generic trigger phrases don't match these specific natural language patterns

1.6 WHEN the AI generates JSON proposals THEN the EDITOR_SYSTEM_PROMPT doesn't provide enough examples of different change types, leading to invalid JSON formats

1.7 WHEN the extract_json_proposal function tries to parse AI responses THEN it only checks for "CODE_EDITOR_MODE" as an error indicator, missing other invalid formats

### Expected Behavior (Correct)

2.1 WHEN a user enables Developer Mode and says "make the theme white in color" THEN the system SHALL detect this as an editor trigger using expanded EDITOR_TRIGGERS with 30+ natural language patterns

2.2 WHEN a user says "change the background to blue" or "update the color scheme" THEN the EDITOR_TRIGGERS list SHALL match these patterns with theme-specific, layout-specific, and CSS-specific phrases

2.3 WHEN the AI needs to generate code changes for CSS in index.html THEN the system SHALL load 15000+ characters per file to include complete CSS rules

2.4 WHEN the AI needs context about the application structure THEN the system SHALL dynamically load all Python files in routes/, services/, models/, utils/ directories plus templates/index.html and style.css

2.5 WHEN a user says theme-related requests like "make it dark mode" or "change colors to blue" THEN the expanded EDITOR_TRIGGERS SHALL include dedicated theme, color, and styling trigger phrases

2.6 WHEN the AI generates JSON proposals THEN the enhanced EDITOR_SYSTEM_PROMPT SHALL provide multiple examples showing replace, create, and append actions with proper formatting

2.7 WHEN the extract_json_proposal function tries to parse AI responses THEN it SHALL provide detailed error messages showing the actual AI response format to help users debug issues

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user is NOT in Developer Mode and says "change the background" THEN the system SHALL CONTINUE TO treat this as a normal chat message, not triggering the editor

3.2 WHEN the system detects an editor request and loads file context THEN it SHALL CONTINUE TO backup files before applying changes using the existing backup_file() function

3.3 WHEN the AI generates a code proposal THEN the system SHALL CONTINUE TO validate Python syntax using validate_python() before applying changes

3.4 WHEN a user applies changes through the editor modal THEN the system SHALL CONTINUE TO use the apply_change() function with "replace", "append", or "create" actions

3.5 WHEN protected files (config.py, .env, requirements.txt, app_refactored.py) are referenced THEN the system SHALL CONTINUE TO block modifications using _safe_path() validation

3.6 WHEN the editor processes changes THEN it SHALL CONTINUE TO generate diffs showing before/after previews using get_file_preview()

3.7 WHEN file uploads are processed THEN the system SHALL CONTINUE TO handle both image attachments and text file context independently from editor triggers

3.8 WHEN web search is enabled THEN the system SHALL CONTINUE TO fetch web context without interfering with editor trigger detection

3.9 WHEN infiltration mode is active THEN the system SHALL CONTINUE TO detect attacks independently from developer mode functionality

3.10 WHEN short-term and long-term memory are managed THEN the system SHALL CONTINUE TO store conversation history and summaries without modification
