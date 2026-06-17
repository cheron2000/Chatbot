# Implementation Plan: Skin Lesion Classifier Integration

## Overview

This implementation plan integrates a pre-trained EfficientNet-based skin lesion classification model into the existing Flask chatbot application. The work is organized into logical phases: core infrastructure (data models and service), API endpoints, chat integration, testing, and configuration.

## Tasks

- [x] 1. Set up project dependencies and infrastructure
  - Install required PyTorch libraries: `torch>=2.0.0`, `timm>=0.9.0`, `torchvision>=0.15.0`
  - Verify model checkpoint exists at `datasets/best_efficientnet_ham10000.pth`
  - Create `models/classification.py` for data models
  - Create `services/skin_classifier.py` for service layer
  - Create `data/diseases.json` for disease information database
  - _Requirements: 1.1, 1.4, 9.1_

- [x] 2. Implement core data models
  - [x] 2.1 Create ClassificationResult dataclass
    - Implement fields: predictions, processing_time_ms, model_info, timestamp, disclaimer
    - Implement `to_dict()` method for JSON serialization
    - Implement `get_top_prediction()` helper method
    - _Requirements: 2.5, 2.6, 2.7, 2.8_

  - [x] 2.2 Create Prediction dataclass
    - Implement fields: disease_code, disease_name, confidence, description, severity, prevalence
    - Add validation for confidence range (0.0 to 1.0)
    - _Requirements: 2.3, 4.1, 4.3_

  - [x] 2.3 Create ModelInfo dataclass
    - Implement fields: name, input_size, num_classes, framework, library, checkpoint_path
    - _Requirements: 2.6_

  - [x] 2.4 Create DiseaseInfo dataclass
    - Implement fields: code, name, description, severity, prevalence, risk_factors, treatment, prognosis
    - Create disease information JSON file with all 7 HAM10000 classes (akiec, bcc, bkl, df, mel, nv, vasc)
    - _Requirements: 4.1, 4.3, 4.5_

- [ ] 3. Implement SkinClassifierService singleton
  - [x] 3.1 Create service class structure with singleton pattern
    - Implement `__init__` with model_path and device parameters
    - Implement singleton instance management (class variable + lock)
    - Implement `is_loaded()` method to check model state
    - _Requirements: 1.1, 1.7, 9.1_

  - [x] 3.2 Implement lazy model loading with thread safety
    - Implement `load_model()` method with double-check locking pattern
    - Load checkpoint and validate required keys (model_state_dict, label_map, model_name)
    - Create EfficientNet model using timm library
    - Load trained weights and move to specified device (CPU/CUDA)
    - Create bidirectional label mappings (index↔label)
    - Set model to evaluation mode
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 9.5_

  - [ ]* 3.3 Write property test for model singleton
    - **Property 4: Model Singleton Integrity**
    - **Validates: Requirements 1.1, 9.1, 9.5**

  - [ ]* 3.4 Write property test for concurrent model loading
    - **Property 9: Thread-Safe Concurrent Model Loading**
    - **Validates: Requirements 1.3, 9.5**

- [ ] 4. Implement image preprocessing pipeline
  - [x] 4.1 Create preprocess_image function
    - Decode image bytes using PIL
    - Convert to RGB color space if needed
    - Resize to 224x224 using bilinear interpolation
    - Convert to tensor and normalize with ImageNet statistics
    - Add batch dimension to create shape (1, 3, 224, 224)
    - Validate image dimensions (minimum 50x50)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 4.2 Write property test for image preprocessing
    - **Property 6: Image Preprocessing Correctness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

  - [ ]* 4.3 Write unit tests for preprocessing edge cases
    - Test with various image formats (JPEG, PNG)
    - Test with small images (< 50x50) - should raise ValueError
    - Test with grayscale images (should convert to RGB)
    - Test tensor shape and dtype
    - _Requirements: 3.7, 7.2_

