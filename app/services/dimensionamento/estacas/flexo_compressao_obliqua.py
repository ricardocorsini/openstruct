"""Verificação de seções circulares à flexocompressão oblíqua.

O equilíbrio da seção é resolvido pelo ``concreteproperties``. Este módulo
adiciona as convenções de unidades da openStruct, um modelo de materiais de
projeto parametrizado para comparação com a NBR 6118 e a busca de alternativas
comerciais de armadura longitudinal.

Importante: ``concreteproperties`` não contém um módulo oficial da NBR 6118.
Por isso, todos os parâmetros constitutivos utilizados são expostos na resposta
e a classificação não substitui as demais verificações normativas.
"""

from __future__ import annotations

import importlib.metadata
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TF_PARA_N = 9_806.65
TF_M_PARA_N_MM = TF_PARA_N * 1_000.0
TOLERANCIA = 1e-9
MAXIMO_COMBINACOES = 80


class ErroFlexoCompressaoObliqua(ValueError):
    """Indica dados incompatíveis com o modelo seccional adotado."""


class DependenciaConcretePropertiesAusente(RuntimeError):
    """Indica que o pacote concreteproperties não está instalado."""


class FalhaAnaliseSecao(RuntimeError):
    """Indica falha numérica durante a análise de uma ou mais seções."""


@dataclass(frozen=True)
class SecaoCircularFCO:
    diametro_m: float
    cobrimento_nominal_mm: float
    diametro_armadura_transversal_mm: float = 6.3
    angulo_inicial_barras_graus: float = 0.0


@dataclass(frozen=True)
class MateriaisFCO:
    fck_mpa: float
    fyk_mpa: float = 500.0
    gamma_c: float = 1.40
    gamma_s: float = 1.15
    fator_reducao_concreto: float = 0.85
    modulo_elasticidade_aco_mpa: float = 200_000.0
    modulo_elasticidade_concreto_mpa: Optional[float] = None
    deformacao_concreto_inicio_patamar: float = 0.002
    deformacao_ultima_concreto: float = 0.0035
    expoente_parabola_concreto: float = 2.0
    deformacao_ultima_aco: float = 0.010


@dataclass(frozen=True)
class EsforcosFCO:
    normal_compressao_sd_tf: float
    momento_x_sd_tf_m: float
    momento_y_sd_tf_m: float


@dataclass(frozen=True)
class CatalogoArmadurasFCO:
    bitolas_longitudinais_mm: Sequence[float]
    quantidades_barras: Sequence[int]
    combinacoes_explicitas: Sequence[Tuple[int, float]] = ()
    espacamento_livre_minimo_mm: float = 20.0
    pontos_diagrama: int = 24
    pontos_contorno_secao: int = 48
    parar_na_primeira_opcao_por_bitola: bool = True
    incluir_diagrama_recomendacao: bool = True
    modo_verificacao: str = "direcional"
    tolerancia_angular_graus: float = 0.05
    max_iteracoes_angulo: int = 8


