from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ErrorDTO:
    code: int
    message: str
    name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ErrorDTO to dictionary for JSON serialization"""
        return {
            "code": self.code,
            "message": self.message,
            "name": self.name
        }