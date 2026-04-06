from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserOut
from app.core.security import hash_password
from app.routers.auth_router import get_current_user_from_cookie

router = APIRouter(prefix="/admin/users", tags=["admin-users"])
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/static/uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_superuser(current_user: User = Depends(get_current_user_from_cookie)) -> User:
    if current_user.role.lower() != "superuser":
        raise HTTPException(status_code=403, detail="No autorizado")
    return current_user


def list_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.id.desc()).all()


@router.get("/")
def users_dashboard(
    request: Request,
    superuser: User = Depends(get_superuser),
    db: Session = Depends(get_db),
):
    users = list_users(db)
    return templates.TemplateResponse(
        "users_admin.html",
        {
            "request": request,
            "user": superuser,
            "users": users,
        },
    )


@router.post("/")
def create_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
    role: str = Form("agent"),
    avatar: UploadFile | None = File(None),
    superuser: User = Depends(get_superuser),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya existe")

    avatar_url = None
    if avatar and avatar.filename:
        extension = Path(avatar.filename).suffix or ".png"
        file_name = f"avatar-{email.replace('@', '_')}{extension}"
        dest = UPLOAD_DIR / file_name
        with dest.open("wb") as buffer:
            buffer.write(avatar.file.read())
        avatar_url = f"/static/uploads/avatars/{file_name}"

    new_user = User(
        email=email,
        hashed_password=hash_password(password),
        display_name=display_name or email,
        role=role or "agent",
        avatar_url=avatar_url,
    )
    db.add(new_user)
    db.commit()

    return RedirectResponse(url="/admin/users", status_code=303)
