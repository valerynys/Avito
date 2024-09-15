from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from db import models
from app.routers import bids, ping, tenders
from db.database import engine
from proposal_manager.bids.exceptions import BidNotFoundError, BidNotFoundErrorResponse
from proposal_manager.exceptions import (
    UserNotFoundError,
    UnauthorizedCreationError,
    UserNotFoundErrorResponse,
    UnauthorizedCreationErrorResponse,
    BadRequestErrorResponse, TenderBidErrorResponse, TenderBidError
)
from proposal_manager.tenders.exceptions import TenderNotFoundError, TenderNotFoundErrorResponse

tags_metadata = [
    {"name": "Tender Management API (1.0)", "description": "API for managing tenders on the Avito platform."},
    {"name": "Bids API", "description": "API for working with tender applications."},
    {"name": "Ping API", "description": "API for service healthcheck"},
    {"name": "Tenders API", "description": "API for working with tenders"},
]


def add_custom_handler(exception_class: type[Exception], response_model, status_code: int):
    async def handler(request: Request, exc: exception_class):
        reason = getattr(exc, "reason", str(exc))
        return JSONResponse(
            status_code=status_code,
            content=response_model(reason=reason).dict()
        )

    return handler


def make_app() -> FastAPI:
    app = FastAPI(openapi_tags=tags_metadata)

    models.Base.metadata.create_all(bind=engine)

    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(bids.router, prefix="/api")
    app.include_router(ping.router, prefix="/api")
    app.include_router(tenders.router, prefix="/api")

    @app.get("/", include_in_schema=False)
    def docs_redirect() -> RedirectResponse:
        return RedirectResponse("/docs")

    app.add_exception_handler(
        RequestValidationError,
        add_custom_handler(RequestValidationError, BadRequestErrorResponse, status.HTTP_400_BAD_REQUEST)
    )
    app.add_exception_handler(
        UserNotFoundError,
        add_custom_handler(UserNotFoundError, UserNotFoundErrorResponse, status.HTTP_401_UNAUTHORIZED)
    )
    app.add_exception_handler(
        UnauthorizedCreationError,
        add_custom_handler(UnauthorizedCreationError, UnauthorizedCreationErrorResponse, status.HTTP_403_FORBIDDEN)
    )
    app.add_exception_handler(
        TenderNotFoundError,
        add_custom_handler(TenderNotFoundError, TenderNotFoundErrorResponse, status.HTTP_404_NOT_FOUND)
    )
    app.add_exception_handler(
        BidNotFoundError,
        add_custom_handler(BidNotFoundError, BidNotFoundErrorResponse, status.HTTP_404_NOT_FOUND)
    )
    app.add_exception_handler(
        TenderBidError,
        add_custom_handler(TenderBidError, TenderBidErrorResponse, status.HTTP_404_NOT_FOUND)
    )
    app.add_exception_handler(
        ValueError,
        add_custom_handler(ValueError, BadRequestErrorResponse, status.HTTP_400_BAD_REQUEST)
    )

    return app

app = make_app()
