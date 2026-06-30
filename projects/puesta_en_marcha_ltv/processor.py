"""
Procesador del proyecto "Puesta en Marcha LTV".

Replica la lógica de la notebook (Puesta_en_Marcha_LTV.ipynb):

  - Proyección  -> Data_2025.csv : impacto ESPERADO a partir del histórico.
  - Seguimiento -> Data_2026.csv : impacto REAL desde el lanzamiento (27-mar-2026).

Expone una única función pública: build(), que la app llama una vez y
cachea. Devuelve un dict { "proyeccion": {...}, "seguimiento": {...} }
con el contexto que consumen las plantillas.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).resolve().parent / "data"
FECHA_LANZAMIENTO = "2026-03-27"

ZONAS_PROPUESTA = ["LIMA TOP", "LIMA MODERNA", "LIMA ESTE"]
ZONAS_PRINCIPALES = ["LIMA TOP", "LIMA MODERNA", "LOS OLIVOS (COMERCIAL)"]


# --- Regla de negocio: LTV máximo por operación ------------------------


def calcular_ltv_maximo(row):
    riesgo = str(row.get("Riesgo", "")).strip()
    zona = str(row.get("Sub zona", "")).strip().upper()
    tipo_fondo = str(row.get("Tipo de Fondo", "")).strip()
    esquema = str(row.get("Esquema", "")).strip()

    es_p2p = tipo_fondo == "Inversionista P2P"
    ltv = np.nan

    categoria_zona = "PRINCIPAL" if zona in ZONAS_PRINCIPALES else "OTROS"

    if riesgo in ["Bajo", "Bajo Medio"]:
        if categoria_zona == "PRINCIPAL":
            ltv = 0.55 if es_p2p else 0.50
        else:
            ltv = 0.45 if es_p2p else 0.40
    elif riesgo == "Moderado":
        if categoria_zona == "PRINCIPAL":
            ltv = 0.55 if es_p2p else 0.50
        else:
            ltv = 0.40
    elif riesgo == "Moderado Medio":
        ltv = 0.50 if categoria_zona == "PRINCIPAL" else 0.40
    elif riesgo == "Medio":
        ltv = 0.40 if categoria_zona == "PRINCIPAL" else 0.25
    elif riesgo == "Alto":
        if zona == "LIMA TOP":
            ltv = 0.35
        elif zona == "LIMA MODERNA":
            ltv = 0.30
        else:
            ltv = 0.15
        # Riesgo alto solo se permite con cuota fija
        if esquema != "Cuota Fija":
            return np.nan

    # Tope de 50% para esquemas distintos de cuota fija
    if esquema != "Cuota Fija" and pd.notna(ltv) and ltv > 0.50:
        ltv = 0.50

    return ltv


# --- Helpers de formato (es-PE) ----------------------------------------


def soles(valor, decimales=0):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    return "S/ " + f"{valor:,.{decimales}f}"


def millones(valor):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    return f"S/ {valor / 1_000_000:,.2f} M"


def pct(valor, decimales=1):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    return f"{valor * 100:,.{decimales}f}%"


def num(valor, decimales=1):
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    return f"{valor:,.{decimales}f}"


# --- Cálculo de cada vista ---------------------------------------------


def _proyeccion():
    df = pd.read_csv(DATA_DIR / "Data_2025.csv").copy()

    df["LTV_Maximo"] = df.apply(calcular_ltv_maximo, axis=1)
    df["Marca_LTV"] = df["LTV_Maximo"] > df["LTV"]
    df["¿Aplica propuesta?"] = (
        (df["Esquema"] == "Cuota Fija")
        & (df["Sub zona"].isin(ZONAS_PROPUESTA))
        & (df["Situacion del credito"] == "RYA")
    )
    df["Marca Contrato"] = df["Codigo de Contrato"].isna() == False  # noqa: E712
    df["Es un caso"] = (df["¿Aplica propuesta?"] & df["Marca_LTV"]) | (
        df["¿Aplica propuesta?"] & (df["Detalle Excepcion"] == "Ratio > al permitido")
    )

    casos = df[df["Es un caso"]]
    cerrados = df[df["Es un caso"] & df["Marca Contrato"]]
    no_cerrados = df[df["Es un caso"] & (df["Marca Contrato"] == False)]  # noqa: E712

    n_casos = len(casos)
    n_cerr = len(cerrados)
    n_noc = len(no_cerrados)
    conv = n_cerr / n_casos if n_casos else float("nan")

    vol_hist = cerrados["Monto Desembolsado Solarizado"].sum()
    vol_pot = vol_hist + no_cerrados["Monto Desembolsado Solarizado"].sum()
    adicional = vol_pot - vol_hist

    ticket_cerr = cerrados["Monto Desembolsado Solarizado"].mean()
    dias = casos["Dias de Cierre"].mean()

    return {
        "n_casos": n_casos,
        "n_cerrados": n_cerr,
        "n_no_cerrados": n_noc,
        "conv": conv,
        "vol_hist": vol_hist,
        "vol_pot": vol_pot,
        "adicional": adicional,
        "ticket": ticket_cerr,
        "dias": dias,
        "f": {
            "n_casos": f"{n_casos}",
            "n_cerrados": f"{n_cerr}",
            "n_no_cerrados": f"{n_noc}",
            "conv": pct(conv),
            "vol_hist": millones(vol_hist),
            "vol_pot": millones(vol_pot),
            "vol_hist_full": soles(vol_hist),
            "vol_pot_full": soles(vol_pot),
            "adicional": soles(adicional),
            "ticket": soles(ticket_cerr),
            "dias": num(dias),
        },
        # Para la barra comparativa histórico vs potencial
        "bar_pct": round(vol_hist / vol_pot * 100, 1) if vol_pot else 0,
    }


def _seguimiento(proy):
    df = pd.read_csv(DATA_DIR / "Data_2026.csv").copy()

    df["Fecha de Creacion"] = pd.to_datetime(df["Fecha de Creacion"])
    df["Fecha de Cierre"] = pd.to_datetime(df["Fecha de Cierre"])
    df["Marca_Lanzamiento"] = np.where(
        df["Fecha de Cierre"] >= FECHA_LANZAMIENTO, "Sí", "No"
    )

    df["¿Aplica propuesta?"] = (
        (df["Esquema"] == "Cuota Fija")
        & (df["Sub zona"].isin(ZONAS_PROPUESTA))
        & (df["Situacion del credito"] == "RYA")
        & (df["Marca_Lanzamiento"] == "Sí")
    )
    df["Marca Contrato"] = df["Codigo de Contrato"].isna() == False  # noqa: E712
    df["LTV_Maximo"] = df.apply(calcular_ltv_maximo, axis=1)
    df["Marca_LTV"] = df["LTV_Maximo"] > df["LTV"]
    df["Es un caso"] = (df["¿Aplica propuesta?"] & df["Marca_LTV"]) | (
        df["¿Aplica propuesta?"] & (df["Detalle Excepcion"] == "Ratio > al permitido")
    )

    casos = df[df["Es un caso"]]
    cerrados = df[df["Es un caso"] & df["Marca Contrato"]]
    no_cerrados = df[df["Es un caso"] & (df["Marca Contrato"] == False)]  # noqa: E712

    n_casos = len(casos)
    n_cerr = len(cerrados)
    n_noc = len(no_cerrados)
    conv = n_cerr / n_casos if n_casos else float("nan")

    vol_cerr = cerrados["Monto Desembolsado Solarizado"].sum()
    ticket_cerr = cerrados["Monto Desembolsado Solarizado"].mean()
    dias = casos["Dias de Cierre"].mean()

    # Deltas esperado (proyección) vs real (seguimiento)
    def delta(real, esperado):
        if esperado in (None, 0) or (isinstance(esperado, float) and np.isnan(esperado)):
            return None
        return (real - esperado) / esperado

    return {
        "n_casos": n_casos,
        "n_cerrados": n_cerr,
        "n_no_cerrados": n_noc,
        "conv": conv,
        "vol_cerr": vol_cerr,
        "ticket": ticket_cerr,
        "dias": dias,
        "f": {
            "n_casos": f"{n_casos}",
            "n_cerrados": f"{n_cerr}",
            "n_no_cerrados": f"{n_noc}",
            "conv": pct(conv),
            "vol_cerr": millones(vol_cerr),
            "vol_cerr_full": soles(vol_cerr),
            "ticket": soles(ticket_cerr),
            "dias": num(dias),
        },
        # Comparación esperado vs real (mismas métricas, distinto periodo)
        "comp": [
            {
                "label": "Conversión",
                "esperado": pct(proy["conv"]),
                "real": pct(conv),
                "delta": delta(conv, proy["conv"]),
                "mejor": "alto",
            },
            {
                "label": "Ticket promedio",
                "esperado": soles(proy["ticket"]),
                "real": soles(ticket_cerr),
                "delta": delta(ticket_cerr, proy["ticket"]),
                "mejor": "alto",
            },
            {
                "label": "Días de cierre",
                "esperado": num(proy["dias"]),
                "real": num(dias),
                "delta": delta(dias, proy["dias"]),
                "mejor": "bajo",
            },
        ],
    }


def build():
    proy = _proyeccion()
    seg = _seguimiento(proy)
    return {"proyeccion": proy, "seguimiento": seg}
