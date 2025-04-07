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
import argparse
from dotenv import load_dotenv
import time
import sys
from flask import Flask, render_template, request, send_file, jsonify, Response
from werkzeug.utils import secure_filename

# Load environment variables from .env file
load_dotenv()

# Debug: Print environment variables
print("Environment variables:")
print("OPENAI_API_KEY:", os.getenv('OPENAI_API_KEY'))
print("PEXELS_API_KEY:", os.getenv('PEXELS_API_KEY'))

app = Flask(__name__)

# Global variable to store progress messages
progress_messages = []


def send_progress(message):
    """Helper function to send progress updates"""
    timestamp = time.strftime("%H:%M:%S")
    progress_messages.append(f"[{timestamp}] {message}")
    return f"data: {message}\n\n"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/progress')
def progress():
    """Endpoint for SSE progress updates"""
    def generate():
        for message in progress_messages:
            yield f"data: {message}\n\n"
        progress_messages.clear()
    return Response(generate(), mimetype='text/event-stream')


@app.route('/generate', methods=['POST'])
def generate():
    try:
        progress_messages.clear()
        data = request.get_json()
        script = data.get('story')

        if not script:
            return jsonify({'error': 'No story provided'}), 400

        # Define constants
        SAMPLE_FILE_NAME = "audio_tts.wav"
        VIDEO_SERVER = "pexel"
        OUTPUT_FILE = "output/rendered_video.mp4"

        send_progress("Starting video generation...")
        send_progress(f"Processing script: {script[:50]}...")

        send_progress("Generating audio using Whisper...")
        generate_audio(script, SAMPLE_FILE_NAME)
        send_progress("Audio generated successfully")

        send_progress("Generating timed captions...")
        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        send_progress("Timed captions generated successfully")
        send_progress(f"Captions: {str(timed_captions)[:100]}...")

        send_progress("Generating video search queries...")
        search_terms = getVideoSearchQueriesTimed(script, timed_captions)
        send_progress("Search queries generated successfully")
        send_progress(f"Search terms: {str(search_terms)[:100]}...")

        send_progress("Fetching background videos...")
        if search_terms is not None:
            background_video_urls = generate_video_url(
                search_terms, VIDEO_SERVER)
            send_progress("Background videos fetched successfully")
            send_progress(f"Video URLs: {str(background_video_urls)[:100]}...")
        else:
            return jsonify({'error': 'Failed to generate search terms'}), 500

        send_progress("Rendering final video...")
        get_output_media(SAMPLE_FILE_NAME, timed_captions,
                         background_video_urls, VIDEO_SERVER)
        send_progress("Video rendering completed!")

        return send_file(OUTPUT_FILE, mimetype='video/mp4')

    except Exception as e:
        error_message = str(e)
        send_progress(f"Error: {error_message}")
        return jsonify({'error': error_message}), 500


def print_status(message, is_error=False):
    timestamp = time.strftime("%H:%M:%S")
    prefix = "❌ ERROR" if is_error else "✅"
    print(f"[{timestamp}] {prefix} {message}")


def main():
    if len(sys.argv) < 2:
        print("Please provide a script as a command line argument")
        print("Usage: python app.py \"Your script text here\"")
        return

    # Define constants
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    # Get the script directly from command line argument
    script = sys.argv[1]

    print_status("Starting video generation")

    try:
        print_status(f"Starting video generation for script: {script}")

        print_status("Generating audio using Whisper...")
        generate_audio(script, SAMPLE_FILE_NAME)
        print_status("Audio generated successfully")

        print_status("Generating timed captions...")
        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        print_status("Timed captions generated successfully")
        print("Captions:", timed_captions)

        print_status("Generating video search queries...")
        search_terms = getVideoSearchQueriesTimed(script, timed_captions)
        print_status("Search queries generated successfully")
        print("Search terms:", search_terms)

        print_status("Fetching background videos...")
        background_video_urls = None
        if search_terms is not None:
            background_video_urls = generate_video_url(
                search_terms, VIDEO_SERVER)
            print_status("Background videos fetched successfully")
            print("Video URLs:", background_video_urls)
        else:
            print_status("No background videos found", is_error=True)

        print_status("Merging video intervals...")
        background_video_urls = merge_empty_intervals(background_video_urls)

        print_status("Rendering final video...")
        if background_video_urls is not None:
            video = get_output_media(
                SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            print_status("Video rendered successfully")
            print("Output video:", video)
        else:
            print_status(
                "Failed to render video - no background videos available", is_error=True)

    except Exception as e:
        print_status(f"An error occurred: {str(e)}", is_error=True)
        raise


if __name__ == "__main__":
    app.run(debug=True)
