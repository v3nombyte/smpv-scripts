from myjdapi import Myjdapi
import os

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
for link in links:
    name = link.get("name")
    size = link.get("bytesTotal")  # can be None
    uuid = link.get("uuid")

    if not name or not uuid:
        continue

    norm_name = normalize(name)

    # --- 1) Name-only duplicates (all files) ---
    if norm_name in seen_name_only:
        if uuid not in duplicates:
            duplicates.append(uuid)
    else:
        seen_name_only[norm_name] = uuid

    # Only proceed with video-specific checks if this is a video
    if is_video(name):

        # --- 2) Name+size duplicates (videos only, if size known) ---
        if size is not None:
            key_name_size = (norm_name, size)
            if key_name_size in seen_name_size:
                if uuid not in duplicates:
                    duplicates.append(uuid)
            else:
                seen_name_size[key_name_size] = uuid

            # --- 3) Size-only duplicates (videos only) ---
            if size in seen_video_size:
                if uuid not in duplicates:
                    duplicates.append(uuid)
            else:
                seen_video_size[size] = uuid

print(f"Found {len(duplicates)} duplicates")

# ======================================================
# DELETE DUPLICATES
# ======================================================
if duplicates:
    device.linkgrabber.remove_links(duplicates)
    print("Duplicates removed.")
else:
    print("No duplicates found.")