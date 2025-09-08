import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from unittest.mock import patch


@pytest.mark.e2e
class TestEndToEndWorkflows:
    """End-to-end tests for the YouTube Blog Converter application"""

    @pytest.fixture(autouse=True)
    def setup_driver(self):
        """Setup Selenium WebDriver for E2E tests"""
        # Skip E2E tests in CI unless explicitly enabled
        if not pytest.config.getoption("--run-e2e", default=False):
            pytest.skip("E2E tests skipped (use --run-e2e to enable)")

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            yield
        except Exception as e:
            pytest.skip(f"WebDriver not available: {e}")
        finally:
            if hasattr(self, "driver"):
                self.driver.quit()

    def test_user_registration_flow(self):
        """Test complete user registration flow"""
        base_url = "http://localhost:5000"

        # Navigate to registration page
        self.driver.get(f"{base_url}/auth/register")

        # Fill registration form
        username_input = self.driver.find_element(By.NAME, "username")
        email_input = self.driver.find_element(By.NAME, "email")
        password_input = self.driver.find_element(By.NAME, "password")
        submit_button = self.driver.find_element(By.TYPE, "submit")

        username_input.send_keys("e2etestuser")
        email_input.send_keys("e2etest@example.com")
        password_input.send_keys("testpassword123")
        submit_button.click()

        # Wait for redirect and verify success
        WebDriverWait(self.driver, 10).until(EC.url_contains("/auth/login"))

        assert "/auth/login" in self.driver.current_url

    def test_login_and_dashboard_access(self):
        """Test login flow and dashboard access"""
        base_url = "http://localhost:5000"

        # Mock existing user for login
        with patch("auth.models.User.find_by_username") as mock_find:
            mock_find.return_value = {
                "_id": "test_user_id",
                "username": "e2etestuser",
                "email": "e2etest@example.com",
                "password_hash": "hashed_password",
                "is_active": True,
            }

            # Navigate to login page
            self.driver.get(f"{base_url}/auth/login")

            # Fill login form
            username_input = self.driver.find_element(By.NAME, "username")
            password_input = self.driver.find_element(By.NAME, "password")
            submit_button = self.driver.find_element(By.TYPE, "submit")

            username_input.send_keys("e2etestuser")
            password_input.send_keys("testpassword123")
            submit_button.click()

            # Wait for redirect to dashboard
            WebDriverWait(self.driver, 10).until(EC.url_contains("/dashboard"))

            assert "/dashboard" in self.driver.current_url

            # Verify dashboard elements are present
            assert self.driver.find_element(By.TAG_NAME, "h1")

    def test_blog_generation_workflow(self):
        """Test complete blog generation workflow"""
        base_url = "http://localhost:5000"

        # Mock authentication and API calls
        with patch("auth.decorators.login_required") as mock_auth, patch(
            "src.tool.get_transcript_from_url"
        ) as mock_transcript, patch(
            "src.tool.generate_blog_from_transcript"
        ) as mock_blog:

            mock_auth.return_value = lambda f: f  # Bypass auth
            mock_transcript.return_value = "Sample transcript content"
            mock_blog.return_value = "# Generated Blog Content\n\nThis is test content"

            # Navigate to generation page
            self.driver.get(f"{base_url}/generate")

            # Fill the generation form
            url_input = self.driver.find_element(By.NAME, "youtube_url")
            style_select = self.driver.find_element(By.NAME, "style")
            generate_button = self.driver.find_element(By.TYPE, "submit")

            url_input.send_keys("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            style_select.send_keys("technical")
            generate_button.click()

            # Wait for generation to complete
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "blog-content"))
            )

            # Verify blog content is displayed
            blog_content = self.driver.find_element(By.CLASS_NAME, "blog-content")
            assert "Generated Blog Content" in blog_content.text

    def test_responsive_design(self):
        """Test responsive design on different screen sizes"""
        base_url = "http://localhost:5000"

        # Test mobile view
        self.driver.set_window_size(375, 667)  # iPhone 6/7/8 size
        self.driver.get(f"{base_url}/")

        # Verify mobile navigation
        mobile_nav = self.driver.find_element(By.CLASS_NAME, "navbar-toggler")
        assert mobile_nav.is_displayed()

        # Test desktop view
        self.driver.set_window_size(1920, 1080)
        self.driver.get(f"{base_url}/")

        # Verify desktop layout
        desktop_nav = self.driver.find_elements(By.CLASS_NAME, "navbar-nav")
        assert len(desktop_nav) > 0

    @pytest.mark.slow
    def test_performance_blog_generation(self):
        """Test performance of blog generation process"""
        base_url = "http://localhost:5000"

        with patch("src.tool.get_transcript_from_url") as mock_transcript, patch(
            "src.tool.generate_blog_from_transcript"
        ) as mock_blog:

            mock_transcript.return_value = "Long transcript content " * 100
            mock_blog.return_value = "# Performance Test Blog\n\n" + "Content " * 500

            self.driver.get(f"{base_url}/generate")

            start_time = time.time()

            # Fill form and submit
            url_input = self.driver.find_element(By.NAME, "youtube_url")
            url_input.send_keys("https://www.youtube.com/watch?v=performance_test")

            generate_button = self.driver.find_element(By.TYPE, "submit")
            generate_button.click()

            # Wait for completion
            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.CLASS_NAME, "blog-content"))
            )

            end_time = time.time()
            generation_time = end_time - start_time

            # Assert reasonable performance (under 60 seconds)
            assert (
                generation_time < 60
            ), f"Blog generation took too long: {generation_time}s"


def pytest_addoption(parser):
    """Add command line option for running E2E tests"""
    parser.addoption(
        "--run-e2e", action="store_true", default=False, help="Run end-to-end tests"
    )
