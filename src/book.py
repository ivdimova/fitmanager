"""Auto-book gym classes at CrossBox El Faro via AimHarder."""

import sys
from datetime import datetime, timedelta
from http.cookiejar import Cookie
from urllib.parse import urlparse

import requests

from src.config import Config, load_config


def _copy_cookies_to_subdomain(session: requests.Session, subdomain: str) -> None:
    """Copy session cookies to the box subdomain so they're sent with API calls."""
    target_domain = urlparse(subdomain).hostname
    if not target_domain:
        return

    for cookie in list(session.cookies):
        if cookie.domain != target_domain:
            session.cookies.set_cookie(
                Cookie(
                    version=cookie.version,
                    name=cookie.name,
                    value=cookie.value,
                    port=cookie.port,
                    port_specified=cookie.port_specified,
                    domain=target_domain,
                    domain_specified=True,
                    domain_initial_dot=target_domain.startswith("."),
                    path=cookie.path,
                    path_specified=cookie.path_specified,
                    secure=cookie.secure,
                    expires=cookie.expires,
                    discard=cookie.discard,
                    comment=cookie.comment,
                    comment_url=cookie.comment_url,
                    rest=cookie._rest,
                    rfc2109=cookie.rfc2109,
                )
            )


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

    # Cookies from aimharder.com may not be sent to crossboxelfaro.aimharder.com
    # unless explicitly scoped to .aimharder.com — copy them to the subdomain.
    _copy_cookies_to_subdomain(session, config.base_url)

    print(f"Login status: {response.status_code}")
    cookie_domains = {c.domain for c in session.cookies}
    print(f"Cookie domains: {cookie_domains}")
    print("Logged in successfully")


def fetch_classes(
    session: requests.Session,
    config: Config,
    date: str,
) -> list[dict]:
    """Fetch available classes for a given date (YYYYMMDD)."""
    url = config.bookings_url
    params = {"day": date, "box": config.box_id}
    print(f"Fetching classes: GET {url} params={params}")
    response = session.get(url, params=params)

    print(f"Fetch status: {response.status_code}")
    print(f"Fetch Content-Type: {response.headers.get('Content-Type')}")
    print(f"Fetch body (first 500 chars): {response.text[:500]}")

    if not response.ok:
        response.raise_for_status()

    if not response.text.strip():
        raise RuntimeError("API returned empty response — likely not authenticated.")

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
    session.headers.update({
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    })
    if config.proxy:
        session.proxies = {"https": config.proxy, "http": config.proxy}
        print(f"Using proxy: yes")

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
