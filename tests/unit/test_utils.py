"""Unit tests for utility functions."""

from app.utils import generate_short_code, is_valid_url


class TestGenerateShortCode:
    def test_default_length(self):
        code = generate_short_code()
        assert len(code) == 6

    def test_custom_length(self):
        code = generate_short_code(length=10)
        assert len(code) == 10

    def test_alphanumeric(self):
        code = generate_short_code()
        assert code.isalnum()

    def test_unique_codes(self):
        codes = {generate_short_code() for _ in range(100)}
        assert len(codes) == 100  # extremely unlikely to collide in 100 tries


class TestIsValidUrl:
    def test_valid_https(self):
        assert is_valid_url("https://example.com") is True

    def test_valid_http(self):
        assert is_valid_url("http://example.com/path") is True

    def test_valid_with_path_and_query(self):
        assert is_valid_url("https://example.com/path?q=1&r=2") is True

    def test_rejects_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_rejects_ftp(self):
        assert is_valid_url("ftp://example.com") is False

    def test_rejects_empty_string(self):
        assert is_valid_url("") is False

    def test_rejects_random_text(self):
        assert is_valid_url("not-a-url") is False

    def test_rejects_just_scheme(self):
        assert is_valid_url("https://") is False
