from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, constr, Field, ConfigDict
from pydantic.alias_generators import to_camel

from proposal_manager.bids.models import AuthorType, BidStatus
from proposal_manager.tenders.models import TenderServiceType, TenderStatusEnum


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class CreateTenderRequest(BaseSchema):
    name: constr(max_length=100)
    description: constr(max_length=500)
    service_type: TenderServiceType
    organization_id: UUID
    creator_username: constr(min_length=1)


class CreateTenderResponse(BaseSchema):
    id: UUID
    name: str
    description: str
    status: str
    service_type: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds') + 'Z'
        }


class TenderResponse(BaseSchema):
    id: UUID
    name: str
    description: str
    status: str
    service_type: str
    organization_id: UUID
    version: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds') + 'Z'
        }


class TenderStatusResponse(BaseSchema):
    status: TenderStatusEnum


class EditTenderRequest(BaseSchema):
    name: Optional[str] = Field(None, max_length=100, description="Полное название тендера")
    description: Optional[str] = Field(None, max_length=500, description="Описание тендера")
    service_type: Optional[TenderServiceType] = Field(None, description="Вид услуги, к которой относится тендер")


class CreateBidRequest(BaseSchema):
    name: constr(max_length=100)
    description: constr(max_length=500)
    tender_id: UUID
    author_type: AuthorType
    author_id: UUID


class BidResponse(BaseSchema):
    id: UUID
    name: constr(max_length=100)
    status: str
    tender_id: UUID
    author_type: AuthorType
    author_id: UUID
    version: int = 1
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds') + 'Z'
        }


class UpdateBidStatusResponse(BaseSchema):
    id: UUID
    name: constr(max_length=100)
    status: str
    author_type: AuthorType
    author_id: UUID
    version: int = 1
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds') + 'Z'
        }


class EditBidRequest(BaseSchema):
    name: Optional[str] = Field(None, max_length=100, description="Полное название тендера")
    description: Optional[str] = Field(None, max_length=500, description="Описание тендера")


class BidStatusResponse(BaseSchema):
    status: BidStatus

class BidFeedbackResponse(BaseSchema):
    id: UUID
    description: str
    createdAt: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(timespec='seconds') + 'Z'
        }