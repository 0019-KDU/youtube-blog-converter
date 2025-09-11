import io
import logging
import re
import time

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   send_file, session, url_for)

from app.crew.tools import PDFGeneratorTool
from app.models.user import BlogPost
from app.services.auth_service import AuthService
from app.services.blog_service import generate_blog_from_youtube
from app.utils.security import retrieve_large_data, store_large_data
from app.utils.validators import (extract_video_id, sanitize_filename,
                                  validate_youtube_url)

logger = logging.getLogger(__name__)

blog_bp = Blueprint("blog", __name__, template_folder="../../templates")


@blog_bp.route("/")
def index():
    """Render the main landing page"""
    try:
        logger.info("Index page accessed")
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error loading index page: {str(e)}", exc_info=True)
        return f"Error loading page: {str(e)}", 500


@blog_bp.route("/generate-page")
def generate_page():
    """Render the generate blog page"""
    try:
        current_user = AuthService.get_current_user()
        if not current_user:
            logger.warning("Unauthorized access to generate page")
            return redirect(url_for("auth.login"))

        logger.info(
            f"Generate page accessed by user: {current_user['username']}")
        return render_template("generate.html")
    except Exception as e:
        logger.error(f"Error loading generate page: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html", error=f"Error loading generate page: {str(e)}"
            ),
            500,
        )


@blog_bp.route("/generate", methods=["POST"])
def generate_blog():
    """Process YouTube URL and generate blog"""
    start_time = time.time()
    blog_model = None

    try:
        current_user = AuthService.get_current_user()
        if not current_user:
            logger.warning("Unauthorized blog generation attempt")
            return (
                jsonify({"success": False, "message": "Authentication required"}),
                401,
            )

        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            youtube_url = data.get("youtube_url", "").strip()
            language = data.get("language", "en")
        else:
            youtube_url = request.form.get("youtube_url", "").strip()
            language = request.form.get("language", "en")

        logger.info(
            f"Blog generation started for user: {
                current_user['username']}, URL: {youtube_url}")

        if not youtube_url:
            logger.warning("Blog generation failed: Empty YouTube URL")
            return (
                jsonify({"success": False, "message": "YouTube URL is required"}),
                400,
            )

        # Validate URL format
        if not validate_youtube_url(youtube_url):
            logger.warning(
                f"Blog generation failed: Invalid URL format - {youtube_url}"
            )
            return (
                jsonify(
                    {"success": False, "message": "Please enter a valid YouTube URL"}
                ),
                400,
            )

        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            logger.warning(
                f"Blog generation failed: Could not extract video ID from {youtube_url}")
            return jsonify(
                {"success": False, "message": "Invalid YouTube URL"}), 400

        logger.info(f"Video ID extracted successfully: {video_id}")

        # Track blog generation start
        # generation_start = time.time()

        # Generate blog content
        try:
            logger.info("Starting blog content generation")
            blog_content = generate_blog_from_youtube(youtube_url, language)

            logger.info(
                f"Blog content generated successfully: {
                    len(blog_content)} characters")

        except Exception as gen_error:
            logger.error(
                f"Blog generation failed: {
                    str(gen_error)}",
                exc_info=True)
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Failed to generate blog: {
                            str(gen_error)}",
                    }),
                500,
            )

        # Check if generation was successful
        if not blog_content or len(blog_content) < 100:
            logger.error(
                f"Blog generation failed: Content too short or empty ({
                    len(blog_content) if blog_content else 0} chars)")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Failed to generate blog content. Please try with a different video.",
                    }),
                500,
            )

        # Check for error responses
        if blog_content.startswith("ERROR:"):
            error_msg = blog_content.replace("ERROR:", "").strip()
            logger.error(f"Blog generation error response: {error_msg}")
            return jsonify({"success": False, "message": error_msg}), 500

        # Track successful generation
        # generation_duration = time.time() - generation_start

        # Extract title from content
        title_match = re.search(r"^#\s+(.+)$", blog_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "YouTube Blog Post"

        logger.info(f"Blog title extracted: {title}")

        # Save blog post to database
        blog_model = BlogPost()
        try:
            logger.info("Saving blog post to database")
            blog_post = blog_model.create_post(
                user_id=current_user["_id"],
                youtube_url=youtube_url,
                title=title,
                content=blog_content,
                video_id=video_id,
            )

            logger.info(f"Blog post saved successfully: {blog_post['_id']}")
        except Exception as db_error:
            logger.error(
                f"Database error creating blog post: {
                    str(db_error)}", exc_info=True)
            raise

        if not blog_post:
            logger.error("Failed to save blog post to database")
            return (
                jsonify({"success": False, "message": "Failed to save blog post"}),
                500,
            )

        generation_time = time.time() - start_time
        word_count = len(blog_content.split())

        # Store large blog data in temporary storage
        blog_data = {
            "blog_content": blog_content,
            "youtube_url": youtube_url,
            "video_id": video_id,
            "title": title,
            "generation_time": generation_time,
            "post_id": str(blog_post["_id"]),
            "word_count": word_count,
        }

        # Store in temporary storage and keep only reference in session
        storage_key = store_large_data(
            "current_blog", blog_data, str(current_user["_id"])
        )

        # Store only the storage key in session
        session["blog_storage_key"] = storage_key
        session["blog_created"] = time.time()

        logger.info(
            f"Blog generation completed successfully in {
                generation_time:.1f}s")

        return jsonify(
            {
                "success": True,
                "blog_content": blog_content,
                "generation_time": f"{generation_time:.1f}s",
                "word_count": word_count,
                "title": title,
                "video_id": video_id,
            }
        )

    except Exception as e:
        logger.error(
            f"Unexpected error during blog generation: {str(e)}", exc_info=True
        )
        return (
            jsonify({"success": False, "message": f"Error generating blog: {str(e)}"}),
            500,
        )

    finally:
        try:
            if blog_model:
                blog_model = None
        except Exception:
            pass


@blog_bp.route("/dashboard")
def dashboard():
    """User dashboard"""
    blog_model = None

    try:
        current_user = AuthService.get_current_user()

        if not current_user:
            logger.warning("Unauthorized dashboard access")
            session.clear()
            return redirect(url_for("auth.login"))

        logger.info(f"Dashboard accessed by user: {current_user['username']}")

        blog_model = BlogPost()
        try:
            posts = blog_model.get_user_posts(current_user["_id"])
            logger.info(
                f"Retrieved {
                    len(posts)} posts for user {
                    current_user['username']}")
        except Exception as db_error:
            logger.error(
                f"Database error retrieving posts: {
                    str(db_error)}", exc_info=True)
            posts = []

        return render_template(
            "dashboard.html",
            user=current_user,
            posts=posts)

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}", exc_info=True)
        session.clear()
        return redirect(url_for("auth.login"))
    finally:
        if blog_model:
            blog_model = None


