from pydantic import BaseModel


class BadRequestErrorResponse(BaseModel):
    reason: str


class UserNotFoundErrorResponse(BaseModel):
    reason: str


class UnauthorizedCreationErrorResponse(BaseModel):
    reason: str


class UserNotFoundError(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class UnauthorizedCreationError(Exception):
    def __init__(self, reason: str):
        self.reason = reason


class TenderBidErrorResponse(BaseModel):
    reason: str


class TenderBidError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