- [ ] 5. Checkpoint - Ensure preprocessing and model loading tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement classification algorithm
  - [x] 6.1 Create classify_image method
    - Call load_model() if not already loaded (lazy initialization)
    - Preprocess input image bytes
    - Run inference with gradient computation disabled
    - Compute softmax probabilities from logits
    - Extract top-K predictions with indices
    - Map indices to disease codes using label map
    - Fetch disease information for each prediction
    - Build Prediction objects with all required fields
    - Record processing time
    - Build and return ClassificationResult
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.6, 8.3_

  - [ ]* 6.2 Write property test for classification determinism
    - **Property 1: Classification Determinism**
    - **Validates: Requirements 2.4, 8.4**

  - [ ]* 6.3 Write property test for probability distribution validity
    - **Property 2: Probability Distribution Validity**
    - **Validates: Requirements 2.3, 8.1, 8.2**

  - [ ]* 6.4 Write property test for prediction ordering
    - **Property 3: Prediction Ordering**
    - **Validates: Requirements 2.1, 5.6, 8.3**

  - [ ]* 6.5 Write property test for top-K parameter enforcement
    - **Property 8: Top-K Parameter Enforcement**
    - **Validates: Requirements 2.2, 5.4, 5.5, 8.5**

  - [ ]* 6.6 Write property test for label map consistency
    - **Property 5: Label Map Bidirectional Consistency**
    - **Validates: Requirements 4.1, 4.7, 8.6, 8.7**

- [ ] 7. Implement error handling in classifier service
  - [ ] 7.1 Add error handling for invalid images
    - Catch PIL.UnidentifiedImageError and ValueError
    - Raise ValueError with clear error message
    - _Requirements: 7.1_

  - [ ] 7.2 Add error handling for missing checkpoint
    - Catch FileNotFoundError during model loading
    - Raise FileNotFoundError with descriptive message
    - _Requirements: 1.6, 7.3_

  - [ ] 7.3 Add error handling for out-of-memory errors
    - Catch torch.cuda.OutOfMemoryError and RuntimeError
    - Implement fallback from GPU to CPU if OOM occurs
    - Raise RuntimeError with user-friendly message
    - _Requirements: 7.4, 9.6_

  - [ ]* 7.4 Write property test for error handling completeness
    - **Property 7: Error Handling Completeness**
    - **Validates: Requirements 7.1, 7.2, 7.6, 7.7**

  - [ ]* 7.5 Write unit tests for error scenarios
    - Test with corrupted image data
    - Test with missing model checkpoint
    - Test with invalid disease codes
    - Test with images smaller than 50x50
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 8. Implement disease information retrieval
  - [x] 8.1 Implement get_disease_info method
    - Load disease information from JSON file
    - Return DiseaseInfo object for given disease code
    - Raise ValueError for invalid disease codes
    - _Requirements: 4.5, 4.6_

  - [x] 8.2 Implement unload_model method for memory management
    - Free model from memory
    - Reset model state to None
    - Log unload event
    - _Requirements: 9.7_

  - [ ]* 8.3 Write unit tests for disease information
    - Test retrieval of all 7 disease classes
    - Test with invalid disease code (should raise ValueError)
    - Verify completeness of disease information fields
    - _Requirements: 4.1, 4.5, 4.6_

- [ ] 9. Checkpoint - Ensure all classifier service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement /classify API endpoint
  - [x] 10.1 Create classify route in routes/chat.py
    - Add POST /classify endpoint
    - Parse JSON request body (image_b64, image_mime, top_k)
    - Validate input parameters (top_k between 1 and 7)
    - Decode base64 image to bytes
    - Call SkinClassifierService.classify_image()
    - Build JSON response with all required fields
    - Return HTTP 200 on success
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 10.2 Add input validation for /classify endpoint
    - Validate image_b64 is not empty
    - Validate top_k is between 1 and 7 if provided (default 3)
    - Validate image size doesn't exceed 10MB
    - Return HTTP 400 for validation errors with descriptive messages
    - _Requirements: 5.5, 7.5_

  - [x] 10.3 Add error handling for /classify endpoint
    - Catch ValueError (invalid image) → HTTP 400
    - Catch FileNotFoundError (model not found) → HTTP 503
    - Catch RuntimeError (inference failure) → HTTP 503
    - Catch Exception (unexpected errors) → HTTP 500
    - Log all errors without exposing sensitive details
    - _Requirements: 5.7, 7.1, 7.3, 7.6, 7.7_

  - [ ]* 10.4 Write integration tests for /classify endpoint
    - Test successful classification with valid image
    - Test with various top_k values (1, 3, 7)
    - Test with JPEG and PNG images
    - Test error responses (invalid image, missing model)
    - Verify response structure matches specification
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7_

