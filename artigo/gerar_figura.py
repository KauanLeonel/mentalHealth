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


if __name__ == "__main__":
    gerar(ROOT / "reports/associacao/associacao.json", ROOT / "artigo/figuras/associacao.png")
