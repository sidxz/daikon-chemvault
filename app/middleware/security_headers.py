# Security and no-cache headers on every response, matching DAIKON's SecurityHeadersMiddleware.
# Pure ASGI rather than @app.middleware("http"), so streaming responses and background tasks are untouched.
# ponytail: Starlette's ServerErrorMiddleware sits outside all user middleware, so the bare-text 500 for an
# unhandled exception goes out without these headers; routes here turn errors into HTTPException(500), which gets them.

SECURITY_HEADERS = {
    # Per-user data and auth errors: no browser, proxy or CDN may store them
    b"cache-control": b"no-store, max-age=0",
    b"pragma": b"no-cache",
    # JSON API: nothing may be rendered, framed, sniffed, embedded or referred from it
    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'",
    b"x-frame-options": b"DENY",
    b"x-content-type-options": b"nosniff",
    b"referrer-policy": b"no-referrer",
    b"cross-origin-resource-policy": b"same-origin",
    # Browsers ignore this over plain HTTP and enforce HTTPS once it arrives over TLS
    b"strict-transport-security": b"max-age=31536000",
}


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                # Replace rather than add, so a route can't weaken them; uvicorn's own Server header is off too.
                kept = [(k, v) for k, v in message.get("headers", []) if k.lower() not in SECURITY_HEADERS and k.lower() != b"server"]
                message["headers"] = kept + list(SECURITY_HEADERS.items())
            await send(message)

        await self.app(scope, receive, send_with_headers)
