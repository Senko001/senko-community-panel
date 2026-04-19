import os
from dotenv import load_dotenv

load_dotenv()

OWNER_ROLE_ID = os.getenv("OWNER_ROLE_ID")
TEAMLEITER_ROLE_ID = os.getenv("TEAMLEITER_ROLE_ID")
ADMIN_ROLE_ID = os.getenv("ADMIN_ROLE_ID")

def get_user_level(role_ids: list[str]) -> str:
    role_ids = [str(r) for r in role_ids]

    if OWNER_ROLE_ID and OWNER_ROLE_ID in role_ids:
        return "owner"
    if TEAMLEITER_ROLE_ID and TEAMLEITER_ROLE_ID in role_ids:
        return "teamleiter"
    if ADMIN_ROLE_ID and ADMIN_ROLE_ID in role_ids:
        return "admin"
    return "member"

def can_access_dashboard(level: str) -> bool:
    return level in ["owner", "teamleiter", "admin"]

def can_moderate(level: str) -> bool:
    return level in ["owner", "teamleiter", "admin"]

def can_manage_roles(level: str) -> bool:
    return level in ["owner", "teamleiter", "admin"]

def can_manage_warns(level: str) -> bool:
    return level in ["owner", "teamleiter", "admin"]
