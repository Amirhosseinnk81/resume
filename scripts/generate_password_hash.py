"""
Generate a new ADMIN_PASSWORD_HASH value for .env.

Usage:
    python scripts/generate_password_hash.py

Prompts for a new password (hidden input) and prints the hash to paste
into .env as ADMIN_PASSWORD_HASH=<value>. The plaintext password is never
stored anywhere — only the hash goes in .env.
"""

import getpass

from werkzeug.security import generate_password_hash


def main():
    password = getpass.getpass("New admin password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords didn't match — nothing generated.")
        return

    if len(password) < 8:
        print("Warning: that's a short password. Consider something longer.")

    print()
    print("Paste this into .env:")
    print(f"ADMIN_PASSWORD_HASH={generate_password_hash(password)}")


if __name__ == "__main__":
    main()
