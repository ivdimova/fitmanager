"""Configuration for AimHarder gym class booking."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Booking configuration with defaults for CrossBox El Faro."""

    email: str
    password: str
    box_name: str = "crossboxelfaro"
    box_id: str = "407431"
    class_time: str = "0930"
    class_name: str = "CrossFit"

    @property
    def base_url(self) -> str:
        return f"https://{self.box_name}.aimharder.com"

    @property
    def login_url(self) -> str:
        return f"{self.base_url}/login"

    @property
    def bookings_url(self) -> str:
        return f"{self.base_url}/api/bookings"

    @property
    def book_url(self) -> str:
        return f"{self.base_url}/api/book"


def load_config() -> Config:
    """Load configuration from environment variables."""
    email = os.environ.get("AIMHARDER_EMAIL")
    password = os.environ.get("AIMHARDER_PASSWORD")

    if not email or not password:
        raise ValueError(
            "AIMHARDER_EMAIL and AIMHARDER_PASSWORD environment variables are required"
        )

    return Config(
        email=email,
        password=password,
        box_name=os.environ.get("BOX_NAME", "crossboxelfaro"),
        box_id=os.environ.get("BOX_ID", "407431"),
        class_time=os.environ.get("CLASS_TIME", "0930"),
        class_name=os.environ.get("CLASS_NAME", "CrossFit"),
    )
