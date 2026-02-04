# How I Built This (and everything that broke along the way)

This is the story of building QuickDrop, including all the bugs, wrong turns, and "why isn't this working" moments. If you're curious about how file transfer actually works under the hood, or you want to learn from my mistakes, keep reading.

## The Goal

Transfer files between a Mac and an Android phone. That's it. Should be simple, right?

## Attempt 1: WiFi Transfer with Flask

The idea was straightforward: run a web server on the Mac, connect from the phone's browser, drag and drop files.

### How it works

```
┌─────────────┐                         ┌─────────────┐
│   MacBook   │◄──── Same WiFi ────────►│   Android   │
│ Flask Server│    http://192.168.x.x   │   Chrome    │
└─────────────┘                         └─────────────┘
```

1. Python script starts a Flask web server on your Mac
2. Server binds to `0.0.0.0:5000` so it's accessible from other devices on the network
3. Script detects your local IP address (like `192.168.1.42`)
4. Generates a QR code pointing to `http://192.168.1.42:5000`
5. Phone scans QR code, opens the page in Chrome
6. Web UI lets you upload files (phone to Mac) or download files (Mac to phone)

Simple enough. I got it working in about an hour. Then the bugs started.

---

## Bug 1: "File not found" on download

### What happened

Small files downloaded fine. Images worked. But when I tried to download a large video file, the browser showed "File not found" even though the file was sitting right there in the folder.

### The filename

```
Family Vacation 2024 (Beach Trip).mp4
```

See the problem? Spaces. Parentheses. Special characters.

### What went wrong

My download route was using Flask's `secure_filename()` function, which sanitizes filenames by removing special characters. So when someone clicked download, the URL would be:

```
/download/Family Vacation 2024 (Beach Trip).mp4
```

But the server was looking for:

```
Family_Vacation_2024_Beach_Trip.mp4
```

The file didn't exist because `secure_filename()` was mangling the name.

### The fix

