"""Gera figura do artigo a partir das OR documentadas, sem estimar incerteza."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def carregar_or(caminho):
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    result = {}
    for linha in dados["odds_ratios"]:
        categoria = linha["categoria_screentime"]
        desfecho = linha["target"]
        if linha["referencia"] != 1 or (desfecho, categoria) in result:
            raise ValueError("Referência inesperada ou categoria duplicada")
        result[(desfecho, categoria)] = float(linha["odds_ratio_ajustada_amostral"])
    if set(result) != {(d, c) for d in ("depressao_atual", "ansiedade_atual") for c in range(2, 6)}:
        raise ValueError("Conjunto incompleto de categorias ou desfechos")
    return result


def fonte(tamanho):
    for caminho in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def gerar(caminho, destino):
    valores = carregar_or(caminho)
    im = Image.new("RGB", (1800, 950), "white")
    draw = ImageDraw.Draw(im)
    font, pequena = fonte(39), fonte(31)
    x0, x1, y0 = 405, 1650, 150
    escala = lambda valor: x0 + (valor - 0.8) / 1.2 * (x1 - x0)
    cores = {"depressao_atual": "#235c9f", "ansiedade_atual": "#a54022"}
    for tick in (0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0):
        x = escala(tick)
        draw.line((x, y0, x, 700), fill="#b1b1b1" if tick == 1 else "#e4e4e4", width=3)
        draw.text((x, 727), f"{tick:.1f}".replace(".", ","), fill="black", font=pequena, anchor="mt")
    for i, rotulo in enumerate(("1 hora", "2 horas", "3 horas", "4 horas ou mais")):
        y = 215 + i * 145
        draw.text((365, y), rotulo, fill="black", font=font, anchor="rm")
        for nome, dy in (("depressao_atual", -25), ("ansiedade_atual", 25)):
            v = valores[(nome, i + 2)]
            x = escala(v)
            draw.ellipse((x-11, y+dy-11, x+11, y+dy+11), fill=cores[nome])
            draw.text((x+17, y+dy), f"{v:.2f}".replace(".", ","), fill=cores[nome], font=pequena, anchor="lm")
    draw.text((1025, 800), "Razão de chances amostral (referência: menos de 1 hora)", fill="black", font=pequena, anchor="mt")
    draw.ellipse((460, 85, 480, 105), fill=cores["depressao_atual"])
    draw.text((495, 95), "Depressão", fill="black", font=font, anchor="lm")
    draw.ellipse((895, 85, 915, 105), fill=cores["ansiedade_atual"])
    draw.text((930, 95), "Ansiedade", fill="black", font=font, anchor="lm")
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, dpi=(300, 300))


def gerar_ponderada(caminho, destino):
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))["desfechos"]
    im = Image.new("RGB", (1800, 920), "white")
    draw = ImageDraw.Draw(im)
    fonte_rotulo, fonte_eixo = fonte(40), fonte(32)
    x0, x1 = 390, 1670
    xmin, xmax = 0.4, 1.8

    def escala(valor):
        return x0 + (valor - xmin) * (x1 - x0) / (xmax - xmin)

    desfechos = [("depressao_atual", "Depressão", "#235c9f", -24),
                 ("ansiedade_atual", "Ansiedade", "#a54022", 24)]
    for i, tick in enumerate((0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8)):
        x = escala(tick)
        draw.line((x, 150, x, 720), fill="#777777" if i == 3 else "#e4e4e4", width=4)
        draw.text((x, 744), f"{tick:.1f}".replace(".", ","), fill="black", font=fonte_eixo, anchor="mt")
    for i, (target, nome, cor, deslocamento) in enumerate(desfechos):
        x = 550 + i * 470
        draw.text((x + 33, 87), nome, fill="black", font=fonte_rotulo, anchor="lm")
        marcador = draw.ellipse if i == 0 else draw.rectangle
        marcador((x-10, 77, x+10, 97), fill=cor)
        valores = dados[target]["modelos"]["completo"]["categorias"]
        for codigo in range(2, 6):
            y = 220 + (codigo - 2) * 142 + deslocamento
            item = valores[str(codigo)]
            lo, hi = item["ic95"]
            x = escala(item["or"])
            if not xmin <= lo <= item["or"] <= hi <= xmax:
                raise ValueError("O intervalo da figura excede o eixo ou está fora de ordem")
            draw.line((escala(lo), y, escala(hi), y), fill=cor, width=6)
            for extremo in (lo, hi):
                xf = escala(extremo)
                draw.line((xf, y-10, xf, y+10), fill=cor, width=4)
            if i == 0:
                draw.ellipse((x-11, y-11, x+11, y+11), fill=cor)
            else:
                draw.rectangle((x-10, y-10, x+10, y+10), fill=cor)
    for i, texto in enumerate(("1 hora", "2 horas", "3 horas", "4 horas ou mais")):
        draw.text((355, 220 + i * 142), texto, fill="black", font=fonte_rotulo, anchor="rm")
    draw.text((1030, 815), "Razão de chances (referência: menos de 1 hora)", fill="black", font=fonte_eixo, anchor="mt")
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, dpi=(300, 300))


if __name__ == "__main__":
    gerar(ROOT / "reports/modelagem/v2_limiar_cv/associacao/associacao.json", ROOT / "artigo/figuras/associacao.png")
    gerar_ponderada(ROOT / "artigo/resultados_reproducao/desenho_nsch.json",
                    ROOT / "artigo/figuras/associacao_ponderada.png")