@dataclass
class DimensionadorFlexoCompressaoObliqua:
    secao: SecaoCircularFCO
    materiais: MateriaisFCO
    esforcos: EsforcosFCO
    catalogo: CatalogoArmadurasFCO

    def analisar(self) -> Dict[str, Any]:
        self._validar_entradas()
        combinacoes, modo_catalogo = self._combinacoes()
        deps = self._carregar_dependencias()
        material_concreto, material_aco = self._criar_materiais(deps)

        opcoes: List[Dict[str, Any]] = []
        interrompidas_por_bitola: Dict[float, int] = {}
        incluir_diagrama_durante_catalogo = (
            self.catalogo.incluir_diagrama_recomendacao
            and self.catalogo.modo_verificacao == "diagrama_completo"
        )

        if modo_catalogo == "grade":
            por_bitola: Dict[float, List[int]] = {}
            for quantidade, bitola in combinacoes:
                por_bitola.setdefault(bitola, []).append(quantidade)

            for bitola in sorted(por_bitola):
                quantidades = sorted(set(por_bitola[bitola]))
                encontrou = False
                for indice, quantidade in enumerate(quantidades):
                    opcao = self._analisar_opcao(
                        deps=deps,
                        material_concreto=material_concreto,
                        material_aco=material_aco,
                        quantidade=quantidade,
                        bitola_mm=bitola,
                        incluir_diagrama=incluir_diagrama_durante_catalogo,
                    )
                    opcoes.append(opcao)
                    if opcao["atende"]:
                        encontrou = True
                        if self.catalogo.parar_na_primeira_opcao_por_bitola:
                            interrompidas_por_bitola[bitola] = (
                                len(quantidades) - indice - 1
                            )
                            break
                if not encontrou:
                    interrompidas_por_bitola.setdefault(bitola, 0)
        else:
            for quantidade, bitola in combinacoes:
                opcoes.append(
                    self._analisar_opcao(
                        deps=deps,
                        material_concreto=material_concreto,
                        material_aco=material_aco,
                        quantidade=quantidade,
                        bitola_mm=bitola,
                        incluir_diagrama=incluir_diagrama_durante_catalogo,
                    )
                )

        candidatas = [opcao for opcao in opcoes if opcao["atende"]]
        recomendacao_original = min(
            candidatas,
            key=lambda item: (
                item["area_aco_total_cm2"],
                item["quantidade_barras"],
                item["diametro_barra_mm"],
            ),
            default=None,
        )

        diagrama_recomendacao: List[Dict[str, float]] = []
        recomendacao = (
            dict(recomendacao_original) if recomendacao_original else None
        )
        if recomendacao and self.catalogo.incluir_diagrama_recomendacao:
            if self.catalogo.modo_verificacao == "diagrama_completo":
                diagrama_recomendacao = recomendacao.pop(
                    "diagrama_mx_my_tf_m", []
                )
            else:
                detalhada = self._analisar_opcao(
                    deps=deps,
                    material_concreto=material_concreto,
                    material_aco=material_aco,
                    quantidade=recomendacao["quantidade_barras"],
                    bitola_mm=recomendacao["diametro_barra_mm"],
                    incluir_diagrama=True,
                )
                diagrama_recomendacao = detalhada.pop(
                    "diagrama_mx_my_tf_m", []
                )
                recomendacao = detalhada

        # Os contornos das demais alternativas sao dados temporarios. A API
        # devolve somente o contorno recomendado para manter a resposta leve.
        for opcao in opcoes:
            opcao.pop("diagrama_mx_my_tf_m", None)

        resumo_por_bitola = self._resumir_por_bitola(
            opcoes=opcoes,
            combinacoes=combinacoes,
            nao_avaliadas=interrompidas_por_bitola,
        )
        parametros = self._parametros_calculados()

        return {
            "sistema_unidades": {
                "forca": "tf",
                "momento": "tf.m",
                "dimensao_secao": "m",
                "armaduras_cobrimento": "mm",
                "area_aco": "cm²",
                "tensao": "MPa",
                "deformacao": "adimensional",
            },
            "metodo": {
                "analise": "compatibilidade de deformacoes e equilibrio seccional",
                "biblioteca": "concreteproperties",
                "versao_biblioteca": deps["versao"],
                "modelo_normativo": "NBR 6118 parametrizado pela openStruct",
                "status_modelo_normativo": (
                    "nao e um modulo NBR oficial do concreteproperties"
                ),
                "criterio_atendimento": (
                    "capacidade resistente na direcao de (Mxd, Myd) para Nsd"
                    if self.catalogo.modo_verificacao == "direcional"
                    else "ponto (Mxd, Myd) dentro do diagrama biaxial para Nsd"
                ),
                "modo_verificacao": self.catalogo.modo_verificacao,
                "otimizacao_secao_circular": (
                    "busca direcional do angulo da linha neutra e expansao "
                    "do contorno pela simetria da armadura"
                    if self.catalogo.modo_verificacao == "direcional"
                    else None
                ),
                "criterio_recomendacao": (
                    "menor area de aco entre as candidatas avaliadas que atendem"
                ),
            },
            "secao": {
                "tipo": "circular macica",
                "diametro_m": self.secao.diametro_m,
                "area_bruta_m2": math.pi * self.secao.diametro_m**2 / 4.0,
                "cobrimento_nominal_mm": self.secao.cobrimento_nominal_mm,
                "diametro_armadura_transversal_mm": (
                    self.secao.diametro_armadura_transversal_mm
                ),
                "angulo_inicial_barras_graus": (
                    self.secao.angulo_inicial_barras_graus
                ),
                "pontos_contorno_numerico": self.catalogo.pontos_contorno_secao,
            },
            "materiais": {
                "entrada": {
                    "fck_mpa": self.materiais.fck_mpa,
                    "fyk_mpa": self.materiais.fyk_mpa,
                    "gamma_c": self.materiais.gamma_c,
                    "gamma_s": self.materiais.gamma_s,
                    "fator_reducao_concreto": (
                        self.materiais.fator_reducao_concreto
                    ),
                },
                "calculo": parametros,
            },
            "esforcos_solicitantes": {
                "normal_compressao_sd_tf": (
                    self.esforcos.normal_compressao_sd_tf
                ),
                "momento_x_sd_tf_m": self.esforcos.momento_x_sd_tf_m,
                "momento_y_sd_tf_m": self.esforcos.momento_y_sd_tf_m,
                "momento_resultante_sd_tf_m": math.hypot(
                    self.esforcos.momento_x_sd_tf_m,
                    self.esforcos.momento_y_sd_tf_m,
                ),
                "angulo_momento_graus": math.degrees(
                    math.atan2(
                        self.esforcos.momento_y_sd_tf_m,
                        self.esforcos.momento_x_sd_tf_m,
                    )
                ),
            },
            "catalogo": {
                "modo": modo_catalogo,
                "bitolas_longitudinais_mm": sorted(
                    {bitola for _, bitola in combinacoes}
                ),
                "quantidades_barras": sorted(
                    {quantidade for quantidade, _ in combinacoes}
                ),
                "espacamento_livre_minimo_mm": (
                    self.catalogo.espacamento_livre_minimo_mm
                ),
                "pontos_diagrama": self.catalogo.pontos_diagrama,
                "modo_verificacao": self.catalogo.modo_verificacao,
                "tolerancia_angular_graus": (
                    self.catalogo.tolerancia_angular_graus
                ),
                "max_iteracoes_angulo": self.catalogo.max_iteracoes_angulo,
                "parar_na_primeira_opcao_por_bitola": (
                    self.catalogo.parar_na_primeira_opcao_por_bitola
                    if modo_catalogo == "grade"
                    else False
                ),
                "quantidade_combinacoes_solicitadas": len(combinacoes),
                "quantidade_opcoes_avaliadas": len(opcoes),
            },
            "opcoes": opcoes,
            "resumo_por_bitola": resumo_por_bitola,
            "recomendacao": recomendacao,
            "diagrama_recomendacao_mx_my_tf_m": diagrama_recomendacao,
            "avisos": [
                (
                    "O modelo verifica apenas a resistencia da secao no ELU. "
                    "Nao inclui efeitos locais/globais de segunda ordem, "
                    "imperfeicoes, fluencia, fissuracao, cisalhamento ou fadiga."
                ),
                (
                    "A verificacao de espacamento usa o valor minimo informado "
                    "na requisicao; cobrimento, armadura minima/maxima, emendas, "
                    "ancoragem e demais regras de detalhamento devem ser verificados."
                ),
                (
                    "As resistencias usam fcd_diagrama = fator_reducao_concreto "
                    "x fck/gamma_c e fyd = fyk/gamma_s, mostrados na resposta."
                ),
                (
                    "No modo direcional, a utilizacao e obtida na direcao exata "
                    "do vetor solicitante apos convergencia do angulo resistente. "
                    "No modo diagrama_completo, usa-se a intersecao radial com "
                    "o poligono resistente discretizado."
                ),
                (
                    "Valide os resultados com casos independentes antes do uso "
                    "em projeto; o endpoint foi estruturado para facilitar essa auditoria."
                ),
            ],
        }

    def _validar_entradas(self) -> None:
        valores_positivos = {
            "diametro_m": self.secao.diametro_m,
            "fck_mpa": self.materiais.fck_mpa,
            "fyk_mpa": self.materiais.fyk_mpa,
            "gamma_c": self.materiais.gamma_c,
            "gamma_s": self.materiais.gamma_s,
            "fator_reducao_concreto": self.materiais.fator_reducao_concreto,
            "modulo_elasticidade_aco_mpa": (
                self.materiais.modulo_elasticidade_aco_mpa
            ),
            "deformacao_concreto_inicio_patamar": (
                self.materiais.deformacao_concreto_inicio_patamar
            ),
            "deformacao_ultima_concreto": (
                self.materiais.deformacao_ultima_concreto
            ),
            "expoente_parabola_concreto": (
                self.materiais.expoente_parabola_concreto
            ),
            "deformacao_ultima_aco": self.materiais.deformacao_ultima_aco,
            "espacamento_livre_minimo_mm": (
                self.catalogo.espacamento_livre_minimo_mm
            ),
        }
        if self.materiais.modulo_elasticidade_concreto_mpa is not None:
            valores_positivos["modulo_elasticidade_concreto_mpa"] = (
                self.materiais.modulo_elasticidade_concreto_mpa
            )
        for nome, valor in valores_positivos.items():
            if not math.isfinite(valor) or valor <= 0:
                raise ErroFlexoCompressaoObliqua(
                    f"{nome} deve ser finito e maior que zero."
                )

        if self.materiais.fck_mpa < 20 or self.materiais.fck_mpa > 50:
            raise ErroFlexoCompressaoObliqua(
                "Esta primeira versao aceita fck entre 20 e 50 MPa. Fora desse "
                "intervalo, os parametros do diagrama precisam ser adaptados "
                "antes da liberacao."
            )
        if self.materiais.deformacao_concreto_inicio_patamar >= (
            self.materiais.deformacao_ultima_concreto
        ):
            raise ErroFlexoCompressaoObliqua(
                "deformacao_concreto_inicio_patamar deve ser menor que "
                "deformacao_ultima_concreto."
            )
        if self.secao.cobrimento_nominal_mm < 0:
            raise ErroFlexoCompressaoObliqua(
                "cobrimento_nominal_mm deve ser maior ou igual a zero."
            )
        if self.secao.diametro_armadura_transversal_mm < 0:
            raise ErroFlexoCompressaoObliqua(
                "diametro_armadura_transversal_mm deve ser maior ou igual a zero."
            )

        for nome, valor in (
            ("normal_compressao_sd_tf", self.esforcos.normal_compressao_sd_tf),
            ("momento_x_sd_tf_m", self.esforcos.momento_x_sd_tf_m),
            ("momento_y_sd_tf_m", self.esforcos.momento_y_sd_tf_m),
        ):
            if not math.isfinite(valor):
                raise ErroFlexoCompressaoObliqua(
                    f"{nome} deve ser um numero finito."
                )
        if self.esforcos.normal_compressao_sd_tf < 0:
            raise ErroFlexoCompressaoObliqua(
                "normal_compressao_sd_tf deve ser positiva para compressao. "
                "Esta rota nao cobre flexotracao."
            )

        if self.catalogo.modo_verificacao not in {
            "direcional",
            "diagrama_completo",
        }:
            raise ErroFlexoCompressaoObliqua(
                "modo_verificacao deve ser 'direcional' ou 'diagrama_completo'."
            )
        if not 12 <= self.catalogo.pontos_diagrama <= 180:
            raise ErroFlexoCompressaoObliqua(
                "pontos_diagrama deve estar entre 12 e 180."
            )
        if not 48 <= self.catalogo.pontos_contorno_secao <= 256:
            raise ErroFlexoCompressaoObliqua(
                "pontos_contorno_secao deve estar entre 48 e 256."
            )
        if not math.isfinite(self.catalogo.tolerancia_angular_graus) or not (
            0.001 <= self.catalogo.tolerancia_angular_graus <= 1.0
        ):
            raise ErroFlexoCompressaoObliqua(
                "tolerancia_angular_graus deve estar entre 0,001 e 1 grau."
            )
        if not 2 <= self.catalogo.max_iteracoes_angulo <= 20:
            raise ErroFlexoCompressaoObliqua(
                "max_iteracoes_angulo deve estar entre 2 e 20."
            )

    def _combinacoes(self) -> Tuple[List[Tuple[int, float]], str]:
        if self.catalogo.combinacoes_explicitas:
            combinacoes = [
                (int(quantidade), float(bitola))
                for quantidade, bitola in self.catalogo.combinacoes_explicitas
            ]
            modo = "explicito"
        else:
            bitolas = sorted(
                {float(bitola) for bitola in self.catalogo.bitolas_longitudinais_mm}
            )
            quantidades = sorted(
                {int(quantidade) for quantidade in self.catalogo.quantidades_barras}
            )
            combinacoes = [
                (quantidade, bitola)
                for bitola in bitolas
                for quantidade in quantidades
            ]
            modo = "grade"

        if not combinacoes:
            raise ErroFlexoCompressaoObliqua(
                "Informe bitolas e quantidades ou combinacoes_explicitas."
            )
        if len(combinacoes) > MAXIMO_COMBINACOES:
            raise ErroFlexoCompressaoObliqua(
                f"O catalogo possui {len(combinacoes)} combinacoes; o limite e "
                f"{MAXIMO_COMBINACOES}."
            )
        if len(set(combinacoes)) != len(combinacoes):
            combinacoes = list(dict.fromkeys(combinacoes))

        for quantidade, bitola in combinacoes:
            if quantidade < 3:
                raise ErroFlexoCompressaoObliqua(
                    "Toda alternativa deve possuir ao menos 3 barras."
                )
            if not math.isfinite(bitola) or bitola <= 0:
                raise ErroFlexoCompressaoObliqua(
                    "Toda bitola longitudinal deve ser finita e maior que zero."
                )
        return combinacoes, modo

    def _parametros_calculados(self) -> Dict[str, float]:
        fcd_base = self.materiais.fck_mpa / self.materiais.gamma_c
        fcd_diagrama = fcd_base * self.materiais.fator_reducao_concreto
        fyd = self.materiais.fyk_mpa / self.materiais.gamma_s
        ec = self.materiais.modulo_elasticidade_concreto_mpa
        if ec is None:
            ec = 5_600.0 * math.sqrt(self.materiais.fck_mpa)
        fctm = 0.3 * self.materiais.fck_mpa ** (2.0 / 3.0)
        return {
            "fcd_base_mpa": fcd_base,
            "fcd_diagrama_mpa": fcd_diagrama,
            "fyd_mpa": fyd,
            "modulo_elasticidade_concreto_mpa": ec,
            "modulo_elasticidade_aco_mpa": (
                self.materiais.modulo_elasticidade_aco_mpa
            ),
            "fctm_mpa": fctm,
            "deformacao_concreto_inicio_patamar": (
                self.materiais.deformacao_concreto_inicio_patamar
            ),
            "deformacao_ultima_concreto": (
                self.materiais.deformacao_ultima_concreto
            ),
            "expoente_parabola_concreto": (
                self.materiais.expoente_parabola_concreto
            ),
            "deformacao_ultima_aco": self.materiais.deformacao_ultima_aco,
        }

    def _carregar_dependencias(self) -> Dict[str, Any]:
        try:
            import concreteproperties.stress_strain_profile as ssp
            from concreteproperties import (
                Concrete,
                ConcreteSection,
                SteelBar,
                add_bar_circular_array,
            )
            from sectionproperties.pre.library import circular_section
        except ImportError as exc:
            raise DependenciaConcretePropertiesAusente(
                "Pacote concreteproperties nao instalado. Execute: "
                "pip install concreteproperties==0.8.0"
            ) from exc

        try:
            versao = importlib.metadata.version("concreteproperties")
        except importlib.metadata.PackageNotFoundError:
            versao = "desconhecida"

        return {
            "ssp": ssp,
            "Concrete": Concrete,
            "ConcreteSection": ConcreteSection,
            "SteelBar": SteelBar,
            "add_bar_circular_array": add_bar_circular_array,
            "circular_section": circular_section,
            "versao": versao,
        }

    def _criar_materiais(self, deps: Dict[str, Any]) -> Tuple[Any, Any]:
        parametros = self._parametros_calculados()
        ssp = deps["ssp"]
        concreto = deps["Concrete"](
            name="Concreto de projeto - modelo parametrizado NBR 6118",
            density=2.4e-6,
            stress_strain_profile=ssp.ConcreteLinearNoTension(
                elastic_modulus=parametros["modulo_elasticidade_concreto_mpa"],
                ultimate_strain=parametros["deformacao_ultima_concreto"],
                compressive_strength=parametros["fcd_diagrama_mpa"],
            ),
            ultimate_stress_strain_profile=ssp.EurocodeParabolicUltimate(
                compressive_strength=parametros["fcd_diagrama_mpa"],
                compressive_strain=(
                    parametros["deformacao_concreto_inicio_patamar"]
                ),
                ultimate_strain=parametros["deformacao_ultima_concreto"],
                n=parametros["expoente_parabola_concreto"],
                n_points=20,
            ),
            flexural_tensile_strength=parametros["fctm_mpa"],
            colour="lightgrey",
        )
        aco = deps["SteelBar"](
            name="Aco longitudinal de projeto",
            density=7.85e-6,
            stress_strain_profile=ssp.SteelElasticPlastic(
                yield_strength=parametros["fyd_mpa"],
                elastic_modulus=parametros["modulo_elasticidade_aco_mpa"],
                fracture_strain=parametros["deformacao_ultima_aco"],
            ),
            colour="grey",
        )
        return concreto, aco

    def _analisar_opcao(
        self,
        deps: Dict[str, Any],
        material_concreto: Any,
        material_aco: Any,
        quantidade: int,
        bitola_mm: float,
        incluir_diagrama: bool,
    ) -> Dict[str, Any]:
        geometria = avaliar_geometria_armadura_circular(
            diametro_secao_mm=self.secao.diametro_m * 1_000.0,
            cobrimento_nominal_mm=self.secao.cobrimento_nominal_mm,
            diametro_armadura_transversal_mm=(
                self.secao.diametro_armadura_transversal_mm
            ),
            quantidade_barras=quantidade,
            diametro_barra_mm=bitola_mm,
            espacamento_livre_minimo_mm=(
                self.catalogo.espacamento_livre_minimo_mm
            ),
        )
        area_barra_mm2 = math.pi * bitola_mm**2 / 4.0
        area_total_mm2 = quantidade * area_barra_mm2
        area_bruta_mm2 = math.pi * (self.secao.diametro_m * 1_000.0) ** 2 / 4.0

        base: Dict[str, Any] = {
            "id": f"{quantidade}x{formatar_bitola_id(bitola_mm)}",
            "rotulo": f"{quantidade} Ø {formatar_numero(bitola_mm)}",
            "quantidade_barras": quantidade,
            "diametro_barra_mm": bitola_mm,
            "area_barra_cm2": area_barra_mm2 / 100.0,
            "area_aco_total_cm2": area_total_mm2 / 100.0,
            "taxa_geometrica_aco_pct": 100.0 * area_total_mm2 / area_bruta_mm2,
            **geometria,
            "atende": False,
            "utilizacao": None,
            "fator_reserva_radial": None,
            "momento_resistente_direcao_tf_m": None,
            "ponto_resistente_direcao_tf_m": None,
            "erro_analise": None,
        }

        if not geometria["viavel_geometricamente"]:
            base["status"] = "inviavel_geometricamente"
            if incluir_diagrama:
                base["diagrama_mx_my_tf_m"] = []
            return base

        try:
            secao_geometrica = deps["circular_section"](
                d=self.secao.diametro_m * 1_000.0,
                n=self.catalogo.pontos_contorno_secao,
                material=material_concreto,
            ).align_center()
            secao_geometrica = deps["add_bar_circular_array"](
                geometry=secao_geometrica,
                area=area_barra_mm2,
                material=material_aco,
                n_bar=quantidade,
                r_array=geometria["raio_eixo_barras_mm"],
                theta_0=math.radians(self.secao.angulo_inicial_barras_graus),
                ctr=(0.0, 0.0),
                n=8,
            )
            secao_concreto = deps["ConcreteSection"](secao_geometrica)
            demanda_n_mm = (
                self.esforcos.momento_x_sd_tf_m * TF_M_PARA_N_MM,
                self.esforcos.momento_y_sd_tf_m * TF_M_PARA_N_MM,
            )
            normal_n = self.esforcos.normal_compressao_sd_tf * TF_PARA_N

            if self.catalogo.modo_verificacao == "direcional":
                avaliacao = avaliar_capacidade_direcional(
                    secao_concreto=secao_concreto,
                    normal_n=normal_n,
                    demanda_n_mm=demanda_n_mm,
                    tolerancia_angular_rad=math.radians(
                        self.catalogo.tolerancia_angular_graus
                    ),
                    max_iteracoes=self.catalogo.max_iteracoes_angulo,
                )
                if not avaliacao["convergiu"]:
                    raise FalhaAnaliseSecao(
                        "A busca direcional nao convergiu: erro angular final "
                        f"de {avaliacao['erro_angular_graus']:.6f} grau(s). "
                        "Tente aumentar max_iteracoes_angulo ou use "
                        "modo_verificacao='diagrama_completo'."
                    )
                erro_diagrama = None
                contorno_n_mm: List[Tuple[float, float]] = []
                if incluir_diagrama:
                    try:
                        contorno_n_mm = gerar_diagrama_biaxial_por_simetria(
                            secao_concreto=secao_concreto,
                            normal_n=normal_n,
                            quantidade_barras=quantidade,
                            pontos_desejados=self.catalogo.pontos_diagrama,
                        )
                    except Exception as exc_diagrama:
                        # A verificacao direcional continua valida mesmo se a
                        # construcao opcional do contorno visual falhar.
                        erro_diagrama = str(exc_diagrama)
            else:
                erro_diagrama = None
                avaliacao = avaliar_por_diagrama_completo(
                    secao_concreto=secao_concreto,
                    normal_n=normal_n,
                    demanda_n_mm=demanda_n_mm,
                    pontos_diagrama=self.catalogo.pontos_diagrama,
                )
                contorno_n_mm = avaliacao.pop("contorno_n_mm")

            ponto_resistente_n_mm = avaliacao["ponto_resistente_n_mm"]
            ponto_resistente = (
                {
                    "mx_rd_tf_m": (
                        ponto_resistente_n_mm[0] / TF_M_PARA_N_MM
                    ),
                    "my_rd_tf_m": (
                        ponto_resistente_n_mm[1] / TF_M_PARA_N_MM
                    ),
                }
                if ponto_resistente_n_mm is not None
                else None
            )
            momento_resistente = (
                avaliacao["momento_resistente_n_mm"] / TF_M_PARA_N_MM
                if avaliacao["momento_resistente_n_mm"] is not None
                else None
            )

            base.update(
                {
                    "status": "atende" if avaliacao["atende"] else "nao_atende",
                    "atende": avaliacao["atende"],
                    "utilizacao": avaliacao["utilizacao"],
                    "fator_reserva_radial": avaliacao["fator_reserva"],
                    "momento_resistente_direcao_tf_m": momento_resistente,
                    "ponto_resistente_direcao_tf_m": ponto_resistente,
                    "angulo_linha_neutra_graus": avaliacao.get(
                        "angulo_linha_neutra_graus"
                    ),
                    "angulo_momento_resistente_graus": avaliacao.get(
                        "angulo_momento_resistente_graus"
                    ),
                    "erro_angular_graus": avaliacao.get(
                        "erro_angular_graus"
                    ),
                    "iteracoes_angulo": avaliacao.get("iteracoes_angulo"),
                    "erro_diagrama_recomendacao": erro_diagrama,
                }
            )
            if incluir_diagrama:
                base["diagrama_mx_my_tf_m"] = [
                    {
                        "mx_rd_tf_m": mx / TF_M_PARA_N_MM,
                        "my_rd_tf_m": my / TF_M_PARA_N_MM,
                    }
                    for mx, my in contorno_n_mm
                ]
            return base
        except Exception as exc:
            base.update(
                {
                    "status": "erro_analise",
                    "erro_analise": str(exc),
                }
            )
            if incluir_diagrama:
                base["diagrama_mx_my_tf_m"] = []
            return base

    def _resumir_por_bitola(
        self,
        opcoes: Sequence[Dict[str, Any]],
        combinacoes: Sequence[Tuple[int, float]],
        nao_avaliadas: Dict[float, int],
    ) -> List[Dict[str, Any]]:
        bitolas = sorted({bitola for _, bitola in combinacoes})
        resumo: List[Dict[str, Any]] = []
        for bitola in bitolas:
            opcoes_bitola = [
                opcao
                for opcao in opcoes
                if math.isclose(opcao["diametro_barra_mm"], bitola)
            ]
            atendentes = [opcao for opcao in opcoes_bitola if opcao["atende"]]
            menor = min(
                atendentes,
                key=lambda item: item["quantidade_barras"],
                default=None,
            )
            if menor:
                situacao = "opcao_encontrada"
            elif any(
                opcao["status"] == "erro_analise" for opcao in opcoes_bitola
            ):
                situacao = "falha_numerica_em_opcao"
            elif opcoes_bitola and all(
                opcao["status"] == "inviavel_geometricamente"
                for opcao in opcoes_bitola
            ):
                situacao = "nenhuma_combinacao_geometricamente_viavel"
            else:
                situacao = "nenhuma_opcao_avaliada_atende"
            resumo.append(
                {
                    "diametro_barra_mm": bitola,
                    "situacao": situacao,
                    "menor_quantidade_que_atende": (
                        menor["quantidade_barras"] if menor else None
                    ),
                    "opcao": menor,
                    "quantidade_opcoes_avaliadas": len(opcoes_bitola),
                    "quantidade_opcoes_nao_avaliadas_apos_atendimento": (
                        nao_avaliadas.get(bitola, 0)
                    ),
                }
            )
        return resumo


