from fastapi import APIRouter, Depends, Response, Request
from datetime import datetime, timezone

from py_ocpi.modules.versions.enums import VersionNumber
from py_ocpi.core.utils import get_auth_token, get_list
from py_ocpi.core import status
from py_ocpi.core.schemas import OCPIResponse
from py_ocpi.core.adapter import Adapter
from py_ocpi.core.crud import Crud
from py_ocpi.core.enums import ModuleID, RoleEnum
from py_ocpi.core.dependencies import get_crud, get_adapter, pagination_filters

router = APIRouter(
    prefix='/cdrs',
)


@router.get("", response_model=OCPIResponse)
async def get_cdrs(response: Response,
                   request: Request,
                   crud: Crud = Depends(get_crud),
                   adapter: Adapter = Depends(get_adapter),
                   filters: dict = Depends(pagination_filters)):
    auth_token = get_auth_token(request)

    data_list = await get_list(response, filters, ModuleID.cdrs, RoleEnum.cpo,
                               VersionNumber.v_2_2_1, crud, auth_token=auth_token)

    if data_list and len(data_list) > 1:
        cdrs = []
        for data in data_list:
            cdrs.append(adapter.cdr_adapter(data).dict())
    else:
        cdrs = len(data_list) == 1 and adapter.cdr_adapter(data_list[0]).dict() or {}

    return OCPIResponse(
        data=cdrs,
        **status.OCPI_1000_GENERIC_SUCESS_CODE,
        timestamp=str(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
    )
