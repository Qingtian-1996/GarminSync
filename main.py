"""Sync Garmin Connect activities to Xingzhe (行者).

Usage:
    python main.py

Environment variables (required):
    GARMIN_EMAIL       Garmin Connect account e-mail address
    GARMIN_PASSWORD    Garmin Connect account password
    XINGZHE_USERNAME   Xingzhe (行者) account username / phone number
    XINGZHE_PASSWORD   Xingzhe (行者) account password

Environment variables (optional):
    SYNC_DAYS          Number of past days to sync (default: 1)
"""
import logging
import os
import sys
from datetime import date, timedelta

import requests
from dotenv import load_dotenv

from garmin import GarminClient
from xingzhe import XingzheClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _sync_days() -> int:
    """Return the number of past days to look back when fetching activities."""
    try:
        return int(os.environ.get("SYNC_DAYS", "1"))
    except ValueError:
        return 1


def main():
    load_dotenv()

    garmin = GarminClient()
    xingzhe = XingzheClient()

    logger.info("Logging in to Garmin Connect …")
    garmin.login()

    logger.info("Logging in to Xingzhe …")
    xingzhe.login()

    days = _sync_days()
    start_date = (date.today() - timedelta(days=days)).isoformat()
    end_date = date.today().isoformat()
    logger.info("Fetching Garmin activities from %s to %s …", start_date, end_date)

    activities = garmin.get_activities_by_date(start_date, end_date)
    if not activities:
        logger.info("No activities found in the specified date range.")
        return

    logger.info("Found %d activity(s). Starting upload …", len(activities))
    errors = 0
    for activity in activities:
        activity_id = activity.get("activityId")
        title = activity.get("activityName") or f"Activity {activity_id}"
        try:
            logger.info("Downloading activity '%s' (id=%s) from Garmin …", title, activity_id)
            fit_data = garmin.download_activity(activity_id)
            xingzhe.upload_activity(fit_data, title)
        except (RuntimeError, requests.RequestException, OSError) as exc:
            logger.error("Failed to sync activity '%s': %s", title, exc)
            errors += 1

    if errors:
        logger.warning("Sync completed with %d error(s).", errors)
        sys.exit(1)
    else:
        logger.info("Sync completed successfully.")


if __name__ == "__main__":
    main()
