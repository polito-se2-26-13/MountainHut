from fastapi import Request
from fastapi.responses import JSONResponse
from server.service.error_service import create_app_error
from server.models.error.app_error import AppError

async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global error handler for FastAPI application
    This is the equivalent of Express's errorHandler middleware
    
    Args:
        request: The FastAPI request object
        exc: The exception that was raised
        
    Returns:
        JSONResponse with error details
    """
    model_error = create_app_error(exc)
    return JSONResponse(
        status_code=model_error.code,
        content=model_error.to_dict()
    )