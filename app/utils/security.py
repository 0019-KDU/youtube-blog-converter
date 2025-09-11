import logging

from flask import current_app, g, request, session
from flask_jwt_extended import decode_token

logger = logging.getLogger(__name__)


def get_current_user():
    """Get current user from various authentication sources"""
    from app.models.user import User

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
                    current_user = user_model.get_user_by_id(current_user_id)
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


def inject_config():
    """Make config available in templates"""
    return dict(config=current_app.config)


def inject_user():
    """Inject current user into all templates"""
    current_user = get_current_user()
    return dict(current_user=current_user, user_logged_in=current_user is not None)


def store_large_data(key, data, user_id=None):
    """Store large data outside of session to avoid cookie size limits"""
    import time

    storage_key = f"{user_id}_{key}" if user_id else key
    current_app.temp_storage[storage_key] = {"data": data, "timestamp": time.time()}

    # Clean old data (older than 1 hour)
    cleanup_old_storage()

    logger.debug(f"Stored large data with key: {storage_key}")
    return storage_key


def retrieve_large_data(key, user_id=None):
    """Retrieve large data from temporary storage"""
    import time

    storage_key = f"{user_id}_{key}" if user_id else key
    stored_item = current_app.temp_storage.get(storage_key)
    if stored_item:
        # Check if data is not too old (1 hour)
        if time.time() - stored_item["timestamp"] < 3600:
            logger.debug(f"Retrieved large data with key: {storage_key}")
            return stored_item["data"]
        else:
            # Remove expired data
            current_app.temp_storage.pop(storage_key, None)
            logger.debug(f"Removed expired data with key: {storage_key}")
    return None


def cleanup_old_storage():
    """Clean up old temporary storage data"""
    import time

    current_time = time.time()
    expired_keys = []
    for key, item in current_app.temp_storage.items():
        if current_time - item["timestamp"] > 3600:  # 1 hour
            expired_keys.append(key)

    for key in expired_keys:
        current_app.temp_storage.pop(key, None)

    if expired_keys:
        logger.info(f"Cleaned up {len(expired_keys)} expired storage items")
