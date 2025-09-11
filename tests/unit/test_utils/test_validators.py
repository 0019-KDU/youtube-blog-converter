import pytest
import re
from unittest.mock import Mock, patch


class TestValidators:
    """Test cases for utility validators"""
    
    def test_validate_youtube_url_valid_watch(self):
        """Test YouTube URL validation for watch URLs"""
        from app.utils.validators import validate_youtube_url
        
        valid_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'http://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'http://youtube.com/watch?v=dQw4w9WgXcQ',
        ]
        
        for url in valid_urls:
            assert validate_youtube_url(url) is True
    
    def test_validate_youtube_url_valid_youtu_be(self):
        """Test YouTube URL validation for youtu.be URLs"""
        from app.utils.validators import validate_youtube_url
        
        valid_urls = [
            'https://youtu.be/dQw4w9WgXcQ',
            'http://youtu.be/dQw4w9WgXcQ',
        ]
        
        for url in valid_urls:
            assert validate_youtube_url(url) is True
    
    def test_validate_youtube_url_invalid(self):
        """Test YouTube URL validation for invalid URLs"""
        from app.utils.validators import validate_youtube_url
        
        invalid_urls = [
            'https://www.example.com/video',
            'not-a-url',
            '',
            None,
            'https://vimeo.com/123456',
            'ftp://youtube.com/watch?v=test',
        ]
        
        for url in invalid_urls:
            assert validate_youtube_url(url) is False
    
    def test_extract_video_id_watch_url(self):
        """Test video ID extraction from watch URLs"""
        from app.utils.validators import extract_video_id
        
        test_cases = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s', 'dQw4w9WgXcQ'),
            ('https://youtube.com/watch?v=abc_123-DEF', 'abc_123-DEF'),
            ('https://m.youtube.com/watch?v=test1234567', 'test1234567'),
        ]
        
        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id
    
    def test_extract_video_id_youtu_be_url(self):
        """Test video ID extraction from youtu.be URLs"""
        from app.utils.validators import extract_video_id
        
        test_cases = [
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ?t=30', 'dQw4w9WgXcQ'),
            ('http://youtu.be/abc_123-DEF', 'abc_123-DEF'),
        ]
        
        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id
    
    def test_extract_video_id_embed_url(self):
        """Test video ID extraction from embed URLs"""
        from app.utils.validators import extract_video_id
        
        test_cases = [
            ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/embed/abc_123-DEF', 'abc_123-DEF'),
        ]
        
        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id
    
    def test_extract_video_id_shorts_url(self):
        """Test video ID extraction from shorts URLs"""
        from app.utils.validators import extract_video_id
        
        test_cases = [
            ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/shorts/abc_123-DEF', 'abc_123-DEF'),
        ]
        
        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id
    
    def test_extract_video_id_invalid_urls(self):
        """Test video ID extraction from invalid URLs"""
        from app.utils.validators import extract_video_id
        
        invalid_urls = [
            'https://www.example.com/video',
            'https://youtube.com/watch',
            'https://youtu.be/',
            '',
            None,
            'not-a-url',
        ]
        
        for url in invalid_urls:
            assert extract_video_id(url) is None
    
    def test_is_valid_email_valid(self):
        """Test email validation with valid emails"""
        from app.utils.validators import is_valid_email
        
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'test123@test-domain.com',
            'a@b.co',
        ]
        
        for email in valid_emails:
            assert is_valid_email(email) is True
    
    def test_is_valid_email_invalid(self):
        """Test email validation with invalid emails"""
        from app.utils.validators import is_valid_email
        
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'test@',
            'test.example.com',
            '',
            None,
            'test@.com',
            'test@com',
        ]
        
        for email in invalid_emails:
            assert is_valid_email(email) is False
    
    def test_is_valid_password_valid(self):
        """Test password validation with valid passwords"""
        from app.utils.validators import is_valid_password
        
        valid_passwords = [
            'password123',
            'StrongP@ssw0rd',
            'verylongpassword',
            '12345678',
        ]
        
        for password in valid_passwords:
            assert is_valid_password(password) is True
    
    def test_is_valid_password_invalid(self):
        """Test password validation with invalid passwords"""
        from app.utils.validators import is_valid_password
        
        invalid_passwords = [
            'short',
            '1234567',  # 7 characters
            '',
            None,
        ]
        
        for password in invalid_passwords:
            assert is_valid_password(password) is False

    def test_sanitize_filename_normal(self):
        """Test filename sanitization with normal filenames"""
        from app.utils.validators import sanitize_filename
        
        test_cases = [
            ("My Blog Post", "My-Blog-Post"),
            ("Test_File_Name", "Test_File_Name"),
            ("Simple", "Simple"),
            ("Multiple   Spaces", "Multiple-Spaces"),
            ("With-Hyphens-Already", "With-Hyphens-Already"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Expected '{expected}' but got '{result}' for input '{input_name}'"
    
    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters"""
        from app.utils.validators import sanitize_filename
        
        test_cases = [
            ('Blog/Post\\File', 'BlogPostFile'),
            ('Test@#$%Post', 'TestPost'),
            ('File:Name?', 'FileName'),
            ('Post|With*Chars', 'PostWithChars'),
            # The regex r"[^\w\s-]" removes dots completely
            ('File.with.dots', 'Filewithdots'),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Expected '{expected}' but got '{result}' for input '{input_name}'"

    def test_sanitize_filename_edge_cases(self):
        """Test sanitize_filename with edge cases"""
        from app.utils.validators import sanitize_filename
        
        # Test empty string
        assert sanitize_filename("") == "untitled"
        
        # Test None
        assert sanitize_filename(None) == "untitled"
        
        # Fix: Test string with only spaces - should return "untitled"
        result = sanitize_filename("   ")
        assert result == "untitled", f"Expected 'untitled' but got '{result}' for input '   '"

    
    def test_sanitize_filename_dots_handling(self):
        """Test that dots are handled correctly in filenames"""
        from app.utils.validators import sanitize_filename
        
        # Based on the actual regex pattern in your validators.py, dots are removed
        # because the pattern is r"[^\w\s-]" which excludes dots
        test_cases = [
            ("File.with.dots", "Filewithdots"),
            ("test.txt", "testtxt"),
            ("my.file.name", "myfilename"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Expected '{expected}' but got '{result}' for input '{input_name}'"
