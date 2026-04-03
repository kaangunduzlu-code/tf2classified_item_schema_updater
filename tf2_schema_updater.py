#!/usr/bin/env python3
"""
TF2 Classified Item Schema Updater
Searches for TF2 Classified installation and updates/installs item schema from GitHub Gist
"""

import os
import sys
import string
import requests
import time
import shutil
import re
from pathlib import Path
from typing import List, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse

# Version
__version__ = "1.0.3"

# GitHub Pages URLs for auto-updates
GITHUB_PAGES_BASE = "https://kaangunduzlu-code.github.io/tf2classified_item_schema_updater"
VERSION_CHECK_URL = f"{GITHUB_PAGES_BASE}/VERSION"
SCRIPT_UPDATE_URL = f"{GITHUB_PAGES_BASE}/tf2_schema_updater.py"

# FastDL URLs for checking required custom files
FASTDL_BASE = "https://kaangunduzlu-code.github.io/fastdl"
FASTDL_REPO = "kaangunduzlu-code/fastdl"
FASTDL_API_URL = f"https://api.github.com/repos/{FASTDL_REPO}/git/trees/main?recursive=1"
BASE_RAW_URL = f"https://raw.githubusercontent.com/{FASTDL_REPO}/main/"

# GitHub Gist URL for the item schema
GIST_URL = "https://gist.githubusercontent.com/kaangunduzlu-code/cad0897491d7d397d0ec279d235141c3/raw"

# Common TF2 Classified installation patterns to search for
TF2_PATTERNS = [
    "TF2 Classified",
    "TF2Classified",
    "tf2classified",
    "tf2 classified",
    "Team Fortress 2 Classified",
]

# Relative paths where schema should be installed
SCHEMA_PATHS = {
    1: "scripts/items",
    2: "custom/itemschema/scripts/items"
}


def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_progress_bar(current: int, total: int, prefix: str = '', length: int = 40):
    """Print a simple progress bar"""
    percent = 100 * (current / float(total))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent:.1f}%', end='', flush=True)
    if current == total:
        print()  # New line on completion


def check_for_updates() -> Optional[str]:
    """Check if a newer version is available on GitHub"""
    try:
        response = requests.get(VERSION_CHECK_URL, timeout=10)
        if response.status_code == 200:
            latest_version = response.text.strip()
            return latest_version
        return None
    except:
        return None


