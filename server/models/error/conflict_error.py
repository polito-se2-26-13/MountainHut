from server.models.error.app_error import AppError

class ConflictError(AppError):
    """Conflict error (409)"""
    
    def __init__(self, message: str):
        super().__init__(message, 409)
        self.name = "ConflictError"