"""Lambda entry point. Wraps the existing Flask app for a Function URL.

Not a rewrite: `create_app()` in app/__init__.py is unchanged, and every route,
template and blueprint behaves exactly as it does under gunicorn today. This
file's only job is translating between a Lambda Function URL event and the
WSGI call Flask expects.

Mangum is built for ASGI, not WSGI, so `asgiref`'s WsgiToAsgi wraps the Flask
app first -- a small, standard, widely-used combination for putting a WSGI
framework on Lambda, and lighter than switching frameworks or hand-rolling an
event translator.

A Function URL sends the same event shape as an API Gateway HTTP API v2
integration, which is the shape Mangum expects by default -- no extra config
needed here for that reason.

Verified 2026-08-28 with a simulated Function URL event (real create_app(),
real templates, no AWS credentials involved): GET / returns the expected
302 to /profile, and GET /profile renders the real 64KB page. See
infra/README.md for how to reproduce that check.
"""

from asgiref.wsgi import WsgiToAsgi
from mangum import Mangum

from app import create_app

flask_app = create_app()
asgi_app = WsgiToAsgi(flask_app)

# lifespan="off": there is no ASGI startup/shutdown event to run here, only a
# WSGI app underneath that Flask already initialized at import time above.
handler = Mangum(asgi_app, lifespan="off")
