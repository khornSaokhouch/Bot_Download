# import os
# import logging
# import tempfile
# import re
# import yt_dlp
# import time
# import traceback
# from telegram import Update, constants
# from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# # --- CONFIGURATION ---
# TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8334519238:AAHBesy3H7I3PUz93n-mrKz9Rv_LSiTaDRI")
# TELEGRAM_MAX_FILE_SIZE = 49 * 1024 * 1024  # 49 MB

# # --- Set up logging ---
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# # --- HELPER FUNCTIONS ---
# def sanitize_filename(name: str) -> str:
#     """Sanitize a string to be a safe filename."""
#     name = name[:100]
#     safe_name = re.sub(r'[^\w\-. ]', '_', name)
#     return f"{safe_name}.mp4"

# def format_duration(seconds: int) -> str:
#     if not seconds:
#         return "N/A"
#     return time.strftime('%H:%M:%S', time.gmtime(seconds))

# def process_video_url(url: str, temp_dir: str) -> dict:
#     try:
#         ydl_opts_info = {'quiet': True, 'noplaylist': True}
#         with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
#             info = ydl.extract_info(url, download=False)

#         title = info.get('title', 'video')
#         uploader = info.get('uploader', 'N/A')
#         duration = info.get('duration')

#         best_format = None
#         for f in info.get('formats', []):
#             filesize = f.get('filesize') or f.get('filesize_approx')
#             if filesize and filesize < TELEGRAM_MAX_FILE_SIZE and f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
#                 best_format = f
#                 break

#         if best_format:
#             filename = sanitize_filename(title)
#             filepath = os.path.join(temp_dir, filename)

#             ydl_opts_download = {
#             'format': best_format['format_id'],
#             'outtmpl': filepath,
#             'quiet': True,
#             'noplaylist': True,
#             'external_downloader': 'aria2c',  # optional
#             'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
#             # --- new timeout & retries options ---
#             'socket_timeout': 30,          # increase from default 10s
#             'retries': 10,                 # retry failed downloads
#             'continuedl': True,            # continue partially downloaded files
#             }


#             with yt_dlp.YoutubeDL(ydl_opts_download) as ydl:
#                 ydl.download([url])

#             if os.path.exists(filepath):
#                 hashtags = re.findall(r'#\w+', title)
#                 clean_title = title
#                 for tag in hashtags:
#                     clean_title = clean_title.replace(tag, '')
#                 clean_title = clean_title.strip()

#                 caption_parts = [
#                     f"🎬 <b>{clean_title}</b>",
#                     f"\n👤 <b>Channel:</b> {uploader}",
#                     f"⏱️ <b>Duration:</b> {format_duration(duration)}"
#                 ]
#                 if hashtags:
#                     hashtag_line = ' '.join([f"<code>{tag}</code>" for tag in hashtags])
#                     caption_parts.append(f"\n#️⃣ <b>Tags:</b> {hashtag_line}")
                
#                 caption = "\n".join(caption_parts)
#                 return {"status": "success", "path": filepath, "caption": caption}
#             else:
#                 return {"status": "error", "message": "Download completed but file not found."}
#         else:
#             direct_url = info.get('url')
#             if info.get('formats'):
#                 direct_url = info['formats'][-1]['url']

#             return {
#                 "status": "too_large",
#                 "title": title,
#                 "uploader": uploader,
#                 "duration": format_duration(duration),
#                 "direct_url": direct_url
#             }

#     except Exception as e:
#         logger.error(f"Error during video processing: {e}\n{traceback.format_exc()}")
#         return {"status": "error", "message": f"Could not process the link. Error: {e}"}


# # --- BOT HANDLERS ---
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     user = update.effective_user
#     welcome_message = (
#         f"Hi <b>{user.first_name}</b>! 👋\n\n"
#         "I am your personal video downloader bot.\n\n"
#         "Send me a link from <b>TikTok, YouTube, Instagram, etc.</b>, and I'll send you the video!\n\n"
#         "✨ If a video is too large for Telegram, I'll provide a direct download link."
#     )
#     await update.message.reply_text(welcome_message, parse_mode=constants.ParseMode.HTML)


# async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     url = update.message.text.strip()

#     if not re.match(r'https?://[^\s]+', url):
#         await update.message.reply_text("❌ That doesn't look like a valid URL. Please send a link starting with http or https.")
#         return

#     processing_message = await update.message.reply_text("✅ Got it! Fetching video info...")

#     with tempfile.TemporaryDirectory() as temp_dir:
#         result = process_video_url(url, temp_dir)

#         if result['status'] == 'success':
#             video_path = result['path']
#             caption = result['caption']

#             await processing_message.edit_text("⏳ Info found! Downloading and uploading to Telegram...")

#             try:
#                 with open(video_path, 'rb') as f:
#                     await context.bot.send_video(
#                         chat_id=update.effective_chat.id,
#                         video=f,
#                         caption=caption,
#                         parse_mode=constants.ParseMode.HTML,
#                         supports_streaming=True
#                     )
#                 await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)

