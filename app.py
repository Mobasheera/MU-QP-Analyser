"""
app.py
--------
Entry point for the Mumbai University Question Paper Analyzer.

Run with:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

from flask import Flask

from backend.routes import bp as main_blueprint
from config import Config, ensure_directories


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    ensure_directories()

    app.register_blueprint(main_blueprint)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
