# ✅ tests/test_main.py
import pytest
from src.main import generate_blog_from_youtube
import os

@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")


def test_generate_blog_invalid_url():
    with pytest.raises(ValueError):
        generate_blog_from_youtube("https://invalid-url.com")


def test_generate_blog_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        generate_blog_from_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_extract_video_id_valid():
    from src.main import _extract_video_id
    url = "https://www.youtube.com/watch?v=abc123xyz"
    assert _extract_video_id(url) == "abc123xyz"


def test_extract_video_id_invalid():
    from src.main import _extract_video_id
    assert _extract_video_id("https://google.com") is None


def test_is_video_related():
    from src.main import _is_video_related
    content = (
        "This video discusses the future of AI and machine learning. "
        "The speaker explains complex concepts and mentions key breakthroughs. "
        "According to experts, this transcript provides a comprehensive summary of the presentation. "
        "The presenter shares personal experiences. " * 5  # Increase content length
    )
    assert _is_video_related(content, "dummy_url") is True



def test_is_video_related_short():
    from src.main import _is_video_related
    assert not _is_video_related("Too short.", "dummy_url")