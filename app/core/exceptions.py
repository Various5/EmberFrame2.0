"""
Custom application exceptions
"""

from fastapi import HTTPException, status


class EmberFrameException(Exception):
    """Base application exception"""
    pass


class AuthenticationError(EmberFrameException):
    """Authentication related errors"""
    pass


class AuthorizationError(EmberFrameException):
    """Authorization related errors"""
    pass


class FileNotFoundError(EmberFrameException):
    """File not found errors"""
    pass


class StorageQuotaExceededError(EmberFrameException):
    """Storage quota exceeded"""
    pass


class InvalidFileTypeError(EmberFrameException):
    """Invalid file type"""
    pass
