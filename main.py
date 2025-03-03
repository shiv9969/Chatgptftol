import os
import pymongo
from flask import Flask, send_file
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ───── ENV VARIABLES ─────
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
FQDN = os.getenv("FQDN", "https://your-default-domain.com")  # Set your public domain in Render!

# ───── INITIALIZE BOT ─────
bot = Client(
    "FileBot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# ───── MONGODB ─────
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["telegram_file_bot"]
files_collection = db["files"]
users_collection = db["users"]

# ───── FLASK APP ─────
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# Route to serve files
@app.route("/download/<file_id>")
def serve_file(file_id):
    file_data = files_collection.find_one({"file_id": file_id})
    if not file_data:
        return "File not found!", 404
    
    file_path = file_data.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return "File not found on server!", 404
    
    # You can set as_attachment=False if you want the browser to try streaming instead of downloading
    return send_file(file_path, as_attachment=True)

def run_flask():
    # Debug print for your FQDN
    print(f"FQDN in Flask: {FQDN}")
    app.run(host="0.0.0.0", port=10000)

# ───── PYROGRAM HANDLERS ─────

@bot.on_message(filters.command("start"))
def start_handler(client, message):
    args = message.command
    user_id = message.from_user.id
    
    # Store user info
    user_data = {"user_id": user_id, "username": message.from_user.username}
    users_collection.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)

    # If there's a file_id argument, try to send that file
    if len(args) > 1:
        file_id = args[1]
        file_data = files_collection.find_one({"file_id": file_id})
        if file_data:
            client.send_document(
                chat_id=message.chat.id,
                document=file_id,
                caption=file_data["file_name"]
            )
        else:
            message.reply_text("⚠️ File not found in database!")
    else:
        message.reply_text(
            "✅ Bot is alive!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Stats", callback_data="stats")]
            ])
        )

@bot.on_callback_query()
def callback_handler(client, callback_query):
    if callback_query.data == "stats":
        user_count = users_collection.count_documents({})
        file_count = files_collection.count_documents({})
        callback_query.message.reply_text(
            f"📊 Total Users: {user_count}\n"
            f"📂 Total Files: {file_count}"
        )

# Use filters.media to catch all media types (photo, video, document, audio, etc.)
@bot.on_message(filters.media)
def media_handler(client, message):
    media = None
    file_name = None

    # Identify which type of media
    if message.document:
        media = message.document
    elif message.video:
        media = message.video
    elif message.audio:
        media = message.audio
    elif message.photo:
        media = message.photo  # Photos have no "file_name", we can set a default

    if not media:
        return  # Not a supported media type

    file_id = media.file_id
    file_name = getattr(media, "file_name", None) or "UnnamedFile.jpg"

    # Create a local path to store the file
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)
    file_path = f"{download_dir}/{file_id}"

    # Download the file locally
    print(f"Downloading file_id: {file_id} as '{file_path}'...")
    client.download_media(message, file_path)

    # Build a public link using FQDN
    file_link = f"{FQDN}/download/{file_id}"
    print(f"Generated file link: {file_link}")

    # Store in MongoDB
    files_collection.update_one(
        {"file_id": file_id},
        {"$set": {
            "file_name": file_name,
            "file_path": file_path
        }},
        upsert=True
    )

    # Send buttons
    buttons = [
        [InlineKeyboardButton("▶️ Stream", url=file_link)],
        [InlineKeyboardButton("📥 Download", url=file_link)],
        [InlineKeyboardButton("🔗 Get File Link", url=file_link)]
    ]

    message.reply_text(
        f"**File:** {file_name}\n📥 [Download File]({file_link})",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

# ───── MAIN ─────
if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run()
