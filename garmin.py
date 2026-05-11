"""Garmin Connect client for downloading activities."""
import logging
import os

from garminconnect import Garmin

logger = logging.getLogger(__name__)


class GarminClient:
    """Client for interacting with Garmin Connect."""

    def __init__(self):
        try:
            self.email = os.environ["GARMIN_EMAIL"]
            self.password = os.environ["GARMIN_PASSWORD"]
        except KeyError as exc:
            raise RuntimeError(
                f"Missing required environment variable {exc}. "
                "Set GARMIN_EMAIL and GARMIN_PASSWORD in your .env file or GitHub Secrets."
            ) from exc
        self._client = Garmin(email=self.email, password=self.password)

    def login(self):
        """Log in to Garmin Connect."""
        self._client.login()
        logger.info("Logged in to Garmin Connect as %s", self.email)

    def get_activities_by_date(self, startdate, enddate=None):
        """Return activities between two dates.

        :param startdate: Start date string in YYYY-MM-DD format.
        :param enddate: Optional end date string in YYYY-MM-DD format.
        :return: List of activity dicts.
        """
        return self._client.get_activities_by_date(startdate, enddate)

    def download_activity(self, activity_id):
        """Download activity as original FIT bytes.

        :param activity_id: Garmin activity ID.
        :return: Raw FIT file bytes.
        """
        return self._client.download_activity(
            activity_id,
            dl_fmt=Garmin.ActivityDownloadFormat.ORIGINAL,
        )
