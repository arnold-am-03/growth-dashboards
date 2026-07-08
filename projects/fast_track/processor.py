"""
Procesador del proyecto "Fast Track".

Consume la DATA DE SALIDA de las notebooks (Proyeccion_Final.ipynb /
Seguimiento_Final.ipynb), que ya traen las comisiones calculadas contra el
tarifario (proceso en Excel que no se traslada aqui). Para actualizar:

    data/Data_Historica.csv    (export estandar de pandas, con indice)
    data/Data_Seguimiento.csv  (export: sep=';', decimal=',')

El lector detecta ambos formatos automaticamente.

La propuesta: canalizar como Fast Track las operaciones P2P Digital de Cuota
Fija en soles. La metrica central es la COMISION (recaudacion).

Definiciones (heredadas de las notebooks y validadas contra la plantilla):
  Proyeccion (base 2025, contratos cerrados):
    - Caso     = "Es Caso en Historico"
                 (P2P & Cuota Fija & PEN & Digital & Fast Track)        245
    - Comision Proyectada = Ratio_Comision_Real_Ideal
                            x COMISION SD. SI FT MONTO IDEAL
                 (la comision que se habria cobrado con el tarifario FT,
                  manteniendo la posicion real de cada caso frente al ideal)
    - Adicional = Comision Proyectada - Comision
  Seguimiento (2026, lanzamiento 25-abr-2026):
    - Caso      = "Condicion Fuerte + Es Caso en Seguimiento"
                  (FT post-lanzamiento cuya comision supera la ideal
                   ajustada sin propuesta)
    - Esperada  = "AJUSTADA COMISION SD. NO FT MONTO IDEAL"
    - Adicional = Comision - Esperada
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from core.charts import dual_bar_chart, increment_bars, line_chart  # noqa: E402

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).resolve().parent / "data"
FECHA_LANZAMIENTO = "25 abr 2026"

COL_IDEAL_FT = "COMISION SD. SI FT MONTO IDEAL"
COL_ESPERADA = "AJUSTADA COMISION SD. NO FT MONTO IDEAL"
COL_CASO_SEG = "Condicion Fuerte + Es Caso en Seguimiento"

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


# --- Helpers de formato (es-PE) ----------------------------------------


def soles(v, dec=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return "S/ " + f"{v:,.{dec}f}"


def millones(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"S/ {v / 1_000_000:,.2f} M"


def miles(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"S/ {v / 1000:,.2f} mil"


def pct(v, dec=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"{v * 100:,.{dec}f}%"


def num(v, dec=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"{v:,.{dec}f}"


def _mes(periodo):
    p = int(periodo)
    return MESES[(p % 100) - 1], p // 100


def _rango(rows):
    labels = [_mes(r["per"])[0] for r in rows]
    a0, a1 = _mes(rows[0]["per"])[1], _mes(rows[-1]["per"])[1]
    return (f"{labels[0]} - {labels[-1]} {a1}" if a0 == a1
            else f"{labels[0]} {a0} - {labels[-1]} {a1}")


def _leer(nombre):
    """Detecta el formato del export: ';' con decimal ',' o CSV estandar
    (en cuyo caso descarta la columna indice si viene sin nombre)."""
    path = DATA_DIR / nombre
    with open(path, encoding="utf-8") as fh:
        primera = fh.readline()
    if ";" in primera:
        return pd.read_csv(path, sep=";", decimal=",")
    df = pd.read_csv(path)
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(columns=df.columns[0])
    return df


# --- Evolucion (comision real vs. proyectada/esperada) ------------------


def _bloque_evolucion(rows, name_a, name_b, en_miles=False):
    if not rows:
        return None

    labels = [_mes(r["per"])[0] for r in rows]
    y_fmt = ((lambda v: f"{v / 1000:,.0f}k") if en_miles
             else (lambda v: f"{v / 1000:,.0f}k"))

    points = [
        {"label": labels[i], "a": r["com_a"], "b": r["com_b"],
         "caption": f"{r['n']} casos"}
        for i, r in enumerate(rows)
    ]

    series = [
        {"label": "Casos",
         "svg": line_chart(labels, [r["n"] for r in rows],
                           y_fmt=lambda v: f"{v:.0f}",
                           tip_fmt=lambda v: f"{v:.0f} casos")},
        {"label": "Comisión adicional por caso",
         "svg": line_chart(labels, [r["adic_caso"] for r in rows],
                           y_fmt=lambda v: f"S/{v:,.0f}",
                           tip_fmt=lambda v: soles(v))},
        {"label": "Recaudación adicional del mes",
         "svg": line_chart(labels, [r["adic"] for r in rows],
                           y_fmt=lambda v: f"S/{v / 1000:,.0f}k",
                           tip_fmt=lambda v: soles(v))},
    ]

    return {
        "rango": _rango(rows),
        "vol_title": "Comisión por mes",
        "vol_unit": f"{name_a} vs. {name_b}, soles",
        "vol_chart": dual_bar_chart(
            points,
            y_fmt=y_fmt,
            tip_fmt=lambda v: soles(v),
            name_a=name_a,
            name_b=name_b,
        ),
        "series": series,
    }


# --- Vistas ------------------------------------------------------------


def _proyeccion():
    df = _leer("Data_Historica.csv")
    casos = df[df["Es Caso en Historico"] == True].copy()  # noqa: E712
    casos["proy"] = casos["Ratio_Comision_Real_Ideal"] * casos[COL_IDEAL_FT]
    casos["adic"] = casos["proy"] - casos["Comision"]

    n_casos, n_total = len(casos), len(df)
    com_hist = casos["Comision"].sum()
    com_proy = casos["proy"].sum()
    adicional = com_proy - com_hist

    rows = []
    for per, g in casos.groupby("Periodo de Cierre"):
        if pd.isna(per):
            continue
        rows.append({
            "per": int(per),
            "n": len(g),
            "com_a": g["Comision"].sum(),
            "com_b": g["proy"].sum(),
            "adic": g["adic"].sum(),
            "adic_caso": g["adic"].mean(),
        })
    rows.sort(key=lambda r: r["per"])

    n_mes = [r["n"] for r in rows]
    adic_caso_mes = [r["adic_caso"] for r in rows]
    esc_min = min(adic_caso_mes) * min(n_mes) if rows else float("nan")
    esc_max = max(adic_caso_mes) * max(n_mes) if rows else float("nan")
    meses_n = len(rows)

    return {
        "datos_hasta": _hasta(df),
        "f": {
            "n_casos": f"{n_casos}",
            "com_caso": soles(casos["Comision"].mean()),
            "com_total": millones(com_hist),
            "dias": num(casos["Dias de Cierre"].mean()),
            "adic_caso": soles(casos["adic"].mean()),
            "adicional": soles(adicional),
            "com_hist_full": soles(com_hist),
            "com_proy_full": soles(com_proy),
            "g_cerrados": f"{n_total:,}",
            "g_cerrados_mes": num(n_total / meses_n, 0) if meses_n else "-",
            "g_com_caso": soles(df["Comision"].mean()),
            "g_com_total": millones(df["Comision"].sum()),
            "g_dias": num(df["Dias de Cierre"].mean()),
            "g_tasa_casos": pct(n_casos / n_total) if n_total else "-",
            "g_ratio": num(casos["Ratio Comision/Monto"].mean(), 2),
            "r_adic_caso": f"{soles(min(adic_caso_mes))} – {soles(max(adic_caso_mes))}",
            "r_casos": f"{min(n_mes)} – {max(n_mes)}",
            "r_casos_prom": num(sum(n_mes) / meses_n, 1) if meses_n else "-",
            "r_recaud": f"{miles(esc_min)} – {miles(esc_max)}",
        },
        "inc_chart": increment_bars(com_hist, com_proy, fmt=lambda v: soles(v),
                                    label_a="Histórica", label_b="Proyectada"),
        "uplift": pct(adicional / com_hist) if com_hist else "-",
        "evol": _bloque_evolucion(rows, "Comisión real", "Comisión proyectada"),
        "_raw": {
            "adic_caso_min_mes": min(adic_caso_mes) if rows else float("nan"),
            "casos_mes_min": min(n_mes) if rows else float("nan"),
            "esc_min": esc_min,
            "tasa_casos": n_casos / n_total if n_total else float("nan"),
            "ratio": casos["Ratio Comision/Monto"].mean(),
        },
    }


def _seguimiento(proy_raw):
    df = _leer("Data_Seguimiento.csv")
    post = df[df["Marca_25_Abril_Cierre"] == "Sí"].copy()
    casos = post[post[COL_CASO_SEG] == True].copy()  # noqa: E712
    casos["adic"] = casos["Comision"] - casos[COL_ESPERADA]

    n_casos = len(casos)
    com_real = casos["Comision"].sum()
    com_esp = casos[COL_ESPERADA].sum()
    adicional = com_real - com_esp

    rows = []
    for per, g in casos.groupby("Periodo de Cierre"):
        if pd.isna(per):
            continue
        rows.append({
            "per": int(per),
            "n": len(g),
            "com_a": g[COL_ESPERADA].sum(),
            "com_b": g["Comision"].sum(),
            "adic": g["adic"].sum(),
            "adic_caso": g["adic"].mean(),
        })
    rows.sort(key=lambda r: r["per"])
    meses_n = len(rows) or 1
    pers = [r["per"] for r in rows]

    # tasa de casos FT por mes, desde el primer mes con casos (los cierres
    # del mes parcial del lanzamiento no pueden ser casos por los tiempos
    # de cierre, asi que no se cuentan)
    base_tasa = post[post["Periodo de Cierre"].isin(pers)]
    tasa_mes = base_tasa.groupby("Periodo de Cierre")["Es Caso en Seguimiento"].mean()
    tasa_real = tasa_mes.mean() if len(tasa_mes) else float("nan")
    ratio_real = casos["Ratio Comision/Monto"].mean()

    glob = df[df["Periodo de Cierre"].isin(pers)]
    cerrados_mes = len(glob) / meses_n

    adic_caso_real = casos["adic"].mean()
    casos_mes_real = n_casos / meses_n
    adic_mes_real = adicional / meses_n

    def delta(real, esp):
        if esp in (None, 0) or (isinstance(esp, float) and np.isnan(esp)):
            return None
        return (real - esp) / esp

    return {
        "datos_hasta": _hasta(df),
        "f": {
            "n_casos": f"{n_casos}",
            "n_meses": f"{meses_n}",
            "com_real": miles(com_real),
            "com_real_full": soles(com_real),
            "adicional": miles(adicional),
            "adicional_full": soles(adicional),
            "adic_caso": soles(adic_caso_real),
            "dias": num(casos["Dias de Cierre"].mean()),
            "ratio": num(ratio_real, 2),
            "cerrados_mes": f"{int(cerrados_mes + 0.5):,}",
        },
        "comp": [
            {"label": "Comisión total del segmento",
             "esperado": miles(com_esp), "real": miles(com_real),
             "delta": delta(com_real, com_esp), "mejor": "alto"},
            {"label": "Comisión adicional por caso",
             "esperado": soles(proy_raw["adic_caso_min_mes"]),
             "real": soles(adic_caso_real),
             "delta": delta(adic_caso_real, proy_raw["adic_caso_min_mes"]),
             "mejor": "alto", "ref": "mínimo histórico"},
            {"label": "Casos por mes",
             "esperado": num(proy_raw["casos_mes_min"], 0),
             "real": num(casos_mes_real, 1),
             "delta": delta(casos_mes_real, proy_raw["casos_mes_min"]),
             "mejor": "alto", "ref": "mínimo histórico"},
            {"label": "Recaudación adicional mensual",
             "esperado": miles(proy_raw["esc_min"]),
             "real": miles(adic_mes_real),
             "delta": delta(adic_mes_real, proy_raw["esc_min"]),
             "mejor": "alto", "ref": "escenario mínimo"},
            {"label": "Tasa de casos (Fast Track)",
             "esperado": pct(proy_raw["tasa_casos"]), "real": pct(tasa_real),
             "delta": delta(tasa_real, proy_raw["tasa_casos"]),
             "mejor": "alto", "ref": "histórico 2025"},
            {"label": "Ratio comisión/monto",
             "esperado": num(proy_raw["ratio"], 2), "real": num(ratio_real, 2),
             "delta": delta(ratio_real, proy_raw["ratio"]),
             "mejor": "alto", "ref": "histórico 2025"},
        ],
        "evol": _bloque_evolucion(rows, "Comisión esperada", "Comisión real",
                                  en_miles=True),
    }


def build():
    proy = _proyeccion()
    seg = _seguimiento(proy.pop("_raw"))
    return {"proyeccion": proy, "seguimiento": seg}


# --- Fecha de corte de los datos ----------------------------------------

_MESES_MIN = ["ene", "feb", "mar", "abr", "may", "jun",
              "jul", "ago", "sep", "oct", "nov", "dic"]


def _hasta(df):
    """Fecha maxima de cierre presente en la data: hasta cuando esta
    actualizado el dashboard."""
    try:
        f = pd.to_datetime(df["Fecha de Cierre"], errors="coerce").max()
        if pd.isna(f):
            return None
        return f"{f.day} {_MESES_MIN[f.month - 1]} {f.year}"
    except Exception:
        return None
