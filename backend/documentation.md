# Text-to-Video Generation System Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [API Documentation](#api-documentation)
5. [Technical Implementation](#technical-implementation)
6. [Pipeline Details](#pipeline-details)
7. [Error Handling](#error-handling)
8. [Future Enhancements](#future-enhancements)

## Introduction

Our text-to-video generation system is a sophisticated platform that transforms written content into engaging video presentations. The system is built with a modular architecture, separating concerns between frontend and backend, and utilizing modern technologies for audio and video processing.

### Key Features

- Text-to-video conversion
- Audio generation from text
- Caption generation and synchronization
- Background video integration
- EPUB file support
- Real-time progress tracking
- RESTful API interface

## System Architecture

### 1. Frontend (React + Vite)

- Built with React and Vite for fast development and optimal performance
- Features a modern, responsive UI with real-time progress tracking
- Supports both text input and EPUB file uploads
- Implements polling mechanisms for status updates
- Uses modern React hooks and async/await patterns

### 2. Backend (Flask API)

- RESTful API built with Flask
- Implements CORS for secure cross-origin requests
- Uses threading for background processing
- Maintains job status tracking
- Handles file uploads and downloads

## Core Components

### 1. Text Processing

- Accepts plain text or EPUB files
- For EPUB files:
  - Uses epubjs for parsing
  - Extracts text content
  - Maintains chapter structure
  - Supports metadata extraction

### 2. Audio Generation

- Utilizes OpenAI's text-to-speech API
- Generates high-quality WAV audio files
- Supports multiple voices and languages
- Implements rate limiting and error handling

### 3. Caption Generation

- Uses Whisper for speech-to-text conversion
- Generates timed captions
- Supports multiple languages
- Maintains synchronization with audio

### 4. Video Generation

- Background video selection from Pexels
- Intelligent scene matching with text content
- Video resizing and processing
- Caption overlay with proper timing

## API Documentation

### Video Generation Endpoints

1. `POST /api/v1/generate`

   ```python
   @app.route('/api/v1/generate', methods=['POST'])
   def generate_video():
       data = request.get_json()
       script = data['text']
       job_id = str(uuid.uuid4())
       # Process video generation
   ```

   - Initiates video generation
   - Returns job ID for tracking
   - Accepts text input

2. `GET /api/v1/status/<job_id>`

   ```python
   @app.route('/api/v1/status/<job_id>', methods=['GET'])
   def get_status(job_id):
       if job_id not in jobs:
           return jsonify({'error': 'Job not found'}), 404
       return jsonify(jobs[job_id])
   ```

   - Provides real-time status updates
   - Includes progress percentage
   - Shows detailed logs

3. `GET /api/v1/download/<job_id>`
   ```python
   @app.route('/api/v1/download/<job_id>', methods=['GET'])
   def download_video(job_id):
       # Handle file retrieval and download
   ```
   - Downloads completed video
   - Supports fallback to default output
   - Handles various error cases

### Audio Generation Endpoints

1. `POST /api/v1/generate-audio`

   ```python
   @app.route('/api/v1/generate-audio', methods=['POST'])
   def generate_audio_only():
       # Process audio generation
   ```

   - Generates audio-only output
   - Returns job ID for tracking

2. `GET /api/v1/audio-status/<job_id>`

   ```python
   @app.route('/api/v1/audio-status/<job_id>', methods=['GET'])
   def get_audio_status(job_id):
       # Track audio generation progress
   ```

   - Tracks audio generation progress
   - Provides detailed status information

3. `GET /api/v1/download-audio/<job_id>`
   ```python
   @app.route('/api/v1/download-audio/<job_id>', methods=['GET'])
   def download_audio(job_id):
       # Handle audio file download
   ```
   - Downloads generated audio files
   - Supports WAV format

## Technical Implementation

### 1. Threading and Concurrency

```python
# Thread-safe operations with locks
jobs_lock = threading.Lock()
audio_jobs_lock = threading.Lock()

# Background processing
thread = threading.Thread(target=process_video_generation, args=(job_id, script))
thread.daemon = True
thread.start()
```

### 2. File Management

- Organized output directory structure
- Unique file naming with UUIDs
- Proper cleanup and error handling
- Supports multiple concurrent jobs

### 3. CORS Configuration

```python
CORS(app,
     resources={r"/api/*": {
         "origins": ["http://localhost:5173"],
         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization", "Accept"],
         "expose_headers": ["Content-Type", "Authorization"],
         "supports_credentials": True,
         "max_age": 3600
     }},
     supports_credentials=True
)
```

## Pipeline Details

### 1. Text Processing Pipeline

- Input handling
- EPUB processing
- Text cleaning and formatting

### 2. Audio Generation Pipeline

```python
def generate_audio(text, output_file):
    client = OpenAI()
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    response.stream_to_file(output_file)
```

### 3. Caption Generation Pipeline

```python
def generate_timed_captions(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return result["segments"]
```

### 4. Video Generation Pipeline

- Background video selection
- Video processing
- Caption overlay
- Final rendering

## Error Handling

### 1. Error Detection and Logging

```python
try:
    # Processing steps
except Exception as e:
    jobs[job_id]['status'] = 'failed'
    jobs[job_id]['message'] = str(e)
    logger.error(f"Error in video generation: {str(e)}", exc_info=True)
```

### 2. Recovery Mechanisms

- Graceful degradation
- Partial completion handling
- Resource cleanup
- Status reporting

## Future Enhancements

### 1. Scalability

- Implement queue system
- Add worker nodes
- Support distributed processing

### 2. Features

- More video customization options
- Additional audio voices
- Enhanced caption styling
- Template support

### 3. Integration

- Cloud storage support
- Social media sharing
- Analytics dashboard
- User management

## Conclusion

Our text-to-video generation system represents a sophisticated solution for creating engaging video content from text. The modular architecture, robust error handling, and comprehensive API make it suitable for various use cases, from educational content to marketing materials. The system's ability to handle both text and EPUB inputs, combined with its real-time progress tracking and status updates, provides a seamless user experience.

The implementation of threading and proper resource management ensures efficient processing of multiple requests, while the comprehensive error handling and logging system makes troubleshooting straightforward. The API's RESTful design and CORS support make it easy to integrate with various frontend applications.
