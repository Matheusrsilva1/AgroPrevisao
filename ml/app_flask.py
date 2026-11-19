"""
AgroPrevisao – painel web para o produtor (Global Solution, Grupo 12).

Executar a partir da pasta ml:
    python app_flask.py
Depois abrir http://127.0.0.1:5000

Usa o mesmo dataset e as mesmas variáveis do notebook produtividade_produtor_rural.ipynb.
"""
import math
import os

import pandas as pd
from flask import Flask, render_template, request
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

_AQUI = os.path.dirname(os.path.abspath(__file__))
# procura o dataset na mesma pasta (entrega) ou em ../data (projeto original)
CAMINHO = next((c for c in (os.path.join(_AQUI, "dataset_soja_pr.csv"),
                            os.path.join(_AQUI, "..", "data", "dataset_soja_pr.csv"))
                if os.path.exists(c)), os.path.join(_AQUI, "dataset_soja_pr.csv"))
FEATURES = ["rend_media3", "rend_ultimo", "area_anterior",
            "precip_safra_mm", "temp_media_safra_c", "tendencia_ano"]
ALVO = "rendimento_kg_ha"
ANO_CORTE = 2019
KG_POR_SACA = 60
PRECO_PADRAO = 120.0
ERRO_MEDIO_SC = 9.5    # erro médio absoluto no teste (570 kg/ha ≈ 9,5 sacas/ha)
MEDIA_CLIMA_ANOS = 10  # clima esperado = média dos últimos 10 anos da cidade

app = Flask(__name__)


def carregar():
    bruto = pd.read_csv(CAMINHO)
    df = bruto.sort_values(["municipio_cod", "ano"]).copy()
    g = df.groupby("municipio_cod")
    df["rend_ultimo"] = g[ALVO].shift(1)
    df["rend_media3"] = g[ALVO].transform(lambda s: s.shift(1).rolling(3).mean())
    df["area_anterior"] = g["area_colhida_ha"].shift(1)
    return df.dropna(subset=FEATURES + [ALVO]).copy()


DF = carregar()
TREINO = DF[DF["ano"] <= ANO_CORTE]
MODELO = make_pipeline(StandardScaler(), LinearRegression())
MODELO.fit(TREINO[FEATURES], TREINO[ALVO])
MUNICIPIOS = sorted(DF["municipio"].unique())
MEDIA_ESTADO_ANO = DF.groupby("ano")[ALVO].mean() / KG_POR_SACA
CHUVA_ESTADO_ANO = DF.groupby("ano")["precip_safra_mm"].mean()


def sc(kg_ha):
    return kg_ha / KG_POR_SACA


def previsao_cidade(cidade):
    """Monta a entrada da próxima safra com o histórico da cidade."""
    h = DF[DF["municipio"] == cidade].sort_values("ano")
    ult = h.iloc[-1]
    recentes = h.tail(MEDIA_CLIMA_ANOS)
    entrada = pd.DataFrame([{
        "rend_media3": h[ALVO].tail(3).mean(),
        "rend_ultimo": ult[ALVO],
        "area_anterior": ult["area_colhida_ha"],
        # clima da próxima safra é desconhecido: usa a média dos últimos anos da cidade
        "precip_safra_mm": recentes["precip_safra_mm"].mean(),
        "temp_media_safra_c": recentes["temp_media_safra_c"].mean(),
        "tendencia_ano": ult["tendencia_ano"] + 1,
    }])
    kg = float(MODELO.predict(entrada[FEATURES])[0])
    return h, int(ult["ano"]) + 1, kg, ult, recentes


