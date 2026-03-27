from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json
import questionary
import os
import sys

# ======================================================
# CONFIG
# ======================================================

INPUT_DIR = 'input'
OUTPUT_DIR = 'output'

JSON_FILES = {
    'url_patterns': 'url_patterns.json',
    'skip_urls': 'skip_url.json'
}

# ======================================================
# HELPERS
# ======================================================

def bar():
    print("")
    print('=' * 50)
    print("")

def section(title):
    print("")
    print(f"  >> {title}")
    print("-" * 50)

def info(msg):
    print(f"  [INFO]  {msg}")

def warn(msg):
    print(f"  [WARN]  {msg}")

def error(msg):
    print(f"  [ERROR] {msg}")

def success(msg):
    print(f"  [OK]    {msg}")

def ensure_directories():
    """Ensure required directories exist, exit gracefully on failure."""
    for d in [INPUT_DIR, OUTPUT_DIR]:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError as e:
            error(f"Could not create directory '{d}': {e}")
            sys.exit(1)

def load_json(label, file_path):
    """Load a JSON file, exit with a clear message on failure."""
    if not os.path.exists(file_path):
        error(f"'{file_path}' not found. Please create it with the appropriate structure.")
        sys.exit(1)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        success(f"Loaded {label}: {len(data)} entries from '{file_path}'")
        return data
    except json.JSONDecodeError as e:
        error(f"Failed to parse '{file_path}': {e}")
        sys.exit(1)
    except OSError as e:
        error(f"Could not read '{file_path}': {e}")
        sys.exit(1)

def identify_forum_source(soup):
    """Identify the forum source from HTML metadata."""
    try:
        og = soup.find('meta', property='og:url')
        if og and og.get('content') and 'celebforum.to' in og['content']:
            return 'celebforum'
        title_tag = soup.find('title')
        if title_tag and 'Social Media Girls' in title_tag.text:
            return 'socialmediagirls'
        icon = soup.find('link', rel='icon')
        if icon and icon.get('href') and 'simpcity.rs' in icon['href']:
            return 'simpcity'
    except Exception as e:
        warn(f"Error identifying forum source: {e}")
    return None

def read_txt_file(file_path):
    """Read a text file and return a set of non-empty stripped lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = {line.strip() for line in f if line.strip()}
        return lines
    except FileNotFoundError:
        warn(f"Text file not found at '{file_path}'.")
        return set()
    except OSError as e:
        error(f"Could not read '{file_path}': {e}")
        return set()

def save_urls(urls, output_file):
    """Write a sorted list of URLs to a file, one per line."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in sorted(urls):
                f.write(url + '\n')
        success(f"Saved {len(urls)} URLs → '{output_file}'")
        return True
    except OSError as e:
        error(f"Could not save URLs to '{output_file}': {e}")
        return False

def append_urls_to_file(new_urls, existing_file):
    """
    Merge new_urls into an existing text file.
    Reads existing content, merges (no duplicates, no empty lines),
    and writes back a clean sorted file.
    Returns the number of newly added URLs.
    """
    existing_urls = read_txt_file(existing_file)
    before_count = len(existing_urls)
    merged = existing_urls | set(new_urls)
    after_count = len(merged)
    added = after_count - before_count
    try:
        with open(existing_file, 'w', encoding='utf-8') as f:
            for url in sorted(merged):
                f.write(url + '\n')
        success(f"Appended to '{existing_file}': {added} new URL(s) added "
                f"(was {before_count}, now {after_count}).")
        if added == 0:
            info("No new unique URLs were added — all extracted URLs already exist in the file.")
    except OSError as e:
        error(f"Could not write to '{existing_file}': {e}")
    return added