def normalizar_angulo_rad(angulo: float) -> float:
    """Normaliza um angulo para o intervalo [-pi, pi)."""

    return (angulo + math.pi) % (2.0 * math.pi) - math.pi


def avaliar_capacidade_direcional(
    *,
    secao_concreto: Any,
    normal_n: float,
    demanda_n_mm: Tuple[float, float],
    tolerancia_angular_rad: float,
    max_iteracoes: int,
) -> Dict[str, Any]:
    """Busca a capacidade com vetor de momento paralelo ao vetor solicitante.

    ``ultimate_bending_capacity`` recebe o angulo da linha neutra, que nao e,
    em geral, exatamente o angulo do momento resistente. A busca abaixo ajusta
    esse angulo por secante, evitando gerar o contorno biaxial completo para
    cada alternativa comercial.
    """

    demanda_modulo = math.hypot(*demanda_n_mm)
    if demanda_modulo <= TOLERANCIA:
        # A chamada ainda valida se a forca normal pertence ao dominio da secao.
        secao_concreto.ultimate_bending_capacity(theta=0.0, n=normal_n)
        return {
            "convergiu": True,
            "atende": True,
            "utilizacao": 0.0,
            "fator_reserva": None,
            "momento_resistente_n_mm": None,
            "ponto_resistente_n_mm": None,
            "angulo_linha_neutra_graus": None,
            "angulo_momento_resistente_graus": None,
            "erro_angular_graus": 0.0,
            "iteracoes_angulo": 1,
        }

    angulo_demanda = math.atan2(demanda_n_mm[1], demanda_n_mm[0])
    theta = angulo_demanda
    theta_anterior: Optional[float] = None
    erro_anterior: Optional[float] = None
    melhor: Optional[Dict[str, Any]] = None
    convergiu = False

    for indice in range(1, max_iteracoes + 1):
        theta_avaliado = normalizar_angulo_rad(theta)
        resultado = secao_concreto.ultimate_bending_capacity(
            theta=theta_avaliado,
            n=normal_n,
        )
        mx = float(resultado.m_x)
        my = float(resultado.m_y)
        angulo_resistente = math.atan2(my, mx)
        erro = normalizar_angulo_rad(angulo_resistente - angulo_demanda)
        projecao = (
            mx * math.cos(angulo_demanda) + my * math.sin(angulo_demanda)
        )

        candidato = {
            "mx": mx,
            "my": my,
            "theta": theta_avaliado,
            "angulo_resistente": angulo_resistente,
            "erro": erro,
            "projecao": projecao,
            "iteracoes": indice,
        }
        if projecao > 0 and (
            melhor is None or abs(erro) < abs(melhor["erro"])
        ):
            melhor = candidato

        if projecao > 0 and abs(erro) <= tolerancia_angular_rad:
            melhor = candidato
            convergiu = True
            break

        if (
            theta_anterior is not None
            and erro_anterior is not None
            and abs(erro - erro_anterior) > 1e-12
        ):
            passo = -erro * (theta - theta_anterior) / (
                erro - erro_anterior
            )
        else:
            # Para uma secao circular, d(angulo_momento)/d(theta) fica
            # proximo de 1. Este e um bom primeiro passo para a secante.
            passo = -erro

        limite_passo = math.pi / 3.0
        passo = max(-limite_passo, min(limite_passo, passo))
        theta_anterior = theta
        erro_anterior = erro
        theta += passo

    if melhor is None:
        return {
            "convergiu": False,
            "erro_angular_graus": 180.0,
            "iteracoes_angulo": max_iteracoes,
        }

    erro_final = abs(melhor["erro"])
    if erro_final <= tolerancia_angular_rad:
        convergiu = True

    momento_resistente = melhor["projecao"]
    if momento_resistente <= TOLERANCIA:
        return {
            "convergiu": False,
            "erro_angular_graus": math.degrees(erro_final),
            "iteracoes_angulo": melhor["iteracoes"],
        }

    versor = (
        demanda_n_mm[0] / demanda_modulo,
        demanda_n_mm[1] / demanda_modulo,
    )
    ponto_resistente = (
        versor[0] * momento_resistente,
        versor[1] * momento_resistente,
    )
    fator_reserva = momento_resistente / demanda_modulo
    utilizacao = 1.0 / fator_reserva

    return {
        "convergiu": convergiu,
        "atende": utilizacao <= 1.0 + 1e-9,
        "utilizacao": utilizacao,
        "fator_reserva": fator_reserva,
        "momento_resistente_n_mm": momento_resistente,
        "ponto_resistente_n_mm": ponto_resistente,
        "angulo_linha_neutra_graus": math.degrees(melhor["theta"]),
        "angulo_momento_resistente_graus": math.degrees(
            melhor["angulo_resistente"]
        ),
        "erro_angular_graus": math.degrees(erro_final),
        "iteracoes_angulo": melhor["iteracoes"],
    }


