import os
from openai import OpenAI
import json
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Debug: Print environment variables
print("Debug - Environment variables in script_generator.py:")
print("OPENAI_API_KEY:", os.getenv('OPENAI_API_KEY'))

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if GROQ_API_KEY and len(GROQ_API_KEY) > 30:
    from groq import Groq
    model = "mixtral-8x7b-32768"
    client = Groq(
        api_key=GROQ_API_KEY,
    )
else:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    print("Debug - Using OpenAI with key:", OPENAI_API_KEY[:10] + "...")
    model = "gpt-4"
    client = OpenAI(api_key=OPENAI_API_KEY)


def generate_script(topic):
    prompt = (
        """You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos. 
        Your facts shorts are very concise, each lasting around 20 seconds (approximately 50-60 words). 
        They are incredibly engaging and original. When a user requests a specific type of facts short, you will create it.

        For instance, if the user asks for:
        Weird facts
        You would produce content like this:

        Weird facts you don't know:
        - Bananas are berries, but strawberries aren't.
        - A single cloud can weigh over a million pounds.
        - Honey never spoils; archaeologists have found 3,000-year-old edible honey.
        - Octopuses have three hearts and blue blood.

        You are now tasked with creating the best short script based on the user's requested type of 'facts'.

        Keep it very brief (20 seconds), highly interesting, and unique.

        Stictly output the script in a JSON format like below, and only provide a parsable JSON object with the key 'script'.

        # Output
        {"script": "Here is the script ..."}
        """
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ]
    )
    content = response.choices[0].message.content
    try:
        # First try to parse as is
        script = json.loads(content)["script"]
    except Exception as e:
        # If that fails, try to extract just the script content
        print(f"Original content: {content}")
        # Find the actual script content between quotes after "script":
        match = re.search(r'"script":\s*"([^"]*)"', content)
        if match:
            script = match.group(1)
        else:
            # If no match found, just return the content as is
            script = content
    return script
