"""
Autor: Ricardo Corsini de Carvalho
Data: 11/11/2025
GitHub: https://github.com/ricardocorsini

Módulo: Dimensionamento ao esforço cortante (Modelo I - NBR 6118/2024)
Descrição: Implementa o cálculo de verificação e dimensionamento de vigas de concreto armado
           submetidas ao esforço cortante.

Testado por: YYYY
Data de teste: YYYY
"""

import numpy as np
import pandas as pd


class Beam:
    """
    Representa uma viga de concreto armado submetida ao esforço cortante.

    Parâmetros
    ----------
    name : str
        Identificação da viga.
    bw : float
        Largura da viga (cm).
    h : float
        Altura total da viga (cm).
    Vk : float
        Esforço cortante característico (kN).
    gama_c : float
        Fator de minoração do concreto (fck).
    gama_c2 : float
        Fator de majoração do esforço cortante (Vk).
    fywk : float
        Resistência característica do aço (MPa).
    gama_s : float
        Fator de minoração do aço.
    fck : float
        Resistência característica do concreto (MPa).
    stirrup_leg : int
        Número de ramos do estribo.
    """

    def __init__(self, name, bw, h, Vk, gama_c, gama_c2, fywk, gama_s, fck, stirrup_leg):
        self.name = name
        self.bw = bw
        self.h = h
        self.Vk = Vk
        self.gama_c = gama_c
        self.gama_c2 = gama_c2
        self.fywk = fywk
        self.gama_s = gama_s
        self.fck = fck
        self.stirrup_leg = stirrup_leg

        # propriedades derivadas
        self.d = self.h - 5  # cm (estimativa)
        self.Vd = self.Vk * self.gama_c2  # kN

        # cálculo inicial das propriedades do concreto e aço
        self.material_props = self._concrete_properties()

    def __str__(self):
        return f"{self.name} - {self.bw:.1f} x {self.h:.1f} cm"

    def _concrete_properties(self):
        """Calcula as propriedades do concreto e aço."""
        fcd = self.fck / self.gama_c
        fywd = self.fywk / self.gama_s
        fctm = 0.3 * self.fck ** (2 / 3)
        fctk_inf = 0.7 * fctm
        fctd = fctk_inf / self.gama_c

        return {
            "fck (MPa)": self.fck,
            "fcd (MPa)": fcd,
            "fywd (MPa)": fywd,
            "fctm (MPa)": fctm,
            "fctk_inf (MPa)": fctk_inf,
            "fctd (MPa)": fctd,
        }

    def compressed_cis(self):
        """Verifica a compressão diagonal (VRd2)."""
        alpha_v2 = 1 - (self.fck / 250)
        vrd2 = 0.27 * alpha_v2 * (self.material_props["fcd (MPa)"] / 10) * self.bw * self.d

        status = "ok" if self.Vd <= vrd2 else "disapproved"

        return {
            "alphaV2": round(alpha_v2, 3),
            "Vrd2 (kN)": round(vrd2, 2),
            "Vd (kN)": round(self.Vd, 2),
            "status": status,
        }

    def tension_cis(self):
        """Dimensiona a armadura transversal (asw) e verifica a resistência VRd3."""
        fctd = self.material_props["fctd (MPa)"]
        fctm = self.material_props["fctm (MPa)"]
        fywd = self.material_props["fywd (MPa)"]

        Vc = 0.6 * (fctd / 10) * self.bw * self.d
        asw_min_cm = 0.2 * fctm * (self.bw / self.fywk)
        asw_min_m = asw_min_cm * 100
        Vsw_min = asw_min_cm * 0.9 * self.d * (fywd / 10)
        vrd3_min = Vsw_min + Vc

        if self.Vd <= vrd3_min:
            asw_adot = asw_min_m
            status = "asw = armadura mínima"
        else:
            asw_adot = 100 * (self.Vd - Vc) / (0.9 * self.d * (fywd / 10))
            status = "asw = acima da mínima"

        return {
            "Vc (kN)": round(Vc, 2),
            "asw_min (cm2/cm)": round(asw_min_cm, 4),
            "asw_min (cm2/m)": round(asw_min_m, 3),
            "Vsw_min (kN)": round(Vsw_min, 2),
            "Vrd3_min (kN)": round(vrd3_min, 2),
            "StatusTension": status,
            "asw_adot (cm2/m)": round(asw_adot, 3),
        }

    def detailing(self):
        """Gera tabela de espaçamento sugerido conforme bitola dos estribos."""
        asw_adot = self.tension_cis()["asw_adot (cm2/m)"]
        diameters = np.array([5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0, 40.0])
        areas = self.stirrup_leg * np.pi * (diameters / 10) ** 2 / 4  # cm² por estribo

        spacing = (areas / asw_adot) * 100  # cm
        spacing = np.floor(spacing)

        return {
            "Diameter (mm)": list(diameters),
            "Spacing (cm)": list(spacing.astype(float)),
        }

    def results_dim_cis(self):
        """Executa todas as verificações e consolida resultados."""
        return {
            "results_concrete": self.material_props,
            "results_compressed_cis": self.compressed_cis(),
            "results_tension": self.tension_cis(),
            "results_detailing": self.detailing(),
        }
