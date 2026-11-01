from server.models.error.app_error import AppError

class BadRequestError(AppError):
    """Bad Request error (400)"""
    
    def __init__(self, message: str):
        super().__init__(message, 400)
        self.name = "BadRequesteError"