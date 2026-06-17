# Requirements Document: Skin Lesion Classifier Integration

## Introduction

This requirements document specifies the functional and non-functional requirements for integrating a pre-trained EfficientNet-based skin lesion classification model into the existing Flask chatbot application. The system shall enable users to upload skin lesion images and receive AI-powered diagnostic predictions with confidence scores and educational information about various skin conditions from the HAM10000 dataset taxonomy.

## Glossary

- **Classifier_Service**: The singleton service component that manages the EfficientNet model lifecycle and provides classification capabilities
- **Classification_Result**: A structured data object containing top-K disease predictions, confidence scores, processing time, and model metadata
- **Prediction**: A single disease prediction containing a disease code, name, confidence score, description, severity level, and prevalence information
- **HAM10000**: A dataset of 10,000 dermatoscopic images covering 7 types of skin lesions used for training the classification model
- **Disease_Code**: A short identifier for skin lesion types: akiec, bcc, bkl, df, mel, nv, vasc
- **Confidence_Score**: A probability value between 0.0 and 1.0 indicating the model's certainty for a prediction
- **Top_K**: The number of highest-confidence predictions to return (1 to 7)
- **Model_Checkpoint**: A .pth file containing the trained EfficientNet model weights, label mappings, and metadata
- **Image_Preprocessing**: The transformation pipeline that converts uploaded images to 224x224 normalized tensors
- **Lazy_Loading**: A design pattern where the model loads into memory only when first needed rather than at startup
- **Thread_Safe**: Property ensuring correct behavior when multiple concurrent requests access shared resources
- **Medical_Disclaimer**: A required warning stating that AI predictions are for educational purposes only and not a substitute for professional medical diagnosis

## Requirements

### Requirement 1: Model Lifecycle Management

**User Story:** As a system developer, I want the classifier service to manage the model lifecycle efficiently, so that resources are used optimally and concurrent requests are handled safely.

#### Acceptance Criteria

1. WHEN the Classifier_Service is instantiated, THE system SHALL implement a singleton pattern ensuring only one model instance exists in memory
2. WHEN the first classification request is received, THE Classifier_Service SHALL load the model from the Model_Checkpoint using lazy loading
3. WHEN multiple concurrent requests attempt to load the model simultaneously, THE Classifier_Service SHALL use thread-safe locking to ensure only one loading operation occurs
4. WHEN the model is loaded, THE Classifier_Service SHALL validate that the checkpoint contains required keys: model_state_dict, label_map, and model_name
5. WHERE GPU hardware is available, THE Classifier_Service SHALL automatically detect and utilize CUDA for accelerated inference
6. WHEN the model fails to load, THE Classifier_Service SHALL raise a descriptive error indicating the failure reason
7. THE Classifier_Service SHALL provide an is_loaded() method that returns the current model loading state

### Requirement 2: Image Classification

**User Story:** As a user, I want to upload a skin lesion image and receive diagnostic predictions with confidence scores, so that I can learn about potential skin conditions.

#### Acceptance Criteria

1. WHEN a valid image is provided to classify_image(), THE Classifier_Service SHALL return a Classification_Result containing Top_K predictions sorted by confidence
2. WHEN classify_image() is called with a top_k parameter, THE system SHALL return exactly that number of predictions
3. FOR ALL classification requests, THE system SHALL ensure the sum of all Confidence_Scores approximates 1.0 within 0.01 tolerance
4. WHEN the same image is classified multiple times with identical model state, THE system SHALL produce identical predictions (deterministic behavior)
5. WHEN an image is classified, THE system SHALL record and return the processing time in milliseconds
6. WHEN classification completes, THE Classification_Result SHALL include model metadata: name, input size, number of classes, framework, and checkpoint path
7. WHEN classification completes, THE Classification_Result SHALL include an ISO 8601 timestamp
8. WHEN classification completes, THE Classification_Result SHALL include the Medical_Disclaimer text

