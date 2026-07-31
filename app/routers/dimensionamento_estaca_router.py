"""Rotas de dimensionamento estrutural de estacas."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.services.dimensionamento.estacas.flexo_compressao_obliqua import (
    CatalogoArmadurasFCO,
    DependenciaConcretePropertiesAusente,
    DimensionadorFlexoCompressaoObliqua,
    ErroFlexoCompressaoObliqua,
    EsforcosFCO,
    FalhaAnaliseSecao,
    MateriaisFCO,
    SecaoCircularFCO,
)


router = APIRouter(tags=["Dimensionamento - Estacas"])
logger = logging.getLogger("uvicorn.error")


EXEMPLO_PCALC = {
    "secao": {
        "diametro_estaca_m": 0.40,
        "cobrimento_nominal_mm": 40.0,
        "diametro_armadura_transversal_mm": 6.3,
        "angulo_inicial_barras_graus": 0.0,
    },
    "materiais": {
        "fck_mpa": 30.0,
        "fyk_mpa": 500.0,
        "gamma_c": 1.40,
        "gamma_s": 1.15,
        "fator_reducao_concreto": 0.85,
    },
    "esforcos": {
        "normal_compressao_sd_tf": 35.0,
        "momento_x_sd_tf_m": 5.0,
        "momento_y_sd_tf_m": 3.0,
    },
    "catalogo": {
        "combinacoes_explicitas": [
            {"quantidade_barras": 6, "diametro_barra_mm": 16.0},
            {"quantidade_barras": 8, "diametro_barra_mm": 16.0},
            {"quantidade_barras": 10, "diametro_barra_mm": 16.0},
            {"quantidade_barras": 8, "diametro_barra_mm": 20.0},
        ],
        "espacamento_livre_minimo_mm": 20.0,
        "pontos_diagrama": 24,
        "pontos_contorno_secao": 48,
        "incluir_diagrama_recomendacao": True,
        "modo_verificacao": "direcional",
        "tolerancia_angular_graus": 0.05,
        "max_iteracoes_angulo": 8,
    },
}


class SecaoCircularFCOInput(BaseModel):
    diametro_estaca_m: float = Field(
        ...,
        gt=0,
        description="Diâmetro externo da seção circular maciça da estaca (m).",
    )
    cobrimento_nominal_mm: float = Field(
        40.0,
        ge=0,
        description=(
            "Distância da face do concreto à face externa da armadura "
            "transversal (mm)."
        ),
    )
    diametro_armadura_transversal_mm: float = Field(
        6.3,
        ge=0,
        description=(
            "Diâmetro do estribo ou espiral considerado para posicionar o "
            "eixo das barras longitudinais (mm)."
        ),
    )
    angulo_inicial_barras_graus: float = Field(
        0.0,
        description=(
            "Ângulo da primeira barra longitudinal em relação ao eixo +X. "
            "É devolvido para permitir reproduzir exatamente o modelo."
        ),
    )


class MateriaisFCOInput(BaseModel):
    fck_mpa: float = Field(
        ...,
        ge=20,
        le=50,
        description=(
            "Resistência característica do concreto (MPa). A primeira versão "
            "é limitada a 50 MPa."
        ),
    )
    fyk_mpa: float = Field(500.0, gt=0, description="fyk do aço (MPa).")
    gamma_c: float = Field(1.40, gt=0, description="Coeficiente γc.")
    gamma_s: float = Field(1.15, gt=0, description="Coeficiente γs.")
    fator_reducao_concreto: float = Field(
        0.85,
        gt=0,
        le=1,
        description=(
            "Fator multiplicador de fck/γc usado no diagrama de cálculo. "
            "Valor default: 0,85."
        ),
    )
    modulo_elasticidade_aco_mpa: float = Field(200_000.0, gt=0)
    modulo_elasticidade_concreto_mpa: Optional[float] = Field(None, gt=0)
    deformacao_concreto_inicio_patamar: float = Field(0.002, gt=0)
    deformacao_ultima_concreto: float = Field(0.0035, gt=0)
    expoente_parabola_concreto: float = Field(2.0, gt=0)
    deformacao_ultima_aco: float = Field(0.010, gt=0)


class EsforcosFCOInput(BaseModel):
    normal_compressao_sd_tf: float = Field(
        ...,
        ge=0,
        description="Força normal de cálculo; compressão positiva (tf).",
    )
    momento_x_sd_tf_m: float = Field(
        ...,
        description="Momento solicitante de cálculo em torno de X (tf.m).",
    )
    momento_y_sd_tf_m: float = Field(
        ...,
        description="Momento solicitante de cálculo em torno de Y (tf.m).",
    )


class CombinacaoArmaduraInput(BaseModel):
    quantidade_barras: int = Field(..., ge=3, le=40)
    diametro_barra_mm: float = Field(..., gt=0, le=50)


class CatalogoArmadurasFCOInput(BaseModel):
    bitolas_longitudinais_mm: List[float] = Field(
        default_factory=lambda: [10.0, 12.5, 16.0, 20.0, 25.0, 32.0],
        description=(
            "Bitolas avaliadas quando combinacoes_explicitas não for informado."
        ),
    )
    quantidades_barras: List[int] = Field(
        default_factory=lambda: [6, 8, 10, 12, 14, 16, 18, 20],
        description=(
            "Quantidades avaliadas para cada bitola no modo de grade."
        ),
    )
    combinacoes_explicitas: Optional[List[CombinacaoArmaduraInput]] = Field(
        None,
        description=(
            "Lista exata de alternativas. Quando informada, substitui a grade "
            "bitolas × quantidades e todas as alternativas são analisadas."
        ),
    )
    espacamento_livre_minimo_mm: float = Field(
        20.0,
        gt=0,
        description=(
            "Espaçamento livre mínimo usado apenas no filtro geométrico (mm)."
        ),
    )
    pontos_diagrama: int = Field(
        24,
        ge=12,
        le=180,
        description=(
            "Quantidade desejada de pontos no contorno visual. No modo "
            "direcional, a simetria da armadura reduz as análises necessárias."
        ),
    )
    pontos_contorno_secao: int = Field(
        48,
        ge=48,
        le=256,
        description="Discretização poligonal da circunferência da estaca.",
    )
    parar_na_primeira_opcao_por_bitola: bool = Field(
        True,
        description=(
            "No modo grade, interrompe cada bitola na primeira quantidade que "
            "atende. Reduz o tempo de resposta."
        ),
    )
    incluir_diagrama_recomendacao: bool = Field(
        True,
        description=(
            "Inclui o polígono Mx-My da alternativa recomendada, pronto para o frontend."
        ),
    )
    modo_verificacao: Literal["direcional", "diagrama_completo"] = Field(
        "direcional",
        description=(
            "direcional usa poucas análises na direção de Mx/My; "
            "diagrama_completo preserva o algoritmo original e é mais lento."
        ),
    )
    tolerancia_angular_graus: float = Field(
        0.05,
        ge=0.001,
        le=1.0,
        description="Tolerância da busca pelo ângulo resistente no modo direcional.",
    )
    max_iteracoes_angulo: int = Field(
        8,
        ge=2,
        le=20,
        description="Máximo de soluções seccionais na busca angular por alternativa.",
    )


class FlexoCompressaoObliquaInput(BaseModel):
    secao: SecaoCircularFCOInput
    materiais: MateriaisFCOInput
    esforcos: EsforcosFCOInput
    catalogo: CatalogoArmadurasFCOInput = Field(
        default_factory=CatalogoArmadurasFCOInput
    )


class FlexoCompressaoObliquaResult(BaseModel):
    sistema_unidades: Dict[str, str]
    metodo: Dict[str, Any]
    secao: Dict[str, Any]
    materiais: Dict[str, Any]
    esforcos_solicitantes: Dict[str, Any]
    catalogo: Dict[str, Any]
    opcoes: List[Dict[str, Any]]
    resumo_por_bitola: List[Dict[str, Any]]
    recomendacao: Optional[Dict[str, Any]]
    diagrama_recomendacao_mx_my_tf_m: List[Dict[str, float]]
    avisos: List[str]


class ErrorResponse(BaseModel):
    detail: str


@router.post(
    "/estacas/flexo-compressao-obliqua",
    summary="Verifica alternativas de armadura para estaca circular",
    description=(
        "Gera alternativas comerciais de armadura longitudinal e verifica cada "
        "seção circular para Nsd, Mxsd e Mysd. No modo direcional, o "
        "concreteproperties calcula somente as capacidades necessárias para "
        "alinhar o momento resistente à solicitação; a openStruct filtra a "
        "geometria, calcula a utilização e organiza a menor alternativa por "
        "bitola. O modo diagrama_completo permanece disponível para auditoria.\n\n"
        "**Unidades de entrada:** diâmetro da estaca em m; cobrimento e barras "
        "em mm; resistências em MPa; força em tf; momentos em tf.m.\n\n"
        "O modelo NBR é parametrizado e auditável, pois a biblioteca não possui "
        "módulo oficial da NBR 6118."
    ),
    response_model=FlexoCompressaoObliquaResult,
    responses={
        400: {"model": ErrorResponse, "description": "Dados incompatíveis."},
        422: {"model": ErrorResponse, "description": "Falha da análise seccional."},
        503: {"model": ErrorResponse, "description": "Dependência ausente."},
        500: {"model": ErrorResponse, "description": "Erro interno."},
    },
)
def verificar_flexo_compressao_obliqua(
    data: FlexoCompressaoObliquaInput = Body(..., examples=[EXEMPLO_PCALC]),
) -> Dict[str, Any]:
    inicio = perf_counter()
    quantidade_opcoes = len(data.catalogo.combinacoes_explicitas or [])
    if not quantidade_opcoes:
        quantidade_opcoes = (
            len(data.catalogo.bitolas_longitudinais_mm)
            * len(data.catalogo.quantidades_barras)
        )
    logger.info(
        "Flexocompressao obliqua iniciada: %s combinacoes, modo=%s, %s pontos.",
        quantidade_opcoes,
        data.catalogo.modo_verificacao,
        data.catalogo.pontos_diagrama,
    )
    try:
        combinacoes = tuple(
            (item.quantidade_barras, item.diametro_barra_mm)
            for item in (data.catalogo.combinacoes_explicitas or [])
        )
        servico = DimensionadorFlexoCompressaoObliqua(
            secao=SecaoCircularFCO(
                diametro_m=data.secao.diametro_estaca_m,
                cobrimento_nominal_mm=data.secao.cobrimento_nominal_mm,
                diametro_armadura_transversal_mm=(
                    data.secao.diametro_armadura_transversal_mm
                ),
                angulo_inicial_barras_graus=(
                    data.secao.angulo_inicial_barras_graus
                ),
            ),
            materiais=MateriaisFCO(
                fck_mpa=data.materiais.fck_mpa,
                fyk_mpa=data.materiais.fyk_mpa,
                gamma_c=data.materiais.gamma_c,
                gamma_s=data.materiais.gamma_s,
                fator_reducao_concreto=(
                    data.materiais.fator_reducao_concreto
                ),
                modulo_elasticidade_aco_mpa=(
                    data.materiais.modulo_elasticidade_aco_mpa
                ),
                modulo_elasticidade_concreto_mpa=(
                    data.materiais.modulo_elasticidade_concreto_mpa
                ),
                deformacao_concreto_inicio_patamar=(
                    data.materiais.deformacao_concreto_inicio_patamar
                ),
                deformacao_ultima_concreto=(
                    data.materiais.deformacao_ultima_concreto
                ),
                expoente_parabola_concreto=(
                    data.materiais.expoente_parabola_concreto
                ),
                deformacao_ultima_aco=data.materiais.deformacao_ultima_aco,
            ),
            esforcos=EsforcosFCO(
                normal_compressao_sd_tf=(
                    data.esforcos.normal_compressao_sd_tf
                ),
                momento_x_sd_tf_m=data.esforcos.momento_x_sd_tf_m,
                momento_y_sd_tf_m=data.esforcos.momento_y_sd_tf_m,
            ),
            catalogo=CatalogoArmadurasFCO(
                bitolas_longitudinais_mm=(
                    data.catalogo.bitolas_longitudinais_mm
                ),
                quantidades_barras=data.catalogo.quantidades_barras,
                combinacoes_explicitas=combinacoes,
                espacamento_livre_minimo_mm=(
                    data.catalogo.espacamento_livre_minimo_mm
                ),
                pontos_diagrama=data.catalogo.pontos_diagrama,
                pontos_contorno_secao=data.catalogo.pontos_contorno_secao,
                parar_na_primeira_opcao_por_bitola=(
                    data.catalogo.parar_na_primeira_opcao_por_bitola
                ),
                incluir_diagrama_recomendacao=(
                    data.catalogo.incluir_diagrama_recomendacao
                ),
                modo_verificacao=data.catalogo.modo_verificacao,
                tolerancia_angular_graus=(
                    data.catalogo.tolerancia_angular_graus
                ),
                max_iteracoes_angulo=data.catalogo.max_iteracoes_angulo,
            ),
        )
        resultado = servico.analisar()
        duracao = perf_counter() - inicio
        resultado["metodo"]["tempo_processamento_s"] = round(duracao, 3)
        logger.info(
            "Flexocompressao obliqua concluida em %.3f s: %s opcoes avaliadas.",
            duracao,
            len(resultado["opcoes"]),
        )
        return resultado
    except ErroFlexoCompressaoObliqua as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except DependenciaConcretePropertiesAusente as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except FalhaAnaliseSecao as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Falha inesperada na flexocompressao obliqua apos %.3f s.",
            perf_counter() - inicio,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Erro inesperado ao verificar a flexocompressao obliqua: "
                f"{exc}"
            ),
        ) from exc
