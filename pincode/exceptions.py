from fastapi.responses import JSONResponse
from fastapi.requests import Request


class PincodeNotFoundException(Exception):
    """Custom exception for Pincode not found."""

    def __init__(self, pincode: str):
        self.pincode = pincode


class InvalidPincodeFormatException(Exception):
    """Custom exception for invalid Pincode format."""

    def __init__(self, pincode: str, reason: str = "Invalid format"):
        self.pincode = pincode
        self.reason = reason




#Custom exception handlers for FastAPI
async def pincode_not_found_exception_handler(request: Request, exc: PincodeNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"message": f"Pincode '{exc.pincode}' not found."},
    )

async def invalid_pincode_format_exception_handler(request: Request, exc: InvalidPincodeFormatException):
    return JSONResponse(
        status_code=400,
        content={"message": f"Pincode '{exc.pincode}' has an invalid format.", "reason": exc.reason},
    )