#             except Exception as e:
#                 logger.error(f"Error sending video: {e}\n{traceback.format_exc()}")
#                 await processing_message.edit_text("❌ An unexpected error occurred while uploading the video.")

#         elif result['status'] == 'too_large':
#             message = (
#                 f"⚠️ <b>Video is Too Large!</b>\n\n"
#                 f"The video \"{result['title']}\" is too large to send directly.\n\n"
#                 f"👉 <a href='{result['direct_url']}'>Click here to download it directly</a>\n\n"
#                 f"<b>Channel:</b> {result['uploader']}\n"
#                 f"<b>Duration:</b> {result['duration']}"
#             )
#             await processing_message.edit_text(message, parse_mode=constants.ParseMode.HTML, disable_web_page_preview=True)

#         else:
#             await processing_message.edit_text(
#                 f"❌ Could not download the video.\n\nError: <code>{result['message']}</code>",
#                 parse_mode=constants.ParseMode.HTML
#             )


# # --- MAIN FUNCTION ---
# def main() -> None:
#     if TELEGRAM_TOKEN == "YOUR_TELEGRAM_TOKEN_HERE":
#         logger.error("Please replace 'YOUR_TELEGRAM_TOKEN_HERE' with your actual bot token.")
#         return

#     application = Application.builder().token(TELEGRAM_TOKEN).build()

#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

#     logger.info("Bot started and polling for messages...")
#     application.run_polling()


# if __name__ == '__main__':
#     main()

# bot.py
# bot.py

"""
An object-oriented redesign of the Telegram bot.

This design encapsulates all bot functionality within a `TelegramBot` class,
improving organization, maintainability, and scalability.
"""

import logging
import re
import textwrap
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- External Handlers & Configuration ---
# These are well-separated, so we keep them as they are.
from config import TELEGRAM_TOKEN
from document_handler import handle_word_file
from downloader import handle_url

# --- Constants & User-Facing Text ---

class BotMessages:
    """A container for all user-facing messages."""
    WELCOME = textwrap.dedent("""
        👋 Hello, <b>{user_first_name}</b>!

        I am your all-in-one media and document assistant.

        🎬 <b>Universal Media Downloader</b>
        Send me a link from many popular websites (like YouTube, TikTok, Instagram, etc.) and I'll download the media for you.

        📄 <b>Word to PDF Converter</b>
        Send a <code>.docx</code> file to convert it to a <code>.pdf</code>.
    """)

    HELP = textwrap.dedent("""
        <b>How I can help you:</b>

        ➡️ <b>To download any media:</b>
        Just paste the link and send it to me.

        ➡️ <b>To convert Word to PDF:</b>
        Attach and send a <code>.docx</code> file.
    """)

    UNKNOWN = "I'm not sure what to do with that. Please send me a valid link or a .docx file."

# --- Core Bot Class ---

class TelegramBot:
    """
    The main class for the Telegram Bot.

    This class encapsulates the application, handlers, and the main run loop.
    """
    # A simple regex to find any URL in a message
    URL_REGEX = re.compile(r'(https?://[^\s]+)', re.IGNORECASE)

    def __init__(self, token: str):
        """Initializes the bot, sets up logging, and registers handlers."""
        if not token or token == "YOUR_TELEGRAM_TOKEN_HERE":
            raise ValueError("Telegram token is not configured. Please set it in config.py.")
        
        self.logger = self._setup_logging()
        self.application = Application.builder().token(token).build()
        self._register_handlers()
        self.logger.info("Bot initialized successfully.")

    def _setup_logging(self) -> logging.Logger:
        """Configures the logging for the application."""
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        return logging.getLogger(__name__)

    def _register_handlers(self) -> None:
        """Registers all command, message, and error handlers for the bot."""
        # Command Handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Message Handlers
        # Handler for .docx files (document conversion)
        self.application.add_handler(MessageHandler(
            filters.Document.FileExtension("docx"), 
            handle_word_file
        ))
        
        # Handler for any message containing a URL (media downloader)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(self.URL_REGEX), 
            handle_url
        ))

        # Handler for any other text that isn't a command or a URL
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.unknown_text
        ))
        self.logger.info("All handlers have been registered.")

    def run(self) -> None:
        """Starts the bot's polling loop."""
        self.logger.info("Bot is starting up...")
        self.application.run_polling()
        
    # --- Handler Methods ---
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a welcome message when the /start command is issued."""
        user = update.effective_user
        await update.message.reply_html(
            BotMessages.WELCOME.format(user_first_name=user.first_name)
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Sends a help message when the /help command is issued."""
        await update.message.reply_html(BotMessages.HELP)

    async def unknown_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles text that doesn't match any other defined handler."""
        await update.message.reply_text(BotMessages.UNKNOWN)


# --- Main Execution ---

def main() -> None:
    """The main entry point for the script."""
    try:
        bot = TelegramBot(token=TELEGRAM_TOKEN)
        bot.run()
    except ValueError as e:
        logging.getLogger(__name__).fatal(f"FATAL: {e}")
    except Exception as e:
        logging.getLogger(__name__).fatal(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == '__main__':
    main()