def download_with_progress(url: str, description: str = "Downloading", binary: bool = False):
    """Download content with progress indication"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        content = []
        
        if total_size > 0:
            downloaded = 0
            chunk_size = 8192
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    content.append(chunk)
                    downloaded += len(chunk)
                    print_progress_bar(downloaded, total_size, prefix=description)
        else:
            # No content-length header, just show spinner
            print(f"{description}...", end='', flush=True)
            content.append(response.content)
            print(" Done!")
        
        full_content = b''.join(content)
        
        # Return binary or text based on parameter
        if binary:
            return full_content
        else:
            return full_content.decode('utf-8')
            
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        return None


def update_script() -> bool:
    """Download and install the latest version of this script"""
    print("\nDownloading latest version from GitHub...")
    
    new_script_content = download_with_progress(SCRIPT_UPDATE_URL, "Downloading update")
    
    if not new_script_content:
        return False
    
    try:
        # Get current script path
        script_path = Path(__file__).resolve()
        backup_path = script_path.with_suffix('.py.backup')
        
        # Create backup
        print("Creating backup of current version...")
        shutil.copy2(script_path, backup_path)
        
        # Write new version
        print("Installing update...")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(new_script_content)
        
        print("\n✓ Update successful!")
        print("The script will now restart with the new version...\n")
        
        # Restart the script
        time.sleep(2)
        os.execv(sys.executable, [sys.executable, str(script_path)] + sys.argv[1:])
        
    except Exception as e:
        print(f"\n✗ Update failed: {e}")
        if backup_path.exists():
            print("Restoring from backup...")
            shutil.copy2(backup_path, script_path)
        return False
    
    return True


def show_update_prompt(latest_version: str) -> bool:
    """Show update notification and ask user"""
    print_header("Update Available")
    print(f"Current version: {__version__}")
    print(f"Latest version:  {latest_version}")
    print(f"\nA new version is available!")
    print("\nWhat would you like to do?")
    print("  1. Update now")
    print("  2. Skip this update")
    
    choice = get_user_choice("\nEnter your choice (1 or 2): ", ['1', '2'])
    return choice == '1'


def get_fastdl_downloads() -> List[Tuple[str, str]]:
    """Fetch list of required download files from fastdl repository
    Returns list of tuples: (relative_path, filename)
    """
    try:
        print("Fetching list of required custom files from fastdl repository...")
        response = requests.get(FASTDL_API_URL, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if 'tree' not in data:
            print("⚠ Could not parse repository structure")
            return []
        
        files = []
        
        # Filter files: only from allowed folders, not maps folder
        for item in data['tree']:
            if item['type'] == 'blob':  # It's a file, not a directory
                path = item['path']
                
                # Check if it's in an allowed folder (case insensitive)
                path_lower = path.lower()
                
                # CRITICAL FIX: Allow materials, models, sound, and downloads. Exclude maps and .git files.
                if ('map' not in path_lower) and not path_lower.startswith('.git'):
                    # Get just the filename
                    filename = os.path.basename(path)
                    files.append((path, filename))
                    print(f"  Found: {path}")
        
        print(f"\n✓ Found {len(files)} custom files")
        return files
        
    except Exception as e:
        print(f"⚠ Could not fetch custom files list: {e}")
        return []


def check_custom_files(tf2_dir: Path) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Check which custom files are present and which are missing
    Returns: (found_files, missing_files) where each is a list of (path, filename) tuples
    """
    required_files = get_fastdl_downloads()
    
    if not required_files:
        return [], []
    
    print(f"\nChecking for {len(required_files)} required custom files...")
    
    # Common locations for custom files in TF2 Classified
    search_paths = [
        tf2_dir / "download",
        tf2_dir / "downloads",
        tf2_dir / "materials",
        tf2_dir / "custom",
        tf2_dir,  # Root tf directory
    ]
    
    found_files = []
    missing_files = []
    
    for file_path, filename in required_files:
        file_found = False
        
        # Search in all common locations
        for search_path in search_paths:
            if search_path.exists():
                # Search recursively for this specific filename
                for found_file in search_path.rglob(filename):
                    if found_file.is_file():
                        found_files.append((file_path, filename))
                        file_found = True
                        break
            
            if file_found:
                break
        
        if not file_found:
            missing_files.append((file_path, filename))
    
    return found_files, missing_files


def download_custom_file(file_path: str, filename: str, tf2_dir: Path) -> bool:
    """Download a custom file from fastdl to the TF2 directory
    file_path: relative path in the repository (e.g., 'materials/models/player.vmt')
    filename: just the filename
    """
    try:
        # CRITICAL FIX: Use BASE_RAW_URL instead of FASTDL_BASE to get the actual file data
        file_url = f"{BASE_RAW_URL}{file_path}"
        
        print(f"\nDownloading {filename}...")
        print(f"  From: {file_path}")
        content = download_with_progress(file_url, f"  Progress", binary=True)
        
        if not content:
            return False
        
        # Preserve the directory structure from the repository
        # Extract the directory structure from file_path
        rel_path = Path(file_path)
        
        # Save to tf2 directory maintaining structure
        target_file = tf2_dir / rel_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write as binary
        with open(target_file, 'wb') as f:
            f.write(content)
        
        print(f"  ✓ Saved to: {target_file}")
        return True
        
    except Exception as e:
        print(f"  ✗ Failed to download {filename}: {e}")
        return False


