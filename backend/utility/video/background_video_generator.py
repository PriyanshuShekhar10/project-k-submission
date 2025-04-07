import os
import requests
from utility.utils import log_response, LOG_TYPE_PEXEL
from openai import OpenAI

PEXELS_API_KEY = os.environ.get('PEXELS_KEY')


def search_videos(query_string, orientation_landscape=True):
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Remove the animation terms enhancement
    params = {
        "query": query_string,  # Use original query directly
        "orientation": "landscape" if orientation_landscape else "portrait",
        "per_page": 15,
        "size": "large"
    }

    response = requests.get(url, headers=headers, params=params)
    json_data = response.json()
    log_response(LOG_TYPE_PEXEL, query_string, response.json())

    return json_data


def getBestVideo(query_string, orientation_landscape=True, used_vids=[]):
    vids = search_videos(query_string, orientation_landscape)
    videos = vids['videos']  # Extract the videos list from JSON

    # Filter and extract videos with width and height as 1920x1080 for landscape or 1080x1920 for portrait
    if orientation_landscape:
        filtered_videos = [video for video in videos if video['width'] >=
                           1920 and video['height'] >= 1080 and video['width']/video['height'] == 16/9]
    else:
        filtered_videos = [video for video in videos if video['width'] >=
                           1080 and video['height'] >= 1920 and video['height']/video['width'] == 16/9]

    # Sort the filtered videos by duration in descending order to prefer longer videos
    sorted_videos = sorted(
        filtered_videos, key=lambda x: x['duration'], reverse=True)

    # Extract the top video URL
    for video in sorted_videos:
        for video_file in video['video_files']:
            if orientation_landscape:
                if video_file['width'] == 1920 and video_file['height'] == 1080:
                    if not (video_file['link'].split('.hd')[0] in used_vids):
                        return video_file['link']
            else:
                if video_file['width'] == 1080 and video_file['height'] == 1920:
                    if not (video_file['link'].split('.hd')[0] in used_vids):
                        return video_file['link']
    print("NO LINKS found for this round of search with query :", query_string)
    return None


def generate_video_url(timed_video_searches, server):
    """
    Generate video URLs for each segment based on search terms
    """
    if server == "pexel":
        return generate_video_url_pexel(timed_video_searches)
    else:
        return None


def generate_video_url_pexel(timed_video_searches):
    """
    Generate video URLs using Pexels API
    """
    if not timed_video_searches:
        return None

    result = []
    for start_time, end_time, search_terms in timed_video_searches:
        if not search_terms:
            continue

        # Use the first search term for video search
        search_term = search_terms[0] if isinstance(
            search_terms, list) else search_terms

        # Get video URL from Pexels
        video_url = search_pexels_video(search_term)
        if video_url:
            result.append([start_time, end_time, video_url])

    return result if result else None


def search_pexels_video(query):
    """
    Search for a video on Pexels
    """
    try:
        headers = {
            'Authorization': os.getenv('PEXELS_API_KEY')
        }

        # Remove the animation terms enhancement
        params = {
            'query': query,  # Use original query directly
            'per_page': 1,
            'orientation': 'portrait',
            'size': 'large'
        }

        response = requests.get(
            'https://api.pexels.com/videos/search',
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('videos'):
                video = data['videos'][0]
                video_files = video['video_files']
                # Get HD video file with height >= 1920
                hd_video = next(
                    (v for v in video_files if v['quality'] == 'hd' and v.get(
                        'height', 0) >= 1920),
                    # Fallback to first video file if no HD version found
                    video_files[0]
                )
                return hd_video['link']
        else:
            print(
                f"Pexels API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error searching Pexels: {str(e)}")

    return None
