# downloader.py

import os
import logging
import tempfile
import yt_dlp
import subprocess
from telegram import Update, constants
from telegram.ext import ContextTypes
import re


from config import TELEGRAM_MAX_FILE_SIZE

logger = logging.getLogger(__name__)

# --- Ensure yt-dlp is up-to-date ---
try:
    subprocess.run(["yt-dlp", "-U"], check=False)
    logger.info("yt-dlp self-update attempted.")
except Exception as e:
    logger.warning(f"Could not self-update yt-dlp: {e}")

# --- Helper Functions ---

def _create_caption(info: dict) -> str:
    """Creates a caption from video info."""
    title = info.get('title', 'Untitled').replace('_', ' ').strip()
    uploader = info.get('uploader')
    hashtags = re.findall(r'#\w+', title)
    clean_title = re.sub(r'#\w+', '', title).strip()

    caption = f"<b>{clean_title}</b>"
    if uploader:
        caption += f"\n<i>by {uploader}</i>"
    if hashtags:
        caption += "\n" + " ".join([f"<code>{tag}</code>" for tag in hashtags])
    return caption


async def _send_media(context: ContextTypes.DEFAULT_TYPE, chat_id: int, filepath: str, caption: str):
    """Send media file to Telegram, checking type and size."""
    try:
        file_ext = os.path.splitext(filepath)[1].lower()
        file_size = os.path.getsize(filepath)

        if file_size > TELEGRAM_MAX_FILE_SIZE:
            await context.bot.send_message(
                chat_id,
                f"⚠️ The file '{os.path.basename(filepath)}' is too large for Telegram "
                f"({file_size // 1024 // 1024}MB)."
            )
            return

        with open(filepath, 'rb') as f:
            if file_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=f,
                    caption=caption, parse_mode=constants.ParseMode.HTML
                )
            elif file_ext in ['.mp4', '.mov', '.mkv', '.webm']:
                await context.bot.send_video(
                    chat_id=chat_id, video=f,
                    caption=caption, parse_mode=constants.ParseMode.HTML,
                    supports_streaming=True
                )
            else:
                await context.bot.send_document(
                    chat_id=chat_id, document=f,
                    caption=caption, parse_mode=constants.ParseMode.HTML
                )
    except Exception as e:
        logger.error(f"Error sending media file {filepath}: {e}")
        await context.bot.send_message(chat_id, text=f"❌ Could not send file: {os.path.basename(filepath)}")


# --- Main Handler ---

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    status_message = await update.message.reply_text("🔗 Link detected! Starting download...")

    with tempfile.TemporaryDirectory() as temp_dir:
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'noprogress': True,
            'noplaylist': True,
            'nocheckcertificate': True
        }

        # Use cookies.txt if available
        if os.path.exists("cookies.txt"):
            ydl_opts["cookiefile"] = "cookies.txt"
            logger.info("Using cookies.txt for yt-dlp.")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            # Handle playlists
            if 'entries' in info and info['entries']:
                entries = info['entries']
                await status_message.edit_text(f"✅ Found {len(entries)} items. Sending them now...")

                for i, entry in enumerate(entries):
                    filepath = ydl.prepare_filename(entry)
                    if os.path.exists(filepath):
                        caption = _create_caption(entry)
                        await _send_media(context, update.effective_chat.id,
                                          filepath, f"({i+1}/{len(entries)}) {caption}")
                    else:
                        logger.warning(f"File for entry {i+1} not found: {filepath}")

            else:
                filepath = ydl.prepare_filename(info)
                if os.path.exists(filepath):
                    caption = _create_caption(info)
                    await _send_media(context, update.effective_chat.id, filepath, caption)
                else:
                    raise FileNotFoundError("Downloaded file not found.")

            await status_message.delete()

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error processing URL '{url}': {e}")

            # TikTok-specific hint
            if "TikTok" in error_message:
                hint = "💡 Try updating yt-dlp or adding cookies.txt."
            else:
                hint = ""

            await status_message.edit_text(
                f"❌ Failed to download.\n\n<b>Reason:</b> <code>{error_message}</code>\n{hint}",
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
