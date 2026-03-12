from pathlib import Path
from datetime import datetime
import pandas as pd


HISTORY_COLUMNS = [
    "timestamp",
    "message_id",
    "email",
    "group",
    "status",
    "message",
]


def ensure_history_file_exists(history_file: Path) -> None:
    if not history_file.exists():
        df = pd.DataFrame(columns=HISTORY_COLUMNS)
        df.to_csv(history_file, index=False, encoding="utf-8-sig")


def load_history(history_file: Path) -> pd.DataFrame:
    ensure_history_file_exists(history_file)
    df = pd.read_csv(history_file)

    for column in HISTORY_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df[HISTORY_COLUMNS]


def append_history_record(
    history_file: Path,
    message_id: str,
    email: str,
    group: str,
    status: str,
    message: str,
) -> None:
    df = load_history(history_file)

    new_row = pd.DataFrame(
        [
            {
                "timestamp": datetime.now().isoformat(),
                "message_id": message_id,
                "email": email,
                "group": group,
                "status": status,
                "message": message,
            }
        ]
    )

    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(history_file, index=False, encoding="utf-8-sig")