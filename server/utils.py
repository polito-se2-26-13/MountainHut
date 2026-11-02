from server.models.error.app_error import AppError
from server.models.error.conflict_error import ConflictError
from server.models.error.notfound_error import NotFoundError
from typing import Optional, Callable, TypeVar, List

T = TypeVar('T')

def find_or_throw_not_found(
    items: Optional[List[T]],
    predicate: Callable[[T], bool],
    error_message: str
) -> T:
    """
    Find an item or throw NotFoundError if not found
    Equivalent to TypeScript's findOrThrowNotFound
    
    Args:
        items: List of items to search (can be None or empty)
        predicate: Function to test each item
        error_message: Error message to throw if not found
        
    Returns:
        The found item
        
    Raises:
        NotFoundError: If item is not found
    """
    if not items:
        raise NotFoundError(error_message)
    
    for item in items:
        if predicate(item):
            return item
    
    raise NotFoundError(error_message)


def throw_conflict_if_found(
    items: Optional[List[T]],
    predicate: Callable[[T], bool],
    error_message: str
) -> None:
    """
    Throw ConflictError if an item is found
    Equivalent to TypeScript's throwConflictIfFound
    
    Args:
        items: List of items to search (can be None or empty)
        predicate: Function to test each item
        error_message: Error message to throw if found
        
    Raises:
        ConflictError: If item is found
    """
    if items:
        for item in items:
            if predicate(item):
                raise ConflictError(error_message)
