import telebot
import os
import schedule
import time
import threading
from telebot import types
from keep_alive import keep_alive  # Import the keep_alive function

# --- Configuration ---
# Your credentials MUST be stored in Replit Secrets for security.
API_TOKEN = os.environ.get(8301628021:AAG4q1qq-FN0-3QX1Ze6aQPgw8E1pd8P5fI)

# A check to ensure the secret is set
if not API_TOKEN:
    raise ValueError(
        "FATAL ERROR: TELEGRAM_BOT_TOKEN must be set in Replit Secrets!")

bot = telebot.TeleBot(API_TOKEN)

# --- In-Memory User Database ---
# This dictionary tracks users who have already received a file.
# It will be cleared automatically every day.
user_usage = {}

# --- File Storage ---
FILES = {
    "coolie":
    "BQACAgUAAxkBAAMOaLIR5k7qLOZH-P-bjrBqfJ89YIwAAokaAAJdAilV__PQyYYJmlM2BA",
    # "file2": "YOUR_FILE_ID_HERE"
}


# --- Automatic Scheduler ---
def reset_daily_sessions():
    """Clears the user usage data."""
    global user_usage
    user_count = len(user_usage)
    user_usage.clear()
    print(
        f"SCHEDULER: Automatic daily reset complete. Cleared {user_count} user sessions."
    )


# Schedule the reset to happen every day at midnight UTC.
# Replit servers run on UTC time.
schedule.every().day.at("00:00").do(reset_daily_sessions)


def run_scheduler():
    """Runs the scheduler in a loop in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(1)


# --- Start Command Handler (Handles Deep Linking) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) == 1:
        bot.reply_to(
            message,
            "👋 Welcome!\n\nTo get a file, you need to use a special link from one of our channels."
        )
        return

    file_key = args[1]

    if file_key not in FILES:
        bot.reply_to(message, "❌ Invalid or expired file link.")
        return

    if user_id in user_usage:
        bot.reply_to(
            message,
            "❌ You have already claimed your one file for today's session.")
        return

    send_file_and_finalize(message, file_key)


def send_file_and_finalize(message, file_key):
    """A single function to send the file, mark usage, and kick the user."""
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id in user_usage:
        bot.send_message(
            chat_id,
            "❌ You have already claimed your one file for today's session.")
        return

    try:
        bot.send_message(chat_id, "📂 Preparing your file...")
        bot.send_document(chat_id,
                          FILES[file_key],
                          caption="✅ Here’s your requested file!")

        user_usage[user_id] = True
        bot.send_message(
            chat_id,
            "You have received your file. Access for today is now complete.")

        if message.chat.type in ["group", "supergroup"]:
            try:
                bot.kick_chat_member(chat_id, user_id)
                bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            except Exception as e:
                print(
                    f"Failed to kick user {user_id} from group {chat_id}: {e}")

    except Exception as e:
        print(f"Error in send_file_and_finalize: {e}")
        bot.send_message(chat_id,
                         "❌ An error occurred while sending the file.")


# --- Helper to get File IDs ---
@bot.message_handler(content_types=['document', 'video', 'audio'])
def get_file_id(message):
    if message.chat.type == 'private':
        file_id = ""
        if message.document:
            file_id = message.document.file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.audio:
            file_id = message.audio.file_id

        reply_text = f"New File ID Found!\n\n**ID:** `{file_id}`"
        print(reply_text)
        bot.reply_to(message, reply_text, parse_mode="Markdown")


# --- Main Bot Execution ---
if __name__ == "__main__":
    print("🤖 Bot is starting...")

    # Start the web server to keep the bot alive
   

    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    print("✔️ Automatic daily reset scheduler started.")

    # Start the bot's polling
    print("✔️ Bot is now polling for messages.")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
