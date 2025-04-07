import time
import os
import tempfile
import zipfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, ImageClip,
                            TextClip, VideoFileClip, concatenate_videoclips)
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
import requests
from moviepy.config import change_settings
from tqdm import tqdm
from PIL import Image
from utility.theme.theme_analyzer import analyze_theme

# Configure ImageMagick binary path
magick_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
if os.path.exists(magick_path):
    change_settings({"IMAGEMAGICK_BINARY": magick_path})
else:
    print("Warning: ImageMagick not found at expected path. Please ensure ImageMagick is installed correctly.")

# Update Pillow's resize method
Image.ANTIALIAS = Image.Resampling.LANCZOS

# Video dimensions for portrait mode
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# Audio settings
VOICE_VOLUME = 1.0  # 100% volume for voice
BACKGROUND_MUSIC_VOLUME = 0.05  # 20% volume for background music


def print_render_status(message, is_error=False):
    timestamp = time.strftime("%H:%M:%S")
    prefix = "❌ ERROR" if is_error else "✅"
    print(f"[{timestamp}] {prefix} {message}")


def download_file(url, filename):
    """
    Download a file from a URL
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.5",
            "Range": "bytes=0-",
            "Connection": "keep-alive"
        }

        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return filename
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)
        return None


def search_program(program_name):
    try:
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None


def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path


def download_video(url_data, output_path):
    print_render_status(f"Downloading video from {url_data}")
    if isinstance(url_data, list):
        # Extract URL from [start_time, end_time, url] format
        url = url_data[2]
    else:
        url = url_data

    print_render_status(f"Downloading from URL: {url}")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(output_path, 'wb') as file, tqdm(
        desc="Downloading",
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            pbar.update(size)
    print_render_status("Video download completed")


def get_output_media(audio_file, timed_captions, background_video_urls, video_server):
    print_render_status("Starting video rendering process")

    # Create output directory if it doesn't exist
    if not os.path.exists("output"):
        os.makedirs("output")

    # Analyze theme and get appropriate background music
    print_render_status("Analyzing content theme")
    all_text = " ".join([text for _, text in timed_captions])
    theme_type, background_music_path = analyze_theme(all_text)
    print_render_status(f"Selected theme: {theme_type}")

    # Get total duration from the last caption
    total_duration = timed_captions[-1][0][1]

    # Download and process background videos
    print_render_status("Processing background videos")
    background_clips = []
    for i, url_data in enumerate(background_video_urls):
        try:
            print_render_status(
                f"Processing video {i+1}/{len(background_video_urls)}")
            video_path = f"output/background_{i}.mp4"
            download_video(url_data, video_path)

            # Load video clip
            print_render_status(f"Loading video {i+1}")
            video_clip = VideoFileClip(video_path)

            # Extract start and end times
            start_time = float(url_data[0])
            end_time = float(url_data[1])
            desired_duration = end_time - start_time

            # If video is shorter than desired duration, loop it
            if video_clip.duration < desired_duration:
                print_render_status(
                    f"Video {i+1} is shorter than desired duration, looping it")
                video_clip = video_clip.loop(duration=desired_duration)
            else:
                # Trim video to match the specified time range
                print_render_status(f"Trimming video {i+1}")
                video_clip = video_clip.subclip(0, desired_duration)

            # Resize video to portrait dimensions
            print_render_status(f"Resizing video {i+1}")
            video_clip = video_clip.resize(newsize=(VIDEO_WIDTH, VIDEO_HEIGHT))

            background_clips.append(video_clip)
        except Exception as e:
            print_render_status(
                f"Error processing video {i+1}: {str(e)}", is_error=True)
            continue

    if not background_clips:
        print_render_status("No valid background clips found", is_error=True)
        return None

    # Concatenate all background clips
    print_render_status("Concatenating background videos")
    final_background = concatenate_videoclips(background_clips)

    # Ensure the background video covers the entire duration
    if final_background.duration < total_duration:
        print_render_status(
            "Extending background video to cover full duration")
        final_background = final_background.loop(duration=total_duration)
    elif final_background.duration > total_duration:
        print_render_status(
            "Trimming background video to match total duration")
        final_background = final_background.subclip(0, total_duration)

    # Load and process audio
    print_render_status("Processing audio")
    voice_audio = AudioFileClip(audio_file)

    # Load theme-appropriate background music
    print_render_status(f"Loading {theme_type} background music")
    background_music = AudioFileClip(background_music_path)

    # Loop background music if needed
    if background_music.duration < total_duration:
        background_music = audio_loop(
            background_music, duration=total_duration)
    else:
        background_music = background_music.subclip(0, total_duration)

    # Adjust volumes
    voice_audio = voice_audio.volumex(VOICE_VOLUME)
    background_music = background_music.volumex(BACKGROUND_MUSIC_VOLUME)

    # Combine audio tracks
    print_render_status("Combining audio tracks")
    final_audio = CompositeAudioClip([background_music, voice_audio])

    # Create text clips for captions
    print_render_status("Creating caption overlays")
    caption_clips = []
    for caption in timed_captions:
        time_range, text = caption
        start_time, end_time = time_range
        text_clip = TextClip(
            text,
            fontsize=60,  # Slightly smaller font for portrait mode
            color='white',
            bg_color='black',
            font='Arial',
            size=(VIDEO_WIDTH - 100, None),  # Leave some margin on the sides
            method='caption',
            align='center'
        )
        # Position captions in the lower third of the screen
        text_clip = text_clip.set_position(('center', VIDEO_HEIGHT - 300)).set_duration(
            end_time - start_time).set_start(start_time)
        caption_clips.append(text_clip)

    # Combine all elements
    print_render_status("Combining video elements")
    final_video = CompositeVideoClip(
        [final_background] + caption_clips,
        size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    )

    # Set audio
    print_render_status("Setting audio track")
    final_video = final_video.set_audio(final_audio)

    # Write final video
    print_render_status("Writing final video (this may take several minutes)")
    output_path = "output/rendered_video.mp4"
    final_video.write_videofile(
        output_path,
        fps=30,
        codec='libx264',
        audio_codec='aac',
        threads=4,
        preset='medium'
    )

    # Clean up
    print_render_status("Cleaning up temporary files")
    final_video.close()
    voice_audio.close()
    background_music.close()
    final_audio.close()
    for clip in background_clips:
        clip.close()

    print_render_status("Video rendering completed successfully")
    return output_path
