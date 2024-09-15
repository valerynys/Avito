from typing import List
from uuid import UUID

from fastapi import APIRouter, Query, Path
from fastapi import Depends

from app.schemas import BidResponse, CreateBidRequest, BidStatusResponse, UpdateBidStatusResponse, EditBidRequest, \
    BidFeedbackResponse
from proposal_manager.bids.dependencies import get_service
from proposal_manager.bids.exceptions import BidNotFoundErrorResponse
from proposal_manager.bids.models import BidStatus, BidDecision
from proposal_manager.bids.service import BidService
from proposal_manager.exceptions import BadRequestErrorResponse, UserNotFoundErrorResponse, \
    UnauthorizedCreationErrorResponse, TenderBidErrorResponse

router = APIRouter(tags=["Bids API"])


@router.post(
    "/bids/new",
    response_model=BidResponse,
    responses={
        400: {"model": BadRequestErrorResponse, "description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет права создавать предложение для этого тендера"}
    }
)
async def create_bid(
        bid_request: CreateBidRequest,
        service: BidService = Depends(get_service)
) -> BidResponse:
    new_bid = await service.create_bid(
        name=bid_request.name,
        description=bid_request.description,
        tender_id=bid_request.tender_id,
        author_type=bid_request.author_type,
        author_id=bid_request.author_id
    )
    return new_bid


@router.get(
    "/bids/my",
    response_model=List[BidResponse],
    responses={
        400: {"model": BadRequestErrorResponse, "description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует или некорректен"},
        404: {"model": BidNotFoundErrorResponse, "description": "Предложения не найдены"}
    }
)
async def get_user_bids(
    limit: int = Query(5, ge=0, le=50, description="Максимальное число возвращаемых объектов"),
    offset: int = Query(0, ge=0, description="Сколько объектов пропустить с начала"),
    username: str = Query(..., description="Уникальный slug пользователя"),
    service: BidService = Depends(get_service),
) -> List[BidResponse]:
    return await service.get_user_bids(username, limit, offset)


@router.get(
    "/bids/{tenderId}/list",
    response_model=List[BidResponse],
    responses={
        400: {"model": BadRequestErrorResponse, "description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет права создавать предложение для этого тендера"},
        404: {"model": TenderBidErrorResponse, "description": "Тендер или предложение не найдено."}

    }
)
async def get_bids_for_tender(
    tenderId: UUID,
    username: str = Query(..., description="Уникальный slug пользователя"),
    limit: int = Query(5, ge=0, le=50, description="Максимальное число возвращаемых объектов"),
    offset: int = Query(0, ge=0, description="Сколько объектов пропустить с начала"),
    bid_service: BidService = Depends(get_service),
) -> List[BidResponse]:
    return await bid_service.get_bids_for_tender(tenderId, username, limit, offset)


@router.get(
    "/bids/{bidId}/status",
    response_model=BidStatusResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": UserNotFoundErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав получения статуса"},
        404: {"model": BidNotFoundErrorResponse, "description": "Предложение не найдено"}
    }
)
async def get_bid_status(
        bidId: UUID,
        username: str = Query(..., description="Уникальный slug пользователя"),
        service: BidService = Depends(get_service)
) -> BidStatusResponse:
    return await service.get_bid_status(bid_id=bidId, username=username)


@router.put(
    "/bids/{bidId}/status",
    response_model=UpdateBidStatusResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": BadRequestErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав на изменение статуса"},
        404: {"model": BidNotFoundErrorResponse, "description": "Предложение не найдено"}
    }
)
async def update_bid_status(
        bidId: UUID,
        status: BidStatus,
        username: str = Query(None, description="Уникальный slug пользователя"),
        service: BidService = Depends(get_service)
) -> UpdateBidStatusResponse:
    return await service.update_bid_status(bid_id=bidId, status=status, username=username)


@router.patch(
    "/bids/{bidId}/edit",
    response_model=BidResponse,
    responses={
        400: {"description": "Некорректные данные"},
        401: {"model": BadRequestErrorResponse, "description": "Пользователь не существует или некорректен"},
        403: {"model": UnauthorizedCreationErrorResponse,
              "description": "Пользователь не имеет прав на изменение предложения"},
        404: {"model": BidNotFoundErrorResponse, "description": "Предложение не найдено"}
    }
)
async def edit_tender(
        bid_data: EditBidRequest,
        bidId: UUID,
        username: str = Query(..., description="Уникальный slug пользователя"),
        service: BidService = Depends(get_service)
) -> BidResponse:
    return await service.edit_bid(bid_id=bidId, username=username, bid_data=bid_data)


@router.put("/bids/{bidId}/rollback/{version}", response_model=BidResponse)
async def rollback_bid_version(
        bidId: UUID = Path(..., description="Уникальный идентификатор предложения"),
        version: int = Path(..., ge=1, description="Номер версии, к которой нужно откатить предложение"),
        username: str = Query(..., description="Уникальный slug пользователя"),
        service: BidService = Depends(get_service)
):
    return await service.rollback_bid_version(bid_id=bidId, version=version, username=username)


@router.put("/bids/{bidId}/submit_decision", response_model=BidResponse)
async def submit_bid_decision(
        bidId: UUID = Path(..., description="Уникальный идентификатор предложения"),
        decision: BidDecision = Query(..., description="Решение по предложению"),
        username: str = Query(..., description="Уникальный slug пользователя"),
        service: BidService = Depends(get_service)
):
    return await service.submit_bid_decision(bid_id=bidId, decision=decision, username=username)


@router.put("/bids/{bidId}/feedback", response_model=BidResponse)
async def submit_bid_feedback(
        bidId: UUID = Path(..., description="Уникальный идентификатор предложения"),
        bidFeedback: str = Query(..., max_length=1000),
        username: str = Query(...),
        service: BidService = Depends(get_service)
) -> BidResponse:
    return await service.submit_feedback(bidId=bidId, bidFeedback=bidFeedback, username=username)


@router.get("/bids/{tenderId}/reviews", response_model=List[BidFeedbackResponse])
async def get_bid_reviews(
        tenderId: UUID = Path(..., description="Уникальный идентификатор тендера"),
        authorUsername: str = Query(..., description="Имя пользователя автора предложений"),
        requesterUsername: str = Query(..., description="Имя пользователя, запрашивающего отзывы"),
        limit: int = Query(5, ge=0, le=50, description="Максимальное число возвращаемых объектов"),
        offset: int = Query(0, ge=0, description="Количество пропущенных объектов"),
        service: BidService = Depends(get_service)
) -> List[BidFeedbackResponse]:
    reviews = await service.get_reviews_for_author(
        tender_id=tenderId,
        author_username=authorUsername,
        requester_username=requesterUsername,
        limit=limit,
        offset=offset
    )
    return reviews
