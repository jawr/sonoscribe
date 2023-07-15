## Sonoscribe

Turn an ebook into a summarized audiobook.

Stiches together some awesome technologies:

- [pszemraj/document-summarization](https://huggingface.co/spaces/pszemraj/document-summarization) Text summarization
- [rhasspy/piper](https://github.com/rhasspy/piper) Text To Speech

### Setup

First install dependencies:

```
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-fdk-aac
```

Next setup the python environment:

```
pipenv
pipenv install
```

Next setup piper. If you can compile/use already compiled do so, on Apple Silicon I had to use a Docker solution:

```
git clone https://github.com/rhasspy/piper.git
cd piper
docker buildx build --target build -t piper:latest .
```

Run the container in another tab so it runs indefinitely:

```
docker run -it --entrypoint bash piper:latest
```

Download the voices you want to use (currently hardcoded to `en_GB-alba-medium`):

```
mkdir piper-voices
curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx
curl -OL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json
```

### Running

Add an epub into epubs with the following format:

```
author-title.epub
william_shakespeare-king_lear.epub
```

And finally run:

```
pipenv run python main.py ebooks/william_shakespeare-king_lear.epub
```

Summarized text and tagged mp3 will be output to:

```
summaries/william_shakespeare-king_lear.txt
summaries/william_shakespeare-king_lear.mp3
```
