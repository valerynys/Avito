from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Query, Depends

from app.schemas import TenderResponse, CreateTenderRequest, TenderStatusResponse, EditTenderRequest, \
    CreateTenderResponse
from proposal_manager.exceptions import BadRequestErrorResponse, UnauthorizedCreationErrorResponse, \
    UserNotFoundErrorResponse
from proposal_manager.tenders.dependencies import get_service
from proposal_manager.tenders.exceptions import TenderNotFoundErrorResponse
from proposal_manager.tenders.models import TenderServiceType, TenderStatus
from proposal_manager.tenders.service import TenderService

router = APIRouter(tags=["Tenders API"])


@router.get(
    "/tenders",
    response_model=List[TenderResponse],
    responses={
        400: {"model": BadRequestErrorResponse, "description": "Неверный формат запроса или его параметры"},
        404: {"model": TenderNotFoundErrorResponse, "description": "Тендеры не найдены"}
    }
)
async def get_tenders(
        service: TenderService = Depends(get_service),
        limit: int = Query(5, ge=0, le=50, description="Максимальное число возвращаемых объектов"),
        offset: int = Query(0, ge=0, description="Количество пропускаемых объектов с начала"),
        service_type: Optional[List[TenderServiceType]] = Query(None, description="Фильтр по типу услуг"),
) -> List[TenderResponse]:
    tenders = await service.get_tenders(limit, offset, service_type)
    return tenders


@router.post(
    "/tenders/new",
    response_model=CreateTenderResponse,
    responses={
        400: {"model": BadRequestErrorResponse, "description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет права создавать тендер для этой организации"}
    }
)
async def create_tender(
        tender_request: CreateTenderRequest,
        service: TenderService = Depends(get_service)
) -> CreateTenderResponse:
    new_tender = await service.create_tender(
        name=tender_request.name,
        description=tender_request.description,
        service_type=tender_request.service_type,
        organization_id=tender_request.organization_id,
        creator_username=tender_request.creator_username
    )
    return new_tender


@router.get(
    "/tenders/my",
    response_model=List[TenderResponse],
    responses={
        400: {"model": BadRequestErrorResponse, "description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует или некорректен"},
        404: {"model": TenderNotFoundErrorResponse, "description": "Тендеры не найдены"}
    }
)
async def get_user_tenders(
        limit: int = Query(5, ge=0, le=50, description="Максимальное число возвращаемых объектов"),
        offset: int = Query(0, ge=0, description="Количество пропускаемых объектов с начала"),
        username: str = Query(None, description="Уникальный slug пользователя"),
        service: TenderService = Depends(get_service)
) -> List[TenderResponse]:
    tenders = await service.get_user_tenders(username, limit, offset)
    return tenders


@router.get(
    "/tenders/{tenderId}/status",
    response_model=TenderStatusResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав получения статуса"},
        404: {"model": TenderNotFoundErrorResponse, "description": "Тендеры не найдены"}
    }
)
async def get_tender_status(
        tenderId: UUID,
        username: str = Query(None, description="Уникальный slug пользователя"),
        service: TenderService = Depends(get_service)
) -> TenderStatusResponse:
    tender = await service.get_tender_status(tender_id=tenderId, username=username)
    return tender


@router.put(
    "/tenders/{tenderId}/status",
    response_model=TenderStatusResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": BadRequestErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав на изменение статуса"},
        404: {"model": TenderNotFoundErrorResponse, "description": "Тендеры не найдены"}
    }
)
async def update_tender_status(
        tenderId: UUID,
        status: TenderStatus,
        username: str = Query(None, description="Уникальный slug пользователя"),
        service: TenderService = Depends(get_service)
) -> TenderStatusResponse:
    updated_tender = await service.update_tender_status(tender_id=tenderId, status=status, username=username)
    return updated_tender


@router.patch(
    "/tenders/{tenderId}/edit",
    response_model=TenderResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": BadRequestErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав на изменение тендера"},
        404: {"model": TenderNotFoundErrorResponse, "description": "Тендеры не найдены"}
    }
)
async def edit_tender(
        tender_data: EditTenderRequest,
        tenderId: UUID,
        username: str = Query(..., description="Уникальный slug пользователя"),
        service: TenderService = Depends(get_service)
) -> TenderResponse:
    updated_tender = await service.edit_tender(tender_id=tenderId, username=username, tender_data=tender_data)
    return updated_tender

@router.put(
    "/tenders/{tenderId}/rollback/{version}",
    response_model=TenderResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": BadRequestErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав на изменение тендера"},
        404: {"model": TenderNotFoundErrorResponse, "description": "Тендер не найден"},
    }
)
async def rollback_tender(
        tenderId: UUID,
        version: int,
        username: str = Query(..., description="Уникальный slug пользователя"),
        service: TenderService = Depends(get_service)
) -> TenderResponse:
    rolled_back_tender = await service.rollback_tender(tender_id=tenderId, version=version, username=username)
    return rolled_back_tender
