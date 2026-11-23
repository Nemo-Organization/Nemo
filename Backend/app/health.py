from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


@router.get("/health", response_model=Health, operation_id="getHealth", tags=["Customer"])
async def get_health() -> Health:
    return Health()
