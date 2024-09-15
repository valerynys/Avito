from fastapi import APIRouter

router = APIRouter(tags=["Ping API"])


@router.get(
    "/ping",
)
async def healthcheck():
    return "ok"
