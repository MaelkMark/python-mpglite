class MPGEException(Exception):
    """Base for MPGE Exceptions"""
    pass


class InvalidURIError(MPGEException):
    """MPGE Exception ✦ Raised when the URI is incorrectly formatted."""
    pass


class ServerNotFoundError(MPGEException):
    """MPGE Exception ✦ Raised when the server is down or the IP/port is wrong."""
    pass


class AuthenticationError(MPGEException):
    """MPGE Exception ✦ Raised when the handshake fails (e.g. wrong version)."""
    pass


class ConnectionLostError(MPGEException):
    """MPGE Exception ✦ Raised when the internet cuts out mid-game."""
    pass

class SignatureError(MPGEException):
    """MPGE Exception ✦ Raised when a callback is missing required parameters."""
    pass