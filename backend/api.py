from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
import os
import json
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
from dotenv import load_dotenv
import time
import uuid
import sys
from io import StringIO
import contextlib
import threading
import logging
import shutil

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS for all origins with specific configuration
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

# Store job statuses
jobs = {}
audio_jobs = {}  # New dictionary for audio-only jobs

# Lock for thread safety
jobs_lock = threading.Lock()
audio_jobs_lock = threading.Lock()


def capture_output(func):
    """Decorator to capture stdout and stderr"""
    def wrapper(*args, **kwargs):
        output = StringIO()
        with contextlib.redirect_stdout(output):
            with contextlib.redirect_stderr(output):
                result = func(*args, **kwargs)
        return result, output.getvalue()
    return wrapper


@capture_output
def process_video_generation(job_id, script):
    """Process video generation in the background"""
    try:
        with jobs_lock:
            jobs[job_id]['status'] = 'processing'
            jobs[job_id]['progress'] = 0
            jobs[job_id]['logs'] = []

        # Define constants
        SAMPLE_FILE_NAME = f"audio_{job_id}.wav"
        VIDEO_SERVER = "pexel"
        OUTPUT_FILE = f"output/video_{job_id}.mp4"

        # Generate audio
        with jobs_lock:
            jobs[job_id]['progress'] = 20
            jobs[job_id]['message'] = "Generating audio..."
            jobs[job_id]['logs'].append("Starting audio generation...")
        generate_audio(script, SAMPLE_FILE_NAME)
        with jobs_lock:
            jobs[job_id]['logs'].append("Audio generation completed")

        # Generate captions
        with jobs_lock:
            jobs[job_id]['progress'] = 40
            jobs[job_id]['message'] = "Generating captions..."
            jobs[job_id]['logs'].append("Starting caption generation...")
        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        with jobs_lock:
            jobs[job_id]['logs'].append("Caption generation completed")

        # Generate search queries
        with jobs_lock:
            jobs[job_id]['progress'] = 60
            jobs[job_id]['message'] = "Generating video search queries..."
            jobs[job_id]['logs'].append("Starting search query generation...")
        search_terms = getVideoSearchQueriesTimed(script, timed_captions)
        with jobs_lock:
            jobs[job_id]['logs'].append("Search query generation completed")

        # Fetch background videos
        with jobs_lock:
            jobs[job_id]['progress'] = 80
            jobs[job_id]['message'] = "Fetching background videos..."
            jobs[job_id]['logs'].append(
                "Starting background video fetching...")
        if search_terms is not None:
            background_video_urls = generate_video_url(
                search_terms, VIDEO_SERVER)
            background_video_urls = merge_empty_intervals(
                background_video_urls)
            with jobs_lock:
                jobs[job_id]['logs'].append(
                    "Background videos fetched successfully")

            # Render final video
            with jobs_lock:
                jobs[job_id]['progress'] = 90
                jobs[job_id]['message'] = "Rendering final video..."
                jobs[job_id]['logs'].append("Starting video rendering...")
            get_output_media(SAMPLE_FILE_NAME, timed_captions,
                             background_video_urls, VIDEO_SERVER)
            with jobs_lock:
                jobs[job_id]['logs'].append("Video rendering completed")

            # Copy the generated video to the job-specific filename
            if os.path.exists("output/rendered_video.mp4"):
                shutil.copy2("output/rendered_video.mp4", OUTPUT_FILE)
                with jobs_lock:
                    jobs[job_id]['logs'].append(
                        "Video file copied to job-specific location")

                    # Update job status to completed
                    jobs[job_id]['status'] = 'completed'
                    jobs[job_id]['progress'] = 100
                    jobs[job_id]['message'] = "Video generation completed"
                    jobs[job_id]['output_file'] = OUTPUT_FILE
                    jobs[job_id]['logs'].append("Job completed successfully")
            else:
                jobs[job_id]['status'] = 'failed'
                jobs[job_id]['message'] = "Failed to copy video file"
                jobs[job_id]['logs'].append(
                    "Error: Output video file not found")

        else:
            jobs[job_id]['status'] = 'failed'
            jobs[job_id]['message'] = "Failed to generate search terms"
            jobs[job_id]['logs'].append(
                "Error: Failed to generate search terms")

    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['message'] = str(e)
        jobs[job_id]['logs'].append(f"Error: {str(e)}")
        logger.error(f"Error in video generation: {str(e)}", exc_info=True)


@app.route('/api/v1/generate', methods=['POST'])
def generate_video():
    """Start video generation process"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'error': 'No text provided in request body'
            }), 400

        job_id = str(uuid.uuid4())
        script = data['text']

        # Initialize job status
        with jobs_lock:
            jobs[job_id] = {
                'status': 'queued',
                'progress': 0,
                'message': 'Job queued',
                'created_at': time.time(),
                'logs': []
            }

        # Start processing in background thread
        thread = threading.Thread(
            target=process_video_generation, args=(job_id, script))
        thread.daemon = True  # Thread will exit when main program exits
        thread.start()

        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Video generation started'
        }), 202

    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/v1/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get status of a video generation job"""
    if job_id not in jobs:
        return jsonify({
            'error': 'Job not found'
        }), 404

    return jsonify(jobs[job_id])


