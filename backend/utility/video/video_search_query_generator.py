from openai import OpenAI
import os
import json
import re
from datetime import datetime
from utility.utils import log_response, LOG_TYPE_GPT

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if GROQ_API_KEY and len(GROQ_API_KEY) > 30:
    from groq import Groq
    model = "llama3-70b-8192"
    client = Groq(
        api_key=GROQ_API_KEY,
    )
else:
    model = "gpt-4"
    OPENAI_API_KEY = os.environ.get('OPENAI_KEY')
    client = OpenAI(api_key=OPENAI_API_KEY)

log_directory = ".logs/gpt_logs"

prompt = """# Instructions

Given the following video script and timed captions, extract three visually concrete and specific keywords for each time segment that can be used to search for background videos. The keywords should be short and capture the main essence of the sentence. They can be synonyms or related terms. If a caption is vague or general, consider the next timed caption for more context. If a keyword is a single word, try to return a two-word keyword that is visually concrete. If a time frame contains two or more important pieces of information, divide it into shorter time frames with one keyword each. Ensure that the time periods are strictly consecutive and cover the entire length of the video. Each keyword should cover between 2-4 seconds. The output should be in JSON format, like this: [[[t1, t2], ["keyword1", "keyword2", "keyword3"]], [[t2, t3], ["keyword4", "keyword5", "keyword6"]], ...]. Please handle all edge cases, such as overlapping time segments, vague or general captions, and single-word keywords.

For example, if the caption is 'The cheetah is the fastest land animal, capable of running at speeds up to 75 mph', the keywords should include 'cheetah running', 'fastest animal', and '75 mph'. Similarly, for 'The Great Wall of China is one of the most iconic landmarks in the world', the keywords should be 'Great Wall of China', 'iconic landmark', and 'China landmark'.

Important Guidelines:

Use only English in your text queries.
Each search string must depict something visual.
The depictions have to be extremely visually concrete, like rainy street, or cat sleeping.
'emotional moment' <= BAD, because it doesn't depict something visually.
'crying child' <= GOOD, because it depicts something visual.
The list must always contain the most relevant and appropriate query searches.
['Car', 'Car driving', 'Car racing', 'Car parked'] <= BAD, because it's 4 strings.
['Fast car'] <= GOOD, because it's 1 string.
['Un chien', 'une voiture rapide', 'une maison rouge'] <= BAD, because the text query is NOT in English.

Note: Your response should be the response only and no extra text or data.
  """


def fix_json(json_str):
    # Replace typographical apostrophes with straight quotes
    json_str = json_str.replace("'", "'")
    # Replace any incorrect quotes (e.g., mixed single and double quotes)
    json_str = json_str.replace(""","\"").replace(""", "\"").replace(
        "'", "\"").replace("'", "\"")
    # Add escaping for quotes within the strings
    json_str = json_str.replace('"you didn"t"', '"you didn\'t"')
    return json_str


def getVideoSearchQueriesTimed(content, timed_captions):
    """
    Generate video search queries for each segment of the content
    """
    try:
        # Extract text segments
        segments = []
        current_segment = []
        current_start = 0
        segment_duration = 4  # seconds per segment

        # Parse timed captions
        captions = []
        for caption in timed_captions:
            if isinstance(caption, tuple) and len(caption) == 2:
                time_range, text = caption
                if isinstance(time_range, tuple) and len(time_range) == 2:
                    start_time, end_time = time_range
                    captions.append((float(start_time), float(end_time), text))

        # Group captions into segments
        if not captions:
            return None

        current_segment = []
        current_start = captions[0][0]
        current_end = current_start + segment_duration
        # Get the end time of the last caption
        total_duration = captions[-1][1]

        for i, caption in enumerate(captions):
            start_time, end_time, text = caption

            # If this caption starts after the current segment ends, create a new segment
            if start_time >= current_end:
                # Create search terms for the current segment
                if current_segment:
                    segment_text = " ".join([c[2] for c in current_segment])
                    search_terms = generate_search_terms(segment_text)
                    segments.append([current_start, current_end, search_terms])

                # Start a new segment
                current_segment = []
                current_start = start_time
                current_end = min(
                    current_start + segment_duration, total_duration)

            current_segment.append(caption)

            # Handle the last caption
            if i == len(captions) - 1:
                # Create search terms for the final segment
                if current_segment:
                    segment_text = " ".join([c[2] for c in current_segment])
                    search_terms = generate_search_terms(segment_text)
                    # Use the actual end time of the last caption
                    segments.append([current_start, end_time, search_terms])

        # Ensure we have coverage for the entire duration
        if segments:
            last_segment_end = segments[-1][1]
            if last_segment_end < total_duration:
                # Add one more segment to cover the remaining time
                last_segment = segments[-1]
                segments.append([
                    last_segment_end,
                    total_duration,
                    last_segment[2]  # Reuse the last segment's search terms
                ])

        return segments
    except Exception as e:
        print(f"Error in getVideoSearchQueriesTimed: {str(e)}")
        return None


def generate_search_terms(text):
    """
    Generate search terms for a segment of text
    """
    try:
        # Use OpenAI to generate relevant search terms
        client = OpenAI()
        prompt = f"Generate 3 specific, visual search terms for video footage that would match this text: '{text}'. Format as a JSON array of strings. Example: ['peaceful nature', 'flowing water', 'sunset view']"

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates specific video search terms."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract and parse the JSON array from the response
        search_terms_str = response.choices[0].message.content.strip()
        if search_terms_str.startswith("[") and search_terms_str.endswith("]"):
            search_terms = json.loads(search_terms_str)
            return search_terms
        else:
            # If not proper JSON, try to extract terms from the text
            terms = re.findall(r'"([^"]*)"', search_terms_str)
            return terms if terms else None

    except Exception as e:
        print(f"Error in generate_search_terms: {str(e)}")
        return None


def call_OpenAI(script, captions_timed):
    user_content = """Script: {}
Timed Captions:{}
""".format(script, "".join(map(str, captions_timed)))
    print("Content", user_content)

    response = client.chat.completions.create(
        model=model,
        temperature=1,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content}
        ]
    )

    text = response.choices[0].message.content.strip()
    text = re.sub('\s+', ' ', text)
    print("Generated search terms:", text)
    log_response(LOG_TYPE_GPT, script, text)
    return text


def merge_empty_intervals(segments):
    """
    Merge empty intervals in the segments list
    """
    if segments is None:
        return []

    if len(segments) == 0:
        return segments

    result = []
    i = 0

    while i < len(segments):
        current = segments[i]

        # Skip if current segment is empty
        if not current[2]:  # if the URL list is empty
            i += 1
            continue

        # Add non-empty segments to result
        result.append(current)
        i += 1

    return result if result else None
