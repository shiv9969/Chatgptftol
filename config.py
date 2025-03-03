import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "7368488558:AAFJZYQoRsnaf4v0UR2NlTRiIj6GnnbwnvY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Kissu:Kissimunda.888@cluster0.f8ssexm.mongodb.net/?retryWrites=true&w=majority")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "cbabdb3f23de6326352ef3ac26338d9c")

# Convert API_ID to int safely
try:
    API_ID = int(API_ID)
except ValueError:
    API_ID = 0  # Fallback to 0 if conversion fails
