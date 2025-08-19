# document_handler.py

import os
import logging
import tempfile
from telegram import Update
from telegram.ext import ContextTypes

# We only need the docx2pdf library now
from docx2pdf import convert

logger = logging.getLogger(__name__)

# --- Handler for .docx files ---
async def handle_word_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Converts a received .docx file to .pdf."""
    doc = update.message.document
    if not doc.file_name.lower().endswith(".docx"):
        await update.message.reply_text("This doesn't seem to be a .docx file.")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        word_path = os.path.join(temp_dir, doc.file_name)
        pdf_path = os.path.join(temp_dir, f"{os.path.splitext(doc.file_name)[0]}.pdf")
        
        status_message = await update.message.reply_text("📥 Downloading Word file...")
        
        try:
            file = await context.bot.get_file(doc.file_id)
            await file.download_to_drive(word_path)
            
            await status_message.edit_text("🔄 Converting to PDF...")
            convert(word_path, pdf_path)
            
            if not os.path.exists(pdf_path):
                raise FileNotFoundError("PDF conversion failed, output file not found.")

            await status_message.edit_text("📤 Uploading PDF...")
            with open(pdf_path, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=pdf_file,
                    filename=os.path.basename(pdf_path)
                )
            await status_message.delete()
        
        except Exception as e:
            logger.error(f"Error in handle_word_file: {e}")
            await status_message.edit_text(f"❌ An error occurred during conversion: {e}")