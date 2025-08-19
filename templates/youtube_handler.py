# youtube_handler.py

import os
import logging
import tempfile
import re
import yt_dlp
from telegram import Update, InputFile
from telegram.ext import CallbackContext
from telegram.error import TelegramError

# Set up logging for this module
logger = logging.getLogger(__name__)

# A helper function to format duration from seconds to HH:MM:SS or MM:SS
def format_duration(seconds: int) -> str:
    if seconds is None:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f'{h:02d}:{m:02d}:{s:02d}'
    else:
        return f'{m:02d}:{s:02d}'

async def download_youtube_video(url: str) -> (str, str, int, str):
    """
    Downloads a YouTube video and returns its path, title, duration, and thumbnail URL.
    Returns (None, None, None, None) on failure.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        ydl_opts_info = {
            'quiet': True,
            'noplaylist': True,
            'skip_download': True, # We only want info first
        }
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'YouTube Video')
            duration = info.get('duration')
            thumbnail = info.get('thumbnail')
            # Sanitize title to create a valid filename
            filename = re.sub(r'[^\w\-. ]', '_', title) + ".mp4"

        video_path = os.path.join(temp_dir, filename)

        # Now set options for the actual download
        ydl_opts_download = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': video_path,
            'quiet': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
            ydl.download([url])

        if os.path.exists(video_path):
            return video_path, title, duration, thumbnail
        else:
            # Cleanup if download failed
            os.rmdir(temp_dir)
            return None, None, None, None
            
    except Exception as e:
        logger.error(f"Error during YouTube download: {e}")
        # Cleanup on any exception
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        return None, None, None, None

async def youtube_download_handler(update: Update, context: CallbackContext) -> None:
    """Handles the /youtube command."""
    if not context.args:
        await update.message.reply_text("Please provide a YouTube link after the command.\n\nUsage: `/youtube <URL>`", parse_mode='Markdown')
        return

    url = context.args[0]
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("This doesn't look like a valid YouTube link.")
        return

    processing_message = await update.message.reply_text("🔎 Processing your YouTube link, please wait...")

    video_path = None # Initialize to ensure it exists for the 'finally' block
    try:
        video_path, title, duration, thumbnail = await download_youtube_video(url)

        if video_path and os.path.exists(video_path):
            duration_str = format_duration(duration)
            caption = f"🎬 **{title}**\n\n🕒 Duration: {duration_str}\n\nDownloaded via @{context.bot.username}"
            
            with open(video_path, 'rb') as video_file:
                try:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption=caption,
                        supports_streaming=True,
                        thumbnail=thumbnail,
                        parse_mode='Markdown'
                    )
                except TelegramError as e:
                    if "Request Entity Too Large" in str(e):
                        logger.warning(f"YouTube video too large to send: {title}")
                        await processing_message.edit_text(
                            f"Sorry, the video '{title}' is too large to be sent through Telegram (>50MB)."
                        )
                    else:
                        logger.error(f"Telegram error sending video: {e}")
                        await processing_message.edit_text("An unexpected error occurred while sending the video.")
                        
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        else:
            await processing_message.edit_text("Sorry, I could not download the video from that YouTube link. It might be private, age-restricted, or an invalid link.")
    
    finally:
        # Cleanup: remove the temporary file and directory
        if video_path and os.path.exists(video_path):
            temp_dir = os.path.dirname(video_path)
            os.remove(video_path)
            os.rmdir(temp_dir)