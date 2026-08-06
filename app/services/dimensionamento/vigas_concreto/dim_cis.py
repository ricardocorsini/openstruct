"""
Autor: Ricardo Corsini de Carvalho
Data: 11/11/2025
GitHub: https://github.com/ricardocorsini

Módulo: Dimensionamento ao esforço cortante (Modelo I - NBR 6118)
Descrição: Implementa o cálculo de verificação e dimensionamento de elementos
           retangulares de concreto armado submetidos ao esforço cortante.

A rotina permite considerar dois casos para a contribuição do concreto Vc:

1) Flexão simples:
       Vc = Vc0

2) Flexocompressão:
       Vc = Vc0 * (1 + M0 / MSd,max) <= 2 * Vc0

   Para seção retangular, na direção da altura h:
       M0 = N0 * h / 6

   onde:
       N0      = força normal de compressão concomitante com VSd, calculada
                 para a tensão normal com gamma_f = 1,0 [kN]
       h       = altura da seção na direção da flexão [m]
       MSd,max = momento fletor de cálculo máximo no trecho analisado [kN.m]

CONVENÇÃO DE UNIDADES
---------------------
Geometria: bw, h, d -> cm
Forças: Vk, Vd, Vc, VRd2, Vsw -> kN
Momentos: M0, MSd,max -> kN.m
Resistências: fck, fywk, fcd, fywd, fctm, fctd -> MPa
Armadura transversal: Asw/s -> cm²/m
"""

import numpy as np


