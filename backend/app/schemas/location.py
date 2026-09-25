import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActiveStatus


class LocationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=20)


class LocationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: ActiveStatus | None = None
    manager_id: uuid.UUID | None = None


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    status: ActiveStatus
    manager_id: uuid.UUID | None


class KitchenStationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class KitchenStationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    status: ActiveStatus | None = None


class KitchenStationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    location_id: uuid.UUID
    name: str
    status: ActiveStatus
