"""Tests for the booking module."""

from unittest.mock import MagicMock, patch

import pytest

from src.book import find_class, get_tomorrow, login
from src.config import Config


@pytest.fixture()
def config() -> Config:
    return Config(email="test@example.com", password="secret")


SAMPLE_CLASSES = [
    {"id": "1", "className": "CrossFit", "timeid": "0930"},
    {"id": "2", "className": "WOD", "timeid": "1130"},
    {"id": "3", "className": "Open Box", "timeid": "0930"},
    {"id": "4", "className": "CrossFit", "timeid": "1200"},
]


class TestFindClass:
    def test_finds_matching_class(self) -> None:
        result = find_class(SAMPLE_CLASSES, "CrossFit", "0930")
        assert result is not None
        assert result["id"] == "1"

    def test_case_insensitive_match(self) -> None:
        result = find_class(SAMPLE_CLASSES, "crossfit", "0930")
        assert result is not None
        assert result["id"] == "1"

    def test_no_match_wrong_time(self) -> None:
        result = find_class(SAMPLE_CLASSES, "CrossFit", "0900")
        assert result is None

    def test_no_match_wrong_name(self) -> None:
        result = find_class(SAMPLE_CLASSES, "Yoga", "0930")
        assert result is None

    def test_empty_classes(self) -> None:
        result = find_class([], "CrossFit", "0930")
        assert result is None

    def test_partial_name_match(self) -> None:
        classes = [{"id": "5", "className": "CrossFit Training", "timeid": "0930"}]
        result = find_class(classes, "CrossFit", "0930")
        assert result is not None
        assert result["id"] == "5"

    def test_alternative_field_names(self) -> None:
        classes = [{"id": "6", "name": "CrossFit", "time": "0930"}]
        result = find_class(classes, "CrossFit", "0930")
        assert result is not None
        assert result["id"] == "6"


class TestGetTomorrow:
    @patch("src.book.datetime")
    def test_returns_next_day(self, mock_dt: MagicMock) -> None:
        from datetime import datetime

        mock_dt.now.return_value = datetime(2026, 2, 14, 22, 30)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = get_tomorrow()
        assert result == "2026-02-15"


class TestLogin:
    def test_login_raises_on_no_cookies(self, config: Config) -> None:
        session = MagicMock()
        session.cookies = {}
        response = MagicMock()
        response.status_code = 200
        response.text = "Invalid credentials"
        response.raise_for_status = MagicMock()
        session.post.return_value = response

        with pytest.raises(RuntimeError, match="Login failed"):
            login(session, config)

    def test_login_succeeds_with_cookies(self, config: Config) -> None:
        session = MagicMock()
        session.cookies = {"session_id": "abc123"}
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        session.post.return_value = response

        login(session, config)  # Should not raise

        session.post.assert_called_once_with(
            config.login_url,
            data={"mail": "test@example.com", "pw": "secret"},
            headers={"Referer": config.base_url},
        )


class TestConfig:
    def test_default_values(self, config: Config) -> None:
        assert config.box_name == "crossboxelfaro"
        assert config.box_id == "407431"
        assert config.class_time == "0930"
        assert config.class_name == "CrossFit"

    def test_urls(self, config: Config) -> None:
        assert config.base_url == "https://crossboxelfaro.aimharder.com"
        assert config.login_url == "https://crossboxelfaro.aimharder.com/login"
        assert config.bookings_url == "https://crossboxelfaro.aimharder.com/api/bookings"
        assert config.book_url == "https://crossboxelfaro.aimharder.com/api/book"

    @patch.dict(
        "os.environ",
        {"AIMHARDER_EMAIL": "a@b.com", "AIMHARDER_PASSWORD": "pw"},
    )
    def test_load_config_from_env(self) -> None:
        from src.config import load_config

        cfg = load_config()
        assert cfg.email == "a@b.com"
        assert cfg.password == "pw"

    @patch.dict("os.environ", {}, clear=True)
    def test_load_config_missing_env_raises(self) -> None:
        from src.config import load_config

        with pytest.raises(ValueError, match="AIMHARDER_EMAIL"):
            load_config()
