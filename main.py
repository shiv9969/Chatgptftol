import os
import pymongo
from flask import Flask, send_file
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
FQDN = os.getenv("FQDN", "https://your-default-domain.com")  # Set this in Render!

# Initialize bot
bot = Client("FileBot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["telegram_file_bot"]
files_collection = db["files"]
users_collection = db["users"]

# Start Command
@bot.on_message(filters.command("start"))
def start(client, message):
    args = message.command
    user_id = message.from_user.id

    # Store user info in MongoDB
    user_data = {"user_id": user_id, "username": message.from_user.username}
    users_collection.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)

    # If a file_id is provided, fetch & send the file
    if len(args) > 1:
        file_id = args[1]
        file_data = files_collection.find_one({"file_id": file_id})
        if file_data:
            client.send_document(chat_id=message.chat.id, document=file_id, caption=file_data["file_name"])
        else:
            message.reply_text("⚠️ File not found!")
    else:
        message.reply_text("✅ Bot is alive!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Stats", callback_data="stats")]
        ]))

# Stats Command
@bot.on_message(filters.command("stats"))
def stats(client, message):
    user_count = users_collection.count_documents({})
    file_count = files_collection.count_documents({})
    message.reply_text(f"📊 Total Users: {user_count}\n📂 Total Files: {file_count}")

# File Handler
@bot.on_message(filters.document | filters.video | filters.audio)
def file_handler(client, message):
    file = message.document or message.video or message.audio
    file_id = file.file_id
    file_name = file.file_name

    # Download file to local storage
    file_path = f"downloads/{file_id}"
    os.makedirs("downloads", exist_ok=True)
    client.download_media(file, file_path)

    # Store file in MongoDB with FQDN-based URL
    file_link = f"{FQDN}/download/{file_id}"
    files_collection.update_one({"file_id": file_id}, {"$set": {"file_name": file_name, "file_path": file_path}}, upsert=True)

    buttons = [
        [InlineKeyboardButton("▶️ Stream", url=file_link)],
        [InlineKeyboardButton("📥 Download", url=file_link)],
        [InlineKeyboardButton("🔗 Get File Link", url=file_link)]
    ]

    message.reply_text(f"**File:** {file_name}\n📥 [Download File]({file_link})",
                       reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)

# Flask Web Server (for file hosting)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/download/<file_id>')
def serve_file(file_id):
    file_data = files_collection.find_one({"file_id": file_id})
    if file_data:
        return send_file(file_data["file_path"], as_attachment=True)
    return "File not found!", 404

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# Run bot and Flask server in parallel
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()
