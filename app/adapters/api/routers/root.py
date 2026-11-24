"""Service root — identifies the service and points to its documentation."""

from fastapi import APIRouter

from app import __version__
from app.adapters.api.schemas import RootResponse

router = APIRouter(tags=["health"])


# HEAD is listed explicitly: Render probes "HEAD /" at startup.
@router.api_route(
    "/",
    methods=["GET", "HEAD"],
    response_model=RootResponse,
    summary="Service identity and useful links",
)
def root() -> RootResponse:
    return RootResponse(version=__version__)
