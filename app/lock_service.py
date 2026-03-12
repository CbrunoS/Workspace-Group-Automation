from pathlib import Path


def acquire_lock(lock_file: Path) -> bool:
    if lock_file.exists():
        return False

    lock_file.write_text("running", encoding="utf-8")
    return True


def release_lock(lock_file: Path) -> None:
    if lock_file.exists():
        lock_file.unlink()