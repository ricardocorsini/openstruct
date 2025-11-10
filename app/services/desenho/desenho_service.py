import ezdxf
from ezdxf.enums import TextEntityAlignment


def gerar_desenho_estacas(circunferencias, nome_arquivo="estacas_com_cargas.dxf"):
    """
    Gera um desenho DXF com estacas (círculos) e cargas.
    """
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    # Camadas
    doc.layers.new(name='ESTACAS', dxfattribs={'color': 3})
    doc.layers.new(name='TEXTOS', dxfattribs={'color': 7})
    doc.layers.new(name='EIXOS', dxfattribs={'color': 1})
    doc.layers.new(name='GERAL', dxfattribs={'color': 8})

    # Eixos
    tamanho_ref = 1.0
    msp.add_line((0, 0), (tamanho_ref, 0), dxfattribs={'layer': 'EIXOS'})
    msp.add_line((0, 0), (0, tamanho_ref), dxfattribs={'layer': 'EIXOS'})
    msp.add_text("X", dxfattribs={'height': 0.12, 'layer': 'EIXOS'}).set_placement(
        (tamanho_ref + 0.05, 0), align=TextEntityAlignment.LEFT
    )
    msp.add_text("Y", dxfattribs={'height': 0.12, 'layer': 'EIXOS'}).set_placement(
        (0, tamanho_ref + 0.05), align=TextEntityAlignment.LEFT
    )

    # Estacas
    for circ in circunferencias:
        centro = (circ["coord_X"], circ["coord_Y"])
        diametro = circ["diametro"]
        texto = circ.get("texto", "")
        raio = diametro / 2

        msp.add_circle(centro, raio, dxfattribs={'layer': 'ESTACAS'})

        cruz = 0.05 * diametro
        msp.add_line((centro[0] - cruz, centro[1]),
                     (centro[0] + cruz, centro[1]), dxfattribs={'layer': 'GERAL'})
        msp.add_line((centro[0], centro[1] - cruz),
                     (centro[0], centro[1] + cruz), dxfattribs={'layer': 'GERAL'})

        linhas_texto = texto.split("\n")
        altura_texto = 0.15 * diametro
        espacamento = altura_texto * 1.2

        for i, linha in enumerate(linhas_texto):
            pos_y = centro[1] + raio + 0.1 - i * espacamento
            msp.add_text(
                linha,
                dxfattribs={'layer': 'TEXTOS', 'height': altura_texto, 'color': 7}
            ).set_placement((centro[0], pos_y), align=TextEntityAlignment.CENTER)

    xs = [c['coord_X'] for c in circunferencias]
    ys = [c['coord_Y'] for c in circunferencias]
    centro_x = (max(xs) + min(xs)) / 2
    base_y = min(ys) - 1.5

    msp.add_text(
        "PLANTA DE ESTACAS COM CARGAS - AULA 07",
        dxfattribs={'height': 0.3, 'layer': 'TEXTOS'}
    ).set_placement((centro_x, base_y), align=TextEntityAlignment.CENTER)

    msp.add_text(
        "Unidades: metros e kN | Escala simbólica 1:100",
        dxfattribs={'height': 0.15, 'layer': 'GERAL'}
    ).set_placement((centro_x, base_y - 0.3), align=TextEntityAlignment.CENTER)

    doc.saveas(nome_arquivo)
    return nome_arquivo
