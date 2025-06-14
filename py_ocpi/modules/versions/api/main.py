from fastapi import APIRouter, Depends

from py_ocpi.core import status
from py_ocpi.core.dependencies import get_versions as get_versions_
from py_ocpi.core.schemas import OCPIResponse

from datetime import datetime, timezone

router = APIRouter()


@router.get("/versions", response_model=OCPIResponse)
async def get_versions(versions=Depends(get_versions_)):
    return OCPIResponse(
        data=versions,
        **status.OCPI_1000_GENERIC_SUCESS_CODE,
        timestamp=str(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
    )
