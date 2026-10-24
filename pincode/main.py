from fastapi import FastAPI
from exceptions import (
    PincodeNotFoundException,
    InvalidPincodeFormatException,
    pincode_not_found_exception_handler,
    invalid_pincode_format_exception_handler,
)

from models import PincodeRequest, LocationResponse, BulkRequest, BulkResponse

from data import pincode_db  # Assume this is a dictionary mapping pincodes to location data

app = FastAPI(
    title="Pincode API",
    description="API for Pincode service for autofill city, state",
)


#register custom exception handlers
app.add_exception_handler(PincodeNotFoundException, pincode_not_found_exception_handler)
app.add_exception_handler(InvalidPincodeFormatException, invalid_pincode_format_exception_handler)



@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to the Pincode API!"}


@app.get("/pincode/{pincode}", response_model=LocationResponse)
async def get_location_by_pincode(pincode: str):
    """Get location information by pincode."""
    # Validate pincode format
    if not pincode.isdigit() or len(pincode) != 6:
        raise InvalidPincodeFormatException(pincode, reason="Pincode must be a 6-digit number.")

   
    if not location_data:
        raise PincodeNotFoundException(pincode)

    location_data = pincode_db.get(pincode)

    return LocationResponse(**location_data)



@app.post("/pincode/bulk", response_model=BulkResponse)
async def get_locations_by_bulk_pincode(request: BulkRequest):
    """Get location information for a list of pincodes."""
    found_results = []
    missing_pincodes = []

    for pincode in request.pincodes:
        # Validate pincode format
        if not pincode.isdigit() or len(pincode) != 6:
            raise InvalidPincodeFormatException(pincode, reason="Pincode must be a 6-digit number.")

        location_data = pincode_db.get(pincode)
        if location_data:
            found_results.append(LocationResponse(**location_data))
        else:
            missing_pincodes.append(pincode)

    return BulkResponse(
        found=len(found_results),
        not_found=len(missing_pincodes),
        results=found_results,
        missing=missing_pincodes,
    )








if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)