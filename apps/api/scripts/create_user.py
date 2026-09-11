"""Create a user.

The only thing in the system that assigns a role. That is what keeps the rule
true that no client can choose its own: there is no HTTP route to create a
user, so an operator with database access is the only way one appears.

    python scripts/create_user.py manager@fleet.example "Morgan Reed" fleet_manager

The password is read from a prompt unless --password is given, so it stays out
of the shell history. It is never logged, and never printed back.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from app.auth.passwords import PasswordTooLongError, hash_password  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.models import User, UserRole  # noqa: E402
from app.repositories import user as user_repository  # noqa: E402

MIN_PASSWORD_LENGTH = 8


def main() -> int:
    args = parse_args()

    password = args.password or prompt_for_password()
    if len(password) < MIN_PASSWORD_LENGTH:
        return fail(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    try:
        password_hash = hash_password(password)
    except PasswordTooLongError as exc:
        return fail(str(exc))

    email = args.email.strip().lower()

    with Session(get_engine()) as session:
        if user_repository.get_by_email(session, email) is not None:
            # Checked here for a readable message; the unique index is what
            # actually guarantees it.
            return fail(f"A user with the email {email} already exists.")

        user = User(
            email=email,
            full_name=args.full_name.strip(),
            password_hash=password_hash,
            role=args.role,
        )
        session.add(user)
        session.commit()

        print(f"Created {user.role} {user.email} (id {user.id})")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument("full_name")
    parser.add_argument("role", choices=[role.value for role in UserRole])
    parser.add_argument(
        "--password",
        help=(
            "The password. Omit it to be prompted, which keeps it out of your "
            "shell history."
        ),
    )
    return parser.parse_args()


def prompt_for_password() -> str:
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords did not match.")
    return password


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
