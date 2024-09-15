from pydantic import BaseModel


class TenderNotFoundErrorResponse(BaseModel):
    reason: str


class TenderError(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class TenderNotFoundError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
