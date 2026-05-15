from __future__ import annotations

import argparse
import sys

from app.domain.auth.passwords import hash_password
from app.storage.user_store import UserStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a user account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args(argv)

    store = UserStore()
    if store.get_by_username(args.username) is not None:
        print("error: username already exists", file=sys.stderr)
        return 1

    user = store.create_user(
        username=args.username,
        password_hash=hash_password(args.password),
    )
    print(user.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