def gerar_diagrama_biaxial_por_simetria(
    *,
    secao_concreto: Any,
    normal_n: float,
    quantidade_barras: int,
    pontos_desejados: int,
) -> List[Tuple[float, float]]:
    """Gera o contorno usando a simetria da estaca e da camada circular.

    Uma camada de ``n`` barras iguais e uniformemente espacadas repete sua
    resposta a cada 2*pi/n. Calculam-se apenas os pontos de um setor e os demais
    sao obtidos por rotacao vetorial.
    """

    repeticoes = max(3, int(quantidade_barras))
    pontos_setor = max(2, math.ceil(pontos_desejados / repeticoes))
    angulo_setor = 2.0 * math.pi / repeticoes
    pontos: List[Tuple[float, float]] = []

    for indice in range(pontos_setor):
        theta = indice * angulo_setor / pontos_setor
        resultado = secao_concreto.ultimate_bending_capacity(
            theta=theta,
            n=normal_n,
        )
        mx_base = float(resultado.m_x)
        my_base = float(resultado.m_y)

        for repeticao in range(repeticoes):
            giro = repeticao * angulo_setor
            cos_giro = math.cos(giro)
            sin_giro = math.sin(giro)
            pontos.append(
                (
                    mx_base * cos_giro - my_base * sin_giro,
                    mx_base * sin_giro + my_base * cos_giro,
                )
            )

    pontos.sort(key=lambda ponto: math.atan2(ponto[1], ponto[0]))
    return fechar_poligono(pontos)


