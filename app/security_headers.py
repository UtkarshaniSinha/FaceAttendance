"""Security headers added to every response.

They are instructions to the browser:
- Content-Security-Policy: only load scripts, styles and images from this site
  (blob: is needed for the photo preview). Injected scripts will not run.
- X-Frame-Options / frame-ancestors: no other site may show this app in a frame
  (stops "clickjacking", where a hidden frame tricks you into clicking buttons).
- X-Content-Type-Options: the browser must not guess file types.
- Referrer-Policy: other sites are not told which page you came from.
- Permissions-Policy: only this site may use the camera; microphone and location are off.
"""

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' blob: data:",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
}


def add_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response