### Requirement 3: Image Preprocessing

**User Story:** As a system developer, I want consistent image preprocessing, so that the model receives properly formatted input regardless of upload format.

#### Acceptance Criteria

1. WHEN an image is received as bytes, THE system SHALL decode it using PIL and convert to RGB color space
2. WHEN an image is decoded, THE system SHALL resize it to 224x224 pixels using bilinear interpolation
3. WHEN an image is resized, THE system SHALL convert it to a tensor with shape (3, 224, 224)
4. WHEN a tensor is created, THE system SHALL normalize each channel using ImageNet statistics: mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
5. WHEN normalization is complete, THE system SHALL add a batch dimension to create final shape (1, 3, 224, 224)
6. FOR ALL preprocessed images, THE output tensor SHALL have dtype float32
7. WHEN preprocessing fails at any stage, THE system SHALL raise a ValueError with a descriptive error message

### Requirement 4: Label Mapping and Disease Information

**User Story:** As a user, I want to receive human-readable disease names and educational descriptions with predictions, so that I can understand the classification results.

#### Acceptance Criteria

1. THE Classifier_Service SHALL maintain a bidirectional label mapping between Disease_Codes and human-readable names
2. WHEN a prediction is generated, THE system SHALL map the model output index to the corresponding Disease_Code
3. WHEN a Disease_Code is identified, THE system SHALL retrieve the corresponding disease information including name, description, severity, and prevalence
4. THE system SHALL support all 7 HAM10000 Disease_Codes: akiec, bcc, bkl, df, mel, nv, vasc
5. WHEN get_disease_info() is called with a valid Disease_Code, THE system SHALL return complete disease information including risk factors, treatment, and prognosis
6. WHEN get_disease_info() is called with an invalid Disease_Code, THE system SHALL raise a ValueError
7. FOR ALL predictions, THE disease name SHALL exactly match the label map entry for the corresponding Disease_Code

### Requirement 5: Classification API Endpoint

**User Story:** As a developer integrating with the application, I want a dedicated /classify endpoint, so that I can programmatically request skin lesion classifications.

#### Acceptance Criteria

1. THE system SHALL provide a POST /classify endpoint that accepts JSON requests with image_b64, image_mime, and optional top_k fields
2. WHEN /classify receives a valid request, THE system SHALL decode the base64 image, perform classification, and return a JSON response
3. WHEN /classify completes successfully, THE system SHALL return HTTP 200 with a JSON object containing status, predictions, processing_time_ms, model_info, and disclaimer
4. WHEN the top_k parameter is omitted, THE system SHALL default to returning 3 predictions
5. WHEN the top_k parameter is provided, THE system SHALL validate it is between 1 and 7 inclusive
6. FOR ALL /classify responses, THE predictions array SHALL be sorted by confidence in descending order
7. WHEN /classify encounters an error, THE system SHALL return an appropriate HTTP error code (400, 503) with an error message

### Requirement 6: Enhanced Chat Endpoint with Classification

**User Story:** As a user, I want to ask questions about skin lesions in the chat interface and receive AI-assisted educational responses, so that I can learn about my condition conversationally.

#### Acceptance Criteria

1. WHEN the /chat endpoint receives a message containing classification keywords ("diagnose", "classify", "what is this", "skin lesion", "mole", "melanoma", "cancer") and an image, THE system SHALL automatically trigger classification
2. WHEN classification is triggered via /chat, THE system SHALL inject classification results into the conversation context before generating the response
3. WHEN classification results are injected, THE context SHALL include the top prediction, confidence score, and alternative possibilities
4. WHEN classification results are injected, THE system SHALL instruct the language model to provide educational information and remind the user to consult a dermatologist
5. WHERE classification has been performed within the last 2 messages, THE system SHALL NOT trigger redundant classification
6. WHEN the user provides an image without classification keywords, THE system SHALL NOT automatically classify the image
7. WHERE a classify_image flag is provided in the request, THE system SHALL respect the explicit user preference

