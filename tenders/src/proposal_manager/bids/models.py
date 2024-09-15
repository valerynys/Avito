from enum import Enum


class BidStatus(str, Enum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CANCELED = "Canceled"


class BidDecision(str, Enum):
    APPROVED = "Approved"
    REJECTED = "Rejected"


class AuthorType(str, Enum):
    ORGANIZATION = "Organization"
    USER = "User"
