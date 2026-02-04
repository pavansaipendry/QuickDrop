#!/usr/bin/env python3
"""
QuickSend - Fast USB file transfer between Mac and Android using ADB
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

# Default destination folder on Android
ANDROID_DEST = "/sdcard/Download/"

def check_adb():
    """Check if ADB is installed and accessible"""
    if shutil.which('adb'):
        return True
    
    # Check common Homebrew locations
    for path in ['/opt/homebrew/bin/adb', '/usr/local/bin/adb']:
        if os.path.exists(path):
            return path
    return False

def get_adb_cmd():
    """Get the ADB command path"""
    if shutil.which('adb'):
        return 'adb'
    for path in ['/opt/homebrew/bin/adb', '/usr/local/bin/adb']:
        if os.path.exists(path):
            return path
    return None

def check_device():
    """Check if an Android device is connected"""
    adb = get_adb_cmd()
    if not adb:
        return False, "ADB not found"
    
    result = subprocess.run([adb, 'devices'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')[1:]  # Skip header
    
    for line in lines:
        if '\tdevice' in line:
            device_id = line.split('\t')[0]
            return True, device_id
    
    if any('\tunauthorized' in line for line in lines):
        return False, "Device unauthorized - check your phone for USB debugging prompt"
    
    return False, "No device connected"

def push_file(source, dest=ANDROID_DEST):
    """Push a file from Mac to Android"""
    adb = get_adb_cmd()
    source_path = Path(source).expanduser().resolve()
    
    if not source_path.exists():
        print(f"❌ File not found: {source}")
        return False
    
    filename = source_path.name
    dest_path = f"{dest}{filename}"
    
    print(f"\n📤 Sending: {filename}")
    print(f"   To: {dest_path}")
    print(f"   Size: {get_size_str(source_path.stat().st_size)}")
    print()
    
    # Use adb push with progress
    result = subprocess.run(
        [adb, 'push', str(source_path), dest_path],
        capture_output=False
    )
    
    if result.returncode == 0:
        print(f"\n✅ Done! File saved to {dest_path}")
        return True
    else:
        print(f"\n❌ Transfer failed")
        return False

def pull_file(source, dest="."):
    """Pull a file from Android to Mac"""
    adb = get_adb_cmd()
    dest_path = Path(dest).expanduser().resolve()
    
    if dest_path.is_dir():
        filename = Path(source).name
        dest_path = dest_path / filename
    
    print(f"\n📥 Downloading: {source}")
    print(f"   To: {dest_path}")
    print()
    
    result = subprocess.run(
        [adb, 'pull', source, str(dest_path)],
        capture_output=False
    )
    
    if result.returncode == 0:
        print(f"\n✅ Done! File saved to {dest_path}")
        return True
    else:
        print(f"\n❌ Transfer failed")
        return False

def list_files(path="/sdcard/Download/"):
    """List files on Android"""
    adb = get_adb_cmd()
    result = subprocess.run(
        [adb, 'shell', 'ls', '-la', path],
        capture_output=True, text=True
    )
    print(f"\n📁 Files in {path}:\n")
    print(result.stdout)

def get_size_str(size_bytes):
    """Convert bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def print_help():
    """Print usage instructions"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              ⚡ QuickSend - USB File Transfer                 ║
╚═══════════════════════════════════════════════════════════════╝

USAGE:
  python3 quicksend.py send <file>           Send file to Android
  python3 quicksend.py send <file> <dest>    Send to specific folder
  python3 quicksend.py get <android_path>    Download from Android
  python3 quicksend.py list [path]           List files on Android
  python3 quicksend.py status                Check connection

EXAMPLES:
  python3 quicksend.py send ~/Downloads/movie.mkv
  python3 quicksend.py send movie.mkv /sdcard/Movies/
  python3 quicksend.py get /sdcard/DCIM/Camera/photo.jpg
  python3 quicksend.py list /sdcard/DCIM/Camera/

DEFAULT ANDROID FOLDER: /sdcard/Download/
""")

def main():
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    # Check ADB installation
    if not check_adb():
        print("❌ ADB not found!")
        print("\nInstall it with Homebrew:")
        print("  brew install android-platform-tools")
        return
    
    if command == 'status':
        connected, info = check_device()
        if connected:
            print(f"✅ Device connected: {info}")
        else:
            print(f"❌ {info}")
    
    elif command == 'send':
        if len(sys.argv) < 3:
            print("Usage: python3 quicksend.py send <file> [destination]")
            return
        
        connected, info = check_device()
        if not connected:
            print(f"❌ {info}")
            return
        
        source = sys.argv[2]
        dest = sys.argv[3] if len(sys.argv) > 3 else ANDROID_DEST
        push_file(source, dest)
    
    elif command == 'get':
        if len(sys.argv) < 3:
            print("Usage: python3 quicksend.py get <android_path> [local_dest]")
            return
        
        connected, info = check_device()
        if not connected:
            print(f"❌ {info}")
            return
        
        source = sys.argv[2]
        dest = sys.argv[3] if len(sys.argv) > 3 else "."
        pull_file(source, dest)
    
    elif command == 'list':
        connected, info = check_device()
        if not connected:
            print(f"❌ {info}")
            return
        
        path = sys.argv[2] if len(sys.argv) > 2 else "/sdcard/Download/"
        list_files(path)
    
    else:
        print_help()

if __name__ == '__main__':
    main()