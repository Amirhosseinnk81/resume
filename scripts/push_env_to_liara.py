"""
Push the variables from a local .env to a Liara app.

    python scripts/push_env_to_liara.py --app amirhosseinnk --dry-run
    python scripts/push_env_to_liara.py --app amirhosseinnk

Values are passed straight to the `liara` CLI and are never printed, so a
long secret like ADMIN_PASSWORD_HASH cannot be mistyped and does not end up
in terminal scrollback. Only key names and a set/empty marker are shown.

Requires the Liara CLI, logged in:

    npm install -g @liara/cli
    liara login
"""

import argparse
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Everything the app reads. Anything absent from .env is reported, not sent.
EXPECTED = [
    "SECRET_KEY",
    "ADMIN_USERNAME",
    "ADMIN_PASSWORD_HASH",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_DEFAULT_SENDER",
    "CONTACT_RECIPIENT_EMAIL",
]

# Values that belong to the deployment rather than to .env.
DEPLOY_DEFAULTS = {
    "APP_ENV": "production",
}

# Without these the app runs, but badly — worth refusing to be silent about.
CRITICAL = {"SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD_HASH", "SITE_URL"}


def looks_like_a_container():
    """
    Detect being run inside the deployed container rather than on the
    developer's machine. .env is gitignored and never deployed, so running
    here finds nothing to send — and the variables belong to the platform,
    not to a container that is replaced on every deploy.
    """
    if os.path.exists("/.dockerenv"):
        return True

    try:
        with open("/proc/1/cgroup", encoding="utf-8") as handle:
            return any(
                marker in handle.read()
                for marker in ("docker", "kubepods", "containerd")
            )
    except OSError:
        return False


def read_env(path):
    """Minimal .env parser: KEY=VALUE, '#' comments, optional quotes."""
    values = {}

    if not os.path.exists(path):
        return values

    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]

            values[key] = value

    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, help="Liara app name")
    parser.add_argument(
        "--site-url",
        help="Public origin, e.g. https://amirhosseinnk.liara.run. "
        "Drives canonical tags, the sitemap, RSS and JSON-LD.",
    )
    parser.add_argument("--env-file", default=os.path.join(BASE_DIR, ".env"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without calling the CLI.",
    )
    args = parser.parse_args()

    if not os.path.exists(args.env_file):
        print(f"No .env at {args.env_file}\n", file=sys.stderr)

        if looks_like_a_container():
            print(
                "This looks like the deployed container. Two reasons that\n"
                "cannot work:\n"
                "  1. .env is gitignored, so it was never deployed here.\n"
                "  2. Environment variables belong to the Liara app, not to a\n"
                "     container that is replaced on the next deploy.\n\n"
                "Run this on your own machine instead, from the project\n"
                "directory that holds .env.",
                file=sys.stderr,
            )
        else:
            print(
                "Run this from the project directory that holds .env, or pass\n"
                "--env-file with its path. Copy .env.example to .env first if\n"
                "you have not created one.",
                file=sys.stderr,
            )
        return 1

    env = read_env(args.env_file)

    payload = {}
    missing = []

    for key in EXPECTED:
        value = env.get(key, "")
        if value:
            payload[key] = value
        else:
            missing.append(key)

    payload.update(DEPLOY_DEFAULTS)

    if args.site_url:
        payload["SITE_URL"] = args.site_url.rstrip("/")
    elif env.get("SITE_URL"):
        payload["SITE_URL"] = env["SITE_URL"].rstrip("/")
    else:
        missing.append("SITE_URL")

    print(f"Reading {args.env_file}")
    print(f"App    : {args.app}\n")

    print("Will set:")
    for key in sorted(payload):
        # SITE_URL and APP_ENV are not secret and are useful to see.
        shown = payload[key] if key in ("SITE_URL", "APP_ENV") else "<hidden>"
        print(f"  {key:<24} {shown}")

    if missing:
        print("\nMissing (nothing will be sent for these):")
        for key in missing:
            flag = "  <-- the app misbehaves without this" if key in CRITICAL else ""
            print(f"  {key}{flag}")

    if args.dry_run:
        print("\nDry run: nothing sent.")
        return 0

    if not shutil.which("liara"):
        print(
            "\nThe 'liara' CLI was not found on PATH.\n"
            "  npm install -g @liara/cli\n"
            "  liara login\n"
            "Or set these in the Liara panel by hand.",
            file=sys.stderr,
        )
        return 1

    print()
    failures = []
    for key in sorted(payload):
        result = subprocess.run(
            ["liara", "env:set", f"{key}={payload[key]}", "--app", args.app],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"  set  {key}")
        else:
            # Print only the key, never the value, even on failure.
            failures.append(key)
            print(f"  FAIL {key}: {result.stderr.strip().splitlines()[:1]}")

    if failures:
        print(f"\n{len(failures)} variable(s) failed: {', '.join(failures)}")
        return 1

    print("\nDone. Redeploy for the new values to take effect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
