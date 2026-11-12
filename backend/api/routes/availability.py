"""Weekly availability CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Availability
from backend.schemas import AvailabilityCreate, AvailabilityOut, AvailabilityUpdate

router = APIRouter(prefix="/api/availability", tags=["availability"])


@router.post("", response_model=AvailabilityOut, status_code=status.HTTP_201_CREATED)
def create_availability(payload: AvailabilityCreate, db: Session = Depends(get_db)) -> Availability:
    """Add a recurring weekly availability window."""
    item = Availability(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[AvailabilityOut])
def list_availability(db: Session = Depends(get_db)) -> list[Availability]:
    """List weekly windows ordered by weekday and start time."""
    return list(db.scalars(select(Availability).order_by(Availability.weekday, Availability.start_time)).all())


@router.get("/{availability_id}", response_model=AvailabilityOut)
def get_availability(availability_id: int, db: Session = Depends(get_db)) -> Availability:
    """Retrieve an availability window by identifier."""
    item = db.get(Availability, availability_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Disponibilité introuvable")
    return item


@router.put("/{availability_id}", response_model=AvailabilityOut)
def update_availability(availability_id: int, payload: AvailabilityUpdate, db: Session = Depends(get_db)) -> Availability:
    """Replace an availability window."""
    item = db.get(Availability, availability_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Disponibilité introuvable")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(availability_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete an availability window."""
    item = db.get(Availability, availability_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Disponibilité introuvable")
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
