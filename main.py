import os
import sys
import subprocess
from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub
from mutagen.mp4 import MP4Cover
from textsum.summarize import Summarizer
from pydub import AudioSegment
from mutagen.mp4 import MP4, MP4Cover

# name of the model to use for summarization
SUMMARY_MODEL_NAME = "pszemraj/long-t5-tglobal-base-16384-booksci-summary-v1"

# token batch length to use for summarization
SUMMARY_TOKEN_BATCH_LENGTH = 3072


def extract_text_from_ebook(ebook_path: str, output_file: str) -> dict:
    book = epub.read_epub(ebook_path)

    metadata = {}

    title = book.get_metadata("DC", "title")
    if title and len(title) > 0 and len(title[0]) > 0:
        metadata["title"] = title[0][0]

    author = book.get_metadata("DC", "creator")
    if author and len(author) > 0 and len(author[0]) > 0:
        metadata["author"] = author[0][0]

    cover = book.get_metadata("OPF", "cover")
    if cover and len(cover) > 0 and len(cover[0]) > 1:
        cover_id = cover[0][1]["content"]
        cover_item = book.get_item_with_id(cover_id)
        assert cover_item
        cover_image = cover_item.get_content()
        metadata["cover_image"] = cover_image

    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as file:
            return metadata

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

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(book_text)

    print(f"Extracted {len(book_text)} characters from {ebook_path}")

    return metadata


def summarize_text(input_file: str, output_file: str) -> str:
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as file:
            return file.read()

    with open(input_file, "r", encoding="utf-8") as file:
        text = file.read()
        summarizer = Summarizer(
            model_name_or_path=SUMMARY_MODEL_NAME,
            token_batch_length=SUMMARY_TOKEN_BATCH_LENGTH,
        )
        summary = summarizer.summarize_string(text)

        with open(output_file, "w", encoding="utf-8") as file:
            file.write(summary)

        print(f"Summarized text saved to: {output_file}")
        return summary


def get_docker_container_id(image_name: str) -> str:
    command = "docker ps --filter ancestor=" + image_name + " --format '{{.ID}}'"
    output = subprocess.check_output(command, shell=True, universal_newlines=True)
    container_id = output.strip()
    return container_id


def docker_copy(source_path: str, destination_path: str) -> None:
    subprocess.run(["docker", "cp", source_path, destination_path])


def docker_exec(container_id: str, command: str) -> None:
    subprocess.run(["docker", "exec", "-it", container_id, "/bin/bash", "-c", command])


def generate_speech(input_file: str, filename: str, container_id: str):
    destination_filename = f"{filename}.txt"
    output_filename = f"{filename}.wav"

    if os.path.exists(f"./wavs/{output_filename}"):
        return

    piper_command = f"cd /dist/piper && cat {destination_filename} | ./piper --model en_GB-alba-medium.onnx --output_file {output_filename}"

    # Command 1: docker cp
    docker_copy(
        input_file,
        f"{container_id}:/dist/piper/{destination_filename}",
    )

    # Command 2: docker exec
    docker_exec(container_id, piper_command)

    # Command 3: docker cp
    docker_copy(
        f"{container_id}:/dist/piper/{output_filename}",
        f"./wavs/{output_filename}",
    )


def get_filename_from_path(path: str) -> str:
    # Extract the base filename from the path
    filename = os.path.basename(path)
    # Remove the file extension
    filename_without_extension = os.path.splitext(filename)[0]
    return filename_without_extension


def convert_wav_to_m4b(filename: str, metadata: dict) -> None:
    wav_file = f"./summaries/{filename}.wav"
    m4b_file = f"./audiobooks/{filename}.m4b"

    audio = AudioSegment.from_wav(wav_file)

    audio.export(m4b_file, format="ipod")

    tags = MP4(m4b_file)

    assert tags is not None

    tags["\xa9nam"] = metadata.get("title")
    tags["\xa9alb"] = metadata.get("title")
    tags["\xa9ART"] = metadata.get("author")

    cover_image = metadata.get("cover_image", None)
    if cover_image:
        tags["covr"] = [MP4Cover(cover_image)]

    tags.save(m4b_file)


def setup_piper(container_id: str) -> None:
    docker_copy(
        "./piper-voices/en_GB-alba-medium.onnx",
        f"{container_id}:/dist/piper/en_GB-alba-medium.onnx",
    )
    docker_copy(
        "./piper-voices/en_GB-alba-medium.onnx.json",
        f"{container_id}:/dist/piper/en_GB-alba-medium.onnx.json",
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python ebook_to_text.py <ebook_path> [--summarize]")
        return

    ebook_path = sys.argv[1]
    filename = get_filename_from_path(ebook_path)

    base_dir = "extracts"
    os.makedirs(base_dir, exist_ok=True)
    extract_file = os.path.join(base_dir, f"{filename}.txt")
    metadata = extract_text_from_ebook(ebook_path, extract_file)

    summarize = False
    if len(sys.argv) >= 3 and sys.argv[2] == "--summarize":
        summarize = True

    source_file = extract_file

    if summarize:
        base_dir = "summaries"
        os.makedirs(base_dir, exist_ok=True)
        summary_file = os.path.join(base_dir, f"{filename}.txt")
        summarize_text(extract_file, summary_file)
        source_file = summary_file

    container_id = get_docker_container_id("piper")
    setup_piper(container_id)

    os.makedirs("wavs", exist_ok=True)
    generate_speech(source_file, filename, container_id)

    os.makedirs("audiobooks", exist_ok=True)
    convert_wav_to_m4b(filename, metadata)


if __name__ == "__main__":
    main()
