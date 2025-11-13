"""
Autor: Alessandro Lopes
E-mail: SEU_EMAIL_AQUI
GitHub: https://github.com/SEU_GITHUB

Data da última atualização: 13/11/2025
Versão: 1.0.0

Módulo: Cálculo de molas horizontais de estacas (k_mola)
Descrição:
    Implementa o cálculo das molas horizontais (k_mola, em tf/m) para análise 
    estrutural de apoios horizontais de estacas. O cálculo utiliza valores 
    empíricos de m (tf/m4) associados ao SPT e ao tipo de solo.

    Fonte da metodologia: https://docs.tqs.com.br/Docs/Details?id=3836&language=pt-BR
    
    Onde:
        - m: coeficiente de reação horizontal do solo (tf/m4) obtido por tabela
        - prof: profundidade do ponto considerado (m)
        - área: área de influência equivalente (m²), calculada como área = diâmetro * 1
    
    Observação:
        Este método segue a prática comum em fundações para modelagem simplificada
        de estacas submetidas a esforços horizontais. Os valores utilizados para "m"
        são derivados de correlações empíricas amplamente empregadas na engenharia
        geotécnica e estrutural.

Testado por: (informar)
Data do teste: (informar)
"""

from datetime import datetime

class SoilAnalysisSystemAPI:

    """
    Classe responsável pelo cálculo das molas horizontais de estacas e geração
    do relatório no formato TXT.

    Métodos:
        - calcular(): retorna m, kmola e área equivalente para um apoio.
        - gerar_relatorio_txt(): monta relatório padrão para exportação.

    Atributos:
        - soil_types: dicionário contendo valores de m (tf/m³) indexados por SPT.
    """

    def __init__(self):
        self.soil_types = {
            'Argila': {
                0: 25.00,1: 75.00, 2: 112.50, 3: 150.00, 4: 200.00, 5: 250.00,
                6: 300.00, 7: 333.33, 8: 366.67, 9: 400.00, 10: 433.33,
                11: 466.67, 12: 500.00, 13: 520, 14: 540.00, 15: 560.00,
                16: 580.00, 17: 600.00, 18: 620.00, 19: 640.00, 20: 660.00,
                21: 680.00, 22: 700.00, 23: 725.00, 24: 750.00, 25: 775.00,
                26: 800.00, 27: 825.00, 28: 850.00, 29: 875.00, 30: 900.00
            },
            'Areia': {
                0: 100.00, 1: 150.00, 2: 175.00, 3: 200.00, 4: 225.00, 5: 250.00,
                6: 275.00, 7: 300.00, 8: 315.38, 9: 330.76, 10: 346.15,
                11: 361.52, 12: 376.92, 13: 392.30, 14: 407.69, 15: 423.07,
                16: 438.46, 17: 453.84, 18: 469.23, 19: 484.56, 20: 500.00,
                21: 515.00, 22: 530.00, 23: 545.00, 24: 560.00, 25: 575.00,
                26: 590.00, 27: 605.00, 28: 620.00, 29: 635.00, 30: 650.00,
                31: 665.00, 32: 680.00, 33: 695.00, 34: 710.00, 35: 725.00,
                36: 740.00, 37: 755.00, 38: 770.00, 39: 785.00, 40: 800.00,
                41: 870.00, 42: 940.00, 43: 1010.00, 44: 1080.00, 45: 1150.00,
                46: 1220.00, 47: 1290.00, 48: 1360.00, 49: 1430.00, 50: 1500.00
            }
        }

    # --------------------------------------------------------
    # Cálculo básico
    # --------------------------------------------------------
    def calcular(self, tipo_solo: str, spt: int, prof: float, diametro: float):

        """
        Calcula os parâmetros da mola horizontal para um único apoio.

        Parâmetros:
            tipo_solo (str): "Areia" ou "Argila".
            spt (int): Valor de SPT correspondente ao nível do apoio.
            prof (float): Profundidade do apoio (m).
            diametro (float): Diâmetro equivalente da estaca (m).

        Retorna:
            dict contendo:
                - solo
                - spt
                - prof
                - area (m²)
                - m (tf/m³)
                - kmola (tf/m)

        Erros:
            {"erro": "..."} quando tipo de solo ou SPT forem inválidos.
        """

        if tipo_solo not in self.soil_types:
            return {"erro": "Tipo de solo inválido"}

        if spt not in self.soil_types[tipo_solo]:
            return {"erro": f"SPT {spt} não encontrado para o solo '{tipo_solo}'"}

        if prof <= 0:
            return {"erro": "Profundidade deve ser maior que zero."}

        if diametro <= 0:
            return {"erro": "Diâmetro deve ser maior que zero."}

        if spt < 0:
            return {"erro": "SPT não pode ser negativo."}

        m = self.soil_types[tipo_solo][spt]

        area = diametro * 1  # área equivalente

        kmola = m * prof * area

        return {
            "solo": tipo_solo,
            "spt": spt,
            "prof": prof,
            "area": area,     # <-- área exportada
            "m": round(m, 2),
            "kmola": round(kmola, 2),
        }

    # --------------------------------------------------------
    # Geração do relatório TXT
    # --------------------------------------------------------
    def gerar_relatorio_txt(self, apoios: list) -> str:

        """
        Gera o relatório TXT padronizado contendo todos os apoios
        e seus respectivos valores de m e kmola.

        Parâmetros:
            apoios (list): lista de dicionários conforme saída do método calcular().

        Retorna:
            str: conteúdo formatado do arquivo TXT.
        """

        linhas = []
        linhas.append("=" * 80)
        linhas.append("RELATÓRIO – MOLAS HORIZONTAIS DE ESTACAS (k_mola)")
        linhas.append(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        linhas.append("=" * 80)
        linhas.append("")

        linhas.append(
            f"{'Apoio':<10}{'Prof(m)':<12}{'Área(m²)':<12}{'Tipo Solo':<12}"
            f"{'SPT':<8}{'m(tf/m4)':<12}{'kmola(tf/m)':<12}"
        )
        linhas.append("-" * 80)

        for d in apoios:
            linhas.append(
                f"{d['apoio']:<10}"
                f"{d['prof']:<12.2f}"
                f"{d['area']:<12.3f}"      # <-- exporta área
                f"{d['tipo_solo']:<12}"
                f"{d['spt']:<8}"
                f"{d['m']:<12.2f}"
                f"{d['kmola']:<12.2f}"
            )

        linhas.append("")
        linhas.append("=" * 80)
        linhas.append(f"Total de apoios: {len(apoios)}")
        linhas.append("=" * 80)

        return "\n".join(linhas)