class Beam:
    """
    Representa um elemento retangular de concreto armado submetido ao cortante.

    Parâmetros
    ----------
    name : str
        Identificação do elemento.
    bw : float
        Largura resistente ao cisalhamento, em cm.
    h : float
        Altura total da seção, em cm.
    Vk : float
        Esforço cortante característico, em kN.
    gama_c : float
        Coeficiente parcial do concreto.
    gama_c2 : float
        Coeficiente de majoração de Vk para obtenção de Vd.
    fywk : float
        Resistência característica do aço transversal, em MPa.
    gama_s : float
        Coeficiente parcial do aço.
    fck : float
        Resistência característica do concreto, em MPa.
    stirrup_leg : int
        Número de ramos resistentes do estribo.
    considerar_flexocompressao : bool, optional
        Quando True, corrige Vc para o caso de flexocompressão.
    N0 : float | None, optional
        Força normal de compressão concomitante com VSd, em kN, utilizada
        na determinação de M0 com gamma_f = 1,0. Informar como valor positivo.
    MSd_max : float | None, optional
        Valor absoluto do momento fletor de cálculo máximo no trecho, em kN.m.

    Observação
    ----------
    A rotina é específica para seção retangular na determinação automática de M0:

        M0 = N0 * h / 6

    com h convertido de cm para m.
    """

    def __init__(
        self,
        name,
        bw,
        h,
        Vk,
        gama_c,
        gama_c2,
        fywk,
        gama_s,
        fck,
        stirrup_leg,
        considerar_flexocompressao=False,
        N0=None,
        MSd_max=None,
    ):
        self.name = name
        self.bw = bw  # cm
        self.h = h  # cm
        self.Vk = Vk  # kN
        self.gama_c = gama_c
        self.gama_c2 = gama_c2
        self.fywk = fywk  # MPa
        self.gama_s = gama_s
        self.fck = fck  # MPa
        self.stirrup_leg = stirrup_leg

        # Caso opcional de flexocompressão.
        self.considerar_flexocompressao = considerar_flexocompressao
        self.N0 = N0  # kN; compressão positiva; gamma_f = 1,0 para cálculo de M0
        self.MSd_max = MSd_max  # kN.m; valor absoluto do momento de cálculo

        self._validate_flexocompression_input()

        # Propriedades derivadas.
        self.d = self.h - 5  # cm (estimativa mantida da rotina original)
        self.Vd = self.Vk * self.gama_c2  # kN

        # Propriedades do concreto e do aço.
        self.material_props = self._concrete_properties()

    def __str__(self):
        return f"{self.name} - {self.bw:.1f} x {self.h:.1f} cm"

    def _validate_flexocompression_input(self):
        """Valida os dados necessários para a correção de Vc por flexocompressão."""
        if not self.considerar_flexocompressao:
            return

        if self.N0 is None:
            raise ValueError(
                "Para considerar flexocompressão, informe N0 em kN "
                "(força normal concomitante com VSd, com gamma_f = 1,0)."
            )

        if self.MSd_max is None:
            raise ValueError(
                "Para considerar flexocompressão, informe MSd_max em kN.m."
            )

        if self.N0 < 0:
            raise ValueError(
                "N0 deve ser informado como módulo positivo da força normal de compressão."
            )

        if self.MSd_max <= 0:
            raise ValueError("MSd_max deve ser maior que zero.")

    def _concrete_properties(self):
        """Calcula as propriedades do concreto e do aço, em MPa."""
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
        """Verifica a compressão diagonal (VRd2), com resultado em kN."""
        alpha_v2 = 1 - (self.fck / 250)

        # fcd [MPa] / 10 = fcd [kN/cm²].
        # bw [cm] * d [cm] -> cm².
        # Resultado: VRd2 [kN].
        vrd2 = (
            0.27
            * alpha_v2
            * (self.material_props["fcd (MPa)"] / 10)
            * self.bw
            * self.d
        )

        status = "ok" if self.Vd <= vrd2 else "disapproved"

        return {
            "alphaV2": round(alpha_v2, 3),
            "Vrd2 (kN)": round(vrd2, 2),
            "Vd (kN)": round(self.Vd, 2),
            "status": status,
        }

    def _concrete_shear_contribution(self):
        """
        Calcula Vc conforme o caso selecionado.

        Flexão simples:
            Vc = Vc0

        Flexocompressão:
            Vc = Vc0 * (1 + M0 / MSd,max) <= 2 * Vc0

        Para seção retangular:
            M0 = N0 * h / 6

        Unidades utilizadas em M0:
            N0 [kN]
            h  [m]
            M0 [kN.m]
        """
        fctd = self.material_props["fctd (MPa)"]

        # fctd [MPa] / 10 = kN/cm²; bw*d = cm²; logo Vc0 em kN.
        vc0 = 0.6 * (fctd / 10) * self.bw * self.d

        if not self.considerar_flexocompressao:
            return {
                "tipo_Vc": "flexao_simples",
                "Vc0 (kN)": vc0,
                "N0 (kN)": None,
                "M0 (kN.m)": None,
                "MSd_max (kN.m)": None,
                "fator_Vc_calculado": 1.0,
                "fator_Vc": 1.0,
                "fator_Vc_limitado": False,
                "Vc (kN)": vc0,
            }

        # h deve entrar em metros para que N0 [kN] * h [m] resulte em kN.m.
        h_m = self.h / 100.0
        m0 = self.N0 * h_m / 6.0

        fator_vc_calculado = 1.0 + (m0 / self.MSd_max)
        fator_vc = min(fator_vc_calculado, 2.0)
        vc = vc0 * fator_vc

        return {
            "tipo_Vc": "flexocompressao",
            "Vc0 (kN)": vc0,
            "N0 (kN)": self.N0,
            "M0 (kN.m)": m0,
            "MSd_max (kN.m)": self.MSd_max,
            "fator_Vc_calculado": fator_vc_calculado,
            "fator_Vc": fator_vc,
            "fator_Vc_limitado": fator_vc_calculado > 2.0,
            "Vc (kN)": vc,
        }

    def tension_cis(self):
        """Dimensiona a armadura transversal (Asw/s) e verifica VRd3."""
        fctm = self.material_props["fctm (MPa)"]
        fywd = self.material_props["fywd (MPa)"]

        vc_data = self._concrete_shear_contribution()
        vc = vc_data["Vc (kN)"]

        # Asw,min/s em cm²/cm; multiplicando por 100 -> cm²/m.
        asw_min_cm = 0.2 * fctm * (self.bw / self.fywk)
        asw_min_m = asw_min_cm * 100

        # Vsw,min em kN.
        Vsw_min = asw_min_cm * 0.9 * self.d * (fywd / 10)
        vrd3_min = Vsw_min + vc

        if self.Vd <= vrd3_min:
            asw_adot = asw_min_m
            status = "asw = armadura mínima"
        else:
            # Resultado intermediário em cm²/cm; x100 -> cm²/m.
            asw_adot = 100 * (self.Vd - vc) / (0.9 * self.d * (fywd / 10))
            status = "asw = acima da mínima"

        return {
            "tipo_Vc": vc_data["tipo_Vc"],
            "Vc0 (kN)": round(vc_data["Vc0 (kN)"], 2),
            "N0 (kN)": None if vc_data["N0 (kN)"] is None else round(vc_data["N0 (kN)"], 2),
            "M0 (kN.m)": None if vc_data["M0 (kN.m)"] is None else round(vc_data["M0 (kN.m)"], 3),
            "MSd_max (kN.m)": (
                None
                if vc_data["MSd_max (kN.m)"] is None
                else round(vc_data["MSd_max (kN.m)"], 3)
            ),
            "fator_Vc_calculado": round(vc_data["fator_Vc_calculado"], 4),
            "fator_Vc": round(vc_data["fator_Vc"], 4),
            "fator_Vc_limitado": vc_data["fator_Vc_limitado"],
            "Vc (kN)": round(vc, 2),
            "asw_min (cm2/cm)": round(asw_min_cm, 4),
            "asw_min (cm2/m)": round(asw_min_m, 3),
            "Vsw_min (kN)": round(Vsw_min, 2),
            "Vrd3_min (kN)": round(vrd3_min, 2),
            "StatusTension": status,
            "asw_adot (cm2/m)": round(asw_adot, 3),
        }

    def detailing(self):
        """Gera tabela de espaçamento sugerido conforme a bitola dos estribos."""
        asw_adot = self.tension_cis()["asw_adot (cm2/m)"]
        diameters = np.array([5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0, 40.0])

        # Diâmetro em mm / 10 -> cm; resultado das áreas em cm² por estribo.
        areas = self.stirrup_leg * np.pi * (diameters / 10) ** 2 / 4

        # areas [cm²] / Asw [cm²/m] -> m; x100 -> cm.
        spacing = (areas / asw_adot) * 100
        spacing = np.floor(spacing)

        return {
            "Diameter (mm)": list(diameters),
            "Spacing (cm)": list(spacing.astype(float)),
        }

    def results_dim_cis(self):
        """Executa todas as verificações e consolida os resultados."""
        return {
            "results_concrete": self.material_props,
            "results_compressed_cis": self.compressed_cis(),
            "results_tension": self.tension_cis(),
            "results_detailing": self.detailing(),
        }
