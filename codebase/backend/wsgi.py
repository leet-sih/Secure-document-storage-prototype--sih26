"""
wsgi.py — app entry point.

WHAT THIS FILE DOES:
    Exposes a module-level `app` object (the Flask application from create_app()).

    Prototype dev:   flask --app wsgi run --debug
    Prototype Docker: CMD runs `flask run` against this module (see Dockerfile).
    Production later: a real WSGI server (Gunicorn) imports `wsgi:app`.

EXPORTS:
    app — the Flask application (also used by the test suite's `client` fixture).
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