@blog_bp.route("/download")
def download_pdf():
    """Generate and download PDF"""
    pdf_generator = None

    try:
        current_user = AuthService.get_current_user()
        if not current_user:
            logger.warning("Unauthorized PDF download attempt")
            return redirect(url_for("auth.login"))

        # Retrieve blog data from temporary storage
        storage_key = session.get("blog_storage_key")
        blog_data = None

        if storage_key:
            blog_data = retrieve_large_data(
                "current_blog", str(current_user["_id"]))

        if not blog_data:
            logger.warning(
                f"PDF download failed: No blog data found for user {
                    current_user['username']}")
            return (
                jsonify({"success": False, "message": "No blog data found or expired"}),
                404,
            )

        blog_content = blog_data["blog_content"]
        title = blog_data["title"]

        # Clean filename
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}_blog.pdf"

        logger.info(
            f"PDF generation started for user {
                current_user['username']}: {title}")

        # Generate PDF
        try:
            pdf_generator = PDFGeneratorTool()
            pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
            logger.info(f"PDF download completed successfully: {filename}")
        finally:
            if pdf_generator:
                pdf_generator = None

        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)

        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
        return (
            jsonify({"success": False, "message": f"PDF generation failed: {str(e)}"}),
            500,
        )
    finally:
        if pdf_generator:
            pdf_generator = None