### Requirement 7: Input Validation and Error Handling

**User Story:** As a system operator, I want robust error handling for invalid inputs, so that the system provides clear feedback and remains stable.

#### Acceptance Criteria

1. WHEN an image with invalid format is uploaded, THE system SHALL return HTTP 400 with error message "Invalid image format. Please upload a valid JPEG or PNG file."
2. WHEN an image smaller than 50x50 pixels is uploaded, THE system SHALL return HTTP 400 with error message "Image too small. Minimum dimensions: 50x50 pixels." including actual dimensions
3. WHEN the Model_Checkpoint file is not found, THE system SHALL return HTTP 503 with error message "Classification service unavailable. Model not found."
4. WHEN the model encounters an out-of-memory error, THE system SHALL attempt to unload the model and return HTTP 503 with message "Classification service temporarily unavailable. Please try again."
5. WHEN an upload exceeds the maximum file size (10MB), THE system SHALL return HTTP 413 with error message "File too large. Maximum size: 10MB."
6. WHEN classification encounters an unexpected error, THE system SHALL log the error with details and return HTTP 500 with a generic error message
7. FOR ALL error responses, THE system SHALL NOT expose sensitive internal details such as file paths or stack traces

### Requirement 8: Prediction Correctness Properties

**User Story:** As a quality assurance engineer, I want to verify the mathematical correctness of classification outputs, so that I can ensure the system produces valid probability distributions.

#### Acceptance Criteria

1. FOR ALL classifications, THE sum of all Confidence_Scores SHALL be between 0.99 and 1.01 (valid probability distribution)
2. FOR ALL predictions in a Classification_Result, THE Confidence_Score SHALL be between 0.0 and 1.0 inclusive
3. FOR ALL Classification_Results with multiple predictions, THE predictions SHALL be sorted such that predictions[i].confidence >= predictions[i+1].confidence
4. WHEN the same image bytes are classified multiple times, THE system SHALL produce predictions with identical confidence scores within floating-point precision tolerance
5. FOR ALL Classification_Results, THE number of predictions returned SHALL equal the requested top_k value
6. FOR ALL predictions, THE Disease_Code SHALL be one of the 7 valid HAM10000 codes
7. FOR ALL predictions, THE disease_name SHALL match the label map entry for the Disease_Code

### Requirement 9: Performance and Resource Management

**User Story:** As a system operator, I want efficient resource usage and fast response times, so that the application can handle multiple users without degradation.

#### Acceptance Criteria

1. WHEN the model is loaded into memory, THE system SHALL use a singleton pattern to ensure only one model instance exists
2. WHEN classification is requested on GPU-enabled hardware, THE inference time SHALL be less than 100ms for a single image
3. WHEN classification is requested on CPU-only hardware, THE inference time SHALL be less than 500ms for a single image
4. WHEN the model is loaded, THE system SHALL occupy approximately 20MB of memory for the checkpoint
5. WHEN multiple concurrent classification requests are received, THE system SHALL handle them without race conditions or data corruption
6. WHERE GPU memory is insufficient, THE system SHALL automatically fall back to CPU processing
7. WHERE the model has been idle for a configurable period (default 30 minutes), THE system SHALL support automatic unloading to free memory

### Requirement 10: Medical Disclaimer and Safety

**User Story:** As a compliance officer, I want all classification results to include medical disclaimers and warnings, so that users understand the limitations and proper use of the AI predictions.

#### Acceptance Criteria

