# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- REQUIRED ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- BOT SETTINGS ---
TELEGRAM_MAX_FILE_SIZE = int(os.getenv("TELEGRAM_MAX_FILE_SIZE", 49 * 1024 * 1024))  # default 49 MB
# FACEBOOK_COOKIES_FILE = os.getenv("FACEBOOK_COOKIES_FILE", "facebook_cookies.txt")