@app.route('/api/v1/download/<job_id>', methods=['GET'])
def download_video(job_id):
    """Download the generated video"""
    try:
        if job_id not in jobs:
            logger.error(f"Job {job_id} not found")
            return jsonify({
                'error': 'Job not found'
            }), 404

        job = jobs[job_id]
        if job['status'] != 'completed':
            logger.error(
                f"Job {job_id} not completed. Current status: {job['status']}")
            return jsonify({
                'error': 'Video not ready for download'
            }), 400

        output_file = job.get('output_file')
        if not output_file:
            logger.error(f"No output file specified for job {job_id}")
            return jsonify({
                'error': 'Output file not found'
            }), 500

        # Get absolute path
        abs_path = os.path.abspath(output_file)
        logger.debug(f"Attempting to download file from: {abs_path}")

        if not os.path.exists(abs_path):
            # Try the default rendered video path as fallback
            default_path = os.path.abspath("output/rendered_video.mp4")
            logger.debug(f"Trying fallback path: {default_path}")
            if os.path.exists(default_path):
                return send_file(
                    default_path,
                    mimetype='video/mp4',
                    as_attachment=True,
                    download_name=f'generated_video_{job_id}.mp4'
                )
            else:
                logger.error(
                    f"File not found at either path: {abs_path} or {default_path}")
                return jsonify({
                    'error': 'Video file not found'
                }), 404

        try:
            return send_file(
                abs_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f'generated_video_{job_id}.mp4'
            )
        except Exception as e:
            logger.error(f"Error sending file: {str(e)}", exc_info=True)
            return jsonify({
                'error': f'Error sending file: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(
            f"Unexpected error in download endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/v1/jobs', methods=['GET'])
def list_jobs():
    """List all jobs"""
    return jsonify({
        'jobs': jobs
    })


@capture_output
def process_audio_generation(job_id, text):
    """Process audio generation in the background"""
    try:
        with audio_jobs_lock:
            audio_jobs[job_id]['status'] = 'processing'
            audio_jobs[job_id]['progress'] = 0
            audio_jobs[job_id]['logs'] = []

        # Define constants
        AUDIO_FILE = f"output/audio_{job_id}.wav"

        # Generate audio
        with audio_jobs_lock:
            audio_jobs[job_id]['progress'] = 50
            audio_jobs[job_id]['message'] = "Generating audio..."
            audio_jobs[job_id]['logs'].append("Starting audio generation...")
        generate_audio(text, AUDIO_FILE)
        with audio_jobs_lock:
            audio_jobs[job_id]['logs'].append("Audio generation completed")

        # Update job status to completed
        with audio_jobs_lock:
            audio_jobs[job_id]['status'] = 'completed'
            audio_jobs[job_id]['progress'] = 100
            audio_jobs[job_id]['message'] = "Audio generation completed"
            audio_jobs[job_id]['output_file'] = AUDIO_FILE
            audio_jobs[job_id]['logs'].append("Job completed successfully")

    except Exception as e:
        audio_jobs[job_id]['status'] = 'failed'
        audio_jobs[job_id]['message'] = str(e)
        audio_jobs[job_id]['logs'].append(f"Error: {str(e)}")
        logger.error(f"Error in audio generation: {str(e)}", exc_info=True)


@app.route('/api/v1/generate-audio', methods=['POST'])
def generate_audio_only():
    """Start audio-only generation process"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                'error': 'No text provided in request body'
            }), 400

        job_id = str(uuid.uuid4())
        text = data['text']

        # Initialize job status
        with audio_jobs_lock:
            audio_jobs[job_id] = {
                'status': 'queued',
                'progress': 0,
                'message': 'Job queued',
                'created_at': time.time(),
                'logs': []
            }

        # Start processing in background thread
        thread = threading.Thread(
            target=process_audio_generation, args=(job_id, text))
        thread.daemon = True  # Thread will exit when main program exits
        thread.start()

        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Audio generation started'
        }), 202

    except Exception as e:
        logger.error(
            f"Error in generate-audio endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/v1/audio-status/<job_id>', methods=['GET'])
def get_audio_status(job_id):
    """Get status of an audio generation job"""
    if job_id not in audio_jobs:
        return jsonify({
            'error': 'Job not found'
        }), 404

    return jsonify(audio_jobs[job_id])


@app.route('/api/v1/download-audio/<job_id>', methods=['GET'])
def download_audio(job_id):
    """Download the generated audio"""
    try:
        if job_id not in audio_jobs:
            logger.error(f"Audio job {job_id} not found")
            return jsonify({
                'error': 'Job not found'
            }), 404

        job = audio_jobs[job_id]
        if job['status'] != 'completed':
            logger.error(
                f"Audio job {job_id} not completed. Current status: {job['status']}")
            return jsonify({
                'error': 'Audio not ready for download'
            }), 400

        output_file = job.get('output_file')
        if not output_file:
            logger.error(f"No output file specified for audio job {job_id}")
            return jsonify({
                'error': 'Output file not found'
            }), 500

        # Get absolute path
        abs_path = os.path.abspath(output_file)
        logger.debug(f"Attempting to download audio file from: {abs_path}")

        if not os.path.exists(abs_path):
            logger.error(f"Audio file not found at path: {abs_path}")
            return jsonify({
                'error': 'Audio file not found'
            }), 404

        try:
            return send_file(
                abs_path,
                mimetype='audio/wav',
                as_attachment=True,
                download_name=f'generated_audio_{job_id}.wav'
            )
        except Exception as e:
            logger.error(f"Error sending audio file: {str(e)}", exc_info=True)
            return jsonify({
                'error': f'Error sending file: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(
            f"Unexpected error in download-audio endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/v1/audio-jobs', methods=['GET'])
def list_audio_jobs():
    """List all audio generation jobs"""
    return jsonify({
        'jobs': audio_jobs
    })


if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    # Run with debug mode but without reloader
    app.run(debug=True, use_reloader=False, threaded=True)
