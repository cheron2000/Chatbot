# Changelog

## [Improved] - 2024

### Security Improvements
- **SECRET_KEY Validation**: Added startup warning when using default SECRET_KEY
- **Infiltration Mode**: Disabled by default for production security
- **Auto-blocking**: Enabled by default to block detected attacks
- **Dependency Pinning**: All dependencies now have fixed versions to prevent supply chain attacks

### Bug Fixes
- **Vector Memory Consistency**: Fixed mismatch between session history and vector DB storage
  - Original user messages now stored in both places
  - Enhanced messages only used for AI processing
- **Prompt Enhancement**: Enhanced prompts now properly injected without corrupting history

### Code Quality
- **Removed Unused Code**: 
  - Deleted `HybridMemory` class (defined but never used)
  - Removed `add_system_instructions` method (defined but never called)
- **Removed Legacy Files**: 
  - `app.py` (superseded by `app_refactored.py`)
  - `chatinfiltration.py` (test file, shouldn't be in production)
  - `vector_memory.py` at root (duplicate of `models/vector_memory.py`)
- **Removed Sensitive Documentation**:
  - `achivementfolder/` containing infiltration guides and security testing notes

### Dependencies
- **Pinned Versions**:
  - Flask==3.0.3
  - Flask-Session==0.8.0
  - Flask-Limiter==3.8.0
  - boto3==1.35.36
  - botocore==1.35.36
  - chromadb==0.5.23
- **Removed**: sentence-transformers (unused dependency)

### Project Structure
- Added comprehensive `.gitignore`
- Added `cleanup.bat` script for easy legacy file removal
- Updated documentation

### Breaking Changes
- `infiltration_auto_block` now defaults to `True` (was `False`)
- `enable_infiltration_mode` now defaults to `False` (was `True`)
- Removed `HybridMemory` class from `models/vector_memory.py`

### Migration Guide
If you were using infiltration mode:
1. Set `enable_infiltration_mode=True` in `config.py` to re-enable
2. Set `infiltration_auto_block=False` if you want log-only mode

If you were using HybridMemory:
- Use `VectorMemory` directly instead
- The current implementation already provides hybrid functionality

### Recommendations
1. Run `cleanup.bat` to remove legacy files
2. Set `SECRET_KEY` environment variable before deploying
3. Review and adjust infiltration mode settings based on your needs
4. Update any scripts that referenced removed files
