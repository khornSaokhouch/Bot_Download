# video_handler.py
import os
import logging
import tempfile
import re
import time
import traceback
import yt_dlp
from telegram import Update, constants
from telegram.ext import ContextTypes
import asyncio

from config import TELEGRAM_MAX_FILE_SIZE

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    name = name[:100]
    safe_name = re.sub(r'[^\w\-. ]', '_', name)
    return f"{safe_name}.mp4"

def format_duration(seconds: int) -> str:
    if not seconds:
        return "N/A"
    return time.strftime('%H:%M:%S', time.gmtime(seconds))

def process_video_url(url: str, temp_dir: str) -> dict:
    """Synchronous video processing (yt-dlp is blocking)."""
    try:
        ydl_opts_info = {'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get('title', 'video')
        uploader = info.get('uploader', 'N/A')
        duration = info.get('duration')

        best_format = None
        for f in info.get('formats', []):
            filesize = f.get('filesize') or f.get('filesize_approx')
            if (filesize and filesize < TELEGRAM_MAX_FILE_SIZE and
                f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('acodec') != 'none'):
                best_format = f
                break

        if best_format:
            filename = sanitize_filename(title)
            filepath = os.path.join(temp_dir, filename)

            ydl_opts_download = {
                'format': best_format['format_id'],
                'outtmpl': filepath,
                'quiet': True,
                'noplaylist': True,
                'external_downloader': 'aria2c',
                'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
                'socket_timeout': 30,
                'retries': 10,
                'continuedl': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
                ydl.download([url])

            if os.path.exists(filepath):
                hashtags = re.findall(r'#\w+', title)
                clean_title = re.sub(r'#\w+', '', title).strip()
                caption_parts = [
                    f"🎬 <b>{clean_title}</b>",
                    f"\n👤 <b>Channel:</b> {uploader}",
                    f"⏱️ <b>Duration:</b> {format_duration(duration)}"
                ]
                if hashtags:
                    hashtag_line = ' '.join([f"<code>{tag}</code>" for tag in hashtags])
                    caption_parts.append(f"\n#️⃣ <b>Tags:</b> {hashtag_line}")
                
                caption = "\n".join(caption_parts)
                return {"status": "success", "path": filepath, "caption": caption}
            else:
                return {"status": "error", "message": "Download finished but file not found."}
        else:
            direct_url = info.get('url') or (info['formats'][-1]['url'] if info.get('formats') else None)
            return {
                "status": "too_large",
                "title": title,
                "uploader": uploader,
                "duration": format_duration(duration),
                "direct_url": direct_url
            }
    except Exception as e:
        logger.error(f"Error in process_video_url: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

async def handle_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Async wrapper to process video URL and send to Telegram."""
    url = update.message.text.strip()
    processing_message = await update.message.reply_text("✅ Link received! Analyzing video...")

    loop = asyncio.get_event_loop()
    with tempfile.TemporaryDirectory() as temp_dir:
        result = await loop.run_in_executor(None, process_video_url, url, temp_dir)

        if result['status'] == 'success':
            await processing_message.edit_text("⏳ Download in progress, please wait...")
            try:
                with open(result['path'], 'rb') as video_file:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption=result['caption'],
                        parse_mode=constants.ParseMode.HTML,
                        supports_streaming=True
                    )
                await processing_message.delete()
            except Exception as e:
                logger.error(f"Error sending video file: {e}\n{traceback.format_exc()}")
                await processing_message.edit_text("❌ A critical error occurred while uploading the video to Telegram.")
        elif result['status'] == 'too_large':
            message = (
                f"⚠️ <b>Video Too Large for Telegram!</b>\n\n"
                f"🎬 <b>Title:</b> {result['title']}\n"
                f"👤 <b>Channel:</b> {result['uploader']}\n"
                f"⏱️ <b>Duration:</b> {result['duration']}\n\n"
                f"👉 <a href='{result['direct_url']}'><b>Click here for a direct download link.</b></a>"
            )
            await processing_message.edit_text(message, parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True)
        else:
            error_message = f"❌ <b>Failed to process video.</b>\n\n<b>Reason:</b>\n<code>{result['message']}</code>"
            await processing_message.edit_text(error_message, parse_mode=constants.ParseMode.HTML)
