"""Análise linear de uma estaca sobre molas horizontais com o PyNite."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


CASO_CARGA = "ISE"
COMBINACAO = "ISE"
TOLERANCIA_PROFUNDIDADE = 1e-9


class ErroModeloEstaca(ValueError):
    """Indica dados incompatíveis com o modelo de estaca adotado."""


class DependenciaPyNiteAusente(RuntimeError):
    """Indica que o pacote PyNiteFEA não está instalado."""


class FalhaAnaliseEstaca(RuntimeError):
    """Indica uma falha do solver durante a análise."""


@dataclass(frozen=True)
class PropriedadesSecao:
    area_m2: float
    inercia_y_m4: float
    inercia_z_m4: float
    constante_torcao_m4: float


@dataclass(frozen=True)
class CargasTopo:
    horizontal_x_tf: float
    momento_z_tf_m: float
    axial_compressao_tf: float


@dataclass
class AnaliseEstacaPyNite:
    """
    Modelo plano XY de uma estaca discretizada de metro em metro.

    Convenções:
    - topo em (0, 0, 0) e estaca orientada no sentido global -Y;
    - molas horizontais bilaterais no grau de liberdade DX;
    - carga axial positiva de entrada representa compressão e é aplicada em -FY;
    - momento positivo atua em +MZ;
    - a ponta impede DX e DY e libera RZ;
    - DZ, RX e RY são impedidos em todos os nós para representar um problema 2D.
    """

    comprimento_m: float
    molas_horizontais_tf_m: Sequence[float]
    cargas: CargasTopo
    modulo_elasticidade_tf_m2: float
    coeficiente_poisson: float
    secao: PropriedadesSecao
    modulo_cisalhamento_tf_m2: Optional[float] = None
    pontos_por_elemento: int = 6

    def analisar(self) -> Dict[str, Any]:
        self._validar_entradas()
        profundidades, rigidezes = self._malha_e_molas()
        modulo_cisalhamento = self._modulo_cisalhamento()
        modelo, nomes_elementos = self._montar_modelo(
            profundidades=profundidades,
            rigidezes=rigidezes,
            modulo_cisalhamento=modulo_cisalhamento,
        )

        try:
            modelo.analyze_linear(
                log=False,
                check_stability=True,
                check_statics=False,
                sparse=True,
            )
        except Exception as exc:
            raise FalhaAnaliseEstaca(
                f"O PyNite não conseguiu resolver o modelo: {exc}"
            ) from exc

        nos = self._resultados_nodais(modelo, profundidades, rigidezes)
        diagramas = self._diagramas(
            modelo=modelo,
            profundidades=profundidades,
            nomes_elementos=nomes_elementos,
        )
        equilibrio = self._verificar_equilibrio(nos)

        return {
            "sistema_unidades": {
                "comprimento": "m",
                "forca": "tf",
                "momento": "tf.m",
                "tensao_modulo": "tf/m²",
                "rigidez_mola": "tf/m",
                "rotacao": "rad",
            },
            "modelo": {
                "tipo": "viga sobre molas horizontais discretas",
                "analise": "linear elastica",
                "plano": "XY",
                "eixo_longitudinal_estaca": "-Y global",
                "direcao_molas": "DX global",
                "numero_nos": len(profundidades),
                "numero_elementos": len(nomes_elementos),
                "profundidades_nos_m": profundidades,
                "profundidades_molas_m": profundidades[1:-1],
                "apoio_ponta": {
                    "DX": "impedido",
                    "DY": "impedido",
                    "RZ": "livre",
                },
            },
            "propriedades": {
                "comprimento_m": self.comprimento_m,
                "modulo_elasticidade_tf_m2": self.modulo_elasticidade_tf_m2,
                "modulo_cisalhamento_tf_m2": modulo_cisalhamento,
                "coeficiente_poisson": self.coeficiente_poisson,
                "area_m2": self.secao.area_m2,
                "inercia_y_m4": self.secao.inercia_y_m4,
                "inercia_z_m4": self.secao.inercia_z_m4,
                "constante_torcao_m4": self.secao.constante_torcao_m4,
            },
            "cargas_aplicadas": {
                "horizontal_x_tf": self.cargas.horizontal_x_tf,
                "momento_z_tf_m": self.cargas.momento_z_tf_m,
                "axial_compressao_tf": self.cargas.axial_compressao_tf,
                "forca_global_FY_aplicada_tf": -self.cargas.axial_compressao_tf,
            },
            "nos": nos,
            "diagramas": diagramas,
            "resumo": self._resumo(nos, diagramas),
            "equilibrio": equilibrio,
            "avisos": [
                (
                    "As molas são lineares e bilaterais. Não são considerados "
                    "plastificação do solo, desaprumo, fissuração ou efeito P-Delta."
                ),
                (
                    "Os elementos de barra do PyNite não consideram deformações "
                    "transversais por cisalhamento."
                ),
                (
                    "Como só foram informadas molas horizontais, a força axial é "
                    "transferida integralmente ao apoio vertical rígido da ponta."
                ),
                (
                    "Valores repetidos na mesma profundidade representam os lados "
                    "superior e inferior do nó e preservam saltos no diagrama de cortante."
                ),
            ],
        }

    def _validar_entradas(self) -> None:
        positivos = {
            "comprimento_m": self.comprimento_m,
            "modulo_elasticidade_tf_m2": self.modulo_elasticidade_tf_m2,
            "area_m2": self.secao.area_m2,
            "inercia_y_m4": self.secao.inercia_y_m4,
            "inercia_z_m4": self.secao.inercia_z_m4,
            "constante_torcao_m4": self.secao.constante_torcao_m4,
        }

        if self.modulo_cisalhamento_tf_m2 is not None:
            positivos["modulo_cisalhamento_tf_m2"] = (
                self.modulo_cisalhamento_tf_m2
            )

        for nome, valor in positivos.items():
            if not math.isfinite(valor) or valor <= 0:
                raise ErroModeloEstaca(f"{nome} deve ser finito e maior que zero.")

        if (
            not math.isfinite(self.coeficiente_poisson)
            or self.coeficiente_poisson <= -1
            or self.coeficiente_poisson >= 0.5
        ):
            raise ErroModeloEstaca(
                "coeficiente_poisson deve estar no intervalo aberto (-1, 0.5)."
            )

        for nome, valor in (
            ("horizontal_x_tf", self.cargas.horizontal_x_tf),
            ("momento_z_tf_m", self.cargas.momento_z_tf_m),
            ("axial_compressao_tf", self.cargas.axial_compressao_tf),
        ):
            if not math.isfinite(valor):
                raise ErroModeloEstaca(f"{nome} deve ser um número finito.")

        if not 2 <= self.pontos_por_elemento <= 50:
            raise ErroModeloEstaca(
                "pontos_por_elemento deve estar entre 2 e 50."
            )

        profundidades_esperadas = self._profundidades_internas()
        if len(self.molas_horizontais_tf_m) != len(profundidades_esperadas):
            raise ErroModeloEstaca(
                "Quantidade incorreta de molas. Para uma estaca de "
                f"{self.comprimento_m:g} m são esperados "
                f"{len(profundidades_esperadas)} valores, correspondentes às "
                f"profundidades {profundidades_esperadas} m. O nó da ponta não "
                "recebe mola porque possui apoio rígido em X e Y."
            )

        for indice, rigidez in enumerate(self.molas_horizontais_tf_m, start=1):
            if not math.isfinite(rigidez) or rigidez < 0:
                raise ErroModeloEstaca(
                    "Toda rigidez de mola deve ser finita e maior ou igual a zero. "
                    f"Valor inválido no índice {indice - 1}."
                )

    def _profundidades_internas(self) -> List[float]:
        limite = math.ceil(self.comprimento_m)
        return [
            float(profundidade)
            for profundidade in range(1, limite)
            if profundidade < self.comprimento_m - TOLERANCIA_PROFUNDIDADE
        ]

    def _malha_e_molas(self) -> Tuple[List[float], Dict[float, float]]:
        internas = self._profundidades_internas()
        profundidades = [0.0, *internas, float(self.comprimento_m)]
        rigidezes = {
            profundidade: float(rigidez)
            for profundidade, rigidez in zip(
                internas, self.molas_horizontais_tf_m
            )
        }
        return profundidades, rigidezes

    def _modulo_cisalhamento(self) -> float:
        if self.modulo_cisalhamento_tf_m2 is not None:
            return float(self.modulo_cisalhamento_tf_m2)
        return self.modulo_elasticidade_tf_m2 / (
            2 * (1 + self.coeficiente_poisson)
        )

    def _montar_modelo(
        self,
        profundidades: Sequence[float],
        rigidezes: Dict[float, float],
        modulo_cisalhamento: float,
    ) -> Tuple[Any, List[str]]:
        try:
            from Pynite import FEModel3D
        except ImportError as exc:
            raise DependenciaPyNiteAusente(
                "Pacote PyNiteFEA não instalado. Execute: "
                "pip install PyNiteFEA==3.0.0"
            ) from exc

        modelo = FEModel3D()
        modelo.add_material(
            "MATERIAL_ESTACA",
            E=self.modulo_elasticidade_tf_m2,
            G=modulo_cisalhamento,
            nu=self.coeficiente_poisson,
            rho=0.0,
        )
        modelo.add_section(
            "SECAO_ESTACA",
            A=self.secao.area_m2,
            Iy=self.secao.inercia_y_m4,
            Iz=self.secao.inercia_z_m4,
            J=self.secao.constante_torcao_m4,
        )

        for indice, profundidade in enumerate(profundidades):
            nome_no = f"N{indice}"
            modelo.add_node(nome_no, 0.0, -profundidade, 0.0)

            # Redução do modelo espacial do PyNite ao plano XY.
            modelo.def_support(
                nome_no,
                support_DZ=True,
                support_RX=True,
                support_RY=True,
            )

            rigidez = rigidezes.get(profundidade)
            if rigidez is not None and rigidez > 0:
                modelo.def_support_spring(
                    nome_no,
                    dof="DX",
                    stiffness=rigidez,
                    direction=None,
                )

        nomes_elementos: List[str] = []
        for indice in range(len(profundidades) - 1):
            nome_elemento = f"E{indice + 1}"
            nomes_elementos.append(nome_elemento)
            modelo.add_member(
                nome_elemento,
                i_node=f"N{indice}",
                j_node=f"N{indice + 1}",
                material_name="MATERIAL_ESTACA",
                section_name="SECAO_ESTACA",
            )

        nome_ponta = f"N{len(profundidades) - 1}"
        modelo.def_support(
            nome_ponta,
            support_DX=True,
            support_DY=True,
            support_DZ=True,
            support_RX=True,
            support_RY=True,
            support_RZ=False,
        )

        modelo.add_node_load(
            "N0", direction="FX", P=self.cargas.horizontal_x_tf, case=CASO_CARGA
        )
        modelo.add_node_load(
            "N0",
            direction="FY",
            P=-self.cargas.axial_compressao_tf,
            case=CASO_CARGA,
        )
        modelo.add_node_load(
            "N0", direction="MZ", P=self.cargas.momento_z_tf_m, case=CASO_CARGA
        )
        modelo.add_load_combo(COMBINACAO, {CASO_CARGA: 1.0})

        return modelo, nomes_elementos

    def _resultados_nodais(
        self,
        modelo: Any,
        profundidades: Sequence[float],
        rigidezes: Dict[float, float],
    ) -> List[Dict[str, Any]]:
        resultados = []
        indice_ponta = len(profundidades) - 1

        for indice, profundidade in enumerate(profundidades):
            no = modelo.nodes[f"N{indice}"]
            rigidez = rigidezes.get(profundidade)
            reacao_x = self._numero(no.RxnFX[COMBINACAO])

            resultados.append(
                {
                    "no": f"N{indice}",
                    "profundidade_m": profundidade,
                    "tipo": (
                        "topo"
                        if indice == 0
                        else "ponta"
                        if indice == indice_ponta
                        else "mola"
                    ),
                    "rigidez_mola_x_tf_m": rigidez,
                    "deslocamento_x_m": self._numero(no.DX[COMBINACAO]),
                    "deslocamento_y_m": self._numero(no.DY[COMBINACAO]),
                    "rotacao_z_rad": self._numero(no.RZ[COMBINACAO]),
                    "reacao_x_tf": reacao_x,
                    "reacao_y_tf": self._numero(no.RxnFY[COMBINACAO]),
                    "momento_reacao_z_tf_m": self._numero(
                        no.RxnMZ[COMBINACAO]
                    ),
                    "reacao_mola_x_tf": reacao_x if rigidez is not None else None,
                }
            )

        return resultados

    def _diagramas(
        self,
        modelo: Any,
        profundidades: Sequence[float],
        nomes_elementos: Sequence[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        diagramas: Dict[str, List[Dict[str, Any]]] = {
            "cortante_x_tf": [],
            "momento_fletor_z_tf_m": [],
            "forca_normal_tf": [],
            "deslocamento_horizontal_x_m": [],
        }

        for indice, nome_elemento in enumerate(nomes_elementos):
            elemento = modelo.members[nome_elemento]
            comprimento_elemento = float(elemento.L())
            profundidade_inicial = profundidades[indice]

            for ponto in range(self.pontos_por_elemento):
                fracao = ponto / (self.pontos_por_elemento - 1)
                x_local = comprimento_elemento * fracao
                profundidade = profundidade_inicial + x_local
                lado = (
                    "topo_elemento"
                    if ponto == 0
                    else "base_elemento"
                    if ponto == self.pontos_por_elemento - 1
                    else "interno"
                )
                metadados = {
                    "profundidade_m": self._numero(profundidade),
                    "elemento": nome_elemento,
                    "x_local_m": self._numero(x_local),
                    "lado": lado,
                }

                diagramas["cortante_x_tf"].append(
                    {
                        **metadados,
                        "valor": self._numero(
                            elemento.shear("Fy", x_local, COMBINACAO)
                        ),
                    }
                )
                diagramas["momento_fletor_z_tf_m"].append(
                    {
                        **metadados,
                        "valor": self._numero(
                            elemento.moment("Mz", x_local, COMBINACAO)
                        ),
                    }
                )
                diagramas["forca_normal_tf"].append(
                    {
                        **metadados,
                        "valor": self._numero(
                            elemento.axial(x_local, COMBINACAO)
                        ),
                    }
                )
                diagramas["deslocamento_horizontal_x_m"].append(
                    {
                        **metadados,
                        "valor": self._numero(
                            elemento.deflection("dy", x_local, COMBINACAO)
                        ),
                    }
                )

        return diagramas

    def _verificar_equilibrio(
        self, nos: Sequence[Dict[str, Any]]
    ) -> Dict[str, float]:
        soma_reacoes_x = sum(no["reacao_x_tf"] for no in nos)
        soma_reacoes_y = sum(no["reacao_y_tf"] for no in nos)
        soma_momentos_reacao_topo = sum(
            no["momento_reacao_z_tf_m"]
            + no["profundidade_m"] * no["reacao_x_tf"]
            for no in nos
        )

        return {
            "soma_reacoes_x_tf": self._numero(soma_reacoes_x),
            "soma_reacoes_y_tf": self._numero(soma_reacoes_y),
            "soma_momentos_reacoes_no_topo_tf_m": self._numero(
                soma_momentos_reacao_topo
            ),
            "residuo_fx_tf": self._numero(
                self.cargas.horizontal_x_tf + soma_reacoes_x
            ),
            "residuo_fy_tf": self._numero(
                -self.cargas.axial_compressao_tf + soma_reacoes_y
            ),
            "residuo_mz_no_topo_tf_m": self._numero(
                self.cargas.momento_z_tf_m + soma_momentos_reacao_topo
            ),
        }

    def _resumo(
        self,
        nos: Sequence[Dict[str, Any]],
        diagramas: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        return {
            "deslocamento_topo_x_m": nos[0]["deslocamento_x_m"],
            "deslocamento_topo_y_m": nos[0]["deslocamento_y_m"],
            "rotacao_topo_z_rad": nos[0]["rotacao_z_rad"],
            "cortante_maximo_absoluto": self._maximo_absoluto(
                diagramas["cortante_x_tf"]
            ),
            "momento_fletor_maximo_absoluto": self._maximo_absoluto(
                diagramas["momento_fletor_z_tf_m"]
            ),
            "forca_normal_maxima_absoluta": self._maximo_absoluto(
                diagramas["forca_normal_tf"]
            ),
            "deslocamento_horizontal_maximo_absoluto": self._maximo_absoluto(
                diagramas["deslocamento_horizontal_x_m"]
            ),
        }

    @staticmethod
    def _maximo_absoluto(
        pontos: Sequence[Dict[str, Any]]
    ) -> Dict[str, Any]:
        ponto = max(pontos, key=lambda item: abs(item["valor"]))
        return {
            "valor": ponto["valor"],
            "profundidade_m": ponto["profundidade_m"],
            "elemento": ponto["elemento"],
        }

    @staticmethod
    def _numero(valor: Any) -> float:
        numero = float(valor)
        return 0.0 if abs(numero) < 1e-12 else numero
