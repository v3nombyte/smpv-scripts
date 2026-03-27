
# Media Scraping & Organization Pipeline

This project provides a **complete workflow for scraping media URLs from forum pages, downloading them via MyJDownloader, and organizing + deduplicating the resulting files**.

It is designed to be modular, with each script handling a specific stage of the pipeline.

---
## 📚 Table of Contents

- [Overview of Workflow](#-overview-of-workflow)
- [Project Structure](#-project-structure)
- [Step-by-Step Usage](#️-step-by-step-usage)
  - [1. Collect HTML Pages](#1-collect-html-pages)
  - [2. Extract URLs](#2-extract-urls)
  - [3. Add URLs to MyJDownloader](#3-add-urls-to-myjdownloader)
  - [4. Remove Duplicate Links (Pre-download)](#4-remove-duplicate-links-pre-download)
  - [5. Download Media](#5-download-media)
  - [6. Organize Media](#6-organize-media)
- [Key Design Concepts](#-key-design-concepts)
  - [Deduplication Strategy](#deduplication-strategy)
  - [URL Extraction Coverage](#url-extraction-coverage)
  - [Safety Features](#safety-features)
- [Important Notes](#️-important-notes)
- [Configuration Files](#-configuration-files)
  - [url_patternsjson](#url_patternsjson)
  - [skip_urljson](#skip_urljson)
- [Troubleshooting](#-troubleshooting)
- [Summary](#-summary)

---

## 🔁 Overview of Workflow

1. Collect HTML pages from supported forums
2. Extract media URLs
3. Queue downloads in MyJDownloader
4. Remove duplicate links before downloading
5. Download media
6. Organize media into structured folders and remove duplicate files by hash

---

## 📂 Project Structure

```

project/
│
├── input/                      # Place HTML files here
├── output/                     # Extracted URL lists
│
├── 1-main.py                  # URL extractor
├── 2-MyJD-Dupecleaner.py      # MyJDownloader duplicate cleaner
├── 3-media_sorter.py          # Media organizer + deduplicator
│
├── url_patterns.json          # URL filtering rules
├── skip_url.json              # URLs to ignore
│
└── README.md

````

---

## ⚙️ Step-by-Step Usage

### 1. Collect HTML

- Go to one of the supported forums:
  - celebforum
  - socialmediagirls
  - simpcity
- Save **ALL pages** of a model/thread as:
  - Format: `HTML only` <-- IMPORTANT
  - Location: `/input`

---

### 2. Extract URLs

Run:

```bash
python 1-main.py
````

#### What it does:

* Scans `/input` for `.html` files
* Detects forum source automatically
* Extracts URLs from:

  * `<a>`, `<img>`, `<video>`, `<source>`, `<iframe>`, etc.
  * `srcset` attributes
  * inline CSS (e.g. background images)
* Applies filters using:

  * `url_patterns.json`
  * `skip_url.json`
* Outputs:

  * A **single merged `.txt` file** in `/output`
* Optionally:

  * Append to existing URL list (no duplicates)
* Moves processed HTML files into an archive folder

#### Extraction Modes:

* **Normal** → applies patterns + skip list
* **No Filter** → extracts everything
* **Reverse Filter** → excludes matching patterns *(Good for discovering URLs that have content, but are not included in the `url_patterns.json`)

---

### 3. Add URLs to MyJDownloader

* Copy the generated `.txt` file contents
* Paste into **MyJDownloader LinkGrabber**
* ⚠️ Do NOT start downloads yet

---

### 4. Remove Duplicate Links (Pre-download)

Run:

```bash
python 2-MyJD-Dupecleaner.py
```

#### Setup required:

Edit the script:

```python
JD_EMAIL = "your-email"
JD_PASSWORD = "your-password"
```

#### What it does:

* Connects to MyJDownloader API
* Scans LinkGrabber queue
* Detects duplicates using:

  * Same filename
  * Same filename + same size (videos)
  * Same size (videos)
* Removes duplicates automatically

---

### 5. Download Media

* Start downloads in MyJDownloader
* Wait until all downloads complete

---

*A additional script will be added soon, to extract the pages # and post # for failed URLs*

---

### 6. Organize Media

Run:

```bash
python 3-media_sorter.py
```

#### What it does:

* Interactive folder selection (starting from `~/Downloads`)
* Creates:

  * `/clips` → videos
  * `/pics` → images
* Moves files from nested folders into these directories
* Supports:

  * `.mp4`, `.mkv`, `.avi`, etc.
  * `.jpg`, `.png`, `.webp`, etc.

#### Additional features:

* Removes duplicates using **SHA256 hash**
* Renames files if conflicts occur
* Moves associated files:

  * `.nfo`
  * `-poster.jpg`
* Deletes empty folders after processing

---

## 🧠 Key Design Concepts

### Deduplication Strategy

| Stage         | Method                 |
| ------------- | ---------------------- |
| Link stage    | Name + size heuristics |
| Sorting stage | SHA256 hash            |

---

### URL Extraction Coverage

The extractor is robust and captures:

* Standard HTML attributes (`src`, `href`)
* Lazy-loaded assets (`srcset`)
* Inline styles (`background-image`)
* Relative → absolute URL resolution

---

### Safety Features

* No duplicate URLs written to output
* Append mode prevents reprocessing
* File hash ensures true duplicate detection
* Interactive confirmations for destructive steps

---

## ⚠️ Important Notes

* Ensure **all pages** of a thread are saved before extraction
* MyJDownloader must be running and connected to MyJD
* Large datasets may take time due to hashing
* Update `BASE_PATH` in `3-media_sorter.py` if needed:

```python
BASE_PATH = os.path.expanduser("~/Downloads")
```

---

## 🧩 Configuration Files

### `url_patterns.json`

* Regex patterns for URLs to include

### `skip_url.json`

* Substrings to exclude unwanted URLs

---

## 🛠 Troubleshooting

### No HTML files found

→ Ensure `/input` contains `.html` files

### MyJDownloader connection fails

→ Verify:

* Credentials
* App is running
* Device is available
* Device (App) is connected to MyJD via Settings

### No files moved

→ Check:

* Correct folder selected
* Files are supported types

---

## ✅ Summary

This pipeline provides:

* Automated scraping
* Intelligent deduplication
* Clean media organization
* Minimal manual effort after setup

---

# 📦 requirements.txt

```txt
beautifulsoup4
lxml
questionary
myjdapi
````

---

## Optional (implicit / standard library used)

These are built-in and **do not need installation**:

* `os`
* `sys`
* `json`
* `re`
* `hashlib`
* `shutil`
* `urllib`
