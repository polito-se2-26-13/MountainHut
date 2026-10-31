from server.models.error.app_error import AppError

class NotFoundError(AppError):
    """Not found error (404)"""
    
    def __init__(self, message: str):
        super().__init__(message, 404)
        self.name = "NotFoundError"