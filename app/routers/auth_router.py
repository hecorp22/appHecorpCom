from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User
from app.schemas.user_schema import UserCreate
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers de cookies
# ---------------------------------------------------------------------------
def _set_auth_cookies(response, access_token: str, refresh_token: str | None = None):
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=UserCreate)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        display_name=user.display_name,
        role=user.role or "agent",
        avatar_url=user.avatar_url,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ---------------------------------------------------------------------------
# Login (GET form + POST)
# ---------------------------------------------------------------------------
@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "hide_nav": True, "user": None}
    )


@router.post("/login")
def login_redirect(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user or not verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    payload = {"sub": db_user.email, "role": db_user.role}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    response = RedirectResponse(url="/home", status_code=302)
    _set_auth_cookies(response, access_token, refresh_token)
    return response


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------
@router.get("/refresh")
def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    payload = decode_token(refresh_token, expected_type="refresh") if refresh_token else None
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    db_user = db.query(User).filter(User.email == payload["sub"]).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    new_access = create_access_token({"sub": db_user.email, "role": db_user.role})
    response = JSONResponse({"ok": True})
    _set_auth_cookies(response, new_access)
    return response


# ---------------------------------------------------------------------------
# Dependency: usuario desde cookie (mantiene la firma original para no romper)
# ---------------------------------------------------------------------------
def get_current_user_from_cookie(
    request: Request, db: Session = Depends(get_db)
):
    # 1) Si el middleware ya lo cargó, reusar
    user = getattr(request.state, "user", None)
    if user is not None:
        return user

    # 2) Fallback: decodificar access_token directo
    access_token = request.cookies.get("access_token")
    payload = decode_token(access_token, expected_type="access") if access_token else None
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="No token cookie")

    db_user = db.query(User).filter(User.email == payload["sub"]).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return db_user


# ---------------------------------------------------------------------------
# Home (mantenido por compatibilidad; home_router también expone /home)
# ---------------------------------------------------------------------------
@router.get("/home-auth")
def index(request: Request, user: User = Depends(get_current_user_from_cookie)):
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "user": user}
    )


# ---------------------------------------------------------------------------
# Logout: borra ambas cookies
# ---------------------------------------------------------------------------
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return response
