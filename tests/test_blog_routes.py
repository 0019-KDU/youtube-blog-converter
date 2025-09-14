import io
import json
import sys
import types
import pytest
from flask import Flask

# -----------------------------------------------------------------------------
# Pre-stub external modules that may not exist so importing the routes works.
# This prevents ImportError at import time and allows later monkeypatching.
# -----------------------------------------------------------------------------

# app.services.auth_service
if "app.services.auth_service" not in sys.modules:
    mod = types.ModuleType("app.services.auth_service")
    class _Auth:
        @staticmethod
        def get_current_user():
            return {"_id": "507f1f77bcf86cd799439011", "username": "tester"}
    mod.AuthService = _Auth
    sys.modules["app.services.auth_service"] = mod

# app.utils.security
if "app.utils.security" not in sys.modules:
    mod = types.ModuleType("app.utils.security")
    def store_large_data(namespace, data, user_id):
        return f"{namespace}:{user_id}:k"
    def retrieve_large_data(namespace, user_id):
        return None
    mod.store_large_data = store_large_data
    mod.retrieve_large_data = retrieve_large_data
    sys.modules["app.utils.security"] = mod

# app.utils.validators
if "app.utils.validators" not in sys.modules:
    mod = types.ModuleType("app.utils.validators")
    mod.extract_video_id = lambda url: "ABCDEFGHIJK"
    mod.sanitize_filename = lambda s: s
    mod.validate_youtube_url = lambda url: True
    sys.modules["app.utils.validators"] = mod

# app.crew.tools
if "app.crew.tools" not in sys.modules:
    mod = types.ModuleType("app.crew.tools")
    class _PDF:
        def generate_pdf_bytes(self, content: str) -> bytes:
            return b"%PDF-1.4\n"
    mod.PDFGeneratorTool = _PDF
    sys.modules["app.crew.tools"] = mod

# Now import the module under test
import app.routes.blog as blog_module


@pytest.fixture()
def app(monkeypatch):
    """Create a minimal Flask app and register the blog blueprint."""
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test-secret", TESTING=True)

    # Avoid failures due to missing templates or routes by stubbing render_template/url_for
    monkeypatch.setattr(blog_module, "render_template", lambda template, **ctx: f"rendered:{template}")
    monkeypatch.setattr(
        blog_module,
        "url_for",
        lambda endpoint, **values: "/login" if endpoint == "auth.login" else f"/{endpoint}",
    )

    # Default: user is authenticated; tests can override per-case
    class _Auth:
        @staticmethod
        def get_current_user():
            return {"_id": "507f1f77bcf86cd799439011", "username": "tester"}

    monkeypatch.setattr(blog_module, "AuthService", _Auth)

    # Default validators and storage helpers
    monkeypatch.setattr(blog_module, "validate_youtube_url", lambda url: True)
    monkeypatch.setattr(blog_module, "extract_video_id", lambda url: "ABCDEFGHIJK")
    # Sanitize: replace slashes and spaces with dash
    monkeypatch.setattr(
        blog_module,
        "sanitize_filename",
        lambda s: s.replace("/", "-").replace("\\", "-").replace(" ", "-").strip(),
    )

    # Default storage helpers
    storage = {}

    def _store_large_data(namespace, data, user_id):
        key = f"{namespace}:{user_id}:k"
        storage[key] = data
        return key

    def _retrieve_large_data(namespace, user_id):
        return storage.get(f"{namespace}:{user_id}:k")

    monkeypatch.setattr(blog_module, "store_large_data", _store_large_data)
    monkeypatch.setattr(blog_module, "retrieve_large_data", _retrieve_large_data)

    # Default PDF generator
    class _PDF:
        def generate_pdf_bytes(self, content: str) -> bytes:
            return b"%PDF-1.4\n%Test PDF bytes\n"

    monkeypatch.setattr(blog_module, "PDFGeneratorTool", _PDF)

    # Default BlogPost model stub
    class _BlogPost:
        def create_post(self, user_id, youtube_url, title, content, video_id):
            return {
                "_id": "60f5a3b6e3b6a2c9e8d1a001",
                "user_id": str(user_id),
                "youtube_url": youtube_url,
                "title": title,
                "content": content,
                "video_id": video_id,
            }

        def get_user_posts(self, user_id, limit=50, skip=0):
            return [
                {
                    "_id": "60f5a3b6e3b6a2c9e8d1a001",
                    "user_id": str(user_id),
                    "title": "Post 1",
                    "content": "Content",
                    "video_id": "ABCDEFGHIJK",
                }
            ]

        def get_post_by_id(self, post_id, user_id=None):
            return {
                "_id": str(post_id),
                "user_id": str(user_id or "507f1f77bcf86cd799439011"),
                "title": "A/Title for PDF",
                "content": "# Title\n\nBody text for PDF.",
            }

        def delete_post(self, post_id, user_id):
            return True

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPost)

    # Register blueprint
    app.register_blueprint(blog_module.blog_bp)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


