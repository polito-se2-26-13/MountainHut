from typing import Any
from server.models.DTO.error_dto import ErrorDTO
from server.models.error.app_error import AppError
from server.service.mapper_service import create_error_dto

def create_app_error(err: Any) -> ErrorDTO:
    """
    Create a standardized ErrorDTO from any exception
    
    Args:
        err: The exception to process
        
    Returns:
        ErrorDTO with appropriate status code and message
    """
    # Default error
    model_error = create_error_dto(
        500,
        getattr(err, 'message', None) or str(err) or "Internal Server Error",
        "InternalServerError"
    )
    
    """# Log the error
    log_error(err)
    
    # Get stack trace
    stack_trace = ''.join(traceback.format_exception(type(err), err, err.__traceback__))
    log_error(f"Error: {str(err)}\nStacktrace:\n{stack_trace or 'No stacktrace available'}")
    """
    # Check if it's an AppError or has a status attribute
    if isinstance(err, AppError) or (hasattr(err, 'status') and isinstance(err.status, int)):
        model_error = create_error_dto(
            err.status,
            getattr(err, 'message', str(err)),
            err.__class__.__name__
        )
    
    return model_error