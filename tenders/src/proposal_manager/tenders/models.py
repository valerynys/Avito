from enum import Enum


class TenderServiceType(Enum):
    CONSTRUCTION = "Construction"
    DELIVERY = "Delivery"
    MANUFACTURE = "Manufacture"


class TenderStatus(str, Enum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CLOSED = "Closed"


class TenderStatusEnum(str, Enum):
    CREATED = "Created"
    PUBLISHED = "Published"
    CLOSED = "Closed"