def svg_barras(rotulos, valores, destaque=None, linha=None, altura=240, unidade=""):
    """Barras em SVG. `linha` é uma lista opcional de valores para uma linha de referência."""
    largura, base, topo_pad = 720, 28, 26
    maximo = max(max(valores), max(linha) if linha else 0) * 1.15
    n = len(valores)
    passo = (largura - 20) / n
    partes = []
    for i, (rot, v) in enumerate(zip(rotulos, valores)):
        x = 10 + i * passo + passo * 0.15
        w = passo * 0.7
        hb = (v / maximo) * (altura - base - topo_pad)
        y = altura - base - hb
        cor = "#c58b1a" if (destaque is not None and i == destaque) else "#d9c9a3"
        partes.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{hb:.1f}" rx="3" fill="{cor}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="11" fill="#333">{v:.0f}{unidade}</text>'
            f'<text x="{x + w / 2:.1f}" y="{altura - 9}" text-anchor="middle" font-size="11" fill="#555">{rot}</text>'
        )
    if linha:
        pontos = []
        for i, v in enumerate(linha):
            x = 10 + i * passo + passo / 2
            y = altura - base - (v / maximo) * (altura - base - topo_pad)
            pontos.append(f"{x:.1f},{y:.1f}")
        partes.append(f'<polyline points="{" ".join(pontos)}" fill="none" stroke="#3b2e13" '
                      f'stroke-width="2" stroke-dasharray="5 4"/>')
    return (f'<svg viewBox="0 0 {largura} {altura}" width="100%" role="img">' + "".join(partes) + "</svg>")


def svg_linhas(rotulos, series, altura=240):
    """Linhas em SVG. `series` = [(nome, valores, cor)]."""
    largura, base = 720, 28
    todos = [v for _, vals, _ in series for v in vals]
    # limites "redondos" para o eixo: passo de 1, 2 ou 5 × potência de 10
    bruto_min, bruto_max = min(todos) * 0.9, max(todos) * 1.05
    faixa = bruto_max - bruto_min
    magnitude = 10 ** math.floor(math.log10(faixa / 4))
    passo_eixo = min((m * magnitude for m in (1, 2, 5, 10) if m * magnitude * 4 >= faixa), default=magnitude * 10)
    minimo = math.floor(bruto_min / passo_eixo) * passo_eixo
    maximo = math.ceil(bruto_max / passo_eixo) * passo_eixo
    n = len(rotulos)
    passo = (largura - 60) / max(n - 1, 1)
    partes = []
    for nome, vals, cor in series:
        pts = []
        for i, v in enumerate(vals):
            x = 40 + i * passo
            y = altura - base - (v - minimo) / (maximo - minimo) * (altura - base - 20)
            pts.append(f"{x:.1f},{y:.1f}")
        partes.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{cor}" stroke-width="2.5"/>')
    for i, rot in enumerate(rotulos):
        x = 40 + i * passo
        partes.append(f'<text x="{x:.1f}" y="{altura - 9}" text-anchor="middle" font-size="11" fill="#555">{rot}</text>')
    # eixo vertical: 4 marcas com valor em sacas (ou mm)
    n_marcas = int(round((maximo - minimo) / passo_eixo))
    for k in range(n_marcas + 1):
        v = minimo + passo_eixo * k
        y = altura - base - (v - minimo) / (maximo - minimo) * (altura - base - 20)
        partes.append(f'<line x1="36" y1="{y:.1f}" x2="{largura - 10}" y2="{y:.1f}" stroke="#eee"/>')
        partes.append(f'<text x="30" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="#777">{v:.0f}</text>')
    return f'<svg viewBox="0 0 {largura} {altura}" width="100%" role="img">' + "".join(partes) + "</svg>"


