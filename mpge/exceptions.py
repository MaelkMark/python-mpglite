class MPGEError(Exception):
    """Base for MPGE Errors"""

    pass


class InvalidURIError(MPGEError):
    """MPGE Error ✦ Raised when the URI is incorrectly formatted."""

    pass


class ServerNotFoundError(MPGEError):
    """MPGE Error ✦ Raised when the server is down or the IP/port is wrong."""

    pass


class AuthenticationError(MPGEError):
    """MPGE Error ✦ Raised when the handshake fails (e.g. wrong version)."""

    pass


class ConnectionLostError(MPGEError):
    """MPGE Error ✦ Raised when the internet cuts out mid-game."""

    pass


class SignatureError(MPGEError):
    """MPGE Error ✦ Raised when a callback is missing required parameters."""

    pass


class UserLeftError(MPGEError):
    """MPGE Error ✦ Raised when the server wants to interact with a user that left the room."""

    pass
