# import csv
# import logging
# from datetime import datetime
# from collections import defaultdict
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import (
#     ApplicationBuilder,
#     CommandHandler,
#     ContextTypes,
#     CallbackQueryHandler,
# )

# # --- Configuration ---
# TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # <-- PASTE YOUR BOT TOKEN HERE
# FILE_NAME = "finance_records.csv" # Renamed for clarity

# # Enable logging
# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# # --- Data Handling Functions ---

# def add_record(amount: float, note: str = ""):
#     """Appends a new record to the CSV. Positive for income, negative for payment."""
#     date_str = datetime.now().strftime("%Y-%m-%d")
#     with open(FILE_NAME, mode="a", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerow([date_str, amount, note])
#     logger.info(f"Added record: {date_str}, {amount}, {note}")

# def load_records():
#     """Reads all records from the CSV file and returns them as a list."""
#     records = []
#     try:
#         with open(FILE_NAME, mode="r", newline="", encoding="utf-8") as f:
#             reader = csv.reader(f)
#             for row in reader:
#                 if row:
#                     # Ensure amount is stored as float for calculations
#                     records.append([row[0], float(row[1]), row[2]])
#     except FileNotFoundError:
#         logger.info(f"'{FILE_NAME}' not found. It will be created on the first entry.")
#     return records

# def delete_last_record():
#     """Deletes the most recent entry from the CSV file."""
#     records = load_records()
#     if not records:
#         return False
    
#     last_record = records.pop()
    
#     with open(FILE_NAME, mode="w", newline="", encoding="utf-8") as f:
#         writer = csv.writer(f)
#         writer.writerows(records)
    
#     logger.info(f"Deleted record: {last_record}")
#     return last_record

# # --- Telegram Command Handlers ---

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handler for the /start command. Welcomes the user."""
#     # ⭐ UPDATED: Added /pay command
#     welcome_message = (
#         "👋 *Welcome to your Personal Finance Tracker!*\n\n"
#         "Track your income and expenses with ease.\n\n"
#         "**Available Commands:**\n"
#         "💰 `/add <amount> [note]`\n"
#         "   _Log income. Ex: `/add 1500 Salary`_\n\n"
#         "💸 `/pay <amount> [note]`\n"
#         "   _Log a payment/expense. Ex: `/pay 75 Groceries`_\n\n"
#         "☀️ `/today`\n"
#         "   _See a summary for today._\n\n"
#         "📊 `/summary`\n"
#         "   _Get a full summary by month, year, or all time._\n\n"
#         "🗑️ `/delete`\n"
#         "   _Remove the last entry you made._\n\n"
#         "❓ `/help`\n"
#         "   _Show this message again._"
#     )
#     await update.message.reply_text(welcome_message, parse_mode="Markdown")

# async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handler for the /help command."""
#     await start(update, context)

# async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handler for the /add command (Income)."""
#     try:
#         amount = abs(float(context.args[0])) # Ensure positive
#         note = " ".join(context.args[1:])
        
#         add_record(amount, note)
        
#         # ⭐ UPDATED: Show Net total for today
#         records = load_records()
#         today_str = datetime.now().strftime("%Y-%m-%d")
#         today_net = sum(r[1] for r in records if r[0] == today_str)
        
#         await update.message.reply_text(
#             f"✅ Income added: `{amount:,.2f}`.\n"
#             f"Today's Net Total is now `{today_net:,.2f}`.",
#             parse_mode="Markdown"
#         )
#     except (IndexError, ValueError):
#         await update.message.reply_text("⚠️ *Invalid format!* Use: `/add <amount> [note]`", parse_mode="Markdown")

# # ⭐ NEW: Handler for the /pay command (Expenses)
# async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handler for the /pay command (Expenses)."""
#     try:
#         # Store payments as a negative number
#         amount = -abs(float(context.args[0]))
#         note = " ".join(context.args[1:])
        
#         add_record(amount, note)

#         # Show Net total for today
#         records = load_records()
#         today_str = datetime.now().strftime("%Y-%m-%d")
#         today_net = sum(r[1] for r in records if r[0] == today_str)

#         await update.message.reply_text(
#             f"✅ Payment added: `{abs(amount):,.2f}`.\n"
#             f"Today's Net Total is now `{today_net:,.2f}`.",
#             parse_mode="Markdown"
#         )
#     except (IndexError, ValueError):
#         await update.message.reply_text("⚠️ *Invalid format!* Use: `/pay <amount> [note]`", parse_mode="Markdown")


# # ⭐ UPDATED: /today command now shows income, payments, and net total
# async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Shows a detailed summary of today's transactions."""
#     today_str = datetime.now().strftime("%Y-%m-%d")
#     records = load_records()
    
#     today_records = [rec for rec in records if rec[0] == today_str]
    
#     if not today_records:
#         await update.message.reply_text(f"No transactions recorded for today, {today_str}.")
#         return

#     income_total = sum(rec[1] for rec in today_records if rec[1] > 0)
#     payment_total = sum(rec[1] for rec in today_records if rec[1] < 0)
#     net_total = income_total + payment_total

#     message = f"☀️ *Summary for Today ({today_str})*\n\n"
#     message += f"💰 *Income:* `{income_total:,.2f}`\n"
#     message += f"💸 *Payments:* `{abs(payment_total):,.2f}`\n"
#     message += "--------------------\n"
#     message += f"📊 *Net Total:* `{net_total:,.2f}`"
    
#     await update.message.reply_text(message, parse_mode="Markdown")


# async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handler for the /summary command. Shows interactive buttons."""
#     keyboard = [
#         [
#             InlineKeyboardButton("This Month", callback_data="summary_month"),
#             InlineKeyboardButton("This Year", callback_data="summary_year"),
#         ],
#         [InlineKeyboardButton("All Time", callback_data="summary_all")],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.reply_text("📊 Which period would you like a summary for?", reply_markup=reply_markup)


# # ⭐ UPDATED: /delete now specifies transaction type
# async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Asks for confirmation before deleting the last entry."""
#     records = load_records()
#     if not records:
#         await update.message.reply_text("There are no records to delete.")
#         return

#     last_record = records[-1]
#     date, amount, note = last_record[0], last_record[1], last_record[2]
    
#     # Determine if it was income or payment
#     transaction_type = "💰 Income" if amount > 0 else "💸 Payment"
    
#     text = (
#         f"Are you sure you want to delete this last entry?\n\n"
#         f"📝 *Type:* {transaction_type}\n"
#         f"📅 *Date:* `{date}`\n"
#         f"💰 *Amount:* `{abs(amount):,.2f}`\n"
#         f"🗒️ *Note:* `{note or 'N/A'}`"
#     )
    
#     keyboard = [
#         [
#             InlineKeyboardButton("✅ Yes, Delete", callback_data="delete_confirm"),
#             InlineKeyboardButton("❌ Cancel", callback_data="delete_cancel"),
#         ]
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# # ⭐ UPDATED: Button handler now calculates and displays full summary
# async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """Handles button presses for summaries and deletions."""
#     query = update.callback_query
#     await query.answer()

#     command = query.data

#     if command.startswith("summary_"):
#         records = load_records()
#         if not records:
#             await query.edit_message_text(text="No records yet. Use `/add` or `/pay` to start!")
#             return

#         period = command.split("_")[1]
#         now = datetime.now()
        
#         # Filter records based on the selected period
#         if period == "month":
#             title = f"📊 *Summary for {now.strftime('%B %Y')}*"
#             filtered_records = [r for r in records if datetime.strptime(r[0], "%Y-%m-%d").strftime("%Y-%m") == now.strftime("%Y-%m")]
#         elif period == "year":
#             title = f"📊 *Summary for {now.strftime('%Y')}*"
#             filtered_records = [r for r in records if datetime.strptime(r[0], "%Y-%m-%d").strftime("%Y") == now.strftime("%Y")]
#         else: # All time
#             title = "📊 *All Time Summary*"
#             filtered_records = records
        
#         if not filtered_records:
#             await query.edit_message_text(text=f"No transactions found for this period.")
#             return
            
#         income = sum(r[1] for r in filtered_records if r[1] > 0)
#         payments = sum(r[1] for r in filtered_records if r[1] < 0)
#         net = income + payments
        
#         msg = f"{title}\n\n"
#         msg += f"💰 *Total Income:* `{income:,.2f}`\n"
#         msg += f"💸 *Total Payments:* `{abs(payments):,.2f}`\n"
#         msg += "--------------------\n"
#         msg += f"📊 *Net Total:* `{net:,.2f}`"
        
#         await query.edit_message_text(text=msg, parse_mode="Markdown")

#     elif command == "delete_confirm":
#         deleted_record = delete_last_record()
#         if deleted_record:
#             amount = deleted_record[1]
#             await query.edit_message_text(text=f"🗑️ Entry for `{abs(amount):,.2f}` has been deleted.", parse_mode="Markdown")
#         else:
#             await query.edit_message_text(text="Could not delete the entry.")

#     elif command == "delete_cancel":
#         await query.edit_message_text(text="❌ Deletion cancelled.")


# # --- Main Bot Setup ---
# if __name__ == "__main__":
#     print("Bot is starting...")
    
#     app = ApplicationBuilder().token(TOKEN).build()
    
#     # Register command handlers
#     app.add_handler(CommandHandler("start", start))
#     app.add_handler(CommandHandler("help", help_command))
#     app.add_handler(CommandHandler("add", add))
#     app.add_handler(CommandHandler("pay", pay)) # ⭐ NEW: Register /pay command
#     app.add_handler(CommandHandler("today", today))
#     app.add_handler(CommandHandler("summary", summary))
#     app.add_handler(CommandHandler("delete", delete))
#     app.add_handler(CallbackQueryHandler(button_handler))
    
#     print("Polling for messages...")
#     app.run_polling()