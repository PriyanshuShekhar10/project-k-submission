# Text-to-Video Generator API Documentation

## Base URL

```
http://localhost:5000/api/v1
```

## Authentication

Currently, the API does not require authentication. However, it requires the following environment variables to be set:

- `OPENAI_API_KEY`: Your OpenAI API key
- `PEXELS_API_KEY`: Your Pexels API key

## Endpoints

### 1. Generate Video

Starts a new video generation job.

**Endpoint:** `POST /generate`

**Request Body:**

```json
{
  "text": "Your story or text content here"
}
```

**Response (202 Accepted):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video generation started"
}
```

**Error Response (400 Bad Request):**

```json
{
  "error": "No text provided in request body"
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "error": "Error message details"
}
```

### 2. Get Job Status

Check the status of a video generation job.

**Endpoint:** `GET /status/<job_id>`

**Parameters:**

- `job_id`: UUID of the job (received from generate endpoint)

**Response (200 OK):**

```json
{
  "status": "processing",
  "progress": 60,
  "message": "Generating video search queries...",
  "created_at": 1648656000,
  "logs": [
    "Starting audio generation...",
    "Audio generation completed",
    "Starting caption generation...",
    "Caption generation completed",
    "Starting search query generation..."
  ]
}
```

**Possible Status Values:**

- `queued`: Job is waiting to start
- `processing`: Video is being generated
- `completed`: Video is ready for download
- `failed`: An error occurred

**Progress Stages:**

- 0%: Job queued
- 20%: Audio generation
- 40%: Caption generation
- 60%: Search query generation
- 80%: Background video fetching
- 90%: Video rendering
- 100%: Completed

**Error Response (404 Not Found):**

```json
{
  "error": "Job not found"
}
```

### 3. Download Video

Download the generated video file.

**Endpoint:** `GET /download/<job_id>`

**Parameters:**

- `job_id`: UUID of the job

**Response (200 OK):**

- Content-Type: video/mp4
- File download with name: `generated_video_<job_id>.mp4`

**Error Responses:**

**404 Not Found:**

```json
{
  "error": "Job not found"
}
```

**400 Bad Request:**

```json
{
  "error": "Video not ready for download"
}
```

**500 Internal Server Error:**

```json
{
  "error": "Output file not found"
}
```

or

```json
{
  "error": "Video file not found"
}
```

or

```json
{
  "error": "Error sending file: [specific error message]"
}
```

**Important Notes for Download:**

1. Always check the job status before attempting to download
2. The video generation process can take several minutes
3. The final video writing step (90-100%) may take longer than other steps
4. Wait until status is "completed" before attempting to download
5. The video file is saved in the `output` directory with the format: `video_<job_id>.mp4`

### 4. List All Jobs

Get a list of all jobs and their statuses.

**Endpoint:** `GET /jobs`

**Response (200 OK):**

```json
{
  "jobs": {
    "job_id_1": {
      "status": "completed",
      "progress": 100,
      "message": "Video generation completed",
      "created_at": 1648656000,
      "output_file": "output/video_job_id_1.mp4",
      "logs": [
        "Starting audio generation...",
        "Audio generation completed"
        // ... more logs
      ]
    },
    "job_id_2": {
      "status": "processing",
      "progress": 60,
      "message": "Generating video search queries...",
      "created_at": 1648656000,
      "logs": [
        // ... processing logs
      ]
    }
  }
}
```

## Usage Examples

### Using cURL

1. Start a new video generation:

```bash
curl -X POST http://localhost:5000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Once upon a time, in a faraway land..."}'
```

2. Check job status:

```bash
curl http://localhost:5000/api/v1/status/550e8400-e29b-41d4-a716-446655440000
```

3. Download video (only after status is "completed"):

```bash
curl http://localhost:5000/api/v1/download/550e8400-e29b-41d4-a716-446655440000 \
  --output video.mp4
```

4. List all jobs:

```bash
curl http://localhost:5000/api/v1/jobs
```

### Using Python

```python
import requests
import time

# Start video generation
response = requests.post(
    'http://localhost:5000/api/v1/generate',
    json={'text': 'Once upon a time, in a faraway land...'}
)
job_id = response.json()['job_id']

# Poll for status
while True:
    status_response = requests.get(f'http://localhost:5000/api/v1/status/{job_id}')
    status_data = status_response.json()

    if status_data['status'] in ['completed', 'failed']:
        break

    print(f"Progress: {status_data['progress']}% - {status_data['message']}")
    time.sleep(2)

# Download video if completed
if status_data['status'] == 'completed':
    video_response = requests.get(f'http://localhost:5000/api/v1/download/{job_id}')
    with open('output_video.mp4', 'wb') as f:
        f.write(video_response.content)
```

## Error Handling

The API uses standard HTTP status codes:

- 200: Success
- 202: Accepted (for async operations)
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

All error responses follow this format:

```json
{
  "error": "Error message description"
}
```

## Notes

1. The API processes videos asynchronously, so you should:

   - First call the generate endpoint
   - Use the returned job_id to poll the status endpoint
   - Once status is 'completed', use the download endpoint

2. Generated files are stored with unique names based on the job_id:

   - Audio: `audio_<job_id>.wav`
   - Video: `output/video_<job_id>.mp4`

3. The API maintains job status in memory, so status information will be lost if the server restarts.

4. For production use, consider:
   - Adding authentication
   - Implementing rate limiting
   - Using a persistent storage for job status
   - Adding input validation
   - Implementing proper error logging
   - Adding request timeout handling
