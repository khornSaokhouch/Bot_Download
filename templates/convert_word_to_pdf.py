# import os
# import logging
# import tempfile
# import shutil
# import re
# import yt_dlp
# import time
# import traceback
# from telegram import Update, constants
# from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
# from docx2pdf import convert
# from pdf2docx import Converter
# from docx import Document
# from pdf2image import convert_from_path
# import pytesseract

# # --- CONFIGURATION ---
# TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8334519238:AAHBesy3H7I3PUz93n-mrKz9Rv_LSiTaDRI")
# TELEGRAM_MAX_FILE_SIZE = 49 * 1024 * 1024  # 49 MB
# KHM_FONT = 'Khmer OS'  # Default Khmer font for Word output

# # --- Set up logging ---
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# # --- HELPER FUNCTIONS ---
# def sanitize_filename(name: str) -> str:
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
#                 'format': best_format['format_id'],
#                 'outtmpl': filepath,
#                 'quiet': True,
#                 'noplaylist': True,
#                 'external_downloader': 'aria2c',
#                 'external_downloader_args': ['-x', '16', '-s', '16', '-k', '1M'],
#                 'socket_timeout': 30,
#                 'retries': 10,
#                 'continuedl': True,
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

# def pdf_to_word(pdf_file, word_file, ocr=False):
#     if not ocr:
#         cv = Converter(pdf_file)
#         cv.convert(word_file, start=0, end=None)
#         cv.close()
#     else:
#         images = convert_from_path(pdf_file)
#         doc = Document()
#         for img in images:
#             text = pytesseract.image_to_string(img, lang='khm')
#             for line in text.splitlines():
#                 paragraph = doc.add_paragraph(line)
#                 for run in paragraph.runs:
#                     run.font.name = KHM_FONT
#         doc.save(word_file)

#     # Apply Khmer font to all runs in Word
#     doc = Document(word_file)
#     for paragraph in doc.paragraphs:
#         for run in paragraph.runs:
#             run.font.name = KHM_FONT
#     doc.save(word_file)

# # --- BOT HANDLERS ---
# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     user = update.effective_user
#     welcome_message = (
#         f"Hi {user.first_name}! 👋\n\n"
#         "I can:\n"
#         "1️⃣ Convert Word (.docx) → PDF\n"
#         "2️⃣ Convert PDF → Word with full Khmer font support\n"
#         "3️⃣ Download videos from YouTube/TikTok/Instagram\n\n"
#         "Send a Word file, PDF, or video URL to get started."
#     )
#     await update.message.reply_text(welcome_message, parse_mode=constants.ParseMode.HTML)

# # --- Word to PDF ---
# async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     doc = update.message.document
#     if not doc.file_name.lower().endswith(".docx"):
#         await update.message.reply_text("❌ Please send a valid .docx Word file.")
#         return

#     temp_dir = tempfile.mkdtemp()
#     try:
#         word_path = os.path.join(temp_dir, doc.file_name)
#         pdf_path = os.path.join(temp_dir, f"{os.path.splitext(doc.file_name)[0]}.pdf")

#         await update.message.reply_text("📥 Downloading Word file...")
#         await (await context.bot.get_file(doc.file_id)).download_to_drive(word_path)

#         await update.message.reply_text("📝 Converting to PDF...")
#         convert(word_path, pdf_path)

#         await update.message.reply_text("📤 Sending PDF...")
#         with open(pdf_path, 'rb') as f:
#             await context.bot.send_document(update.effective_chat.id, f, filename=os.path.basename(pdf_path))

#         await update.message.reply_text("✅ Conversion complete!")
#     finally:
#         shutil.rmtree(temp_dir)

# # --- PDF to Word ---
# async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     doc = update.message.document
#     if not doc.file_name.lower().endswith(".pdf"):
#         await update.message.reply_text("❌ Please send a PDF file.")
#         return

#     temp_dir = tempfile.mkdtemp()
#     try:
#         pdf_path = os.path.join(temp_dir, doc.file_name)
#         word_path = os.path.join(temp_dir, f"{os.path.splitext(doc.file_name)[0]}.docx")

#         await update.message.reply_text("📥 Downloading PDF...")
#         await (await context.bot.get_file(doc.file_id)).download_to_drive(pdf_path)

#         await update.message.reply_text("📝 Converting PDF to Word...")
#         pdf_to_word(pdf_path, word_path, ocr=True)

#         await update.message.reply_text("📤 Sending Word file...")
#         with open(word_path, 'rb') as f:
#             await context.bot.send_document(update.effective_chat.id, f, filename=os.path.basename(word_path))

#         await update.message.reply_text("✅ Conversion complete!")
#     finally:
#         shutil.rmtree(temp_dir)

# # --- Video downloader ---
# async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     url = update.message.text.strip()
#     if not re.match(r'https?://[^\s]+', url):
#         await update.message.reply_text("❌ That doesn't look like a valid URL.")
#         return

#     processing_message = await update.message.reply_text("✅ Got it! Fetching video info...")

#     with tempfile.TemporaryDirectory() as temp_dir:
#         result = process_video_url(url, temp_dir)

#         if result['status'] == 'success':
#             video_path = result['path']
#             caption = result['caption']

#             await processing_message.edit_text("⏳ Downloading and uploading video...")
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
#                 logger.error(f"Error sending video: {e}")
#                 await processing_message.edit_text("❌ Error uploading video.")

#         elif result['status'] == 'too_large':
#             message = (
#                 f"⚠️ <b>Video is Too Large!</b>\n\n"
#                 f"The video \"{result['title']}\" is too large to send directly.\n\n"
#                 f"👉 <a href='{result['direct_url']}'>Click here to download</a>\n\n"
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
# def main():
#     if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
#         logger.error("Set your Telegram bot token first!")
#         return

#     app = Application.builder().token(TELEGRAM_TOKEN).build()
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(MessageHandler(filters.Document.FileExtension("docx"), handle_word))
#     app.add_handler(MessageHandler(filters.Document.FileExtension("pdf"), handle_pdf))
#     app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

#     logger.info("Bot started...")
#     app.run_polling()

# if __name__ == "__main__":
#     main()
