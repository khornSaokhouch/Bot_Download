# downloader.py

import os
import logging
import tempfile
import yt_dlp
import subprocess
from telegram import Update, constants
from telegram.ext import ContextTypes

# Import configuration
from config import TELEGRAM_MAX_FILE_SIZE

logger = logging.getLogger(__name__)

# --- Ensure yt-dlp is always up-to-date ---
try:
    subprocess.run(["yt-dlp", "-U"], check=False)
    logger.info("yt-dlp self-update attempted.")
except Exception as e:
    logger.warning(f"Could not self-update yt-dlp: {e}")


def _create_caption(info: dict) -> str:
    """Creates a clean, simple caption from the media's info."""
    title = info.get('title', 'Untitled')
    uploader = info.get('uploader')

    # Clean up common junk from titles
    title = title.replace('_', ' ').strip()

    if uploader:
        return f"<b>{title}</b>\n<i>by {uploader}</i>"
    return f"<b>{title}</b>"


async def _send_media(context: ContextTypes.DEFAULT_TYPE, chat_id: int, filepath: str, caption: str):
    """Detects file type and sends it as a photo, video, or document."""
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


# --- Handler for ALL URLs ---
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles any message containing a URL and attempts to download the media."""
    url = update.message.text.strip()

    status_message = await update.message.reply_text("🔗 Link detected! Starting download process...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # yt-dlp options
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'noprogress': True,
            'noplaylist': True,
        }

        # If cookies.txt exists, use it (helps with TikTok)
        if os.path.exists("cookies.txt"):
            ydl_opts["cookiefile"] = "cookies.txt"
            logger.info("Using cookies.txt for yt-dlp.")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            # Handle playlists or multiple entries
            if 'entries' in info and info['entries']:
                entries = info['entries']
                await status_message.edit_text(f"✅ Found {len(entries)} items! Sending them now...")

                for i, entry in enumerate(entries):
                    filepath = ydl.prepare_filename(entry)
                    if os.path.exists(filepath):
                        caption = _create_caption(entry)
                        await _send_media(
                            context, update.effective_chat.id,
                            filepath, f"({i+1}/{len(entries)}) {caption}"
                        )
                    else:
                        logger.warning(f"File for entry {i+1} not found after download: {filepath}")
            else:
                await status_message.edit_text("✅ Download complete! Sending file...")
                filepath = ydl.prepare_filename(info)
                if os.path.exists(filepath):
                    caption = _create_caption(info)
                    await _send_media(context, update.effective_chat.id, filepath, caption)
                else:
                    raise FileNotFoundError("Downloaded file could not be found.")

            await status_message.delete()

        except Exception as e:
            error_message = str(e).split('; ERROR: ')[-1]
            logger.error(f"Error processing URL '{url}': {e}")

            # Special hint for TikTok issues
            if "TikTok" in error_message:
                error_message += "\n\n💡 Try updating yt-dlp or adding cookies.txt."

            await status_message.edit_text(
                f"❌ Failed to download.\n\n<b>Reason:</b> <code>{error_message}</code>",
                parse_mode=constants.ParseMode.HTML
            )
