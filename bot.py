# bot.py
import logging
import re
import textwrap
import asyncio
import sys

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

from config import TELEGRAM_TOKEN
from document_handler import handle_word_file
from downloader import handle_url

class BotMessages:
    """Container for all user-facing messages."""
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


class TelegramBot:
    """Main class for the Telegram Bot."""
    URL_REGEX = re.compile(r'(https?://[^\s]+)', re.IGNORECASE)

    def __init__(self, token: str):
        if not token or token == "YOUR_TELEGRAM_TOKEN_HERE":
            raise ValueError("Telegram token is not configured. Please set it in config.py.")

        self.logger = self._setup_logging()
        self.application = Application.builder().token(token).build()
        self._register_handlers()
        self.logger.info("Bot initialized successfully.")

    def _setup_logging(self) -> logging.Logger:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        return logging.getLogger(__name__)

    def _register_handlers(self) -> None:
        """Registers command, message, and error handlers."""
        # Command Handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Document Handler (.docx)
        self.application.add_handler(MessageHandler(
            filters.Document.FileExtension("docx"), 
            handle_word_file
        ))

        # URL Handler
        self.application.add_handler(MessageHandler(
            filters.Regex(self.URL_REGEX) & ~filters.COMMAND, 
            handle_url
        ))

        # Unknown Text Handler
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.unknown_text
        ))

        # Error Handler
        self.application.add_error_handler(self.error_handler)
        self.logger.info("All handlers have been registered.")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Logs errors."""
        self.logger.error(f"Update {update} caused error {context.error}", exc_info=True)

    async def clear_pending_updates(self):
        """Clears old updates to prevent 409 Conflict."""
        updates = await self.application.bot.get_updates(offset=-1)
        if updates:
            self.logger.info(f"Cleared {len(updates)} pending updates.")

    def run(self) -> None:
        """Starts the bot's polling loop safely."""
        self.logger.info("Bot is starting up...")

        # Fix for Python 3.10+ on Windows
        if sys.platform.startswith("win") and sys.version_info >= (3, 10):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Clear pending updates before polling
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.clear_pending_updates())

        # Start polling (manages its own event loop)
        self.application.run_polling()

    # --- Command Handlers ---
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        await update.message.reply_html(
            BotMessages.WELCOME.format(user_first_name=user.first_name)
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_html(BotMessages.HELP)

    async def unknown_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(BotMessages.UNKNOWN)


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
