import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.platform import Platform
from app.schemas.platform import PlatformCreate, PlatformResponse, PlatformUpdate
from app.services.crypto import encrypt_credentials

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.post("", response_model=PlatformResponse, status_code=201)
async def create_platform(
    body: PlatformCreate, db: AsyncSession = Depends(get_db)
):
    platform = Platform(
        name=body.name,
        base_url=body.base_url,
        login_url=body.login_url,
        credentials_encrypted=encrypt_credentials(body.credentials),
        login_selectors=body.login_selectors,
        extra_config=body.extra_config,
    )
    db.add(platform)
    await db.commit()
    await db.refresh(platform)
    return platform


@router.get("", response_model=list[PlatformResponse])
async def list_platforms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Platform).order_by(Platform.created_at.desc()))
    return result.scalars().all()


@router.get("/{platform_id}", response_model=PlatformResponse)
async def get_platform(
    platform_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    platform = await db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    return platform


@router.put("/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: uuid.UUID,
    body: PlatformUpdate,
    db: AsyncSession = Depends(get_db),
):
    platform = await db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    update_data = body.model_dump(exclude_unset=True)
    if "credentials" in update_data:
        update_data["credentials_encrypted"] = encrypt_credentials(
            update_data.pop("credentials")
        )

    for field, value in update_data.items():
        setattr(platform, field, value)

    await db.commit()
    await db.refresh(platform)
    return platform


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(
    platform_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    platform = await db.get(Platform, platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    await db.delete(platform)
    await db.commit()
