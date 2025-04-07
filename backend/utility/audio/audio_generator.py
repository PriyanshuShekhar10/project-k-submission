# import os
# from openai import OpenAI


# def generate_audio(text, output_filename):
#     """
#     Generate audio from text using OpenAI's text-to-speech API
#     """
#     client = OpenAI()

#     # Generate speech using OpenAI's API
#     response = client.audio.speech.create(
#         model="tts-1",
#         voice="alloy",
#         input=text
#     )

#     # Save the audio file
#     response.stream_to_file(output_filename)

#     return output_filename


import os
from openai import OpenAI
import base64


def generate_audio(text: str, output_filename: str) -> str:
    """
    Generate audio from text using OpenAI's new GPT-4 audio model
    """
    client = OpenAI()

    # Generate speech using OpenAI's new GPT-4 audio model
    response = client.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": "alloy", "format": "wav"},
        messages=[
            {
                "role": "user",
                "content": text
            }
        ],
        store=True
    )

    # Extract audio data from response
    audio_data = response.choices[0].message.audio.data

    # Decode base64 audio data and write to file
    with open(output_filename, 'wb') as f:
        f.write(base64.b64decode(audio_data))

    return output_filename
