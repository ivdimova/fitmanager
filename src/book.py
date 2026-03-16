"""Auto-book gym classes at CrossBox El Faro via AimHarder."""

import sys
from datetime import datetime, timedelta

import requests

from src.config import Config, load_config


def login(session: requests.Session, config: Config) -> None:
    """Log in to AimHarder and establish session cookies."""
    response = session.post(
        config.login_url,
        data={"login": "Log in", "mail": config.email, "pw": config.password},
    )
    response.raise_for_status()

    # Check for session cookie as proof of successful login
    if not session.cookies:
        body = response.text[:200]
        raise RuntimeError(f"Login failed — no session cookies set. Response: {body}")

    print("Logged in successfully")


def fetch_classes(
    session: requests.Session,
    config: Config,
    date: str,
) -> list[dict]:
    """Fetch available classes for a given date (YYYY-MM-DD)."""
    response = session.get(
        config.bookings_url,
        params={"day": date, "box": config.box_id},
    )
    if not response.ok:
        print(f"Fetch classes failed ({response.status_code}): {response.text[:300]}")
        response.raise_for_status()

    data = response.json()
    if isinstance(data, dict) and "bookings" in data:
        return data["bookings"]
    if isinstance(data, list):
        return data
    return []


def find_class(
    classes: list[dict],
    class_name: str,
    class_time: str,
) -> dict | None:
    """Find a specific class by name and time."""
    for cls in classes:
        name = cls.get("className", "") or cls.get("name", "")
        time = cls.get("timeid", "") or cls.get("time", "")
        if class_name.lower() in name.lower() and str(time) == class_time:
            return cls
    return None


def book_class(
    session: requests.Session,
    config: Config,
    class_info: dict,
    date: str,
) -> dict:
    """Book a specific class."""
    class_id = class_info.get("id", "")
    response = session.post(
        config.book_url,
        data={
            "id": class_id,
            "day": date,
            "insist": 0,
        },
    )
    response.raise_for_status()
    return response.json()


def get_tomorrow() -> str:
    """Return tomorrow's date as YYYYMMDD."""
    return (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")


def main() -> None:
    """Run the booking flow."""
    config = load_config()
    target_date = get_tomorrow()

    print(f"Booking {config.class_name} at {config.class_time} on {target_date}")

    session = requests.Session()

    login(session, config)

    classes = fetch_classes(session, config, target_date)
    if not classes:
        print(f"No classes found for {target_date}")
        sys.exit(1)

    target = find_class(classes, config.class_name, config.class_time)
    if target is None:
        print(f"Class '{config.class_name}' at {config.class_time} not found on {target_date}")
        sys.exit(1)

    print(f"Found class: {target.get('className', target.get('name', 'unknown'))}")

    result = book_class(session, config, target, target_date)

    error = result.get("error")
    if error:
        print(f"Booking failed: {error}")
        sys.exit(1)

    print(f"Booked successfully! Response: {result}")


if __name__ == "__main__":
    main()
