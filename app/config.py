from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "automation.log"

GOOGLE_CREDENTIALS_FILE = BASE_DIR / os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "credentials.json",
)
DELEGATED_ADMIN_EMAIL = os.getenv("DELEGATED_ADMIN_EMAIL")

GOOGLE_WORKSPACE_DOMAIN = "ampfy.com"

PENDING_ONBOARDINGS_FILE = DATA_DIR / "pending_onboardings.csv"
ONBOARDING_HISTORY_FILE = REPORTS_DIR / "onboarding_history.csv"

GMAIL_LABEL_PENDING = "onboarding-pendente"
GMAIL_LABEL_DONE = "onboarding-processado"
GMAIL_LABEL_IGNORED = "onboarding-ignorado"
LOCK_FILE = BASE_DIR / ".automation.lock"