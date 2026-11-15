from server.models.error.app_error import AppError

class ForbiddenError(AppError):
    """Forbidden error (403)"""
    
    def __init__(self, message: str):
        super().__init__(message, 403)
        self.name = "ForbiddenError"