from flask import Flask, request, render_template, send_file
import yt_dlp
import tempfile
import os
import re

app = Flask(__name__)

def sanitize_filename(name: str) -> str:
    """Sanitize a string to be a safe filename."""
    # Replace any character that is not a letter, number, underscore, hyphen, or period with an underscore
    safe_name = re.sub(r'[^\w\-. ]', '_', name)
    if not safe_name.lower().endswith(".mp4"):
        safe_name += ".mp4"
    return safe_name

@app.get("/")
def home():
    """Render the homepage from the template file."""
    return render_template("home.html")

@app.post("/download")
def download():
    """Handle video download requests."""
    page_url = (request.form.get("url") or "").strip()
    if not page_url:
        return "Please provide a valid video URL.", 400

    # Create a temporary directory to store the downloaded video
    temp_dir = tempfile.mkdtemp()
    
    try:
        # --- NEW, MORE ROBUST LOGIC ---

        # 1. Get video info first to extract the title
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(page_url, download=False)
            title = info.get('title', 'video')
            filename = sanitize_filename(title)

        # 2. Configure yt-dlp to download the video to our temporary path
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            # Use 'outtmpl' to specify the exact output path and filename
            'outtmpl': os.path.join(temp_dir, filename),
            'quiet': True,
        }

        # 3. Let yt-dlp handle the entire download process
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([page_url])

        # 4. Serve the downloaded file to the user
        video_path = os.path.join(temp_dir, filename)
        
        return send_file(
            video_path,
            as_attachment=True,
            # The attachment_filename is deprecated but we set it for older browsers.
            # download_name is the modern way.
            download_name=filename,
            mimetype='video/mp4'
        )

    except yt_dlp.utils.DownloadError as e:
        # Handle errors from yt-dlp (e.g., unsupported URL, private video)
        return f"Download failed: Unsupported URL or the video is private/unavailable. Please check the link.", 400
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        # 5. Clean up: ALWAYS remove the temporary file and directory
        # This is crucial to avoid filling up the server's disk space.
        try:
            if 'video_path' in locals() and os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            # Log cleanup errors if you have a logging system
            print(f"Error cleaning up temp files: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)