1. FOR ALL Classification_Results, THE system SHALL include the complete Medical_Disclaimer text
2. THE Medical_Disclaimer SHALL state that predictions are for educational purposes only
3. THE Medical_Disclaimer SHALL state that the tool is not a substitute for professional medical advice, diagnosis, or treatment
4. THE Medical_Disclaimer SHALL instruct users to consult a qualified dermatologist or healthcare provider
5. THE Medical_Disclaimer SHALL state that the tool is not FDA-approved
6. WHEN displaying classification results in the UI, THE system SHALL prominently display the Medical_Disclaimer
7. WHEN classification results are provided via API, THE disclaimer field SHALL be non-empty and clearly visible in the JSON response

### Requirement 11: Security and Privacy

**User Story:** As a security engineer, I want uploaded images to be handled securely without persistent storage, so that user privacy is protected and attack vectors are minimized.

#### Acceptance Criteria

1. WHEN an image is uploaded for classification, THE system SHALL process it in memory without writing to disk
2. WHEN classification is complete, THE system SHALL immediately discard the image bytes from memory
3. THE system SHALL NOT store any uploaded images in any persistent storage system
4. THE system SHALL NOT log image bytes or base64-encoded image data
5. WHEN validating uploaded files, THE system SHALL verify the MIME type matches the actual file content to prevent malicious file uploads
6. THE system SHALL enforce a maximum upload size of 10MB to prevent denial-of-service attacks
7. WHEN the Model_Checkpoint file is loaded, THE system SHALL verify file permissions prevent unauthorized modification

### Requirement 12: Rate Limiting and Abuse Prevention

**User Story:** As a system administrator, I want rate limiting on classification endpoints, so that the service remains available and is not abused by excessive requests.

#### Acceptance Criteria

1. THE /classify endpoint SHALL enforce a rate limit of 10 requests per minute per IP address
2. WHEN a client exceeds the rate limit, THE system SHALL return HTTP 429 with message "Too many requests. Please try again later."
3. WHEN a rate limit is enforced, THE response SHALL include a Retry-After header indicating when the client can retry
4. THE rate limit configuration SHALL be configurable without code changes
5. WHERE different rate limits are needed for authenticated vs anonymous users, THE system SHALL support tiered rate limiting
6. WHEN rate limit thresholds are reached, THE system SHALL log the event for monitoring and analysis
7. THE rate limiting mechanism SHALL be thread-safe and accurate under concurrent load

### Requirement 13: Configuration Management

**User Story:** As a deployment engineer, I want configurable parameters for the classifier service, so that I can tune the system for different environments without code changes.

#### Acceptance Criteria

1. THE system SHALL support configuration of the model_path parameter specifying the location of the Model_Checkpoint file
2. THE system SHALL support configuration of the device parameter with values: "cpu", "cuda", or "auto"
3. THE system SHALL support configuration of enable_caching to control response caching
4. THE system SHALL support configuration of cache_size to control the maximum number of cached results
5. THE system SHALL support configuration of auto_unload_minutes to control automatic model unloading after inactivity
6. THE system SHALL support configuration of max_image_size_mb to control the maximum upload size
7. THE system SHALL support configuration of rate_limit to control API rate limiting parameters

### Requirement 14: Health Monitoring and Observability

**User Story:** As a system operator, I want to monitor the health and performance of the classification service, so that I can detect and respond to issues proactively.

#### Acceptance Criteria

1. THE system SHALL provide a /health/classifier endpoint that returns the current service status
2. WHEN the model is loaded and operational, THE /health/classifier endpoint SHALL return HTTP 200 with status "healthy"
3. WHEN the model is not loaded or unavailable, THE /health/classifier endpoint SHALL return HTTP 503 with status "unavailable"
4. THE system SHALL log each classification request with metadata: timestamp, processing_time_ms, top_prediction, and status
5. THE system SHALL log model loading events with metadata: timestamp, device, memory_usage, and loading_time_ms
6. WHEN errors occur, THE system SHALL log error events with metadata: error_type, error_message, and request_context
7. THE logging output SHALL NOT include sensitive information such as image data or personal identifiers

### Requirement 15: Backwards Compatibility

