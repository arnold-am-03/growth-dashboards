"""
App principal. Sirve el mosaico de proyectos y, por cada proyecto, sus
vistas (proyección, seguimiento, etc.).

Las rutas son genéricas: no conocen ningún proyecto en concreto. Todo
sale del registro que arma core.registry a partir de las carpetas.
"""

import os

from flask import Flask, abort, redirect, render_template, request, url_for
from jinja2 import ChoiceLoader, FileSystemLoader

from core.auth import init_auth
from core.registry import (
    BASE_DIR,
    PROJECTS_DIR,
    STATIC_DIR,
    TEMPLATES_DIR,
    discover_projects,
)

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)

# El loader busca primero en /templates (base, índice) y luego dentro de
# /projects, lo que permite referenciar las vistas como
# "<carpeta>/templates/<vista>.html".
app.jinja_loader = ChoiceLoader(
    [
        FileSystemLoader(str(TEMPLATES_DIR)),
        FileSystemLoader(str(PROJECTS_DIR)),
    ]
)

# Protege toda la plataforma detrás de un inicio de sesión.
init_auth(app)

# --- Registro y caché --------------------------------------------------

_REGISTRY = {}
_DATA_CACHE = {}


def get_registry():
    global _REGISTRY
    if not _REGISTRY:
        _REGISTRY = discover_projects()
    return _REGISTRY


def get_project_data(project, refresh=False):
    if refresh or project.slug not in _DATA_CACHE:
        _DATA_CACHE[project.slug] = project.build()
    return _DATA_CACHE[project.slug]


# --- Rutas -------------------------------------------------------------


@app.route("/")
def index():
    projects = sorted(get_registry().values(), key=lambda p: (p.order, p.title))
    kpis = []
    tags_path = BASE_DIR / "tags.json"
    if tags_path.exists():
        import json
        kpis = json.loads(tags_path.read_text(encoding="utf-8")).get("kpis", [])
    return render_template("index.html", projects=projects, kpis=kpis)


@app.route("/p/<slug>")
def project_home(slug):
    project = get_registry().get(slug)
    if not project or not project.views:
        abort(404)
    return redirect(url_for("project_view", slug=slug, view=project.views[0]["slug"]))


@app.route("/p/<slug>/<view>")
def project_view(slug, view):
    project = get_registry().get(slug)
    if not project or view not in project.view_slugs:
        abort(404)

    refresh = request.args.get("refresh") == "1"
    data = get_project_data(project, refresh=refresh)
    context = data.get(view, {})

    # notas contextuales/metodológicas opcionales del proyecto
    notas_tpl = None
    if (project.path / "templates" / "_notas.html").exists():
        notas_tpl = f"{project.dirname}/templates/_notas.html"

    return render_template(
        project.template_for(view),
        project=project,
        views=project.views,
        current_view=view,
        notas_tpl=notas_tpl,
        **context,
    )


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    # Local: python app.py  ->  http://127.0.0.1:5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
