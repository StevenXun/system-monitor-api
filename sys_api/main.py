from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sys_api.routes.metrics import router
from sys_api.utils import build_error_response

app = FastAPI()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response("request failed", exc.detail)
    )


app.include_router(router)