def handle_custom_files_check(tf2_dir: Path):
    """Handle the custom files check and offer to download missing ones"""
    print_header("Checking Custom Item Files")
    
    found_files, missing_files = check_custom_files(tf2_dir)
    
    if not found_files and not missing_files:
        print("⚠ Could not check custom files (fastdl unavailable or no files listed)")
        return
    
    total_required = len(found_files) + len(missing_files)
    
    if not missing_files:
        print(f"✓ All {total_required} required custom files are installed!")
        print("\nYour installation is complete and ready to use.")
        return
    
    print(f"\nStatus:")
    print(f"  ✓ Found: {len(found_files)}/{total_required}")
    print(f"  ✗ Missing: {len(missing_files)}/{total_required}")
    
    if missing_files:
        print("\nMissing files:")
        for file_path, filename in missing_files[:10]:  # Show first 10
            print(f"  • {filename}")
            print(f"    Path: {file_path}")
        
        if len(missing_files) > 10:
            print(f"  ... and {len(missing_files) - 10} more")
        
        print("\n⚠ WARNING: The item schema requires these custom files to work properly!")
        print("Without them, you may experience crashes or missing content.")
        
        print("\nWhat would you like to do?")
        print("  1. Download missing files now")
        print("  2. Skip (not recommended)")
        
        choice = get_user_choice("\nEnter your choice (1 or 2): ", ['1', '2'])
        
        if choice == '1':
            print_header("Downloading Missing Files")
            
            successful = 0
            failed = 0
            
            for file_path, filename in missing_files:
                if download_custom_file(file_path, filename, tf2_dir):
                    successful += 1
                else:
                    failed += 1
            
            print(f"\n{'='*60}")
            print(f"Download Summary:")
            print(f"  ✓ Successful: {successful}")
            if failed > 0:
                print(f"  ✗ Failed: {failed}")
            print(f"{'='*60}\n")
            
            if successful > 0:
                print("✓ Custom files have been installed!")
        else:
            print("\n⚠ Skipping custom files download.")
            print("You can run this tool again later to download them.")


def get_available_drives() -> List[str]:
    """Get all available drive letters on Windows"""
    if os.name != 'nt':
        return ['/']
    
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


def search_tf2_directories(drives: List[str]) -> List[Path]:
    """Search all drives for TF2 installation directories"""
    print_header("Searching for TF2 Classified Installation")
    print("Scanning drives: " + ", ".join(drives))
    print("This may take a moment...\n")
    
    tf2_dirs = []
    total_drives = len(drives)
    
    for idx, drive in enumerate(drives, 1):
        print(f"[{idx}/{total_drives}] Scanning {drive}...")
        try:
            # Search common locations first (faster)
            common_paths = [
                Path(drive) / "Program Files (x86)" / "Steam" / "steamapps" / "common",
                Path(drive) / "Program Files" / "Steam" / "steamapps" / "common",
                Path(drive) / "Steam" / "steamapps" / "common",
                Path(drive) / "SteamLibrary" / "steamapps" / "common",
            ]
            
            for base_path in common_paths:
                if base_path.exists():
                    for pattern in TF2_PATTERNS:
                        # Check for both direct pattern match and pattern/tf subdirectory
                        for subdir in [pattern, f"{pattern}/tf2classic", f"{pattern}/tf2classified", f"{pattern}/tf"]:
                            tf2_path = base_path / subdir
                            if tf2_path.exists() and tf2_path.is_dir():
                                print(f"  ✓ Found: {tf2_path}")
                                tf2_dirs.append(tf2_path)
                            
        except PermissionError:
            continue
        except Exception as e:
            print(f"  Error scanning {drive}: {e}")
    
    print()  # Empty line after scanning
    return list(set(tf2_dirs))  # Remove duplicates


def check_schema_exists(tf2_dir: Path) -> dict:
    """Check which schema locations already have files"""
    existing = {}
    
    for option, rel_path in SCHEMA_PATHS.items():
        schema_path = tf2_dir / rel_path
        schema_file = schema_path / "items_game.txt"
        
        if schema_file.exists():
            existing[option] = schema_path
    
    return existing


def download_schema() -> Optional[str]:
    """Download the item schema from GitHub Gist"""
    print("\nDownloading item schema from GitHub...")
    schema_content = download_with_progress(GIST_URL, "Downloading schema")
    
    if schema_content:
        print("✓ Download successful!\n")
    
    return schema_content


def install_schema(tf2_dir: Path, schema_content: str, option: int) -> bool:
    """Install schema to the selected location"""
    rel_path = SCHEMA_PATHS[option]
    target_dir = tf2_dir / rel_path
    target_file = target_dir / "items_game.txt"
    
    try:
        # Create directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Write the schema file
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(schema_content)
        
        print(f"\n✓ Successfully installed to: {target_file}\n")
        return True
    except Exception as e:
        print(f"\n✗ Installation failed: {e}\n")
        return False


