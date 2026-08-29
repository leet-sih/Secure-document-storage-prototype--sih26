"""Password hashing — bcrypt cost and 72-byte cap."""

import pytest

from app.core.security import hash_password, verify_password


def test_hash_and_verify() -> None:
    h = hash_password("ChangeMe!2345")
    assert h != "ChangeMe!2345"
    assert verify_password("ChangeMe!2345", h)
    assert not verify_password("wrong-password", h)


def test_reject_over_72_bytes() -> None:
    with pytest.raises(ValueError):
        hash_password("A" * 73)
