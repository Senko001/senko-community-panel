from itsdangerous import URLSafeSerializer
import os
from dotenv import load_dotenv

load_dotenv()

SESSION_SECRET = os.getenv("SESSION_SECRET", "fallback_secret")
serializer = URLSafeSerializer(SESSION_SECRET, salt="senko-dashboard")

def create_session(data: dict) -> str:
    return serializer.dumps(data)

def read_session(token: str) -> dict:
    return serializer.loads(token)
