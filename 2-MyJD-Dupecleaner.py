from myjdapi import Myjdapi
import os
from collections import defaultdict

# ======================================================
# CONFIG
# ======================================================
JD_EMAIL = "your-myjdownloader-email@example.com"
JD_PASSWORD = "your-myjdownloader-password"

if JD_EMAIL == "your-myjdownloader-email@example.com" or JD_PASSWORD == "your-myjdownloader-password":
    print("Please set your MyJDownloader email and password in the script.")
    exit(1)


VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv",
    ".flv", ".webm", ".mpeg", ".mpg", ".m4v"
}

# ======================================================
# CONNECT
# ======================================================
jd = Myjdapi()
jd.set_app_key("duplicate_cleaner")
jd.connect(JD_EMAIL, JD_PASSWORD)
device = jd.get_device(jd.list_devices()[0]['name'])

# ======================================================
# FETCH LINKS
# ======================================================
links = device.linkgrabber.query_links([
    {"name": True, "bytesTotal": True, "uuid": True}
])

# ======================================================
# HELPERS
# ======================================================
def normalize(name):
    return name.strip().lower()

def get_extension(name):
    return os.path.splitext(name.split("?")[0])[1].lower()

def is_video(name):
    return get_extension(name) in VIDEO_EXTENSIONS

# ======================================================
# TRACKERS
# ======================================================
seen_name_only = {}
seen_name_size = {}
seen_video_size = {}

duplicates = []

# ======================================================
# PROCESS LINKS
# ======================================================
def find_duplicates(links):
    """
    Detect duplicate entries in a list of MyJDownloader links.

    Rules:
      - For all files (images, videos, etc.):
          - Same normalized name AND same size -> duplicate.
      - For videos only:
          - Same size (regardless of name) -> duplicate (high chance).

    Links with missing name, UUID, or size are ignored for duplicate detection.

    Args:
        links (list of dict): Each dict contains at least:
            - "name" (str): original file name.
            - "bytesTotal" (int, optional): file size in bytes.
            - "uuid" (str): unique identifier.

    Returns:
        list: UUIDs of all links that are considered duplicates.
    """
    from collections import defaultdict

    # Helper functions (assumed to be defined elsewhere)
    # def normalize(name: str) -> str: ...
    # def is_video(name: str) -> bool: ...

    # Groups for different duplicate criteria
    image_groups = defaultdict(list)        # key: (norm_name, size)
    video_name_size_groups = defaultdict(list)  # key: (norm_name, size)
    video_size_groups = defaultdict(list)        # key: size

    # First pass: collect links into groups
    for link in links:
        name = link.get("name")
        size = link.get("bytesTotal")
        uuid = link.get("uuid")

        if not name or not uuid or size is None:
            # Missing required data -> cannot reliably compare
            continue

        norm_name = normalize(name)

        if is_video(name):
            # Videos are added to both grouping strategies
            key = (norm_name, size)
            video_name_size_groups[key].append(uuid)
            video_size_groups[size].append(uuid)
        else:
            # Non-video files (images, etc.) are only grouped by name+size
            key = (norm_name, size)
            image_groups[key].append(uuid)

    # Second pass: collect duplicates from all groups
    duplicates = set()

    for uuids in image_groups.values():
        if len(uuids) > 1:
            duplicates.update(uuids)

    for uuids in video_name_size_groups.values():
        if len(uuids) > 1:
            duplicates.update(uuids)

    for uuids in video_size_groups.values():
        if len(uuids) > 1:
            duplicates.update(uuids)

    return list(duplicates)

duplicates = find_duplicates(links)

print(f"Found {len(duplicates)} duplicates")

# ======================================================
# DELETE DUPLICATES
# ======================================================
if duplicates:
    device.linkgrabber.remove_links(duplicates)
    print("Duplicates removed.")
else:
    print("No duplicates found.")
