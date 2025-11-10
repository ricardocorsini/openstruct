import os
import uuid
import time
from ezdxf import new
from ezdxf.enums import TextEntityAlignment

TMP_DIR = "app/tmp"

def estacas_cargas(circunferencias, nome_base="estacas"):
    """
    Gera um desenho DXF com estacas em planta com as respectivas cargas atuantes.
    Retorna o caminho absoluto do arquivo gerado.
    """
    os.makedirs(TMP_DIR, exist_ok=True)

    nome_arquivo = f"{nome_base}_{uuid.uuid4().hex[:8]}.dxf"
    caminho_arquivo = os.path.join(TMP_DIR, nome_arquivo)

    doc = new(dxfversion="R2010")
    msp = doc.modelspace()

    # Camadas
    doc.layers.new(name="ESTACAS", dxfattribs={"color": 4})
    doc.layers.new(name="TEXTOS", dxfattribs={"color": 3})
    doc.layers.new(name="EIXOS", dxfattribs={"color": 8})
    doc.layers.new(name="GERAL", dxfattribs={"color": 8})

    # Eixos
    tamanho_ref = 1.0
    msp.add_line((0, 0), (tamanho_ref, 0), dxfattribs={"layer": "EIXOS"})
    msp.add_line((0, 0), (0, tamanho_ref), dxfattribs={"layer": "EIXOS"})
    msp.add_text("X", dxfattribs={"height": 0.12, "layer": "EIXOS"}).set_placement(
        (tamanho_ref + 0.05, 0), align=TextEntityAlignment.LEFT
    )
    msp.add_text("Y", dxfattribs={"height": 0.12, "layer": "EIXOS"}).set_placement(
        (0, tamanho_ref + 0.05), align=TextEntityAlignment.LEFT
    )

    # Estacas
    for circ in circunferencias:
        centro = (circ["coord_X"], circ["coord_Y"])
        diametro = circ["diametro"]
        texto = circ.get("texto", "")
        raio = diametro / 2

        msp.add_circle(centro, raio, dxfattribs={"layer": "ESTACAS"})

        cruz = 0.1
        msp.add_line((centro[0] - cruz, centro[1]),
                     (centro[0] + cruz, centro[1]), dxfattribs={"layer": "GERAL"})
        msp.add_line((centro[0], centro[1] - cruz),
                     (centro[0], centro[1] + cruz), dxfattribs={"layer": "GERAL"})

        linhas_texto = texto.split("\n")
        altura_texto = 0.20
        espacamento_texto = 0.05

        for i, linha in enumerate(linhas_texto):
            pos_y = centro[1] + raio + espacamento_texto + (len(linhas_texto) * (altura_texto + espacamento_texto)) - (altura_texto + espacamento_texto) * (i) 

            msp.add_text(
                linha,
                dxfattribs={"layer": "TEXTOS", "height": altura_texto},
            ).set_placement(
                (centro[0], pos_y),
                align=TextEntityAlignment.BOTTOM_LEFT
            )

    xs = [c["coord_X"] for c in circunferencias]
    ys = [c["coord_Y"] for c in circunferencias]
    centro_x = (max(xs) + min(xs)) / 2
    base_y = min(ys) - 1.5

    msp.add_text(
        "PLANTA DE ESTACAS COM CARGAS",
        dxfattribs={"height": 0.3, "layer": "TEXTOS"},
    ).set_placement((centro_x, base_y), align=TextEntityAlignment.CENTER)

    doc.saveas(caminho_arquivo)
    return caminho_arquivo