def avaliar_por_diagrama_completo(
    *,
    secao_concreto: Any,
    normal_n: float,
    demanda_n_mm: Tuple[float, float],
    pontos_diagrama: int,
) -> Dict[str, Any]:
    """Mantem o algoritmo original como modo de auditoria mais demorado."""

    resultado = secao_concreto.biaxial_bending_diagram(
        n=normal_n,
        n_points=pontos_diagrama,
        progress_bar=False,
    )
    mx_n_mm, my_n_mm = resultado.get_results_lists()
    contorno_n_mm = fechar_poligono(
        [(float(mx), float(my)) for mx, my in zip(mx_n_mm, my_n_mm)]
    )
    intersecao = intersecao_raio_poligono(
        demanda=demanda_n_mm,
        poligono=contorno_n_mm,
    )
    atende = bool(
        resultado.point_in_diagram(
            m_x=demanda_n_mm[0],
            m_y=demanda_n_mm[1],
        )
    )

    if math.hypot(*demanda_n_mm) <= TOLERANCIA:
        utilizacao = 0.0
        fator_reserva = None
        momento_resistente = None
        ponto_resistente = None
    elif intersecao is None:
        utilizacao = None
        fator_reserva = None
        momento_resistente = None
        ponto_resistente = None
    else:
        fator_reserva = intersecao["fator_escala"]
        utilizacao = 1.0 / fator_reserva if fator_reserva > 0 else None
        ponto_resistente = intersecao["ponto"]
        momento_resistente = math.hypot(*ponto_resistente)

    return {
        "convergiu": True,
        "atende": atende,
        "utilizacao": utilizacao,
        "fator_reserva": fator_reserva,
        "momento_resistente_n_mm": momento_resistente,
        "ponto_resistente_n_mm": ponto_resistente,
        "contorno_n_mm": contorno_n_mm,
        "angulo_linha_neutra_graus": None,
        "angulo_momento_resistente_graus": None,
        "erro_angular_graus": None,
        "iteracoes_angulo": pontos_diagrama,
    }


