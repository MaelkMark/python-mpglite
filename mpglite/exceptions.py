class MPGLiteError(Exception):
    """Base for MPGLite Errors"""

    pass


class InvalidURIError(MPGLiteError):
    """MPGLite Error ✦ Raised when the URI is incorrectly formatted."""

    pass


class ServerNotFoundError(MPGLiteError):
    """MPGLite Error ✦ Raised when the server is down or the IP/port is wrong."""

    pass


class AuthenticationError(MPGLiteError):
    """MPGLite Error ✦ Raised when the handshake fails (e.g. wrong version)."""

    pass


class ConnectionLostError(MPGLiteError):
    """MPGLite Error ✦ Raised when the internet cuts out mid-game."""

    pass


class SignatureError(MPGLiteError):
    """MPGLite Error ✦ Raised when a callback is missing required parameters."""

    pass


class UserLeftError(MPGLiteError):
    """MPGLite Error ✦ Raised when the server wants to interact with a user that left the room."""

    pass
