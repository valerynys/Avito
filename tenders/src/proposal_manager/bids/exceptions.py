from pydantic import BaseModel


class BidNotFoundErrorResponse(BaseModel):
    reason: str


class BidError(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class BidNotFoundError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
