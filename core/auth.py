"""
Autenticación simple para toda la plataforma.

Diseño y garantías de seguridad:

  - La contraseña NO está en el código ni se envía al navegador. Vive en una
    variable de entorno del servidor (Render), idealmente como hash.
  - Se prefiere APP_PASSWORD_HASH (hash PBKDF2 generado con werkzeug). Como
    alternativa de conveniencia se admite APP_PASSWORD (texto plano), que
    igual permanece del lado servidor y nunca llega al cliente.
  - La sesión se guarda en una cookie FIRMADA con SECRET_KEY. Sin esa clave
    nadie puede falsificar una sesión válida.
  - La cookie es HttpOnly (no accesible por JavaScript) y Secure en producción
    (solo viaja por HTTPS, que Render ya provee).
  - Todas las rutas quedan detrás del login salvo la propia pantalla de acceso
    y los archivos estáticos (para que cargue el CSS del login).

Para generar el hash:  python scripts/gen_password_hash.py
"""

from __future__ import annotations

import datetime
import hmac
import os
from urllib.parse import urlparse

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__)

# Endpoints que se pueden visitar sin haber iniciado sesión.
OPEN_ENDPOINTS = {"auth.login", "static"}


def _verify(candidate: str) -> bool:
    """Compara el intento contra el hash (preferente) o el texto plano."""
    if not candidate:
        return False
    hashed = os.environ.get("APP_PASSWORD_HASH")
    if hashed:
        try:
            return check_password_hash(hashed, candidate)
        except Exception:
            return False
    plain = os.environ.get("APP_PASSWORD")
    if plain:
        return hmac.compare_digest(plain, candidate)
    return False


def is_authenticated() -> bool:
    return bool(session.get("auth"))


def _safe_next(target: str) -> str:
    """Evita open-redirect: solo admite rutas internas relativas."""
    if not target:
        return "/"
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return "/"
    if not target.startswith("/") or target.startswith("//"):
        return "/"
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if is_authenticated():
        return redirect(url_for("index"))

    nxt = _safe_next(request.values.get("next", ""))
    error = None

    if request.method == "POST":
        if _verify(request.form.get("password", "")):
            session.clear()
            session["auth"] = True
            session.permanent = True
            return redirect(nxt)
        error = "Contraseña incorrecta."

    return render_template("login.html", error=error, next=nxt)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


def init_auth(app):
    """Configura sesión, registra rutas y protege toda la app."""
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        # Clave efímera: sirve en local, pero invalida sesiones en cada
        # reinicio. En producción SIEMPRE definir SECRET_KEY en Render.
        secret = os.urandom(32).hex()
        app.logger.warning(
            "SECRET_KEY no definido; usando clave efímera (solo desarrollo)."
        )

    app.secret_key = secret
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not app.debug,
        PERMANENT_SESSION_LIFETIME=datetime.timedelta(days=7),
    )

    app.register_blueprint(auth_bp)

    @app.before_request
    def _require_login():
        if request.endpoint in OPEN_ENDPOINTS:
            return None
        if is_authenticated():
            return None
        return redirect(url_for("auth.login", next=request.path))