# -------------------- Index --------------------

def test_index_success(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "rendered:index.html"


def test_index_error_render_template_failure(app, client, monkeypatch):
    # Force render failure to hit except block
    monkeypatch.setattr(blog_module, "render_template", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("tpl fail")))
    resp = client.get("/")
    assert resp.status_code == 500
    assert "Error loading page" in resp.get_data(as_text=True)


# -------------------- Generate page --------------------

def test_generate_page_redirect_when_unauth(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.get("/generate-page")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_generate_page_success(client):
    resp = client.get("/generate-page")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "rendered:generate.html"


def test_generate_page_error_path(client, monkeypatch):
    def mock_render_template(*args, **kwargs):
        if args[0] == "generate.html":
            raise RuntimeError("boom")
        elif args[0] == "error.html":
            return f"Error loading generate page: boom"
        return "default"

    monkeypatch.setattr(blog_module, "render_template", mock_render_template)
    resp = client.get("/generate-page")
    assert resp.status_code == 500
    assert "Error loading generate page" in resp.get_data(as_text=True)


# -------------------- Generate blog --------------------

def test_generate_blog_auth_required(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/x", "language": "en"})
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["success"] is False and "Authentication required" in data["message"]


def test_generate_blog_empty_url(client):
    resp = client.post("/generate", json={"youtube_url": "  ", "language": "en"})
    assert resp.status_code == 400
    assert resp.get_json()["message"] == "YouTube URL is required"


def test_generate_blog_invalid_url(client, monkeypatch):
    monkeypatch.setattr(blog_module, "validate_youtube_url", lambda _url: False)
    resp = client.post("/generate", json={"youtube_url": "not-a-url", "language": "en"})
    assert resp.status_code == 400
    assert "valid YouTube URL" in resp.get_json()["message"]


def test_generate_blog_extract_id_fail(client, monkeypatch):
    monkeypatch.setattr(blog_module, "extract_video_id", lambda _url: None)
    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/abc", "language": "en"})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_generate_blog_generation_exception(client, monkeypatch):
    # Cause the generator to raise
    def _raise(url, lang):
        raise RuntimeError("gen failed")

    monkeypatch.setattr(blog_module, "generate_blog_from_youtube", _raise)
    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/abc", "language": "en"})
    assert resp.status_code == 500
    assert "Failed to generate blog" in resp.get_json()["message"]


def test_generate_blog_content_too_short(client, monkeypatch):
    monkeypatch.setattr(blog_module, "generate_blog_from_youtube", lambda *_: "short content")
    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/abc", "language": "en"})
    assert resp.status_code == 500
    assert "Failed to generate blog content" in resp.get_json()["message"]


def test_generate_blog_error_prefix(client, monkeypatch):
    # Make the error message long enough to pass the length check but still start with ERROR:
    long_error = "ERROR: Something bad happened during processing and we need to make this error message long enough to pass the 100 character minimum length check that happens first in the code"
    monkeypatch.setattr(blog_module, "generate_blog_from_youtube", lambda *_: long_error)
    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/abc", "language": "en"})
    assert resp.status_code == 500
    assert resp.get_json()["message"] == "Something bad happened during processing and we need to make this error message long enough to pass the 100 character minimum length check that happens first in the code"


def test_generate_blog_db_error_raises_top_level(client, monkeypatch):
    # Success content but make DB save raise
    content = "# A Valid Title\n\n" + ("word " * 200)

    class _BlogPostErr:
        def create_post(self, *a, **k):
            raise RuntimeError("db failure")

    monkeypatch.setattr(blog_module, "generate_blog_from_youtube", lambda *_: content)
    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostErr)
    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/abc", "language": "en"})
    assert resp.status_code == 500
    assert "Error generating blog" in resp.get_json()["message"]


def test_generate_blog_success_json_and_session(client, monkeypatch):
    content = "# My Blog Title\n\n" + ("body " * 200)
    monkeypatch.setattr(blog_module, "generate_blog_from_youtube", lambda *_: content)

    resp = client.post("/generate", json={"youtube_url": "https://youtu.be/abc", "language": "en"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["title"] == "My Blog Title"
    assert data["video_id"] == "ABCDEFGHIJK"
    assert data["word_count"] > 100

    # Validate session keys were stored
    with client.session_transaction() as sess:
        assert "blog_storage_key" in sess
        assert "blog_created" in sess


# -------------------- Dashboard --------------------

def test_dashboard_requires_auth(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_dashboard_success(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "rendered:dashboard.html"


def test_dashboard_db_error_returns_empty_posts(client, monkeypatch):
    class _BlogPostBad:
        def get_user_posts(self, *_a, **_k):
            raise RuntimeError("db read fail")

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostBad)
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    # Still renders dashboard even if posts retrieval fails
    assert "rendered:dashboard.html" in resp.get_data(as_text=True)


# -------------------- Download PDF from session --------------------

def test_download_pdf_unauth_redirect(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.get("/download")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_download_pdf_no_data_returns_404(client):
    # Ensure no storage key is present
    with client.session_transaction() as sess:
        sess.clear()
    resp = client.get("/download")
    assert resp.status_code == 404
    assert resp.get_json()["message"].startswith("No blog data")


def test_download_pdf_success(client):
    # Pre-store blog data for current user and set the session key
    key = blog_module.store_large_data(
        "current_blog",
        {"blog_content": "# Title\n\nBody", "title": "A/Title for PDF"},
        "507f1f77bcf86cd799439011",
    )
    with client.session_transaction() as sess:
        sess["blog_storage_key"] = key
    resp = client.get("/download")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    # Sanitized filename should replace slash and spaces with '-'
    cd = resp.headers.get("Content-Disposition", "")
    assert "filename=A-Title-for-PDF_blog.pdf" in cd or "filename=\"A-Title-for-PDF_blog.pdf\"" in cd


# -------------------- Delete post --------------------

def test_delete_post_requires_auth(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.delete("/delete-post/123")
    assert resp.status_code == 401


def test_delete_post_success(client):
    resp = client.delete("/delete-post/60f5a3b6e3b6a2c9e8d1a001")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_delete_post_not_found(client, monkeypatch):
    class _BlogPostNF:
        def delete_post(self, *_a, **_k):
            return False

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostNF)
    resp = client.delete("/delete-post/60f5a3b6e3b6a2c9e8d1a009")
    assert resp.status_code == 404


def test_delete_post_db_error_returns_500(client, monkeypatch):
    class _BlogPostErr:
        def delete_post(self, *_a, **_k):
            raise RuntimeError("db delete fail")

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostErr)
    resp = client.delete("/delete-post/60f5a3b6e3b6a2c9e8d1a009")
    assert resp.status_code == 500
    assert resp.get_json()["success"] is False


# -------------------- Get post --------------------

def test_get_post_requires_auth(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.get("/get-post/60f5a3b6e3b6a2c9e8d1a001")
    assert resp.status_code == 401


def test_get_post_success(client):
    resp = client.get("/get-post/60f5a3b6e3b6a2c9e8d1a001")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["post"]["title"] == "A/Title for PDF"


def test_get_post_not_found(client, monkeypatch):
    class _BlogPostNF:
        def get_post_by_id(self, *_a, **_k):
            return None

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostNF)
    resp = client.get("/get-post/60f5a3b6e3b6a2c9e8d1a002")
    assert resp.status_code == 404


def test_get_post_db_error_returns_500(client, monkeypatch):
    class _BlogPostErr:
        def get_post_by_id(self, *_a, **_k):
            raise RuntimeError("db read fail")

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostErr)
    resp = client.get("/get-post/60f5a3b6e3b6a2c9e8d1a002")
    assert resp.status_code == 500


# -------------------- Download Post PDF --------------------

def test_download_post_pdf_requires_auth(client, monkeypatch):
    class _Auth:
        @staticmethod
        def get_current_user():
            return None

    monkeypatch.setattr(blog_module, "AuthService", _Auth)
    resp = client.get("/download-post/60f5a3b6e3b6a2c9e8d1a001")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_download_post_pdf_not_found(client, monkeypatch):
    class _BlogPostNF:
        def get_post_by_id(self, *_a, **_k):
            return None

    monkeypatch.setattr(blog_module, "BlogPost", _BlogPostNF)
    resp = client.get("/download-post/60f5a3b6e3b6a2c9e8d1a099")
    assert resp.status_code == 404


def test_download_post_pdf_success(client):
    resp = client.get("/download-post/60f5a3b6e3b6a2c9e8d1a001")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"
    cd = resp.headers.get("Content-Disposition", "")
    assert "filename=A-Title-for-PDF_blog.pdf" in cd or "filename=\"A-Title-for-PDF_blog.pdf\"" in cd


def test_download_post_pdf_generator_failure(client, monkeypatch):
    class _PDFBad:
        def generate_pdf_bytes(self, *_a, **_k):
            raise RuntimeError("pdf gen fail")

    monkeypatch.setattr(blog_module, "PDFGeneratorTool", _PDFBad)
    resp = client.get("/download-post/60f5a3b6e3b6a2c9e8d1a001")
    assert resp.status_code == 500
    assert "PDF generation failed" in resp.get_json()["message"]


# -------------------- Contact --------------------

def test_contact_success(client):
    resp = client.get("/contact")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "rendered:contact.html"


def test_contact_error(client, monkeypatch):
    def mock_render_template(*args, **kwargs):
        if args[0] == "contact.html":
            raise RuntimeError("boom")
        elif args[0] == "error.html":
            return f"Error loading contact page: boom"
        return "default"

    monkeypatch.setattr(blog_module, "render_template", mock_render_template)
    resp = client.get("/contact")
    assert resp.status_code == 500
    assert "Error loading contact page" in resp.get_data(as_text=True)
