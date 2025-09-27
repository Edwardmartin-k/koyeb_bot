import telebot
import os
import schedule
import time
import threading
from telebot import types
from keep_alive import keep_alive # Import the keep_alive function

# --- Configuration ---
# This code now correctly reads the secrets from Render's Environment Variables
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID_STR = os.environ.get('ADMIN_USER_ID')

# A check to ensure the secrets are set on the server
if not API_TOKEN or not ADMIN_USER_ID_STR:
    raise ValueError("FATAL ERROR: TELEGRAM_BOT_TOKEN and ADMIN_USER_ID must be set as Environment Variables on Render.")

try:
    ADMIN_USER_ID = int(ADMIN_USER_ID_STR)
except ValueError:
    raise ValueError("FATAL ERROR: ADMIN_USER_ID must be a valid integer.")

bot = telebot.TeleBot(API_TOKEN)
user_usage = {}

# --- File Storage (Add your files here) ---
FILES = {
    "coolie": {
        "type": "single",
        "file_id": "YOUR_FILE_ID_HERE"
    },
}

# --- Automatic Daily Reset ---
def reset_user_sessions():
    global user_usage
    print("--- SCHEDULER: Resetting all user sessions... ---")
    user_usage = {}
    print("--- SESSIONS CLEARED ---")

schedule.every().day.at("00:00", "UTC").do(reset_user_sessions)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- Bot Logic (Handlers) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) == 1:
        bot.reply_to(message, "👋 Welcome! Please use a special link to get a file.")
        return
    file_key = args[1]
    if file_key not in FILES:
        bot.reply_to(message, "❌ Invalid or expired file link.")
        return
    if user_id in user_usage:
        bot.reply_to(message, "❌ You have already claimed your one file for this session.")
        return
    file_entry = FILES[file_key]
    if file_entry['type'] == 'single':
        send_file_and_finalize(message, file_key)
    elif file_entry['type'] == 'series':
        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(s_text, callback_data=f"getfile:{s_key}") for s_key, s_text in file_entry['seasons'].items()]
        markup.add(*buttons)
        bot.reply_to(message, f"🎬 Please select a season for **{file_entry['title']}**:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('getfile:'))
def handle_file_request(call):
    user_id = call.from_user.id
    file_key = call.data.split(':')[1]
    if user_id in user_usage:
        bot.answer_callback_query(call.id, "❌ You have already used your file for this session.", show_alert=True)
        return
    bot.answer_callback_query(call.id, "✅ Preparing your file...")
    season_title = FILES[file_key].get('title', file_key)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"You selected: **{season_title}**", parse_mode="Markdown")
    send_file_and_finalize(call.message, file_key)

def send_file_and_finalize(message, file_key):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if user_id in user_usage:
        # This check is slightly redundant but safe
        return
    try:
        file_id = FILES[file_key]['file_id']
        bot.send_message(chat_id, "📂 Preparing your file...")
        bot.send_document(chat_id, file_id, caption="✅ Here’s your file!")
        user_usage[user_id] = True
        bot.send_message(chat_id, "Access is now complete.")
    except Exception as e:
        print(f"Error sending file {file_key}: {e}")
        bot.send_message(chat_id, "❌ An error occurred.")

@bot.message_handler(content_types=['document', 'video', 'audio'])
def get_file_id(message):
    if message.from_user.id == ADMIN_USER_ID and message.chat.type == 'private':
        file_id = ""
        if message.document: file_id = message.document.file_id
        elif message.video: file_id = message.video.file_id
        elif message.audio: file_id = message.audio.file_id
        reply_text = f"New File ID Found!\n\n**ID:** `{file_id}`"
        print(reply_text)
        bot.reply_to(message, reply_text, parse_mode="Markdown")

# --- Main Execution ---
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    keep_alive() # Start the web server
    print("✔️ Web server started.")
    
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    print("✔️ Scheduler started.")
    
    print("✔️ Bot is now polling.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

