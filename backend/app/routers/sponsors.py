from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_sponsor, get_tournament
from app.models import models
from app.schemas import schemas

router = APIRouter(prefix="/tournaments/{tournament_id}/sponsors", tags=["sponsors"])

MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_LOGO_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}


@router.post("", response_model=schemas.Sponsor)
async def add_sponsor(
    name: str = Form(...),
    logo: UploadFile = File(...),
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    if tournament.status == "started":
        raise HTTPException(
            status_code=400,
            detail="Turnier wurde bereits gestartet – keine Sponsoren mehr hinzufügen",
        )
    if not name.strip():
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")
    if logo.content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Logo muss ein Bild sein (PNG, JPEG, GIF, WebP oder SVG)",
        )
    data = await logo.read()
    if not data:
        raise HTTPException(status_code=400, detail="Logo-Datei ist leer")
    if len(data) > MAX_LOGO_SIZE:
        raise HTTPException(status_code=400, detail="Logo darf maximal 5 MB gross sein")

    db_sponsor = models.Sponsor(
        name=name.strip(),
        logo_data=data,
        logo_content_type=logo.content_type,
        tournament_id=tournament.id,
    )
    db.add(db_sponsor)
    db.commit()
    db.refresh(db_sponsor)
    return db_sponsor


@router.get("", response_model=list[schemas.Sponsor])
def list_sponsors(
    tournament: models.Tournament = Depends(get_tournament),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Sponsor)
        .filter(models.Sponsor.tournament_id == tournament.id)
        .order_by(models.Sponsor.id)
        .all()
    )


@router.get("/{sponsor_id}/logo")
def get_sponsor_logo(sponsor: models.Sponsor = Depends(get_sponsor)):
    return Response(content=sponsor.logo_data, media_type=sponsor.logo_content_type)


@router.delete("/{sponsor_id}", status_code=204)
def remove_sponsor(
    tournament: models.Tournament = Depends(get_tournament),
    sponsor: models.Sponsor = Depends(get_sponsor),
    db: Session = Depends(get_db),
):
    if tournament.status == "started":
        raise HTTPException(
            status_code=400,
            detail="Turnier wurde bereits gestartet – Sponsoren können nicht entfernt werden",
        )
    db.delete(sponsor)
    db.commit()
