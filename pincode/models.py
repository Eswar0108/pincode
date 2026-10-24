from pydantic import BaseModel, field_validator

class PincodeRequest(BaseModel):
    """A request to the pincode service, which is a proxy for the stateful proxy."""

    pincode: str
    model: str | None = None
    prompt: str | None = None

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 6:
            raise ValueError("Pincode must be a 6-digit number.")
        return value


class LocationResponse(BaseModel):
    """Response from the pincode service containing location information."""

    pincode: str
    district: str
    city: str
    state: str


class BulkRequest(BaseModel):
    """A request to the pincode service for bulk pincode lookups."""

    pincodes: list[str]
    model: str | None = None
    prompt: str | None = None

    @field_validator("pincodes")
    @classmethod
    def validate_pincodes(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("Pincodes list cannot be empty.")
        if len(value) > 20:
            raise ValueError("Pincodes list cannot contain more than 20 entries.")
        for pincode in value:
            if not pincode.isdigit() or len(pincode) != 6:
                raise ValueError(f"Pincode '{pincode}' must be a 6-digit number.")
        return value



class BulkResponse(BaseModel):
    """Response from the pincode service for bulk pincode lookups."""
    status: str = "success"
    found: int
    not_found: int
    results: list[LocationResponse] = []
    missing: list[str] = []


    results: list[LocationResponse]