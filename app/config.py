import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GOOGLE_CREDENTIALS_PATH = Path(
    os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials/service-account.json")
)
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
GOOGLE_WORKSHEET_NAME = os.environ.get("GOOGLE_WORKSHEET_NAME", "Sheet1")
SCHEDULE_TIME = os.environ.get("SCHEDULE_TIME", "03:00")
