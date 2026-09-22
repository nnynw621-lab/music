import logging
import os
import shutil
import sys


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("railway-start")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required Railway variable is missing: {name}")
    return value


def main() -> None:
    # Validate configuration before importing the bot so Railway logs the real cause.
    require_env("CREATOR_BOT_TOKEN")
    require_env("API_ID")
    require_env("API_HASH")
    require_env("DEV_ID")

    try:
        int(os.environ["API_ID"])
        int(os.environ["DEV_ID"])
    except ValueError as exc:
        raise RuntimeError("API_ID and DEV_ID must be integers") from exc

    if not shutil.which("ffmpeg"):
        log.warning("ffmpeg was not found; audio conversion may fail")

    # Railway volumes are mounted at /data. The fallback keeps local runs working.
    data_dir = os.getenv("DATA_DIR", "/data")
    if not os.path.isdir(data_dir) or not os.access(data_dir, os.W_OK):
        data_dir = os.getcwd()
    os.makedirs(data_dir, exist_ok=True)
    os.chdir(data_dir)
    os.environ.setdefault("DATABASE_PATH", os.path.join(data_dir, "bot_maker.db"))

    log.info("Starting creator bot from %s", data_dir)
    os.execv(sys.executable, [sys.executable, os.path.join(os.path.dirname(__file__), "bot.py")])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Smart Railway startup validation failed")
        raise