**User Story:** As an existing application user, I want the new classification feature to not disrupt existing chat functionality, so that I can continue using the application without interruption.

#### Acceptance Criteria

1. WHEN the classification feature is added, THE existing /chat endpoint SHALL maintain its current API contract
2. WHEN the classification feature is added, THE existing /upload endpoint SHALL continue to function without changes
3. WHEN the classification feature is added, THE existing session management SHALL remain unchanged
4. WHERE the Model_Checkpoint file is missing, THE chat functionality SHALL continue to operate normally
5. WHERE classification is disabled via configuration, THE application SHALL function normally without classification capabilities
6. WHEN existing users access the application, THE user interface SHALL remain familiar with classification features as optional additions
7. THE classification feature SHALL NOT introduce breaking changes to any existing API endpoints

## Non-Functional Requirements

### NFR 1: Performance

**Description**: The system shall provide responsive classification with acceptable latency under normal operating conditions.

**Criteria**:
- Model loading time shall not exceed 5 seconds on recommended hardware
- Single image classification shall complete within 100ms on GPU or 500ms on CPU
- The application shall handle at least 10 concurrent classification requests without degradation
- Memory usage shall not exceed 2GB for the classifier service including model and buffers

### NFR 2: Reliability

**Description**: The system shall operate consistently and recover gracefully from failures.

**Criteria**:
- The classifier service shall achieve 99.9% uptime during normal operation
- Classification determinism shall be maintained: identical inputs produce identical outputs
- The system shall recover automatically from transient errors without manual intervention
- Model loading failures shall not crash the application or affect other services

### NFR 3: Scalability

**Description**: The system shall support future growth in usage and capability.

**Criteria**:
- The architecture shall support horizontal scaling by running multiple application instances
- The singleton pattern shall be scoped per-process to enable multi-instance deployment
- The design shall accommodate future addition of response caching (Redis) without architectural changes
- The design shall support future migration to asynchronous processing (Celery) without breaking changes

### NFR 4: Maintainability

**Description**: The system shall be easy to understand, modify, and extend.

**Criteria**:
- Code coverage shall exceed 85% for the classifier service and related components
- All public interfaces shall have comprehensive docstrings with parameter and return type documentation
- Error messages shall be clear and actionable for both users and developers
- Configuration shall be externalized and modifiable without code changes

### NFR 5: Security

**Description**: The system shall protect user data and resist common attack vectors.

**Criteria**:
- All image uploads shall be transmitted over HTTPS
- The system shall validate all inputs and reject malformed requests
- Rate limiting shall prevent resource exhaustion attacks
- No user-uploaded content shall be persisted to disk
- Error messages shall not expose internal system details or file paths

### NFR 6: Compliance

**Description**: The system shall meet medical software ethical and legal standards.

**Criteria**:
- All predictions shall include the Medical_Disclaimer prominently
- The system shall not claim diagnostic accuracy or FDA approval
- Users shall be clearly informed that the tool is for educational purposes only
- The system shall direct users to consult qualified medical professionals
- All interactions shall be designed to prevent misuse for medical decision-making

### NFR 7: Usability

**Description**: The system shall be intuitive and provide clear feedback to users.

**Criteria**:
- Classification results shall use plain language disease names, not codes
- Confidence scores shall be presented as percentages for user comprehension
- Error messages shall be user-friendly and suggest corrective actions
- The UI shall clearly indicate when classification is in progress
- Results shall include educational descriptions of predicted conditions

### NFR 8: Portability

**Description**: The system shall operate across different hardware and deployment environments.

**Criteria**:
- The system shall function on CPU-only hardware without requiring GPU
- GPU acceleration shall be automatically detected and utilized when available
- The system shall operate on Linux, macOS, and Windows operating systems
- Hardware requirements shall be clearly documented in deployment guides
- The system shall gracefully degrade from GPU to CPU if GPU memory is insufficient
