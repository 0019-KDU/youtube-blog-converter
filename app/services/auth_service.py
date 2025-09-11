import logging

from flask import g, request, session
from flask_jwt_extended import decode_token

from app.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for handling user authentication across the app"""

    @staticmethod
    def get_current_user():
        """Get current user from various authentication sources"""
        user_model = None
        try:
            token = None

            # Check Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

            # Check session for token
            if not token:
                token = session.get("access_token")

            # Check user_id directly in session as fallback
            if not token:
                user_id = session.get("user_id")
                if user_id:
                    user_model = User()
                    current_user = user_model.get_user_by_id(user_id)
                    if current_user:
                        g.user_id = str(current_user["_id"])
                        return current_user

            if token:
                try:
                    decoded_token = decode_token(token)
                    current_user_id = decoded_token.get("sub")

                    if current_user_id:
                        user_model = User()
                        current_user = user_model.get_user_by_id(
                            current_user_id)
                        if current_user:
                            g.user_id = str(current_user["_id"])
                            return current_user
                except Exception:
                    session.pop("access_token", None)

            return None

        except Exception as e:
            logger.error(
                "Error getting current user",
                extra={
                    "event": "user_authentication_error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            return None
        finally:
            if user_model:
                user_model = None

    @staticmethod
    def is_authenticated():
        """Check if current user is authenticated"""
        return AuthService.get_current_user() is not None

    @staticmethod
    def clear_session():
        """Clear user session"""
        session.clear()
