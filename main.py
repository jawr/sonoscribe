import os
import subprocess
import sys
from bs4 import BeautifulSoup
from ebooklib import ITEM_DOCUMENT, epub
from textsum.summarize import Summarizer
from pydub import AudioSegment

# name of the model to use for summarization
SUMMARY_MODEL_NAME = "pszemraj/long-t5-tglobal-base-16384-booksci-summary-v1"

# token batch length to use for summarization
SUMMARY_TOKEN_BATCH_LENGTH = 3072


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


def summarize_text(text: str, output_file: str) -> str:
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as file:
            return file.read()

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


def generate_speech(filename: str, container_id: str):
    # Parameters
    destination_filename = f"{filename}.txt"
    output_filename = f"{filename}.wav"

    if os.path.exists(f"./summaries/{output_filename}"):
        return

    piper_command = f"cd /dist/piper && cat {destination_filename} | ./piper --model en_GB-alba-medium.onnx --output_file {output_filename}"

    # Command 1: docker cp
    docker_copy(
        f"./summaries/{destination_filename}",
        f"{container_id}:/dist/piper/{destination_filename}",
    )

    # Command 2: docker exec
    docker_exec(container_id, piper_command)

    # Command 3: docker cp
    docker_copy(
        f"{container_id}:/dist/piper/{output_filename}",
        f"./summaries/{output_filename}",
    )


def get_filename_from_path(path: str) -> str:
    # Extract the base filename from the path
    filename = os.path.basename(path)
    # Remove the file extension
    filename_without_extension = os.path.splitext(filename)[0]
    return filename_without_extension


def convert_wav_to_mp3(filename: str) -> None:
    tags = {
        "title": filename.split("-")[1].replace("_", " ").strip().title(),
        "artist": filename.split("-")[0].replace("_", " ").strip().title(),
        "album": "Book Summary",
    }

    wav_file = f"./summaries/{filename}.wav"
    mp3_file = f"./summaries/{filename}.mp3"

    audio = AudioSegment.from_wav(wav_file)

    audio.export(mp3_file, format="mp3", tags=tags)


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
    if len(sys.argv) != 2:
        print("Usage: python ebook_to_text.py <ebook_path>")
        return

    ebook_path = sys.argv[1]
    text: str = extract_text_from_ebook(ebook_path)

    filename = get_filename_from_path(ebook_path)

    base_dir = "summaries"
    os.makedirs(base_dir, exist_ok=True)
    summary_file = os.path.join(base_dir, f"{filename}.txt")

    summarize_text(text, summary_file)

    container_id = get_docker_container_id("piper")
    setup_piper(container_id)

    generate_speech(filename, container_id)

    convert_wav_to_mp3(filename)


if __name__ == "__main__":
    main()
