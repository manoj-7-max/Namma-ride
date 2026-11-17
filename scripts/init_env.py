#!/usr/bin/env python3
"""Create local-only credentials without overwriting an existing .env."""

import os
import secrets
from pathlib import Path


def main():
    target = Path(__file__).resolve().parents[1] / ".env"
    content = (
        "POSTGRES_DB=namma_ride\nPOSTGRES_USER=namma\n"
        f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
        f"ADMIN_API_KEY={secrets.token_urlsafe(48)}\n"
        "API_BIND_HOST=127.0.0.1\n"
    )
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit(
            ".env already exists; leaving existing credentials unchanged."
        ) from None
    with os.fdopen(descriptor, "w") as stream:
        stream.write(content)
    print("Created local .env with random secrets. Keep it out of version control.")


if __name__ == "__main__":
    main()
