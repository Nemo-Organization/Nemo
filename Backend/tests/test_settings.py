import pytest
from pydantic import ValidationError

from app.settings import Settings


@pytest.mark.parametrize(
    "origin", ["*", "https://user:password@example.com", "https://example.com/path", "file:///tmp"]
)
def test_settings_reject_non_origin_values(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, public_app_origin=origin)


def test_origin_is_normalized_for_exact_comparison():
    settings = Settings(_env_file=None, public_app_origin="https://example.com/")

    assert settings.public_app_origin == "https://example.com"


def test_settings_hide_model_and_database_secrets():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:private-password@localhost/guardian",
        ai_api_key="private-model-key",
    )

    assert "private-password" not in repr(settings)
    assert "private-model-key" not in repr(settings)


def test_database_configuration_rejects_an_unexpected_driver():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite:///local.db")


def test_hold_deadline_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, hold_ttl_seconds=0)
