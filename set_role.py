import argparse

from sqlalchemy import select

from db_config import Session
from models import User


def main():
    parser = argparse.ArgumentParser(description="Assign a role to a registered user.")
    parser.add_argument("username")
    parser.add_argument("role", choices=["admin", "editor", "user"])
    args = parser.parse_args()
    with Session() as db:
        user = db.execute(select(User).where(User.username == args.username)).scalar_one_or_none()
        if user is None:
            raise SystemExit("User not found. Start the app and register this user first.")
        user.role = args.role
        db.commit()
        print(f"{user.username} now has the '{user.role}' role.")


if __name__ == "__main__":
    main()
