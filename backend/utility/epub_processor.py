import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re


def read_epub(epub_file):
    """Process EPUB file and extract chapters"""
    book = epub.read_epub(epub_file)
    chapters = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Parse HTML content
            soup = BeautifulSoup(item.get_content(), 'html.parser')

            # Extract text content
            text = soup.get_text()
            text = re.sub(r'\s+', ' ', text).strip()

            # Only include non-empty chapters
            if text and len(text) > 100:  # Minimum length to be considered a chapter
                chapter_title = soup.find(['h1', 'h2'])
                title = chapter_title.get_text().strip(
                ) if chapter_title else f"Chapter {len(chapters) + 1}"

                chapters.append({
                    'title': title,
                    'content': text
                })

    return chapters