@app.route("/", methods=["GET"])
def index():
    cidade = request.args.get("cidade", "Londrina - PR" if "Londrina - PR" in MUNICIPIOS else MUNICIPIOS[0])
    if cidade not in MUNICIPIOS:
        cidade = MUNICIPIOS[0]
    try:
        hectares = max(1.0, float(request.args.get("hectares", 50)))
    except ValueError:
        hectares = 50.0
    try:
        preco = max(10.0, float(request.args.get("preco", PRECO_PADRAO)))
    except ValueError:
        preco = PRECO_PADRAO

    h, ano_prox, previsto_kg, ult, recentes = previsao_cidade(cidade)
    previsto_sc = sc(previsto_kg)
    media3_sc = sc(h[ALVO].tail(3).mean())
    media10_sc = sc(recentes[ALVO].mean())

    if previsto_sc >= media3_sc * 1.05:
        situacao, cor, dica = ("Acima da média dos últimos anos", "verde",
                               "Boa perspectiva. Vale considerar negociar parte da venda com antecedência.")
    elif previsto_sc <= media3_sc * 0.95:
        situacao, cor, dica = ("Abaixo da média dos últimos anos", "vermelho",
                               "Atenção: planeje custos com cuidado e converse com a cooperativa sobre a safra.")
    else:
        situacao, cor, dica = ("Perto da média dos últimos anos", "amarelo",
                               "Safra dentro do normal. Mantenha o manejo e acompanhe o clima.")

    # clima da última safra comparado com a média da cidade
    chuva_media = recentes["precip_safra_mm"].mean()
    chuva_ult = ult["precip_safra_mm"]
    diff_chuva = (chuva_ult - chuva_media) / chuva_media * 100
    if diff_chuva <= -15:
        clima_txt = f"A chuva da última safra ficou {abs(diff_chuva):.0f}% abaixo da média da cidade."
    elif diff_chuva >= 15:
        clima_txt = f"A chuva da última safra ficou {diff_chuva:.0f}% acima da média da cidade."
    else:
        clima_txt = "A chuva da última safra ficou perto da média da cidade."

    # posição da cidade no estado (última safra conhecida)
    ultimo_ano = int(ult["ano"])
    do_ano = DF[DF["ano"] == ultimo_ano].sort_values(ALVO, ascending=False).reset_index(drop=True)
    posicao = int(do_ano.index[do_ano["municipio"] == cidade][0]) + 1
    total_mun = len(do_ano)
    percentil = round((1 - (posicao - 1) / total_mun) * 100)

    total_sacas = previsto_sc * hectares
    faixa_min = max(previsto_sc - ERRO_MEDIO_SC, 0)
    faixa_max = previsto_sc + ERRO_MEDIO_SC

    # cenários de preço
    cenarios = []
    for p in [80, 100, 120, 140, 160]:
        cenarios.append({"preco": p, "valor": total_sacas * p, "destaque": abs(p - preco) < 1e-6})

    # gráfico 1: safras da cidade com a estimativa
    hist = h.tail(15)
    rot1 = [str(int(a))[2:] for a in hist["ano"]] + [str(ano_prox)[2:]]
    val1 = [sc(v) for v in hist[ALVO]] + [previsto_sc]
    graf_safras = svg_barras(rot1, val1, destaque=len(val1) - 1)

    # gráfico 2: cidade x estado ao longo dos anos
    anos = [int(a) for a in h["ano"].tail(12)]
    cidade_serie = [sc(v) for v in h.set_index("ano").loc[anos, ALVO]]
    estado_serie = [float(MEDIA_ESTADO_ANO.loc[a]) for a in anos]
    graf_comparacao = svg_linhas([str(a)[2:] for a in anos],
                                 [("Sua cidade", cidade_serie, "#c58b1a"),
                                  ("Média do Paraná", estado_serie, "#3b2e13")])

    # gráfico 3: chuva da safra na cidade x média do estado
    chuva_serie = [float(v) for v in h.set_index("ano").loc[anos, "precip_safra_mm"]]
    chuva_estado = [float(CHUVA_ESTADO_ANO.loc[a]) for a in anos]
    graf_chuva = svg_linhas([str(a)[2:] for a in anos],
                            [("Sua cidade", chuva_serie, "#2f6f9f"),
                             ("Média do Paraná", chuva_estado, "#999999")])

    return render_template(
        "index.html",
        municipios=MUNICIPIOS,
        cidade=cidade,
        hectares=hectares,
        preco=preco,
        ano_prox=ano_prox,
        ultimo_ano=ultimo_ano,
        previsto_sc=previsto_sc,
        faixa_min=faixa_min,
        faixa_max=faixa_max,
        media3_sc=media3_sc,
        media10_sc=media10_sc,
        situacao=situacao,
        cor=cor,
        dica=dica,
        clima_txt=clima_txt,
        posicao=posicao,
        total_mun=total_mun,
        percentil=percentil,
        total_sacas=total_sacas,
        receita=total_sacas * preco,
        receita_min=faixa_min * hectares * preco,
        receita_max=faixa_max * hectares * preco,
        cenarios=cenarios,
        ultima_sc=sc(ult[ALVO]),
        chuva_ult=chuva_ult,
        chuva_media=chuva_media,
        graf_safras=graf_safras,
        graf_comparacao=graf_comparacao,
        graf_chuva=graf_chuva,
    )


if __name__ == "__main__":
    app.run(debug=False, port=5000)