@blog_bp.route("/delete-post/<post_id>", methods=["DELETE"])
def delete_post(post_id):
    """Delete a blog post"""
    blog_model = None

    try:
        current_user = AuthService.get_current_user()
        if not current_user:
            logger.warning(
                f"Unauthorized post deletion attempt for post {post_id}")
            return (
                jsonify({"success": False, "message": "Authentication required"}),
                401,
            )

        logger.info(
            f"Post deletion requested by user {
                current_user['username']}: {post_id}")

        blog_model = BlogPost()
        try:
            success = blog_model.delete_post(post_id, current_user["_id"])
        except Exception as db_error:
            logger.error(
                f"Database error deleting post: {str(db_error)}", exc_info=True
            )
            raise

        if success:
            logger.info(f"Post deleted successfully: {post_id}")
            return jsonify({"success": True,
                            "message": "Post deleted successfully"})
        else:
            logger.warning(f"Post not found for deletion: {post_id}")
            return jsonify(
                {"success": False, "message": "Post not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if blog_model:
            blog_model = None


@blog_bp.route("/get-post/<post_id>")
def get_post(post_id):
    """Get a specific blog post for viewing"""
    blog_model = None

    try:
        current_user = AuthService.get_current_user()
        if not current_user:
            logger.warning(
                f"Unauthorized post access attempt for post {post_id}")
            return (
                jsonify({"success": False, "message": "Authentication required"}),
                401,
            )

        logger.info(
            f"Post retrieval requested by user {
                current_user['username']}: {post_id}")

        blog_model = BlogPost()
        try:
            post = blog_model.get_post_by_id(post_id, current_user["_id"])
        except Exception as db_error:
            logger.error(
                f"Database error retrieving post: {
                    str(db_error)}", exc_info=True)
            raise

        if post:
            logger.info(f"Post retrieved successfully: {post_id}")
            return jsonify({"success": True, "post": post})
        else:
            logger.warning(f"Post not found: {post_id}")
            return jsonify(
                {"success": False, "message": "Post not found"}), 404

    except Exception as e:
        logger.error(
            f"Error retrieving post {post_id}: {
                str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if blog_model:
            blog_model = None


@blog_bp.route("/download-post/<post_id>")
def download_post_pdf(post_id):
    """Download PDF for a specific blog post"""
    pdf_generator = None
    blog_model = None

    try:
        current_user = AuthService.get_current_user()
        if not current_user:
            logger.warning(
                f"Unauthorized PDF download attempt for post {post_id}")
            return redirect(url_for("auth.login"))

        logger.info(f"PDF download requested for post: {post_id}")

        blog_model = BlogPost()
        try:
            post = blog_model.get_post_by_id(post_id, current_user["_id"])
        except Exception as db_error:
            logger.error(
                f"Database error retrieving post for PDF: {str(db_error)}",
                exc_info=True,
            )
            raise

        if not post:
            logger.warning(f"Post not found for PDF download: {post_id}")
            return jsonify(
                {"success": False, "message": "Post not found"}), 404

        blog_content = post["content"]
        title = post["title"]

        # Clean filename
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}_blog.pdf"

        logger.info(f"PDF generation started for post {post_id}: {title}")

        # Generate PDF
        try:
            pdf_generator = PDFGeneratorTool()
            pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
            logger.info(f"PDF generated successfully for post {post_id}")
        finally:
            if pdf_generator:
                pdf_generator = None

        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)

        logger.info(f"PDF download completed for post {post_id}")

        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    except Exception as e:
        logger.error(
            f"PDF generation failed for post {post_id}: {
                str(e)}", exc_info=True)
        return (
            jsonify({"success": False, "message": f"PDF generation failed: {str(e)}"}),
            500,
        )
    finally:
        if blog_model:
            blog_model = None
        if pdf_generator:
            pdf_generator = None


@blog_bp.route("/contact")
def contact():
    """Contact page"""
    try:
        logger.info("Contact page accessed")
        return render_template("contact.html")
    except Exception as e:
        logger.error(f"Error loading contact page: {str(e)}", exc_info=True)
        return (
            render_template(
                "error.html", error=f"Error loading contact page: {str(e)}"
            ),
            500,
        )