- [ ] 11. Add rate limiting to /classify endpoint
  - [x] 11.1 Apply rate limiter to /classify route
    - Use Flask-Limiter with 10 requests per minute per IP
    - Return HTTP 429 when limit exceeded
    - Include Retry-After header in 429 responses
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ]* 11.2 Write property test for rate limiting accuracy
    - **Property 12: Rate Limiting Accuracy**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.7**

  - [ ]* 11.3 Write integration tests for rate limiting
    - Test enforcement of rate limit with rapid requests
    - Test Retry-After header presence
    - Test rate limit reset after time window
    - _Requirements: 12.1, 12.2, 12.3, 12.6_

- [ ] 12. Enhance /chat endpoint with classification context
  - [x] 12.1 Add classification trigger detection logic
    - Detect keywords: "diagnose", "classify", "what is this", "skin lesion", "mole", "melanoma", "cancer"
    - Check if image_b64 is provided
    - Check if classification was performed in last 2 messages (avoid redundancy)
    - _Requirements: 6.1, 6.5_

  - [x] 12.2 Implement classification context injection
    - When trigger detected, call SkinClassifierService.classify_image()
    - Format classification results as context injection text
    - Include top prediction, confidence, and alternatives
    - Add instructions for educational response and medical disclaimer reminder
    - Inject context into Bedrock prompt before generating response
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 12.3 Add explicit classify_image flag support
    - Accept optional classify_image boolean in /chat request
    - Respect explicit user preference over keyword detection
    - _Requirements: 6.6, 6.7_

  - [ ]* 12.4 Write integration tests for chat with classification
    - Test automatic classification trigger with keywords
    - Test classification context injection
    - Test with classify_image flag enabled/disabled
    - Test redundancy prevention (no duplicate classification)
    - Verify Bedrock receives classification context
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 13. Checkpoint - Ensure all API endpoint tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Add configuration for classifier service
  - [x] 14.1 Create ClassifierConfig in config.py
    - Add model_path field with default "datasets/best_efficientnet_ham10000.pth"
    - Add device field with default "auto"
    - Add enable_caching field with default True
    - Add cache_size field with default 100
    - Add auto_unload_minutes field with default 30
    - Add max_image_size_mb field with default 10
    - Add rate_limit field with default "10 per minute"
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

  - [x] 14.2 Update AppConfig to include ClassifierConfig
    - Add classifier field with ClassifierConfig instance
    - Ensure configuration is loaded before service initialization
    - _Requirements: 13.1, 13.2, 13.7_

  - [ ] 14.3 Initialize SkinClassifierService in app factory
    - Create classifier service instance in create_app()
    - Pass configuration from config.classifier
    - Pass classifier service to chat blueprint
    - _Requirements: 1.1, 13.1, 13.2_

- [ ] 15. Implement medical disclaimer
  - [ ] 15.1 Create disclaimer constant
    - Define MEDICAL_DISCLAIMER constant in services/skin_classifier.py
    - Include all required disclaimer text per requirements
    - Mention educational purpose only, consult dermatologist, not FDA-approved
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 15.2 Include disclaimer in all classification results
    - Add disclaimer field to ClassificationResult
    - Set disclaimer in every ClassificationResult instance
    - _Requirements: 2.8, 10.1, 10.7_

  - [ ]* 15.3 Write property test for disclaimer presence
    - **Property 10: Medical Disclaimer Presence**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.7**

  - [ ]* 15.4 Write unit tests for disclaimer content
    - Verify disclaimer is non-empty
    - Verify disclaimer mentions educational purpose
    - Verify disclaimer mentions consulting dermatologist
    - Verify disclaimer mentions not FDA-approved
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 16. Implement health check endpoint
  - [ ] 16.1 Create /health/classifier endpoint
    - Add GET /health/classifier route
    - Check if model is loaded using is_loaded()
    - Return HTTP 200 with status "healthy" if loaded
    - Return HTTP 503 with status "unavailable" if not loaded
    - Include model info in healthy response
    - _Requirements: 14.1, 14.2, 14.3_

  - [ ]* 16.2 Write integration tests for health endpoint
    - Test health check before model is loaded
    - Test health check after model is loaded
    - Test health check after model loading failure
    - Verify correct HTTP status codes and response format
    - _Requirements: 14.1, 14.2, 14.3_

