from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import GOOGLE_CREDENTIALS_FILE, DELEGATED_ADMIN_EMAIL


ADMIN_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.group.member",
]

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
]


def _build_credentials(scopes: list[str]):
    if not DELEGATED_ADMIN_EMAIL:
        raise ValueError("DELEGATED_ADMIN_EMAIL não configurado no .env")

    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=scopes,
    )
    return credentials.with_subject(DELEGATED_ADMIN_EMAIL)


def get_directory_service():
    delegated_credentials = _build_credentials(ADMIN_SCOPES)
    return build("admin", "directory_v1", credentials=delegated_credentials)


def get_gmail_service():
    delegated_credentials = _build_credentials(GMAIL_SCOPES)
    return build("gmail", "v1", credentials=delegated_credentials)