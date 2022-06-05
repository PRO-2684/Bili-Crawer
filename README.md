# Bili-Crawer
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🪄 Functions
* Comments crawling
* Danmakus crawling
* Video downloading

Your stars are highly welcomed.

## 📥 Installation
1. `pip install -r requirements.txt`.
2. Download `dm_pb2.py` and `bili-crawer.py`.

## 📖 Usage
```text
bili-crawer.py [-h] [-o OUTPUT] [-v] [-c] [-d] [-O] [-p PAGELIST] [-l] target
positional arguments:
  target                🎯 A string with target BV id in it, for example "prefixbV1GJ411x7h7suffix".

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        📂 Output directory.
  -v, --video           🎥 If included, download video(s).
  -c, --comment         💬 If included, download comments.
  -d, --danmaku         ☁️ If included, download danmakus.
  -O, --overwrite       ⛔ If included, force overwrite files/folders.
  -p PAGELIST, --pagelist PAGELIST
                        👉 Specify which parts in the pagelist you'd like to download.
  -l, --playlist        📃 If included, download the whole playlist.
```

## 🪧 Example

