# QuickDrop

A simple, no-nonsense way to transfer files between your Mac and Android phone. No cloud uploads, no account signups, no app installations (mostly). Just your devices talking directly to each other.

I built this because I was tired of emailing files to myself or uploading stuff to Google Drive just to move a video from my laptop to my phone. There had to be a better way — turns out there are two.

---

## Two Ways to Transfer

| Method | Best For | Speed | Setup Time |
|--------|----------|-------|------------|
| [WiFi Transfer](#method-1-wifi-transfer) | Quick transfers, small-medium files | 5-30 MB/s | 2 minutes |
| [USB Transfer](#method-2-usb-transfer) | Large files, movies, bulk transfers | 30-60 MB/s | 5 minutes |

Pick whichever suits your situation. I usually use WiFi for quick stuff and USB when I'm moving movies or large folders.

---

## Method 1: WiFi Transfer

This runs a tiny web server on your Mac. You open a webpage on your phone's browser and drag-drop files either direction. Dead simple.

### What You'll Need

- Mac and Android on the same WiFi network
- Python 3 (comes pre-installed on Mac)
- 2 minutes of your time

### Setup

**1. Clone or download this repo**

```bash
git clone https://github.com/YOUR_USERNAME/QuickDrop.git
cd QuickDrop
```

**2. Create a virtual environment**

This keeps dependencies isolated and avoids module conflicts:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You'll see `(.venv)` appear at the start of your terminal prompt — that means it's active.

**3. Install the dependencies**

```bash
pip install flask qrcode Pillow waitress
```

**4. Run it**

```bash
python3 file_transfer.py
```

> **Note:** Every time you open a new terminal window, you'll need to activate the virtual environment again with `source .venv/bin/activate` before running the script.

You'll see something like this:

```
==================================================
  ⚡ QuickDrop - File Transfer Server
==================================================

  📁 Shared folder: /Users/you/Downloads/PhoneTransfer

  🌐 Open this URL on your Android phone:

     http://192.168.1.42:5000

  📱 Or scan the QR code below:

     █████████████████
     █████████████████
     █████████████████
     
==================================================
  Press Ctrl+C to stop the server
==================================================

  🚀 Running with Waitress (production server)
     Expected speeds: 30-100+ MB/s on 5GHz WiFi
```

**4. Connect your phone**

Either scan the QR code with your camera, or just type that URL into Chrome on your phone.

### How to Use It

**Sending files from Android to Mac:**
- Tap "Select Files" or drag-and-drop onto the upload zone
- Files land in `~/Downloads/PhoneTransfer` on your Mac

**Sending files from Mac to Android:**
- Drop files into `~/Downloads/PhoneTransfer` on your Mac
- Refresh the page on your phone
- Tap "Download" next to any file

### Troubleshooting

**Can't connect from phone?**
- Double-check both devices are on the same WiFi network
- Try turning off your Mac's firewall temporarily (System Preferences → Security → Firewall)
- Make sure you're using the right IP address (it changes if you switch networks)

**Slow speeds?**
- Check if you're on 5GHz WiFi (Settings → WiFi → tap your network)
- Move closer to your router
- Close other bandwidth-heavy apps

**File not found errors on download?**
- This can happen with filenames that have special characters
- Try renaming the file to something simpler (no parentheses, brackets, etc.)

---

## Method 2: USB Transfer

This uses ADB (Android Debug Bridge) over a USB cable. It's faster and more reliable for large files, but requires a bit more setup the first time.

### What You'll Need

- USB-C to USB-C cable (or USB-C to USB-A, whatever fits your Mac)
- Homebrew (Mac package manager)
- About 5 minutes for first-time setup

### First-Time Setup

You only need to do this once.

**Step 1: Install Homebrew (if you don't have it)**

Open Terminal and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. This takes a couple minutes.

To verify it worked:
```bash
brew --version
```

**Step 2: Install ADB**

```bash
brew install android-platform-tools
```

Verify it's installed:
```bash
adb --version
```

**Step 3: Enable Developer Options on your Android phone**

This is a hidden menu that you need to unlock:

1. Open **Settings**
2. Scroll down to **About Phone**
3. Find **Build Number**
4. Tap it **7 times** rapidly

You'll see a toast message saying "You are now a developer!" (or something like that).

**Step 4: Enable USB Debugging**

1. Go back to **Settings**
2. You'll now see **Developer Options** (usually near the bottom, or under System)
3. Open it and scroll to find **USB Debugging**
4. Turn it **ON**
5. Confirm the warning prompt

**Step 5: Connect and authorize**

1. Plug your phone into your Mac with the USB cable
2. A prompt will appear on your phone: "Allow USB debugging?"
3. Check **"Always allow from this computer"**
4. Tap **Allow**

**Step 6: Verify the connection**

On your Mac, run:

```bash
adb devices
```

You should see your device listed:
```
List of devices attached
RZCWA1WSYLF    device
```

If it says "unauthorized" instead of "device", check your phone — the permission prompt might be waiting.

### How to Use It

**Send a file to your phone:**
```bash
adb push /path/to/file.mp4 /sdcard/Download/
```

**Send an entire folder:**
```bash
adb push ~/Downloads/MyFolder /sdcard/Download/
```

**Pull a file from your phone:**
```bash
adb pull /sdcard/DCIM/Camera/photo.jpg ~/Desktop/
```

**Pull all your photos:**
```bash
adb pull /sdcard/DCIM/Camera/ ~/Desktop/CameraBackup/
```

**List files on your phone:**
```bash
adb shell ls /sdcard/Download/
```

### Common Android Folders

| What | Path |
|------|------|
| Downloads | `/sdcard/Download/` |
| Camera photos | `/sdcard/DCIM/Camera/` |
| Screenshots | `/sdcard/DCIM/Screenshots/` |
| Movies | `/sdcard/Movies/` |
| Music | `/sdcard/Music/` |

### Troubleshooting

**"no devices/emulators found"**
- Is USB debugging enabled?
- Try a different USB cable (some cables are charge-only)
- Try a different USB port
- Unplug and replug the cable

**"unauthorized"**
- Check your phone for the "Allow USB debugging?" prompt
- If you dismissed it, unplug and replug the cable

**Transfer seems stuck**
- Large files take time — a 2GB file at 40 MB/s takes about 50 seconds
- ADB shows progress, just wait for it

---

## Video Playback Issues

If a video transfers successfully but won't play on your phone, it's probably a codec issue, not a corrupt file.

Modern videos often use **x265/HEVC** or **10-bit color**, which the default Android video player can't handle.

**Solution:** Install [VLC for Android](https://play.google.com/store/apps/details?id=org.videolan.vlc) from the Play Store. It plays basically everything.

To make VLC the default player:
1. Open your file manager
2. Long-press on a video file
3. Tap "Open with"
4. Select VLC
5. Choose "Always"

---

## Quick Reference

### WiFi Method
```bash
# Activate virtual environment (do this first!)
source .venv/bin/activate

# Start server
python3 file_transfer.py

# Files go to/from: ~/Downloads/PhoneTransfer
```

### USB Method
```bash
# Mac → Phone
adb push file.mp4 /sdcard/Download/
adb push ~/folder /sdcard/Download/

# Phone → Mac
adb pull /sdcard/Download/file.mp4 ~/Desktop/
adb pull /sdcard/DCIM/Camera/ ~/Desktop/Photos/

# Browse phone files
adb shell ls /sdcard/
```

---

## License

MIT — do whatever you want with it.

---

## Acknowledgments

Built out of frustration with existing solutions. Sometimes the simplest approach is the best one.