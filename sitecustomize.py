"""Load YouTube cookies securely from Railway environment variables.

Set YOUTUBE_COOKIES_B64 in Railway to a base64-encoded Netscape cookies.txt
file. No cookie content is stored in the repository.
"""
import atexit
import base64
import os
import tempfile

import yt_dlp

_cookie_path = None


def _cookie_file_from_environment():
    global _cookie_path
    encoded = os.getenv("YOUTUBE_COOKIES_B64", "").strip()
    if not encoded:
        return None

    try:
        contents = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError("YOUTUBE_COOKIES_B64 is not valid base64") from exc

    if not contents:
        raise RuntimeError("YOUTUBE_COOKIES_B64 is empty")

    handle = tempfile.NamedTemporaryFile(
        mode="wb", prefix="yt-cookies-", suffix=".txt", delete=False
    )
    try:
        handle.write(contents)
        handle.flush()
    finally:
        handle.close()

    os.chmod(handle.name, 0o600)
    _cookie_path = handle.name
    return _cookie_path


_cookie_path = _cookie_file_from_environment()
_original_youtube_dl = yt_dlp.YoutubeDL


class SecureYoutubeDL(_original_youtube_dl):
    def __init__(self, params=None):
        params = dict(params or {})
        if _cookie_path and not params.get("cookiefile"):
            params["cookiefile"] = _cookie_path
        super().__init__(params)


yt_dlp.YoutubeDL = SecureYoutubeDL


def _remove_cookie_file():
    if _cookie_path:
        try:
            os.remove(_cookie_path)
        except FileNotFoundError:
            pass


atexit.register(_remove_cookie_file)
