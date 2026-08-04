"""Dimensionamento à flexão simples de vigas retangulares de concreto armado.

O módulo trabalha no ELU, recebe o momento de cálculo ``Msd`` e usa o bloco
retangular equivalente de compressão do concreto. A rotina contempla armadura
simples e dupla e não executa o detalhamento físico das barras na seção.

Referência de projeto indicada: ABNT NBR 6118:2026. A utilização em projeto
deve ser acompanhada por conferência independente do engenheiro responsável.
"""

from __future__ import annotations

from math import isfinite, log, sqrt
from typing import Any, Dict, Optional


NORMA_REFERENCIA = "ABNT NBR 6118:2026"


class FlexureDesignError(ValueError):
    """Erro de entrada ou de inviabilidade geométrica do dimensionamento."""


class RectangularBeamFlexure:
    """Dimensiona uma seção retangular submetida à flexão simples.

    Todas as dimensões geométricas são informadas em centímetros, as
    resistências em MPa e o momento de cálculo em kN.m.
    """

    def __init__(
        self,
        *,
        name: str,
        bw_cm: float,
        h_cm: float,
        momento_sd_kn_m: float,
        fck_mpa: float,
        fyk_mpa: float = 500.0,
        gamma_c: float = 1.4,
        gamma_s: float = 1.15,
        es_mpa: float = 210_000.0,
        beta_redistribuicao: float = 1.0,
        cobrimento_cm: float = 3.0,
        diametro_estribo_mm: float = 5.0,
        diametro_barra_tracao_mm: float = 16.0,
        diametro_barra_compressao_mm: Optional[float] = None,
        d_cm: Optional[float] = None,
        d_linha_cm: Optional[float] = None,
        considerar_armadura_minima: bool = True,
    ) -> None:
        self.name = name.strip()
        self.bw_cm = float(bw_cm)
        self.h_cm = float(h_cm)
        self.momento_sd_kn_m = float(momento_sd_kn_m)
        self.fck_mpa = float(fck_mpa)
        self.fyk_mpa = float(fyk_mpa)
        self.gamma_c = float(gamma_c)
        self.gamma_s = float(gamma_s)
        self.es_mpa = float(es_mpa)
        self.beta_redistribuicao = float(beta_redistribuicao)
        self.cobrimento_cm = float(cobrimento_cm)
        self.diametro_estribo_mm = float(diametro_estribo_mm)
        self.diametro_barra_tracao_mm = float(diametro_barra_tracao_mm)
        self.diametro_barra_compressao_mm = float(
            diametro_barra_compressao_mm
            if diametro_barra_compressao_mm is not None
            else diametro_barra_tracao_mm
        )
        self.d_informado_cm = float(d_cm) if d_cm is not None else None
        self.d_linha_informado_cm = (
            float(d_linha_cm) if d_linha_cm is not None else None
        )
        self.considerar_armadura_minima = considerar_armadura_minima

        self._validate_inputs()
        self.d_cm, self.d_linha_cm = self._effective_depths()
        self._validate_geometry()

    def _validate_inputs(self) -> None:
        if not self.name:
            raise FlexureDesignError("A identificação da viga não pode ser vazia.")

        positive_values = {
            "bw_cm": self.bw_cm,
            "h_cm": self.h_cm,
            "momento_sd_kn_m": self.momento_sd_kn_m,
            "fck_mpa": self.fck_mpa,
            "fyk_mpa": self.fyk_mpa,
            "gamma_c": self.gamma_c,
            "gamma_s": self.gamma_s,
            "es_mpa": self.es_mpa,
            "cobrimento_cm": self.cobrimento_cm,
            "diametro_estribo_mm": self.diametro_estribo_mm,
            "diametro_barra_tracao_mm": self.diametro_barra_tracao_mm,
            "diametro_barra_compressao_mm": self.diametro_barra_compressao_mm,
        }
        for field_name, value in positive_values.items():
            if not isfinite(value) or value <= 0:
                raise FlexureDesignError(
                    f"O parâmetro '{field_name}' deve ser um número finito e positivo."
                )

        for field_name, value in {
            "d_cm": self.d_informado_cm,
            "d_linha_cm": self.d_linha_informado_cm,
        }.items():
            if value is not None and (not isfinite(value) or value <= 0):
                raise FlexureDesignError(
                    f"O parâmetro '{field_name}' deve ser positivo quando informado."
                )

        if not 20.0 <= self.fck_mpa <= 90.0:
            raise FlexureDesignError(
                "A rotina aceita fck entre 20 MPa e 90 MPa."
            )
        if not 0.75 <= self.beta_redistribuicao <= 1.0:
            raise FlexureDesignError(
                "beta_redistribuicao deve estar entre 0,75 e 1,00."
            )

    def _effective_depths(self) -> tuple[float, float]:
        estribo_cm = self.diametro_estribo_mm / 10.0
        barra_tracao_cm = self.diametro_barra_tracao_mm / 10.0
        barra_compressao_cm = self.diametro_barra_compressao_mm / 10.0

        d_calculado = self.h_cm - (
            self.cobrimento_cm + estribo_cm + barra_tracao_cm / 2.0
        )
        d_linha_calculado = (
            self.cobrimento_cm + estribo_cm + barra_compressao_cm / 2.0
        )

        return (
            self.d_informado_cm
            if self.d_informado_cm is not None
            else d_calculado,
            self.d_linha_informado_cm
            if self.d_linha_informado_cm is not None
            else d_linha_calculado,
        )

    def _validate_geometry(self) -> None:
        if not 0 < self.d_cm < self.h_cm:
            raise FlexureDesignError(
                "A altura útil d deve estar entre zero e a altura total h."
            )
        if not 0 < self.d_linha_cm < self.h_cm:
            raise FlexureDesignError(
                "A distância d' deve estar entre zero e a altura total h."
            )
        if self.d_linha_cm >= self.d_cm:
            raise FlexureDesignError("A distância d' deve ser menor que a altura útil d.")

    def _material_properties(self) -> Dict[str, float]:
        fck = self.fck_mpa
        if fck <= 50.0:
            fctm = 0.3 * fck ** (2.0 / 3.0)
            epsilon_cu = 3.5 / 1000.0
            alpha_c = 0.85
            lambda_ = 0.80
            xi_lim = 0.8 * self.beta_redistribuicao - 0.35
        else:
            fctm = 2.12 * log(1.0 + 0.11 * fck)
            epsilon_cu = (2.6 + 35.0 * ((90.0 - fck) / 100.0) ** 4) / 1000.0
            alpha_c = 0.85 * (1.0 - (fck - 50.0) / 200.0)
            lambda_ = 0.80 - (fck - 50.0) / 400.0
            xi_lim = 0.8 * self.beta_redistribuicao - 0.45

        fcd = fck / self.gamma_c
        fyd = self.fyk_mpa / self.gamma_s
        sigma_cd = alpha_c * fcd

        if xi_lim <= 0:
            raise FlexureDesignError(
                "A profundidade relativa limite da linha neutra resultou não positiva."
            )

        return {
            "fcd_mpa": fcd,
            "fyd_mpa": fyd,
            "fctm_mpa": fctm,
            "fctk_superior_mpa": 1.3 * fctm,
            "epsilon_cu": epsilon_cu,
            "alpha_c": alpha_c,
            "lambda": lambda_,
            "sigma_cd_mpa": sigma_cd,
            "xi_lim": xi_lim,
        }

    def _steel_state(
        self, *, x_cm: float, depth_cm: float, compression: bool, props: Dict[str, float]
    ) -> tuple[float, float]:
        if x_cm <= 0:
            raise FlexureDesignError("A profundidade da linha neutra deve ser positiva.")

        if compression:
            strain = props["epsilon_cu"] * (x_cm - depth_cm) / x_cm
        else:
            strain = props["epsilon_cu"] * (depth_cm - x_cm) / x_cm

        if strain <= 0:
            return strain, 0.0
        stress_mpa = min(self.es_mpa * strain, props["fyd_mpa"])
        return strain, stress_mpa

    def _simple_design_for_moment(
        self, momento_kn_m: float, props: Dict[str, float]
    ) -> Dict[str, float]:
        sigma_cd_kn_cm2 = props["sigma_cd_mpa"] / 10.0
        mu = (momento_kn_m * 100.0) / (
            sigma_cd_kn_cm2 * self.bw_cm * self.d_cm**2
        )
        discriminant = 1.0 - 2.0 * mu
        if discriminant < -1e-12:
            raise FlexureDesignError(
                "O momento não pode ser resolvido como armadura simples."
            )

        xi = (1.0 - sqrt(max(discriminant, 0.0))) / props["lambda"]
        x_cm = xi * self.d_cm
        strain_s, stress_s_mpa = self._steel_state(
            x_cm=x_cm,
            depth_cm=self.d_cm,
            compression=False,
            props=props,
        )
        if stress_s_mpa <= 0:
            raise FlexureDesignError("A tensão calculada na armadura tracionada é nula.")

        concrete_force_kn = (
            sigma_cd_kn_cm2
            * self.bw_cm
            * props["lambda"]
            * x_cm
        )
        as_cm2 = concrete_force_kn / (stress_s_mpa / 10.0)

        return {
            "mu": mu,
            "xi": xi,
            "x_cm": x_cm,
            "epsilon_s": strain_s,
            "sigma_s_mpa": stress_s_mpa,
            "as_cm2": as_cm2,
        }

    def _minimum_reinforcement(
        self, props: Dict[str, float], momento_limite_kn_m: float
    ) -> Dict[str, float]:
        area_concreto_cm2 = self.bw_cm * self.h_cm
        modulo_resistente_cm3 = self.bw_cm * self.h_cm**2 / 6.0
        momento_minimo_kn_m = (
            0.8
            * modulo_resistente_cm3
            * props["fctk_superior_mpa"]
            * 0.001
        )
        momento_para_calculo = min(momento_minimo_kn_m, momento_limite_kn_m)
        as_por_momento = self._simple_design_for_moment(
            momento_para_calculo, props
        )["as_cm2"]
        as_taxa_absoluta = 0.0015 * area_concreto_cm2

        return {
            "momento_minimo_kn_m": momento_minimo_kn_m,
            "as_por_momento_cm2": as_por_momento,
            "as_taxa_015_cm2": as_taxa_absoluta,
            "as_minima_cm2": max(as_por_momento, as_taxa_absoluta),
        }

    @staticmethod
    def _rounded(data: Dict[str, Any], digits: int = 6) -> Dict[str, Any]:
        rounded: Dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, float):
                rounded[key] = round(value, digits)
            elif isinstance(value, dict):
                rounded[key] = RectangularBeamFlexure._rounded(value, digits)
            else:
                rounded[key] = value
        return rounded

    def calculate(self) -> Dict[str, Any]:
        """Executa o dimensionamento e retorna resultados serializáveis em JSON."""

        props = self._material_properties()
        lambda_ = props["lambda"]
        xi_lim = props["xi_lim"]
        x_lim_cm = xi_lim * self.d_cm
        mu_lim = lambda_ * xi_lim * (1.0 - 0.5 * lambda_ * xi_lim)
        sigma_cd_kn_cm2 = props["sigma_cd_mpa"] / 10.0
        momento_limite_kn_m = (
            mu_lim
            * sigma_cd_kn_cm2
            * self.bw_cm
            * self.d_cm**2
            / 100.0
        )

        min_reinf = self._minimum_reinforcement(props, momento_limite_kn_m)
        avisos = []

        if self.momento_sd_kn_m <= momento_limite_kn_m + 1e-9:
            simple = self._simple_design_for_moment(self.momento_sd_kn_m, props)
            tipo_armadura = "simples"
            x_cm = simple["x_cm"]
            xi = simple["xi"]
            as_tracao_calculada_cm2 = simple["as_cm2"]
            as_compressao_calculada_cm2 = 0.0
            epsilon_s = simple["epsilon_s"]
            sigma_s_mpa = simple["sigma_s_mpa"]
            epsilon_s_linha = 0.0
            sigma_s_linha_mpa = 0.0
            momento_concreto_kn_m = self.momento_sd_kn_m
            momento_armadura_dupla_kn_m = 0.0
        else:
            tipo_armadura = "dupla"
            x_cm = x_lim_cm
            xi = xi_lim

            if self.d_linha_cm >= x_lim_cm:
                raise FlexureDesignError(
                    "A armadura dupla é inviável: d' deve ser menor que x_lim. "
                    "Aumente a seção ou informe a geometria real das armaduras."
                )

            epsilon_s, sigma_s_mpa = self._steel_state(
                x_cm=x_lim_cm,
                depth_cm=self.d_cm,
                compression=False,
                props=props,
            )
            epsilon_s_linha, sigma_s_linha_mpa = self._steel_state(
                x_cm=x_lim_cm,
                depth_cm=self.d_linha_cm,
                compression=True,
                props=props,
            )
            if sigma_s_linha_mpa <= 0:
                raise FlexureDesignError(
                    "A armadura de compressão não está na região comprimida da seção."
                )

            concrete_force_kn = (
                sigma_cd_kn_cm2 * self.bw_cm * lambda_ * x_lim_cm
            )
            as_equilibrio_concreto_cm2 = concrete_force_kn / (
                sigma_s_mpa / 10.0
            )
            momento_excedente_kn_m = self.momento_sd_kn_m - momento_limite_kn_m
            forca_armadura_dupla_kn = (
                momento_excedente_kn_m * 100.0
                / (self.d_cm - self.d_linha_cm)
            )
            as_compressao_calculada_cm2 = forca_armadura_dupla_kn / (
                sigma_s_linha_mpa / 10.0
            )
            as_tracao_adicional_cm2 = forca_armadura_dupla_kn / (
                sigma_s_mpa / 10.0
            )
            as_tracao_calculada_cm2 = (
                as_equilibrio_concreto_cm2 + as_tracao_adicional_cm2
            )
            momento_concreto_kn_m = momento_limite_kn_m
            momento_armadura_dupla_kn_m = momento_excedente_kn_m
            avisos.append(
                "A seção exige armadura dupla; avalie também o aumento da altura da viga."
            )

        as_minima_cm2 = (
            min_reinf["as_minima_cm2"]
            if self.considerar_armadura_minima
            else 0.0
        )
        as_tracao_adotada_cm2 = max(as_tracao_calculada_cm2, as_minima_cm2)
        area_concreto_cm2 = self.bw_cm * self.h_cm
        taxa_tracao_percentual = 100.0 * as_tracao_adotada_cm2 / area_concreto_cm2
        taxa_total_percentual = 100.0 * (
            as_tracao_adotada_cm2 + as_compressao_calculada_cm2
        ) / area_concreto_cm2
        taxa_total_ok = taxa_total_percentual <= 4.0 + 1e-9

        if as_tracao_adotada_cm2 > as_tracao_calculada_cm2 + 1e-9:
            avisos.append("A armadura mínima governou a armadura tracionada adotada.")
        if not taxa_total_ok:
            avisos.append(
                "A soma das armaduras longitudinais supera 4% da área de concreto; "
                "redimensione a seção."
            )

        result = {
            "norma_referencia": NORMA_REFERENCIA,
            "materiais": {
                "fck_mpa": self.fck_mpa,
                "fyk_mpa": self.fyk_mpa,
                "fcd_mpa": props["fcd_mpa"],
                "fyd_mpa": props["fyd_mpa"],
                "fctm_mpa": props["fctm_mpa"],
                "fctk_superior_mpa": props["fctk_superior_mpa"],
                "es_mpa": self.es_mpa,
                "alpha_c": props["alpha_c"],
                "lambda": lambda_,
                "epsilon_cu_por_mil": props["epsilon_cu"] * 1000.0,
                "sigma_cd_mpa": props["sigma_cd_mpa"],
            },
            "geometria": {
                "bw_cm": self.bw_cm,
                "h_cm": self.h_cm,
                "d_cm": self.d_cm,
                "d_linha_cm": self.d_linha_cm,
                "d_foi_informado": self.d_informado_cm is not None,
                "d_linha_foi_informado": self.d_linha_informado_cm is not None,
                "area_concreto_cm2": area_concreto_cm2,
            },
            "solicitacao": {
                "momento_sd_kn_m": self.momento_sd_kn_m,
                "momento_limite_armadura_simples_kn_m": momento_limite_kn_m,
                "momento_minimo_normativo_kn_m": min_reinf["momento_minimo_kn_m"],
                "momento_resistido_pelo_concreto_kn_m": momento_concreto_kn_m,
                "momento_resistido_pelo_binario_de_aco_kn_m": momento_armadura_dupla_kn_m,
            },
            "linha_neutra": {
                "x_cm": x_cm,
                "x_sobre_d": xi,
                "x_lim_cm": x_lim_cm,
                "x_lim_sobre_d": xi_lim,
                "mu_lim": mu_lim,
            },
            "armaduras": {
                "tipo": tipo_armadura,
                "as_tracao_calculada_cm2": as_tracao_calculada_cm2,
                "as_tracao_adotada_cm2": as_tracao_adotada_cm2,
                "as_compressao_calculada_cm2": as_compressao_calculada_cm2,
                "as_minima_por_momento_cm2": min_reinf["as_por_momento_cm2"],
                "as_minima_taxa_015_cm2": min_reinf["as_taxa_015_cm2"],
                "as_minima_considerada_cm2": as_minima_cm2,
                "taxa_tracao_percentual": taxa_tracao_percentual,
                "taxa_total_percentual": taxa_total_percentual,
            },
            "deformacoes_e_tensoes": {
                "epsilon_s_tracao_por_mil": epsilon_s * 1000.0,
                "sigma_s_tracao_mpa": sigma_s_mpa,
                "epsilon_s_compressao_por_mil": epsilon_s_linha * 1000.0,
                "sigma_s_compressao_mpa": sigma_s_linha_mpa,
            },
            "verificacoes": {
                "momento_atendido": True,
                "linha_neutra_no_limite_de_ductilidade": xi <= xi_lim + 1e-9,
                "taxa_total_ate_4_porcento": taxa_total_ok,
                "status": "dimensionado" if taxa_total_ok else "redimensionar",
            },
            "avisos": avisos,
        }
        return self._rounded(result)


def dimensionar_viga_retangular_flexao(**kwargs: Any) -> Dict[str, Any]:
    """Atalho funcional para uso pelo router e por outros serviços."""

    return RectangularBeamFlexure(**kwargs).calculate()