def avaliar_geometria_armadura_circular(
    *,
    diametro_secao_mm: float,
    cobrimento_nominal_mm: float,
    diametro_armadura_transversal_mm: float,
    quantidade_barras: int,
    diametro_barra_mm: float,
    espacamento_livre_minimo_mm: float,
) -> Dict[str, Any]:
    """Verifica se uma camada circular de barras cabe geometricamente."""

    raio_eixo = (
        diametro_secao_mm / 2.0
        - cobrimento_nominal_mm
        - diametro_armadura_transversal_mm
        - diametro_barra_mm / 2.0
    )
    if raio_eixo <= 0:
        return {
            "viavel_geometricamente": False,
            "motivo_inviabilidade_geometrica": "raio_do_eixo_das_barras_nao_positivo",
            "raio_eixo_barras_mm": raio_eixo,
            "espacamento_entre_eixos_mm": None,
            "espacamento_livre_mm": None,
        }

    espacamento_eixos = 2.0 * raio_eixo * math.sin(math.pi / quantidade_barras)
    espacamento_livre = espacamento_eixos - diametro_barra_mm
    viavel = espacamento_livre + TOLERANCIA >= espacamento_livre_minimo_mm
    return {
        "viavel_geometricamente": viavel,
        "motivo_inviabilidade_geometrica": (
            None if viavel else "espacamento_livre_inferior_ao_minimo_informado"
        ),
        "raio_eixo_barras_mm": raio_eixo,
        "espacamento_entre_eixos_mm": espacamento_eixos,
        "espacamento_livre_mm": espacamento_livre,
    }


