from fastapi import FastAPI
from exceptions import (
    PincodeNotFoundException,
    InvalidPincodeFormatException,
    pincode_not_found_exception_handler,
    invalid_pincode_format_exception_handler,
)

from models import PincodeRequest, LocationResponse, BulkRequest, BulkResponse

from data import fetch_pincode_from_api, map_api_to_location_response

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

   
    # MAP: Transform API response to LocationResponse model
    location = map_api_to_location_response(pincode, api_data)
    return location



@app.post("/pincode/bulk", response_model=BulkResponse)
async def get_locations_by_bulk_pincode(request: BulkRequest):
    """Get location information for a list of pincodes."""
    found_results = []
    missing_pincodes = []

    for pincode in request.pincodes:
        # Validate pincode format
        if not pincode.isdigit() or len(pincode) != 6:
            raise InvalidPincodeFormatException(pincode, reason="Pincode must be a 6-digit number.")

        # Fetch from online API
        api_data = fetch_pincode_from_api(pincode)

        if api_data:
            # MAP: Transform API data to LocationResponse
            location = map_api_to_location_response(pincode, api_data)
            found_results.append(location)
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