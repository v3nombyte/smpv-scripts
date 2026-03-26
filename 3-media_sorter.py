#!/usr/bin/env python3
"""
Media Sorter - Standalone Script
Organizes images and videos from nested folders into 'pics' and 'clips' folders.
Removes duplicates based on file hash and cleans up empty directories.
"""

import os
import shutil
import hashlib
import sys
import questionary

# ======================================================
# FILE EXTENSIONS
# ======================================================
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}

BASE_PATH = os.path.expanduser("~/Downloads")  # Change this to your desired base path

# ======================================================
# HELPERS
# ======================================================
def is_video(file):
    return os.path.splitext(file)[1].lower() in VIDEO_EXTENSIONS

def is_image(file):
    return os.path.splitext(file)[1].lower() in IMAGE_EXTENSIONS

def file_hash(filepath, chunk_size=8192):
    """Compute SHA256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error hashing file {filepath}: {e}")
        return None

def unique_path(path):
    """If path exists, append a number before the extension."""
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{base}_{counter}{ext}"
        counter += 1
    return path

def process_folders(chosen_folder, remove_duplicates=True):
    """
    Move video and image files from the chosen folder (including subfolders) into:
    - chosen_folder/clips for videos
    - chosen_folder/pics for images
    Cleans up empty directories and optionally removes duplicates.
    """
    if not os.path.exists(chosen_folder):
        print(f"Error: Folder '{chosen_folder}' does not exist!")
        return False
    
    if not os.path.isdir(chosen_folder):
        print(f"Error: '{chosen_folder}' is not a directory!")
        return False
    
    clips_path = os.path.join(chosen_folder, 'clips')
    pics_path = os.path.join(chosen_folder, 'pics')
    
    for subfolder_path in [clips_path, pics_path]:
        try:
            os.makedirs(subfolder_path, exist_ok=True)
            print(f"Created folder: {subfolder_path}")
        except Exception as e:
            print(f"Error creating subfolder {subfolder_path}: {e}")
            return False

    seen_hashes = set() if remove_duplicates else None
    total_videos = 0
    total_images = 0
    total_duplicates = 0
    moved_videos = []

    for root, dirs, files in os.walk(chosen_folder, topdown=True):
        # Skip the clips and pics folders themselves
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
                # Skip non-media files
                continue
            
            if remove_duplicates:
                h = file_hash(file_path)
                if h is None:
                    continue  # Skip files that could not be hashed
                if h in seen_hashes:
                    total_duplicates += 1
                    try:
                        os.remove(file_path)
                        print(f"Removed duplicate: {file}")
                        continue
                    except Exception as e:
                        print(f"Error deleting duplicate {file_path}: {e}")
                        continue
                else:
                    seen_hashes.add(h)
            
            # Move the file
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
    
    for original_path, new_path in moved_videos:
        # Get the base name of the video file
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        original_dir = os.path.dirname(original_path)
        dest_base_name = os.path.splitext(os.path.basename(new_path))[0]
        dest_dir = os.path.dirname(new_path)
        
        # Move .nfo file if exists
        nfo_path = os.path.join(original_dir, f"{base_name}.nfo")
        if os.path.exists(nfo_path):
            dest_nfo = os.path.join(dest_dir, f"{dest_base_name}.nfo")
            try:
                shutil.move(nfo_path, dest_nfo)
                print(f"Moved associated .nfo file: {base_name}.nfo")
            except Exception as e:
                print(f"Error moving .nfo file {nfo_path}: {e}")
        
        # Move -poster.jpg file if exists
        poster_path = os.path.join(original_dir, f"{base_name}-poster.jpg")
        if os.path.exists(poster_path):
            dest_poster = os.path.join(dest_dir, f"{dest_base_name}-poster.jpg")
            try:
                shutil.move(poster_path, dest_poster)
                print(f"Moved associated poster image: {base_name}-poster.jpg")
            except Exception as e:
                print(f"Error moving poster file {poster_path}: {e}")
    
    for root, dirs, files in os.walk(chosen_folder, topdown=False):
        # Skip clips and pics folders
        if root == clips_path or root == pics_path:
            continue
        if clips_path in root or pics_path in root:
            continue
        if root == chosen_folder:
            continue  # Don't delete the chosen folder itself
            
        if not os.listdir(root):
            try:
                os.rmdir(root)
                print(f"Removed empty directory: {root}")
            except Exception as e:
                print(f"Error removing empty directory {root}: {e}")

    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"  Videos moved: {total_videos}")
    print(f"  Images moved: {total_images}")
    if remove_duplicates:
        print(f"  Duplicates removed: {total_duplicates}")
    else:
        print(f"  Duplicates: Not checked")
    print(f"  Destination: {chosen_folder}")
    print("="*50)
    return True

def move_media_and_cleanup(current_folder, dest_path, seen_hashes):
    pass

def browse_folders(current_path):
    """
    Recursive folder browser that lets users navigate folders.
    Returns the selected folder path or None if cancelled.
    """
    while True:
        try:
            # Get list of subfolders in current path
            items = [f for f in os.listdir(current_path) if os.path.isdir(os.path.join(current_path, f))]
            items.sort()
            
            # Create choices list
            choices = []
            
            # Add option to select current folder
            choices.append(questionary.Choice(
                title=f"📁 [Select this folder: {os.path.basename(current_path) or current_path}]",
                value="__SELECT__"
            ))
            
            # Add parent directory option if not at base path
            if current_path != BASE_PATH:
                choices.append(questionary.Choice(
                    title="⬆️  [Go back to parent folder]",
                    value="__BACK__"
                ))
            
            # Add separator
            if items:
                choices.append(questionary.Separator("--- Subfolders ---"))
                
                # Add all subfolders
                for item in items:
                    choices.append(questionary.Choice(
                        title=f"📂 {item}",
                        value=item
                    ))
            else:
                choices.append(questionary.Separator("(No subfolders found)"))
            
            # Ask user to select
            selection = questionary.select(
                f"Current: {current_path}\nChoose an action:",
                choices=choices
            ).ask()
            
            if not selection:
                return None  # User cancelled
            
            if selection == "__SELECT__":
                return current_path
            elif selection == "__BACK__":
                current_path = os.path.dirname(current_path)
            else:
                # Navigate into selected subfolder
                current_path = os.path.join(current_path, selection)
                
        except Exception as e:
            print(f"Error browsing folders: {e}")
            return None

def interactive_mode():
    """Run the script in interactive mode with questionary."""
    print("="*50)
    print("MEDIA SORTER - Interactive Mode")
    print("="*50)
    print("\nThis script will:")
    print("  1. Let you choose a folder from the base path")
    print("  2. Create 'clips' and 'pics' folders inside")
    print("  3. Move videos to 'clips' folder")
    print("  4. Move images to 'pics' folder")
    print("  5. Optionally remove duplicate files (by hash)")
    print("  6. Clean up empty folders")
    print()
    
    # Check if base path exists
    if not os.path.exists(BASE_PATH):
        print(f"Error: Base path '{BASE_PATH}' does not exist!")
        print("Please update the BASE_PATH variable in the script.")
        return
    
    print(f"Starting at base path: {BASE_PATH}\n")
    chosen_folder = browse_folders(BASE_PATH)
    
    if not chosen_folder:
        print("Operation cancelled.")
        return
    
    print(f"\n✓ Selected folder: {chosen_folder}\n")
    
    # Ask if duplicates should be removed
    remove_duplicates = questionary.confirm(
        "Remove duplicate files?",
        default=True
    ).ask()
    
    print(f"\nProcessing folder: {chosen_folder}")
    print(f"Remove duplicates: {'Yes' if remove_duplicates else 'No'}\n")
    
    # Confirm before proceeding
    confirm = questionary.confirm(
        "Continue with the operation?",
        default=True
    ).ask()
    
    if not confirm:
        print("Operation cancelled.")
        return
    
    # Process the folder
    success = process_folders(chosen_folder, remove_duplicates)
    if success:
        print("\n✓ Operation completed successfully!")
    else:
        print("\n✗ Operation failed!")

def main():
    """Main entry point with both CLI and interactive mode support."""
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Media Sorter - Interactive Mode")
        print("="*50)
        print("This script helps you organize media files.")
        print("\nUsage:")
        print("  python media_sorter.py")
        print("\nConfiguration:")
        print(f"  Base path: {BASE_PATH}")
        print("  (Update BASE_PATH variable in the script)")
        return
    
    interactive_mode()

if __name__ == '__main__':
    main()