def intersecao_raio_poligono(
    *,
    demanda: Tuple[float, float],
    poligono: Sequence[Tuple[float, float]],
) -> Optional[Dict[str, Any]]:
    """Intersecta o raio ``t * demanda`` com o contorno resistente.

    Retorna a primeira interseção positiva. Para um contorno que contém a
    origem, ``t >= 1`` significa que a demanda está no interior do diagrama.
    """

    dx, dy = demanda
    if math.hypot(dx, dy) <= TOLERANCIA:
        return None
    pontos = fechar_poligono(poligono)
    if len(pontos) < 4:
        return None

    candidatos: List[Tuple[float, float, Tuple[float, float]]] = []
    for p, q in zip(pontos, pontos[1:]):
        sx = q[0] - p[0]
        sy = q[1] - p[1]
        denominador = produto_vetorial_2d((dx, dy), (sx, sy))
        if abs(denominador) <= TOLERANCIA:
            continue
        t = produto_vetorial_2d(p, (sx, sy)) / denominador
        u = produto_vetorial_2d(p, (dx, dy)) / denominador
        if t >= -TOLERANCIA and -TOLERANCIA <= u <= 1.0 + TOLERANCIA:
            t = max(0.0, t)
            candidatos.append((t, u, (t * dx, t * dy)))

    positivos = [item for item in candidatos if item[0] > TOLERANCIA]
    if not positivos:
        return None
    t, u, ponto = min(positivos, key=lambda item: item[0])
    return {
        "fator_escala": t,
        "parametro_segmento": u,
        "ponto": ponto,
    }


def fechar_poligono(
    pontos: Iterable[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    saida = [(float(x), float(y)) for x, y in pontos]
    if not saida:
        return saida
    if saida[0] != saida[-1]:
        saida.append(saida[0])
    return saida


def produto_vetorial_2d(
    a: Tuple[float, float], b: Tuple[float, float]
) -> float:
    return a[0] * b[1] - a[1] * b[0]


def formatar_numero(valor: float) -> str:
    return f"{valor:g}".replace(".", ",")


def formatar_bitola_id(valor: float) -> str:
    return f"{valor:g}".replace(".", "p")
