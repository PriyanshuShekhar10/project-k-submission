import os
from openai import OpenAI
from typing import Literal, Tuple

ThemeType = Literal["comedy", "exciting", "relaxing", "sad", "thriller"]


def analyze_theme(text: str) -> Tuple[ThemeType, str]:
    """
    Analyze the text content to determine the appropriate theme and background music.
    Returns a tuple of (theme_type, music_file_path)
    """
    client = OpenAI()

    prompt = f"""Analyze the following text and determine its emotional theme. 
    Choose one of these themes: comedy, exciting, relaxing, sad, thriller.
    Consider the overall tone, emotional content, and purpose of the text.
    
    Text: {text}
    
    Respond with just the theme name, nothing else."""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a theme analyzer that categorizes content into specific emotional themes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3  # Lower temperature for more consistent categorization
    )

    theme = response.choices[0].message.content.strip().lower()

    # Map theme to music file
    theme_to_music = {
        "comedy": "utility/comedy.mp3",
        "exciting": "utility/exciting.mp3",
        "relaxing": "utility/relaxing.mp3",
        "sad": "utility/sad.mp3",
        "thriller": "utility/thriller.mp3"
    }

    # Default to relaxing if theme is not recognized
    theme_type = theme if theme in theme_to_music else "relaxing"
    music_path = theme_to_music[theme_type]

    return theme_type, music_path
