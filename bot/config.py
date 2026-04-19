import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN fehlt in der .env")
