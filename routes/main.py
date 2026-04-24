"""Main route handlers."""
from flask import Blueprint, render_template


main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def home():
    """Render the main chat interface."""
    return render_template("index.html")