def extract_urls(soup, url_patterns, skip_urls, filter=False, reverse_filter=False, base_url=None):
    """
    Extract URLs from a BeautifulSoup object.
    Returns a set of URL strings.
    """
    urls = set()

    attrs = {
        "a": "href",
        "img": "src",
        "script": "src",
        "link": "href",
        "iframe": "src",
        "source": "src",
        "video": "src"
    }

    # Remove message-signature blocks entirely
    for sig in soup.select(".message-signature"):
        sig.decompose()

    # 1. Standard tag attributes
    for tag, attr in attrs.items():
        for element in soup.find_all(tag):
            url = element.get(attr)
            if url:
                urls.add(url.strip())

    # 2. srcset attributes
    for element in soup.find_all(srcset=True):
        for part in element["srcset"].split(","):
            url = part.strip().split(" ")[0].strip()
            if url:
                urls.add(url)

    # 3. Inline styles (background-image etc.)
    style_pattern = re.compile(r'url\(["\']?(.*?)["\']?\)')
    for element in soup.find_all(style=True):
        for match in style_pattern.findall(element["style"]):
            url = match.strip()
            if url:
                urls.add(url)

    # 4. Resolve relative URLs to absolute
    if base_url:
        urls = {urljoin(base_url, url) for url in urls}

    # 5. Keep only http/https URLs
    urls = {url for url in urls if url.startswith('http://') or url.startswith('https://')}

    # 6. Apply filters
    if filter:
        filtered = set()
        for url in urls:
            if any(skip in url for skip in skip_urls):
                continue
            if any(re.search(pattern, url) for pattern in url_patterns):
                filtered.add(url)
        return filtered

    if reverse_filter:
        return {url for url in urls if not any(re.search(p, url) for p in url_patterns)}

    return urls

def merge_text_files(input_dir, output_file, txt_files):
    """
    Merge multiple text files into one output file.
    Removes duplicates and empty lines. Deletes the individual files after merging.
    """
    merged = set()
    for filename in txt_files:
        file_path = os.path.join(input_dir, filename)
        file_urls = read_txt_file(file_path)
        merged.update(file_urls)
        # Remove individual temp file (only if it's not the final output)
        if os.path.abspath(file_path) != os.path.abspath(output_file):
            try:
                os.remove(file_path)
            except OSError as e:
                warn(f"Could not remove temp file '{file_path}': {e}")

    save_urls(merged, output_file)
    return merged

def move_htmlfiles_to_folder(input_dir, folder_name):
    """Move all .html files in input_dir to a subfolder named folder_name."""
    folder_path = os.path.join(input_dir, folder_name)
    try:
        os.makedirs(folder_path, exist_ok=True)
    except OSError as e:
        warn(f"Could not create folder '{folder_path}': {e}")
        return

    moved = 0
    for filename in os.listdir(input_dir):
        if filename.endswith('.html'):
            src = os.path.join(input_dir, filename)
            dst = os.path.join(folder_path, filename)
            try:
                if os.path.exists(dst):
                    warn(f"'{dst}' already exists — skipping move for '{filename}'.")
                else:
                    os.rename(src, dst)
                    moved += 1
            except OSError as e:
                warn(f"Could not move '{filename}': {e}")
    info(f"Moved {moved} HTML file(s) to '{folder_path}'.")

# ======================================================
# MAIN
# ======================================================

bar()
print("  Welcome to the Simp HTML URL Fetcher!")
bar()

# -- Setup directories
ensure_directories()

# -- Load JSON config files
section("Loading configuration")
url_patterns = load_json("URL patterns", JSON_FILES['url_patterns'])
skip_urls    = load_json("Skip URLs",    JSON_FILES['skip_urls'])
bar()

# -- Discover HTML files
section("Scanning input directory")
try:
    html_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.html')]
except OSError as e:
    error(f"Cannot read input directory '{INPUT_DIR}': {e}")
    sys.exit(1)

if not html_files:
    error(f"No HTML files found in '{INPUT_DIR}'. Please add some and try again.")
    sys.exit(1)

info(f"Found {len(html_files)} HTML file(s): {', '.join(html_files)}")
bar()

# -- Model name
model_name = questionary.text("Enter the model name for output file naming:").ask()
if not model_name or not model_name.strip():
    error("No model name entered. Exiting.")
    sys.exit(1)
model_name = model_name.strip()
bar()

# -- Identify forum source from first HTML file
section("Identifying forum source")
try:
    with open(os.path.join(INPUT_DIR, html_files[0]), 'r', encoding='utf-8') as f:
        soup_first = BeautifulSoup(f, 'lxml')
    forum_source = identify_forum_source(soup_first)
except OSError as e:
    error(f"Could not open '{html_files[0]}': {e}")
    sys.exit(1)

if forum_source:
    output_filename = f"{forum_source}_{model_name}_urls.txt"
    success(f"Forum source identified: '{forum_source}'")
else:
    output_filename = f"{model_name}_urls.txt"
    warn("Could not identify forum source — output will be named by model name only.")

info(f"Output file will be: '{output_filename}'")
bar()

# -- Check for existing output text file
merged_output_file = os.path.join(OUTPUT_DIR, output_filename)
# filename must match in lowercase compared to existing files to be considered the same (case-insensitive match)
existing_txt_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.txt') and f.lower() == output_filename.lower()]

append_to_existing = False
selected_existing_file = None

