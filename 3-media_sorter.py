#!/usr/bin/env python3

import os
import shutil
import hashlib
import sys
import questionary
import subprocess
import tempfile
from PIL import Image
import imagehash
from tkinter import filedialog
import tkinter as tk

# ======================================================
# CONFIG
# ======================================================

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

BASE_PATH = os.path.expanduser("~/Downloads")

IMAGE_HASH_THRESHOLD = 5   # similarity threshold


# ======================================================
# HELPERS
# ======================================================

def is_video(file):
    return os.path.splitext(file)[1].lower() in VIDEO_EXTENSIONS

def is_image(file):
    return os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS


def file_hash(filepath, chunk_size=8192):
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None


def perceptual_image_hash(path):
    try:
        img = Image.open(path).convert("RGB")
        return imagehash.phash(img)
    except:
        return None


def perceptual_video_hash(path):
    try:
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_img:
            temp_img_path = temp_img.name

        subprocess.run([
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-ss', '00:00:01', '-i', path,
            '-frames:v', '1', temp_img_path
        ], check=True)

        img = Image.open(temp_img_path)
        hash_val = imagehash.phash(img)
        img.close()
        os.remove(temp_img_path)

        return hash_val
    except:
        return None


def unique_path(path):
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{base}_{counter}{ext}"
        counter += 1
    return path


# ======================================================
# CORE PROCESS
# ======================================================

def process_folders(chosen_folder, remove_duplicates=True):

    if not os.path.exists(chosen_folder):
        print(f"Error: Folder '{chosen_folder}' does not exist!")
        return False
    
    if not os.path.isdir(chosen_folder):
        print(f"Error: '{chosen_folder}' is not a directory!")
        return False
    
    clips_path = os.path.join(chosen_folder, 'clips')
    pics_path = os.path.join(chosen_folder, 'pics')
    
    for subfolder_path in [clips_path, pics_path]:
        os.makedirs(subfolder_path, exist_ok=True)

    seen_hashes = set() if remove_duplicates else None
    image_hashes = {} if remove_duplicates else None  # NEW

    total_videos = 0
    total_images = 0
    total_duplicates = 0
    moved_videos = []

    for root, dirs, files in os.walk(chosen_folder, topdown=True):

        if root == clips_path or root == pics_path:
            continue
        if clips_path in root or pics_path in root:
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            
            if is_video(file):
                dest = os.path.join(clips_path, file)
                file_type = 'video'
            elif is_image(file):
                dest = os.path.join(pics_path, file)
                file_type = 'image'
            else:
                continue
            
            # ------------------------
            # DUPLICATE DETECTION
            # ------------------------
            if remove_duplicates:

                # SHA256 (existing logic)
                h = file_hash(file_path)
                if h is None:
                    continue

                if h in seen_hashes:
                    total_duplicates += 1
                    try:
                        os.remove(file_path)
                        print(f"[SHA DUPLICATE] Removed: {file}")
                        continue
                    except Exception as e:
                        print(f"Error deleting duplicate {file_path}: {e}")
                        continue
                else:
                    seen_hashes.add(h)

                # NEW: perceptual image duplicate detection
                if file_type == "image":
                    try:
                        img = Image.open(file_path).convert("RGB")
                        phash = imagehash.phash(img)

                        for existing_hash, existing_path in image_hashes.items():
                            if phash - existing_hash <= 5:
                                total_duplicates += 1
                                os.remove(file_path)
                                print(f"[IMG DUPLICATE] Removed: {file}")
                                break
                        else:
                            image_hashes[phash] = file_path

                        # If deleted, skip move
                        if not os.path.exists(file_path):
                            continue

                    except Exception as e:
                        print(f"Image hash error {file}: {e}")

            # ------------------------
            # MOVE FILE (UNCHANGED)
            # ------------------------
            dest = unique_path(dest)

            try:
                shutil.move(file_path, dest)

                if file_type == 'video':
                    total_videos += 1
                    moved_videos.append((file_path, dest))
                else:
                    total_images += 1

                print(f"Moved {file_type}: {file}")

            except Exception as e:
                print(f"Error moving {file_path} to {dest}: {e}")

    # --- KEEP YOUR ORIGINAL POST-PROCESSING (unchanged) ---
    for original_path, new_path in moved_videos:
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        original_dir = os.path.dirname(original_path)
        dest_base_name = os.path.splitext(os.path.basename(new_path))[0]
        dest_dir = os.path.dirname(new_path)
        
        nfo_path = os.path.join(original_dir, f"{base_name}.nfo")
        if os.path.exists(nfo_path):
            dest_nfo = os.path.join(dest_dir, f"{dest_base_name}.nfo")
            try:
                shutil.move(nfo_path, dest_nfo)
            except:
                pass
        
        poster_path = os.path.join(original_dir, f"{base_name}-poster.jpg")
        if os.path.exists(poster_path):
            dest_poster = os.path.join(dest_dir, f"{dest_base_name}-poster.jpg")
            try:
                shutil.move(poster_path, dest_poster)
            except:
                pass

    # cleanup
    for root, dirs, files in os.walk(chosen_folder, topdown=False):
        if root == clips_path or root == pics_path:
            continue
        if clips_path in root or pics_path in root:
            continue
        if root == chosen_folder:
            continue
            
        if not os.listdir(root):
            try:
                os.rmdir(root)
            except:
                pass

    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"  Videos moved: {total_videos}")
    print(f"  Images moved: {total_images}")
    if remove_duplicates:
        print(f"  Duplicates removed: {total_duplicates}")
    print("="*50)

    return True


# ======================================================
# INTERACTIVE MODE
# ======================================================

def select_folder():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title="Select Folder to Scan for Duplicates")

def interactive_mode():

    print("\nMEDIA SORTER v2\n")

    chosen_folder = select_folder()

    if not chosen_folder:
        return

    remove_duplicates = questionary.confirm(
        "Remove duplicates?",
        default=True
    ).ask()

    process_folders(chosen_folder, remove_duplicates)


# ======================================================
# MAIN
# ======================================================

def main():
    interactive_mode()


if __name__ == "__main__":
    main()