def get_user_choice(prompt: str, valid_choices: List[str]) -> str:
    """Get validated user input"""
    while True:
        choice = input(prompt).strip()
        if choice in valid_choices:
            return choice
        print(f"Invalid choice. Please enter one of: {', '.join(valid_choices)}")


def show_location_menu() -> int:
    """Show installation location menu and get user choice"""
    print("\nSelect installation location:")
    print("  1. scripts/items/")
    print("  2. custom/itemschema/scripts/items/")
    
    choice = get_user_choice("\nEnter your choice (1 or 2): ", ['1', '2'])
    return int(choice)


def main():
    """Main program flow"""
    clear_screen()
    print_header("TF2 Classified Item Schema Updater")
    print(f"Version {__version__}\n")
    
    # Check for updates
    print("Checking for updates...")
    latest_version = check_for_updates()
    
    if latest_version and latest_version != __version__:
        if show_update_prompt(latest_version):
            if update_script():
                return  # Script will restart
            else:
                print("\nContinuing with current version...\n")
                time.sleep(1)
    elif latest_version:
        print("✓ You're running the latest version!\n")
    else:
        print("⚠ Could not check for updates (no internet or GitHub unavailable)\n")
    
    # Step 1: Search for TF2 installation
    drives = get_available_drives()
    tf2_dirs = search_tf2_directories(drives)
    
    if not tf2_dirs:
        print("\n✗ No TF2 Classified installation found on any drive.")
        print("\nMake sure TF2 Classified is installed and try again.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Step 2: Let user select TF2 directory if multiple found
    if len(tf2_dirs) > 1:
        print(f"\nFound {len(tf2_dirs)} TF2 Classified installations:")
        for i, tf2_dir in enumerate(tf2_dirs, 1):
            print(f"  {i}. {tf2_dir}")
        
        choices = [str(i) for i in range(1, len(tf2_dirs) + 1)]
        choice = get_user_choice(f"\nSelect installation (1-{len(tf2_dirs)}): ", choices)
        selected_tf2 = tf2_dirs[int(choice) - 1]
    else:
        selected_tf2 = tf2_dirs[0]
        print(f"\nUsing TF2 Classified installation: {selected_tf2}")
    
    # Step 3: Check if schema already exists
    existing_schemas = check_schema_exists(selected_tf2)
    
    if existing_schemas:
        print_header("Item Schema Already Installed")
        print("Existing schema files found in:")
        for option, path in existing_schemas.items():
            location_name = SCHEMA_PATHS[option]
            print(f"  • {location_name}")
        
        print("\nWhat would you like to do?")
        print("  1. Update")
        print("  2. Reinstall")
        print("  3. Quit")
        
        action = get_user_choice("\nEnter your choice (1-3): ", ['1', '2', '3'])
        
        if action == '3':
            print("\nExiting...")
            sys.exit(0)
        
        # Update or reinstall
        schema_content = download_schema()
        if not schema_content:
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        # Ask which location to update/reinstall
        location = show_location_menu()
        
        action_text = "Updating" if action == '1' else "Reinstalling"
        print(f"\n{action_text} schema...")
        
        if install_schema(selected_tf2, schema_content, location):
            print(f"✓ {action_text} complete!")
        else:
            print(f"✗ {action_text} failed!")
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    else:
        print_header("Item Schema Not Found")
        print("No existing schema installation detected.")
        print("\nWhat would you like to do?")
        print("  1. Install")
        print("  2. Quit")
        
        action = get_user_choice("\nEnter your choice (1 or 2): ", ['1', '2'])
        
        if action == '2':
            print("\nExiting...")
            sys.exit(0)
        
        # Install fresh
        schema_content = download_schema()
        if not schema_content:
            input("\nPress Enter to exit...")
            sys.exit(1)
        
        location = show_location_menu()
        
        print("\nInstalling schema...")
        
        if install_schema(selected_tf2, schema_content, location):
            print("✓ Installation complete!")
        else:
            print("✗ Installation failed!")
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    print_header("Success!")
    print("Item schema has been successfully installed/updated.")
    print(f"Location: {selected_tf2 / SCHEMA_PATHS[location]}")
    
    # Check for required custom files
    time.sleep(1)
    handle_custom_files_check(selected_tf2)
    
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ An unexpected error occurred: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)