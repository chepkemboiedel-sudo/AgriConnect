"""Convenience launcher:  python -m agriconnect

Seeds the database on first run (if empty), then starts the server at
http://127.0.0.1:8000 . For auto-reload during development use:
    python -m uvicorn agriconnect.main:app --reload --port 8000
"""
from __future__ import annotations
import os
import socket

import uvicorn

from . import config, db, seed


def _ensure_seed() -> None:
    if not os.path.exists(config.DB_PATH):
        print("No database found - seeding sample data...")
        seed.seed()
        return
    db.init_db(reset=False)
    if not db.list_tenants():
        print("Empty database - seeding sample data...")
        seed.seed()


def _free_port(preferred: int) -> int:
    """Return the preferred port if free, otherwise the next open one."""
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:  # nothing listening
                return port
    return preferred


def main() -> None:
    _ensure_seed()
    port = int(os.environ.get("AGRI_PORT", "0")) or _free_port(8000)
    base = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 48)
    print("  AgriConnect AI is running")
    print(f"  Customer chat : {base}/")
    print(f"  Staff inbox   : {base}/inbox")
    print(f"  LLM provider  : {config.PROVIDER}")
    print("  (Press CTRL+C to stop)")
    print("=" * 48 + "\n")
    uvicorn.run("agriconnect.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