- [ ] 17. Implement logging and observability
  - [ ] 17.1 Add structured logging for classification events
    - Log each classification request with timestamp, processing_time_ms, top_prediction
    - Log model loading events with device, memory_usage, loading_time_ms
    - Do not log image bytes or personal information
    - _Requirements: 14.4, 14.5, 14.7_

  - [ ] 17.2 Add error logging
    - Log all errors with error_type, error_message, request_context
    - Do not log sensitive information or stack traces in production
    - _Requirements: 14.6, 14.7_

  - [ ]* 17.3 Write unit tests for logging
    - Verify classification events are logged correctly
    - Verify errors are logged with correct metadata
    - Verify no sensitive information is logged
    - _Requirements: 14.4, 14.5, 14.6, 14.7_

- [ ] 18. Add security measures
  - [ ] 18.1 Implement image upload security
    - Validate MIME type matches actual file content
    - Verify image structure using PIL before processing
    - Reject files that cannot be decoded as images
    - Enforce 10MB maximum file size
    - _Requirements: 11.1, 11.5, 11.6_

  - [ ] 18.2 Ensure no persistent image storage
    - Process images in memory only
    - Discard image bytes immediately after classification
    - Do not write images to disk at any point
    - _Requirements: 11.1, 11.2, 11.3_

  - [ ] 18.3 Verify model checkpoint security
    - Check file permissions on model checkpoint (read-only)
    - Optionally verify checkpoint hash on first load
    - _Requirements: 11.7_

  - [ ]* 18.4 Write integration tests for security measures
    - Test file size limit enforcement (upload >10MB)
    - Test MIME type validation
    - Test that images are not written to disk
    - _Requirements: 11.1, 11.5, 11.6_

- [ ] 19. Ensure backwards compatibility
  - [x] 19.1 Verify existing chat endpoint functionality
    - Test that /chat works without classification
    - Test that /upload continues to function
    - Test that session management is unchanged
    - _Requirements: 15.1, 15.2, 15.3_

  - [x] 19.2 Add graceful degradation for missing model
    - If model checkpoint doesn't exist, classification returns 503
    - Chat functionality continues to work normally
    - Log warning about missing model
    - _Requirements: 15.4, 15.5_

  - [ ]* 19.3 Write integration tests for backwards compatibility
    - Test /chat without images (existing behavior)
    - Test /upload endpoint unchanged
    - Test application startup without model checkpoint
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

- [ ] 20. Create disease information database
  - [ ] 20.1 Create data/diseases.json file
    - Add complete information for all 7 HAM10000 classes
    - Include: code, name, description, severity, prevalence, risk_factors, treatment, prognosis
    - Disease classes: akiec, bcc, bkl, df, mel, nv, vasc
    - Ensure descriptions are educational and accurate
    - _Requirements: 4.1, 4.3, 4.5_

  - [ ]* 20.2 Write unit tests for disease database
    - Verify all 7 disease classes are present
    - Verify all required fields are populated
    - Verify JSON structure is valid
    - _Requirements: 4.1, 4.5_

- [ ] 21. Final checkpoint - Full integration test
  - [ ]* 21.1 Write comprehensive end-to-end integration tests
    - Test complete flow: upload image → classify → receive results
    - Test complete flow: chat with image → auto-classify → receive educational response
    - Test error scenarios end-to-end
    - Test concurrent classification requests
    - Test rate limiting enforcement
    - **Property 11: Classification Result Completeness**
    - **Validates: Requirements 2.5, 2.6, 2.7, 2.8, 5.3**

  - [ ] 21.2 Verify all requirements are met
    - Review requirements document and verify each criterion
    - Run full test suite and ensure >85% coverage
    - Verify all property tests pass
    - Ensure all tests pass, ask the user if questions arise.

- [ ] 22. Documentation and deployment preparation
  - [x] 22.1 Update API documentation
    - Document /classify endpoint with request/response examples
    - Document enhanced /chat endpoint behavior
    - Document /health/classifier endpoint
    - Document error codes and responses

  - [x] 22.2 Create deployment checklist
    - Verify model checkpoint location
    - Configure device (CPU/GPU) for production
    - Set up monitoring and logging
    - Verify rate limits are appropriate
    - Test with real images
    - Review medical disclaimer with legal team (if required)

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end workflows
- The implementation uses Python with Flask, PyTorch, and timm as specified in the design
- All classification results must include the medical disclaimer
- No user images are stored persistently - all processing is in-memory only
