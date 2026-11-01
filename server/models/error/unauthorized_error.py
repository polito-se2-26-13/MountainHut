from server.models.error.app_error import AppError

class UnauthorizedError(AppError):
    """Unauthorized error (401)"""
    
    def __init__(self, message: str):
        super().__init__(message, 401)
        self.name = "UnauthorizedError"