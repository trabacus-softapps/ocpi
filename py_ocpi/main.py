from typing import Any, List
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from py_ocpi.core.endpoints import ENDPOINTS

from py_ocpi.modules.versions.api import router as versions_router, versions_v_2_2_1_router
from py_ocpi.modules.versions.enums import VersionNumber
from py_ocpi.modules.versions.schemas import Version
from py_ocpi.core.dependencies import get_crud, get_adapter, get_versions, get_endpoints
from py_ocpi.core import status
from py_ocpi.core.enums import RoleEnum
from py_ocpi.core.config import settings
from py_ocpi.core.data_types import URL
from py_ocpi.core.schemas import OCPIResponse
from py_ocpi.core.exceptions import AuthorizationOCPIError, NotFoundOCPIError
from py_ocpi.core.push import http_router as http_push_router, websocket_router as websocket_push_router
from py_ocpi.routers import v_2_2_1_cpo_router, v_2_2_1_emsp_router


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ):
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", "")
            response.headers["X-Correlation-ID"] = request.headers.get("X-Correlation-ID", "")
        except AuthorizationOCPIError as e:
            raise HTTPException(403, str(e)) from e
        except NotFoundOCPIError as e:
            raise HTTPException(404, str(e)) from e
        except ValidationError:
            response = JSONResponse(
                OCPIResponse(
                    data=[],
                    **status.OCPI_3000_GENERIC_SERVER_ERROR,
                    timestamp=str(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
                ).dict()
            )
        return response


def get_application(
    version_numbers: List[VersionNumber],
    roles: List[RoleEnum],
    crud: Any,
    adapter: Any,
    http_push: bool = False,
    websocket_push: bool = False,
) -> FastAPI:
    _app = FastAPI(
        title=settings.PROJECT_NAME,
        docs_url=f'/{settings.OCPI_PREFIX}/docs',
        openapi_url=f"/{settings.OCPI_PREFIX}/openapi.json"
    )

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _app.add_middleware(ExceptionHandlerMiddleware)

    _app.include_router(
        versions_router,
        prefix=f'/{settings.OCPI_PREFIX}',
    )

    if http_push:
        _app.include_router(
            http_push_router,
            prefix=f'/{settings.PUSH_PREFIX}',
        )

    if websocket_push:
        _app.include_router(
            websocket_push_router,
            prefix=f'/{settings.PUSH_PREFIX}',
        )

    versions = []
    version_endpoints = {}

    if VersionNumber.v_2_2_1 in version_numbers:
        _app.include_router(
            versions_v_2_2_1_router,
            prefix=f'/{settings.OCPI_PREFIX}',
        )

        versions.append(
            Version(
                version=VersionNumber.v_2_2_1,
                url=URL(f'https://{settings.OCPI_HOST}/{settings.OCPI_PREFIX}/{VersionNumber.v_2_2_1.value}/details')
            ).dict(),
        )

        version_endpoints[VersionNumber.v_2_2_1] = []

        if RoleEnum.cpo in roles:
            _app.include_router(
                v_2_2_1_cpo_router,
                prefix=f'/{settings.OCPI_PREFIX}/cpo/{VersionNumber.v_2_2_1.value}',
                tags=['CPO']
            )
            version_endpoints[VersionNumber.v_2_2_1] += ENDPOINTS[VersionNumber.v_2_2_1][RoleEnum.cpo]

        if RoleEnum.emsp in roles:
            _app.include_router(
                v_2_2_1_emsp_router,
                prefix=f'/{settings.OCPI_PREFIX}/emsp/{VersionNumber.v_2_2_1.value}',
                tags=['EMSP']
            )
            version_endpoints[VersionNumber.v_2_2_1] += ENDPOINTS[VersionNumber.v_2_2_1][RoleEnum.emsp]

    def override_get_crud():
        return crud

    _app.dependency_overrides[get_crud] = override_get_crud

    def override_get_adapter():
        return adapter

    _app.dependency_overrides[get_adapter] = override_get_adapter

    def override_get_versions():
        return versions

    _app.dependency_overrides[get_versions] = override_get_versions

    def override_get_endpoints():
        return version_endpoints

    _app.dependency_overrides[get_endpoints] = override_get_endpoints

    return _app