I rewrote the download route to:
1. URL-decode the filename properly
2. Skip `secure_filename()` for downloads (only needed for uploads to prevent malicious filenames)
3. Add path traversal protection manually (so people can't request `/download/../../etc/passwd`)

```python
@app.route('/download/<path:filename>')
def download(filename):
    from urllib.parse import unquote
    filename = unquote(filename)
    
    # Security: prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    # ... rest of download logic
```

I also had to URL-encode the filename in the HTML template:

```html
<a href="/download/{{ file.name | urlencode }}">Download</a>
```

---

## Bug 2: Painfully slow downloads

### What happened

I tried downloading a 2GB file. The browser said "1 hour remaining."

Over WiFi. On the same network. That's about 0.5 MB/s. My WiFi router can do 100 MB/s. Something was very wrong.

### What went wrong

Two things:

1. **Flask's development server is slow.** It's single-threaded and not meant for production. It's fine for testing but terrible for actual file transfers.

2. **No streaming.** The default `send_from_directory()` was loading chunks inefficiently.

### The fix

**Switched to Waitress** (a production WSGI server):

```python
from waitress import serve
serve(app, host='0.0.0.0', port=5000, threads=8)
```

**Added chunked streaming** with 1MB chunks:

```python
def generate():
    chunk_size = 1024 * 1024  # 1MB
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

return Response(generate(), mimetype='application/octet-stream')
```

**Added resume support** with HTTP Range headers. This way if a download fails halfway, the browser can pick up where it left off instead of starting over.

After these changes, speeds improved to 5-30 MB/s depending on WiFi conditions. Better, but still not great for large files.

---

## Attempt 2: USB Transfer with ADB

For really large files, WiFi just wasn't cutting it. Time for a different approach.

### How it works

ADB (Android Debug Bridge) is a command-line tool that lets you talk to Android devices over USB. It's normally used for app development, but it can also push and pull files.

```bash
# Send file to phone
adb push video.mkv /sdcard/Download/

# Pull file from phone
adb pull /sdcard/DCIM/Camera/photo.jpg ~/Desktop/
```

The speeds are dramatically better: 30-60 MB/s over USB, compared to 5-30 MB/s over WiFi.

### Setup required

This is the annoying part. You need to:

1. Install Homebrew on Mac (if not already installed)
2. Install ADB: `brew install android-platform-tools`
3. Enable Developer Options on Android (tap "Build Number" 7 times)
4. Enable USB Debugging
5. Connect USB cable and accept the authorization prompt

It's a one-time setup, but it's definitely more involved than the WiFi approach.

---

## Bug 3: Video won't play after transfer

### What happened

I transferred a 2GB file over USB. Transfer completed successfully. Opened it on my phone. "Can't play video."

Tried different video player apps. Same error.

### What went wrong

Nothing, actually. The file transferred perfectly. The problem was the video codec.

The file was:
```
x265 HEVC 10-bit
```

Most default Android video players can't handle x265 or 10-bit color. They only support older codecs like x264.

### The fix

Install VLC. It plays everything.

This wasn't a bug in my code, but it's worth documenting because it's confusing when it happens. The file isn't corrupt, your player just doesn't support the format.

---

## Bug 4: Large uploads fail from phone

### What happened

Uploading images from phone to Mac worked fine. Uploading a 900MB file worked. Uploading a 3GB file failed silently.

### What went wrong

The browser was trying to load the entire file into memory before uploading it. Mobile browsers typically have a memory limit around 1-2GB. When you try to load a 3GB file, the browser just gives up.

### The fix

Chunked uploads. Instead of sending the whole file at once, split it into small pieces (10MB each) and send them one at a time.

Client side (JavaScript):
```javascript
const CHUNK_SIZE = 10 * 1024 * 1024; // 10MB

async function uploadFileChunked(file) {
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    
    for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);
        
        await fetch('/upload_chunk', {
            method: 'POST',
            body: formData  // contains just this chunk
        });
    }
}
```

Server side (Python):
```python
@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    # Save chunk to temp folder
    # When all chunks received, reassemble into final file
    # Delete temp chunks
```

Now the browser only holds 10MB in memory at a time. A 3GB file becomes 300 small uploads that get stitched together on the Mac.

---

## Architecture Overview

Here's how the final system works:

### WiFi Mode

```
Phone (Chrome)                         Mac (Python)
     │                                      │
     │──── GET / ──────────────────────────►│ Returns HTML page
     │◄─── HTML + JS ──────────────────────│
     │                                      │
     │──── POST /upload_chunk ─────────────►│ Receives 10MB chunk
     │◄─── { status: "chunk_received" } ───│
     │           ... repeat ...             │
     │◄─── { status: "complete" } ─────────│ Assembles final file
     │                                      │
     │──── GET /download/file.mp4 ─────────►│ Streams file in 1MB chunks
     │◄─── Binary data stream ─────────────│
```

### USB Mode

```
Mac (Terminal)                         Phone (ADB daemon)
     │                                      │
     │──── adb push file.mp4 /sdcard/ ─────►│ Direct file copy
     │◄─── Progress: 45.2 MB/s ────────────│
     │◄─── Done ───────────────────────────│
```

---

## What I Learned

1. **Flask's dev server is not for production.** Use Waitress, Gunicorn, or similar for any real workload.

2. **URL encoding is trickier than it looks.** Filenames with spaces, unicode characters, and special symbols need careful handling on both client and server.

3. **Browsers have memory limits.** You can't just load a 3GB file into a FormData object and POST it. Chunking is necessary for large files.

4. **WiFi speeds vary wildly.** 5GHz vs 2.4GHz makes a huge difference. Distance from router matters. Other devices on the network matter.

5. **USB is king for large files.** ADB over USB-C consistently hits 30-60 MB/s. If you're transferring videos or backups, use the cable.

6. **Codec issues look like transfer failures.** If a video won't play, it might not be corrupt. Check if your player supports the format.

---

## File Structure

```
QuickDrop/
├── file_transfer.py    # Main WiFi transfer server
├── quicksend.py        # Helper script for ADB commands
├── requirements.txt    # Python dependencies
├── .gitignore          # Excludes .venv, media files, etc.
└── README.md           # Setup and usage instructions
```

---

## Future Improvements (maybe)

Things I might add if I get around to it:

- [ ] Encryption for transfers (currently plaintext over local network)
- [ ] Auto-discovery so you don't need to scan QR code
- [ ] Desktop app with drag-and-drop instead of terminal
- [ ] iOS support (would need a different approach)
- [ ] Transfer history/logs

But honestly, it works for my use case. Sometimes "good enough" is good enough.

---

## Final Thoughts

This started because I wanted to watch a video on a flight and didn't want to pay for MacDroid or wait for Google Drive to upload 3GB.

It turned into a weekend project that taught me more about HTTP streaming, browser memory limits, and USB protocols than I expected.

If you're reading this and thinking "I could just use [insert app here]", you're probably right. But where's the fun in that?