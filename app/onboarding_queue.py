from pathlib import Path
from datetime import datetime

import pandas as pd


QUEUE_COLUMNS = [
    "message_id",
    "email",
    "groups",
    "status",
    "attempts",
    "created_at",
    "processed_at",
]

TEXT_COLUMNS = [
    "message_id",
    "email",
    "groups",
    "status",
    "created_at",
    "processed_at",
]


def ensure_queue_file_exists(queue_file: Path) -> None:
    if not queue_file.exists():
        df = pd.DataFrame(columns=QUEUE_COLUMNS)
        df.to_csv(queue_file, index=False, encoding="utf-8-sig")


def load_queue(queue_file: Path) -> pd.DataFrame:
    ensure_queue_file_exists(queue_file)

    df = pd.read_csv(queue_file, dtype=str)

    for column in QUEUE_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[QUEUE_COLUMNS]

    for column in TEXT_COLUMNS:
        df[column] = df[column].fillna("").astype(str)

    df["attempts"] = pd.to_numeric(df["attempts"], errors="coerce").fillna(0).astype(int)

    return df


def save_queue(df: pd.DataFrame, queue_file: Path) -> None:
    df.to_csv(queue_file, index=False, encoding="utf-8-sig")


def onboarding_exists(df: pd.DataFrame, message_id: str) -> bool:
    if df.empty:
        return False

    return str(message_id) in df["message_id"].astype(str).values


def pending_email_exists(df: pd.DataFrame, email: str) -> bool:
    if df.empty:
        return False

    filtered = df[
        (df["email"].astype(str).str.lower() == str(email).lower())
        & (df["status"].astype(str).str.lower() == "pending")
    ]

    return not filtered.empty


def email_already_finished(df: pd.DataFrame, email: str) -> bool:
    if df.empty:
        return False

    filtered = df[
        (df["email"].astype(str).str.lower() == str(email).lower())
        & (df["status"].astype(str).str.lower() == "done")
    ]

    return not filtered.empty


def add_onboarding_to_queue(
    queue_file: Path,
    message_id: str,
    email: str,
    groups: list[str],
) -> bool:
    df = load_queue(queue_file)

    if onboarding_exists(df, message_id):
        return False

    if pending_email_exists(df, email):
        return False

    if email_already_finished(df, email):
        return False

    now = datetime.now().isoformat()

    new_row = pd.DataFrame(
        [
            {
                "message_id": str(message_id),
                "email": str(email),
                "groups": ";".join(groups),
                "status": "pending",
                "attempts": 0,
                "created_at": now,
                "processed_at": "",
            }
        ]
    )

    df = pd.concat([df, new_row], ignore_index=True)
    save_queue(df, queue_file)

    return True


def get_pending_records(queue_file: Path) -> list[dict]:
    df = load_queue(queue_file)

    if df.empty:
        return []

    pending_df = df[df["status"] == "pending"]
    return pending_df.to_dict(orient="records")


def update_record_status(
    queue_file: Path,
    message_id: str,
    status: str,
    attempts: int | None = None,
    processed_at: str | None = None,
) -> None:
    df = load_queue(queue_file)

    mask = df["message_id"].astype(str) == str(message_id)
    df.loc[mask, "status"] = str(status)

    if attempts is not None:
        df.loc[mask, "attempts"] = int(attempts)

    if processed_at is not None:
        df.loc[mask, "processed_at"] = str(processed_at)

    save_queue(df, queue_file)