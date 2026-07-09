from typing import Optional

from pydantic import BaseModel


class RequestCreate(BaseModel):
    ranger_id: int
    species_id: int
    camera_id: Optional[int] = None


class DeviceRegister(BaseModel):
    ranger_id: int
    fcm_token: str
    platform: str
