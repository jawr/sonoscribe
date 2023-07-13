import os
import sys
from ebooklib import ITEM_DOCUMENT, epub
from bs4 import BeautifulSoup
from textsum.summarize import Summarizer


def extract_text_from_ebook(ebook_path: str) -> str:
    book = epub.read_epub(ebook_path)

    book_text = ""
    for item in book.get_items():
        # Skip non-HTML items and irrelevant metadata
        if not item.get_type() == ITEM_DOCUMENT or item.get_content() == "":
            continue

        # Extract the content and remove irrelevant metadata
        soup = BeautifulSoup(item.get_content(), "html.parser")
        content = soup.get_text().strip()

        # Append the content to the book text
        book_text += content + "\n"

    print(f"Extracted {len(book_text)} characters from {ebook_path}")

    return book_text


def summarize_text(
    text: str,
    model_name: str = "pszemraj/led-base-book-summary",
    token_batch_length: int = 4096,
) -> str:
    summarizer = Summarizer(
        model_name_or_path=model_name,
        token_batch_length=token_batch_length,
    )
    summary = summarizer.summarize_string(text)
    print(f"Summarized text to {len(summary)} characters")
    return summary


def save_summarized_text(filename: str, summarized_text: str) -> None:
    base_dir = "summaries"
    os.makedirs(base_dir, exist_ok=True)
    output_file = os.path.join(base_dir, f"{os.path.splitext(filename)[0]}.txt")

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(summarized_text)
    print(f"Summarized text saved to: {output_file}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python ebook_to_text.py <ebook_path>")
        return

    ebook_path = sys.argv[1]
    text: str = extract_text_from_ebook(ebook_path)

    summarized_text = summarize_text(text)

    filename = os.path.basename(ebook_path)
    save_summarized_text(filename, summarized_text)


if __name__ == "__main__":
    main()
