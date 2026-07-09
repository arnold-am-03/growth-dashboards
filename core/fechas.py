"""
Fecha de subida de un archivo de datos.

Prioriza la fecha del ultimo commit que toco el archivo (git conserva la
historia real de cuando se subio la data, y Render mantiene el repositorio
clonado en tiempo de ejecucion). Si git no esta disponible, cae a la fecha
de modificacion del archivo en disco (en local es la fecha real de copia;
tras un deploy equivale a la fecha del deploy).
"""

from __future__ import annotations

import datetime
import os
import subprocess
from pathlib import Path

_MESES_MIN = ["ene", "feb", "mar", "abr", "may", "jun",
              "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt(ts: float) -> str:
    d = datetime.datetime.fromtimestamp(ts)
    return f"{d.day} {_MESES_MIN[d.month - 1]} {d.year}"


def fecha_subida(path) -> str | None:
    """Fecha (es-PE corta) en que se subio/actualizo el archivo."""
    path = Path(path)
    if not path.exists():
        return None

    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", path.name],
            capture_output=True, text=True, timeout=5, cwd=str(path.parent),
        )
        crudo = out.stdout.strip()
        if out.returncode == 0 and crudo:
            return _fmt(int(crudo))
    except Exception:
        pass

    try:
        return _fmt(os.path.getmtime(path))
    except OSError:
        return None


def fecha_subida_dir(dirpath) -> str | None:
    """Fecha de subida mas reciente entre los archivos de un directorio,
    priorizando el archivo de seguimiento si existe."""
    dirpath = Path(dirpath)
    if not dirpath.is_dir():
        return None
    archivos = sorted(dirpath.glob("*.csv"))
    if not archivos:
        return None
    seguimiento = [a for a in archivos
                   if "Seguimiento" in a.name or "2026" in a.name]
    objetivo = seguimiento[0] if seguimiento else archivos[-1]
    return fecha_subida(objetivo)