if existing_txt_files:
    section("Existing text file detected")
    info(f"Found {len(existing_txt_files)} existing text file(s) in '{OUTPUT_DIR}':")
    for tf in existing_txt_files:
        existing_count = len(read_txt_file(os.path.join(OUTPUT_DIR, tf)))
        info(f"  • {tf}  ({existing_count} URLs)")

    use_existing = questionary.confirm(
        "Do you want to append extracted URLs to an existing text file? (No duplicates will be added)"
    ).ask()

    if use_existing is None:
        error("No answer provided. Exiting.")
        sys.exit(1)

    if use_existing:
        choices = existing_txt_files + ["[ Create a new file instead ]"]
        selected = questionary.select(
            "Select the text file to append to:",
            choices=choices
        ).ask()

        if selected is None:
            error("No file selected. Exiting.")
            sys.exit(1)

        if selected != "[ Create a new file instead ]":
            selected_existing_file = os.path.join(OUTPUT_DIR, selected)
            append_to_existing = True
            info(f"Will append new URLs to: '{selected_existing_file}'")
        else:
            info("Will create a new output file.")
    bar()

# -- Extraction type
extraction_type = questionary.select(
    "Select the type of URL extraction:",
    choices=[
        "Normal (apply both URL patterns and skip list)",
        "No Filter (extract all URLs without applying patterns or skip list)",
        "Reverse Filter (extract URLs that do NOT match the patterns)"
    ]
).ask()
if extraction_type is None:
    error("No extraction type selected. Exiting.")
    sys.exit(1)
bar()

# -- Process each HTML file
section("Extracting URLs")
all_extracted_urls = set()
temp_txt_files     = []

for idx, filename in enumerate(html_files, start=1):
    input_file_path = os.path.join(INPUT_DIR, filename)
    info(f"[{idx}/{len(html_files)}] Processing '{filename}'...")

    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml')
    except OSError as e:
        error(f"  Could not open '{input_file_path}': {e} — skipping.")
        continue
    except Exception as e:
        error(f"  Failed to parse '{filename}': {e} — skipping.")
        continue

    try:
        if extraction_type == "Normal (apply both URL patterns and skip list)":
            extracted = extract_urls(soup, url_patterns, skip_urls, filter=True)
        elif extraction_type == "No Filter (extract all URLs without applying patterns or skip list)":
            extracted = extract_urls(soup, url_patterns, skip_urls, filter=False)
        else:
            extracted = extract_urls(soup, url_patterns, skip_urls, reverse_filter=True)
    except Exception as e:
        error(f"  Extraction failed for '{filename}': {e} — skipping.")
        continue

    new_in_file = extracted - all_extracted_urls
    all_extracted_urls.update(extracted)

    info(f"  Extracted : {len(extracted)} URLs")
    info(f"  New unique: {len(new_in_file)} URLs  |  Running total: {len(all_extracted_urls)}")

    # Save individual temp file
    temp_output = os.path.join(OUTPUT_DIR, filename.replace('.html', '.txt'))
    if save_urls(extracted, temp_output):
        temp_txt_files.append(filename.replace('.html', '.txt'))
    print()

bar()

# -- Merge or append
section("Finalising output")

if append_to_existing and selected_existing_file:
    # Append all extracted URLs to the selected existing file (no duplicates)
    info(f"Merging {len(all_extracted_urls)} extracted URL(s) into '{selected_existing_file}'...")

    # Also clean up the temp individual files
    for tf in temp_txt_files:
        temp_path = os.path.join(OUTPUT_DIR, tf)
        if os.path.abspath(temp_path) != os.path.abspath(selected_existing_file):
            try:
                os.remove(temp_path)
            except OSError as e:
                warn(f"Could not remove temp file '{temp_path}': {e}")

    append_urls_to_file(all_extracted_urls, selected_existing_file)

else:
    info(f"Merging all temp files into '{merged_output_file}'...")
    final_urls = merge_text_files(OUTPUT_DIR, merged_output_file, temp_txt_files)
    info(f"Final file contains {len(final_urls)} unique URL(s).")

# -- Move HTML files (not for Reverse Filter)
if extraction_type != "Reverse Filter (extract URLs that do NOT match the patterns)":
    section("Archiving HTML files")
    folder_name = f"{forum_source}_{model_name}" if forum_source else model_name
    move_htmlfiles_to_folder(INPUT_DIR, folder_name)

bar()
print(f"  All done!  Total unique URLs extracted this run: {len(all_extracted_urls)}")
bar()
