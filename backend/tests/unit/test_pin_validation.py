"""Unit tests for PIN validation in auth schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import ChangePinRequest, ResetChildPinRequest


class TestChangePinRequest:
    def test_valid_request(self):
        req = ChangePinRequest(old_pin="1234", new_pin="5678")
        assert req.old_pin == "1234"
        assert req.new_pin == "5678"

    def test_new_pin_too_short(self):
        with pytest.raises(ValidationError, match="新密码至少4位"):
            ChangePinRequest(old_pin="1234", new_pin="123")

    def test_new_pin_too_long(self):
        with pytest.raises(ValidationError, match="新密码不能超过64位"):
            ChangePinRequest(old_pin="1234", new_pin="x" * 65)

    def test_new_pin_exact_min_length(self):
        req = ChangePinRequest(old_pin="1234", new_pin="abcd")
        assert req.new_pin == "abcd"

    def test_new_pin_exact_max_length(self):
        pin = "a" * 64
        req = ChangePinRequest(old_pin="1234", new_pin=pin)
        assert req.new_pin == pin


class TestResetChildPinRequest:
    def test_valid_request(self):
        req = ResetChildPinRequest(parent_pin="1234", new_child_pin="5678")
        assert req.parent_pin == "1234"
        assert req.new_child_pin == "5678"

    def test_new_child_pin_too_short(self):
        with pytest.raises(ValidationError, match="新PIN码至少4位"):
            ResetChildPinRequest(parent_pin="1234", new_child_pin="12")

    def test_new_child_pin_too_long(self):
        with pytest.raises(ValidationError, match="新PIN码不能超过64位"):
            ResetChildPinRequest(parent_pin="1234", new_child_pin="x" * 65)

    def test_new_child_pin_exact_min_length(self):
        req = ResetChildPinRequest(parent_pin="1234", new_child_pin="abcd")
        assert req.new_child_pin == "abcd"

    def test_new_child_pin_exact_max_length(self):
        pin = "a" * 64
        req = ResetChildPinRequest(parent_pin="1234", new_child_pin=pin)
        assert req.new_child_pin == pin
