"""
Descubrimiento automático de proyectos.

Cada carpeta dentro de /projects que contenga un meta.json se registra
como un dashboard. No hay que tocar el código de la app para sumar uno
nuevo: basta con copiar una carpeta que respete la convención.

Convención de carpeta de proyecto:

    projects/<carpeta>/
        meta.json            -> ficha del proyecto (título, vistas, etc.)
        data/                -> archivos de datos crudos (csv, xls, ...)
        processor.py         -> expone build() -> {vista: contexto}
        templates/<vista>.html

El procesador se importa de forma aislada y su resultado se cachea en la
app, de modo que el cálculo pesado (leer CSVs, aplicar reglas) corre una
sola vez por arranque y no en cada request.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
PROJECTS_DIR = BASE_DIR / "projects"
STATIC_DIR = BASE_DIR / "static"


class Project:
    """Un dashboard descubierto en /projects."""

    def __init__(self, path: Path, meta: dict, module):
        self.path = path
        self.dirname = path.name
        self.meta = meta
        self.module = module

    @property
    def slug(self) -> str:
        return self.meta.get("slug", self.dirname)

    @property
    def title(self) -> str:
        return self.meta.get("title", self.dirname.replace("_", " ").title())

    @property
    def subtitle(self) -> str:
        return self.meta.get("subtitle", "")

    @property
    def description(self) -> str:
        return self.meta.get("description", "")

    @property
    def tag(self) -> str:
        return self.meta.get("tag", "")

    @property
    def order(self) -> int:
        return int(self.meta.get("order", 999))

    @property
    def views(self) -> list[dict]:
        return self.meta.get("views", [])

    @property
    def view_slugs(self) -> list[str]:
        return [v["slug"] for v in self.views]

    def template_for(self, view: str) -> str:
        # Ruta namespaceada por carpeta para evitar colisiones entre
        # proyectos que tengan vistas con el mismo nombre.
        return f"{self.dirname}/templates/{view}.html"

    def build(self) -> dict:
        """Ejecuta el procesador del proyecto y devuelve {vista: contexto}."""
        if self.module and hasattr(self.module, "build"):
            return self.module.build()
        return {}


def _load_processor(path: Path):
    proc_path = path / "processor.py"
    if not proc_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        f"projects_{path.name}_processor", proc_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_projects() -> dict[str, Project]:
    """Recorre /projects y registra cada carpeta válida."""
    registry: dict[str, Project] = {}
    if not PROJECTS_DIR.exists():
        return registry

    for child in sorted(PROJECTS_DIR.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith((".", "_")):
            continue
        meta_path = child / "meta.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        module = _load_processor(child)
        project = Project(child, meta, module)
        registry[project.slug] = project

    return registry
