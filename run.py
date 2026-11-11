"""Local development entry point for FaceAttendance."""

import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    # Debug mode (auto-reload + interactive error debugger) only when asked for
    # with FLASK_DEBUG=1, because the debugger can run code from the browser.
    # The server listens on 127.0.0.1 only (this computer).
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
