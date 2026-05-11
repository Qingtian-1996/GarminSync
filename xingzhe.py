"""Xingzhe (行者) client for uploading activities."""
import base64
import logging
import os
import re

import requests
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)

_LOGIN_PAGE_URL = "https://www.imxingzhe.com/user/login"
_LOGIN_API_URL = "https://www.imxingzhe.com/api/v4/account/login"
_UPLOAD_URL = "https://www.imxingzhe.com/api/v4/upload_fits"

# Xingzhe error code for a duplicate activity (already uploaded).
_ERR_DUPLICATE = 9007


class XingzheClient:
    """Client for interacting with Xingzhe (行者)."""

    def __init__(self):
        try:
            self.username = os.environ["XINGZHE_USERNAME"]
            self.password = os.environ["XINGZHE_PASSWORD"]
        except KeyError as exc:
            raise RuntimeError(
                f"Missing required environment variable {exc}. "
                "Set XINGZHE_USERNAME and XINGZHE_PASSWORD in your .env file or GitHub Secrets."
            ) from exc
        self._session = requests.Session()

    def login(self):
        """Log in to Xingzhe using RSA-encrypted credentials."""
        response = self._session.get(_LOGIN_PAGE_URL)
        response.raise_for_status()

        match = re.search(
            r'<textarea[^>]+id="pubkey"[^>]*>(.*?)</textarea>',
            response.text,
            re.DOTALL,
        )
        if not match:
            raise RuntimeError("Failed to retrieve RSA public key from Xingzhe login page")

        rd_cookie = response.cookies.get("rd", "")
        # Xingzhe requires the password to be combined with the "rd" session cookie
        # value before RSA encryption, as an extra authentication challenge.
        safe_password = self.password + ";" + rd_cookie
        recipient_key = RSA.import_key(match.group(1))
        cipher = PKCS1_v1_5.new(recipient_key)
        encrypted_password = base64.b64encode(
            cipher.encrypt(safe_password.encode())
        ).decode()

        payload = {
            "account": self.username,
            "password": encrypted_password,
            "source": "web",
        }
        resp = self._session.post(_LOGIN_API_URL, json=payload)
        resp.raise_for_status()
        content = resp.json()
        if content.get("res") != 1:
            raise RuntimeError(
                "Xingzhe login failed: " + content.get("error_message", "unknown error")
            )
        logger.info("Logged in to Xingzhe as %s", self.username)

    def upload_activity(self, fit_data: bytes, title: str) -> dict:
        """Upload a FIT activity to Xingzhe.

        :param fit_data: Raw FIT file bytes.
        :param title: Activity title shown on Xingzhe.
        :return: JSON response dict from Xingzhe.
        :raises RuntimeError: If the upload fails.
        """
        files = {
            "upload_file_name": (title + ".fit", fit_data, "application/octet-stream")
        }
        data = {"title": title}
        response = self._session.post(_UPLOAD_URL, data=data, files=files)
        content = response.json()

        if response.status_code == 400 and content.get("code") == _ERR_DUPLICATE:
            logger.info("Activity '%s' already exists on Xingzhe, skipping.", title)
            return content

        if response.status_code != 200 or "serverId" not in content:
            raise RuntimeError(
                f"Failed to upload activity '{title}' to Xingzhe: {response.text}"
            )

        logger.info(
            "Uploaded activity '%s' to Xingzhe (serverId: %s)",
            title,
            content.get("serverId"),
        )
        return content
