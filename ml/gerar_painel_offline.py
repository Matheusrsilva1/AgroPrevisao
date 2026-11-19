"""
Gera o painel AgroPrevisao como UM arquivo HTML que funciona sem internet e sem servidor.

Executar a partir da pasta ml:
    python gerar_painel_offline.py
Saída: AgroPrevisao_Offline.html (abrir com duplo clique, no computador ou no celular).

Os números vêm do mesmo dataset e do mesmo modelo (Regressão Linear) do notebook e do app_flask.py.
Nada é digitado à mão: o script calcula a estimativa de cada município e grava tudo dentro do HTML.
"""
import json
import os

from app_flask import (ALVO, DF, ERRO_MEDIO_SC, MUNICIPIOS, MEDIA_ESTADO_ANO, CHUVA_ESTADO_ANO,
                       PRECO_PADRAO, previsao_cidade, sc)

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "AgroPrevisao_Offline.html")


def dados_cidade(cidade):
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

    chuva_media = float(recentes["precip_safra_mm"].mean())
    chuva_ult = float(ult["precip_safra_mm"])
    diff = (chuva_ult - chuva_media) / chuva_media * 100
    if diff <= -15:
        clima_txt = f"A chuva da última safra ficou {abs(diff):.0f}% abaixo da média da cidade."
    elif diff >= 15:
        clima_txt = f"A chuva da última safra ficou {diff:.0f}% acima da média da cidade."
    else:
        clima_txt = "A chuva da última safra ficou perto da média da cidade."

    ultimo_ano = int(ult["ano"])
    do_ano = DF[DF["ano"] == ultimo_ano].sort_values(ALVO, ascending=False).reset_index(drop=True)
    posicao = int(do_ano.index[do_ano["municipio"] == cidade][0]) + 1
    total = len(do_ano)
    percentil = round((1 - (posicao - 1) / total) * 100)

    hist = h.tail(15)
    anos12 = [int(a) for a in h["ano"].tail(12)]
    idx = h.set_index("ano")
    r1 = lambda v: round(float(v), 1)
    return {
        "ano_prox": ano_prox, "ultimo_ano": ultimo_ano,
        "previsto": r1(previsto_sc), "media3": r1(media3_sc), "media10": r1(media10_sc),
        "ultima": r1(sc(ult[ALVO])), "situacao": situacao, "cor": cor, "dica": dica,
        "clima_txt": clima_txt, "chuva_ult": round(chuva_ult), "chuva_media": round(chuva_media),
        "posicao": posicao, "total": total, "percentil": percentil,
        "hist_rot": [str(int(a))[2:] for a in hist["ano"]],
        "hist_val": [r1(sc(v)) for v in hist[ALVO]],
        "anos12": [str(a)[2:] for a in anos12],
        "cidade12": [r1(sc(idx.loc[a, ALVO])) for a in anos12],
        "estado12": [r1(MEDIA_ESTADO_ANO.loc[a]) for a in anos12],
        "chuva12": [round(float(idx.loc[a, "precip_safra_mm"])) for a in anos12],
        "chuva_estado12": [round(float(CHUVA_ESTADO_ANO.loc[a])) for a in anos12],
    }


MODELO_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AgroPrevisao – sua safra de soja (versão offline)</title>
  <style>
    :root { --fundo:#f7f2e7; --card:#ffffff; --texto:#2b2b2b; --suave:#6b6b6b; --ouro:#c58b1a;
            --verde:#2e7d32; --amarelo:#b38600; --vermelho:#c62828; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: system-ui, "Segoe UI", Roboto, sans-serif; background:var(--fundo); color:var(--texto); }
    header { background:#3b2e13; color:#fff; padding:22px 20px; }
    header h1 { margin:0; font-size:1.6rem; }
    header p { margin:4px 0 0 0; opacity:.85; }
    main { max-width:960px; margin:0 auto; padding:20px 16px 40px; }
    form { background:var(--card); border-radius:14px; padding:18px; display:grid; gap:14px;
           grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); box-shadow:0 1px 4px rgba(0,0,0,.06); }
    label { font-size:.9rem; color:var(--suave); display:grid; gap:6px; }
    select, input { font-size:1rem; padding:10px; border:1px solid #d8cdb5; border-radius:8px; background:#fff; }
    button { font-size:1rem; padding:11px 16px; border:0; border-radius:8px; background:var(--ouro);
             color:#fff; font-weight:600; cursor:pointer; align-self:end; }
    .grid { display:grid; gap:16px; margin-top:18px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
    .card { background:var(--card); border-radius:14px; padding:20px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
    .card h2 { font-size:1rem; color:var(--suave); margin:0 0 8px 0; font-weight:600; }
    .numero { font-size:2.4rem; font-weight:800; margin:0; line-height:1.1; }
    .sub { color:var(--suave); margin:6px 0 0 0; font-size:.95rem; }
    .selo { display:inline-block; padding:6px 12px; border-radius:999px; font-weight:700; color:#fff; font-size:.9rem; }
    .verde { background:var(--verde); } .amarelo { background:var(--amarelo); } .vermelho { background:var(--vermelho); }
    .dica { border-left:4px solid var(--ouro); padding:10px 14px; background:#fbf6ea; border-radius:8px; margin-top:12px; }
    .wide { grid-column: 1 / -1; }
    .escala { display:flex; justify-content:space-between; font-size:.85rem; color:var(--suave); margin-top:8px; }
    .faixa { height:10px; border-radius:6px; background:linear-gradient(90deg,#eadfc6,#c58b1a,#eadfc6); margin-top:10px; }
    .mini { display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; margin-top:12px; }
    .mini div { background:#fbf6ea; border-radius:10px; padding:10px; text-align:center; }
    .mini b { display:block; font-size:1.15rem; }
    .mini span { font-size:.8rem; color:var(--suave); }
    table { width:100%; border-collapse:collapse; margin-top:8px; font-size:.95rem; }
    td, th { padding:8px 6px; border-bottom:1px solid #eee; text-align:left; }
    tr.dest td { background:#fbf6ea; font-weight:700; }
    .legenda { display:flex; gap:16px; font-size:.85rem; color:var(--suave); margin-top:6px; flex-wrap:wrap; }
    .legenda i { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:middle; }
    svg { display:block; margin-top:8px; }
    footer { color:var(--suave); font-size:.82rem; margin-top:22px; line-height:1.5; }
    @media (max-width: 520px) { .numero { font-size:2rem; } .mini { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>AgroPrevisao</h1>
    <p>Quanto a sua lavoura de soja deve render na próxima safra · funciona sem internet</p>
  </header>

  <main>
    <form id="form">
      <label>Seu município
        <select id="cidade"></select>
      </label>
      <label>Hectares de soja
        <input type="number" id="hectares" min="1" step="1" value="50">
      </label>
      <label>Preço esperado por saca (R$)
        <input type="number" id="preco" min="10" step="5" value="__PRECO__">
      </label>
      <button type="submit">Ver estimativa</button>
    </form>

    <div class="grid" id="painel"></div>

    <footer>
      A estimativa é um apoio ao planejamento. Ela não garante a safra. Em média, erra cerca de __ERRO__ sacas por hectare,
      e nos anos de seca o erro costuma ser maior. Use junto com a orientação da sua cooperativa ou da extensão rural.
      Fontes: IBGE (produção municipal) e INMET (estações meteorológicas). O valor por saca é o que você informa; não é previsão de preço.
      Esta página é um único arquivo: depois de baixada, abre sem internet.
    </footer>
  </main>

<script>
const DADOS = __DADOS__;
const ERRO = __ERRO__;
const fmt = (v) => Math.round(v).toLocaleString("pt-BR");

function svgBarras(rot, val, destaque) {
  const L = 720, H = 240, base = 28, topo = 26;
  const max = Math.max(...val) * 1.15, n = val.length, passo = (L - 20) / n;
  let s = "";
  val.forEach((v, i) => {
    const x = 10 + i * passo + passo * 0.15, w = passo * 0.7;
    const hb = (v / max) * (H - base - topo), y = H - base - hb;
    const cor = i === destaque ? "#c58b1a" : "#d9c9a3";
    s += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${hb.toFixed(1)}" rx="3" fill="${cor}"/>` +
         `<text x="${(x + w / 2).toFixed(1)}" y="${(y - 6).toFixed(1)}" text-anchor="middle" font-size="11" fill="#333">${Math.round(v)}</text>` +
         `<text x="${(x + w / 2).toFixed(1)}" y="${H - 9}" text-anchor="middle" font-size="11" fill="#555">${rot[i]}</text>`;
  });
  return `<svg viewBox="0 0 ${L} ${H}" width="100%" role="img">${s}</svg>`;
}

function svgLinhas(rot, series) {
  const L = 720, H = 240, base = 28;
  const todos = series.flatMap(s => s.vals);
  const bmin = Math.min(...todos) * 0.9, bmax = Math.max(...todos) * 1.05, faixa = bmax - bmin;
  const mag = Math.pow(10, Math.floor(Math.log10(faixa / 4)));
  let passoEixo = mag * 10;
  for (const m of [1, 2, 5, 10]) { if (m * mag * 4 >= faixa) { passoEixo = m * mag; break; } }
  const min = Math.floor(bmin / passoEixo) * passoEixo, max = Math.ceil(bmax / passoEixo) * passoEixo;
  const n = rot.length, passo = (L - 60) / Math.max(n - 1, 1);
  const Y = (v) => H - base - (v - min) / (max - min) * (H - base - 20);
  let s = "";
  series.forEach(se => {
    const pts = se.vals.map((v, i) => `${(40 + i * passo).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
    s += `<polyline points="${pts}" fill="none" stroke="${se.cor}" stroke-width="2.5"/>`;
  });
  rot.forEach((r, i) => { s += `<text x="${(40 + i * passo).toFixed(1)}" y="${H - 9}" text-anchor="middle" font-size="11" fill="#555">${r}</text>`; });
  const marcas = Math.round((max - min) / passoEixo);
  for (let k = 0; k <= marcas; k++) {
    const v = min + passoEixo * k, y = Y(v);
    s += `<line x1="36" y1="${y.toFixed(1)}" x2="${L - 10}" y2="${y.toFixed(1)}" stroke="#eee"/>` +
         `<text x="30" y="${(y + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="#777">${Math.round(v)}</text>`;
  }
  return `<svg viewBox="0 0 ${L} ${H}" width="100%" role="img">${s}</svg>`;
}

function desenhar() {
  const cidade = document.getElementById("cidade").value;
  const ha = Math.max(1, parseFloat(document.getElementById("hectares").value) || 50);
  const preco = Math.max(10, parseFloat(document.getElementById("preco").value) || __PRECO__);
  const d = DADOS[cidade];
  const fmin = Math.max(d.previsto - ERRO, 0), fmax = d.previsto + ERRO;
  const total = d.previsto * ha;
  const cen = [80, 100, 120, 140, 160].map(p =>
    `<tr class="${Math.abs(p - preco) < 1e-6 ? "dest" : ""}"><td>R$ ${p}</td><td>R$ ${fmt(total * p)}</td></tr>`).join("");
  const histRot = d.hist_rot.concat([String(d.ano_prox).slice(2)]);
  const histVal = d.hist_val.concat([d.previsto]);
  document.getElementById("painel").innerHTML = `
    <section class="card"><h2>Safra ${d.ano_prox} · sua cidade</h2>
      <p class="numero">${Math.round(d.previsto)} sc/ha</p><p class="sub">Sacas por hectare, estimadas</p>
      <p class="sub">Pode variar entre <b>${Math.round(fmin)}</b> e <b>${Math.round(fmax)}</b> sacas/ha.</p>
      <div class="faixa"></div><div class="escala"><span>${Math.round(fmin)}</span><span>${Math.round(fmax)}</span></div></section>
    <section class="card"><h2>Situação da safra</h2><span class="selo ${d.cor}">${d.situacao}</span>
      <div class="mini"><div><b>${Math.round(d.media3)}</b><span>3 anos</span></div>
      <div><b>${Math.round(d.media10)}</b><span>10 anos</span></div>
      <div><b>${Math.round(d.ultima)}</b><span>safra ${d.ultimo_ano}</span></div></div>
      <div class="dica">${d.dica}</div></section>
    <section class="card"><h2>Na sua lavoura de ${Math.round(ha)} ha</h2>
      <p class="numero">${fmt(total)}</p><p class="sub">sacas estimadas no total</p>
      <p class="sub">Valor estimado: <b>R$ ${fmt(total * preco)}</b> (a R$ ${Math.round(preco)} por saca)</p>
      <p class="sub">Faixa de valor: R$ ${fmt(fmin * ha * preco)} a R$ ${fmt(fmax * ha * preco)}</p></section>
    <section class="card"><h2>E se o preço da saca mudar?</h2>
      <table><tr><th>Preço por saca</th><th>Valor da safra</th></tr>${cen}</table></section>
    <section class="card"><h2>Sua cidade no Paraná</h2>
      <p class="numero">${d.posicao}º <span style="font-size:1rem;color:var(--suave)">de ${d.total} municípios</span></p>
      <p class="sub">Na safra de ${d.ultimo_ano}, sua cidade ficou entre os <b>${100 - d.percentil + 1}%</b> mais produtivos do estado.</p></section>
    <section class="card"><h2>Chuva na safra</h2>
      <p class="sub" style="font-size:1rem;color:var(--texto)">${d.clima_txt}</p>
      <p class="sub">Última safra: <b>${d.chuva_ult} mm</b> · média da cidade: <b>${d.chuva_media} mm</b></p>
      <div class="dica">Chuva fora do normal costuma pesar mais que a média. Acompanhe os alertas da sua região.</div></section>
    <section class="card wide"><h2>Safras da sua cidade (sacas por hectare)</h2>
      ${svgBarras(histRot, histVal, histVal.length - 1)}
      <div class="legenda"><span><i style="background:#d9c9a3"></i>Safras colhidas</span>
      <span><i style="background:#c58b1a"></i>Estimativa ${d.ano_prox}</span></div></section>
    <section class="card wide"><h2>Sua cidade x média do Paraná (últimos 12 anos)</h2>
      ${svgLinhas(d.anos12, [{vals: d.cidade12, cor: "#c58b1a"}, {vals: d.estado12, cor: "#3b2e13"}])}
      <div class="legenda"><span><i style="background:#c58b1a"></i>Sua cidade</span>
      <span><i style="background:#3b2e13"></i>Média do Paraná</span></div>
      <p class="sub">Eixo: sacas por hectare. Quando a linha da cidade fica acima da média do estado, a lavoura está rendendo mais que a média paranaense.</p></section>
    <section class="card wide"><h2>Chuva da safra: sua cidade x média do Paraná</h2>
      ${svgLinhas(d.anos12, [{vals: d.chuva12, cor: "#2f6f9f"}, {vals: d.chuva_estado12, cor: "#999999"}])}
      <div class="legenda"><span><i style="background:#2f6f9f"></i>Sua cidade</span>
      <span><i style="background:#999999"></i>Média do Paraná</span></div>
      <p class="sub">Eixo: milímetros de chuva na safra (outubro a abril). Anos com pouca chuva costumam ser os de menor produtividade.</p></section>`;
}

const sel = document.getElementById("cidade");
Object.keys(DADOS).forEach(m => { const o = document.createElement("option"); o.value = o.textContent = m; sel.appendChild(o); });
sel.value = DADOS["Londrina - PR"] ? "Londrina - PR" : Object.keys(DADOS)[0];
document.getElementById("form").addEventListener("submit", e => { e.preventDefault(); desenhar(); });
["cidade", "hectares", "preco"].forEach(id => document.getElementById(id).addEventListener("change", desenhar));
desenhar();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    dados = {m: dados_cidade(m) for m in MUNICIPIOS}
    html = (MODELO_HTML
            .replace("__DADOS__", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
            .replace("__ERRO__", str(ERRO_MEDIO_SC))
            .replace("__PRECO__", str(int(PRECO_PADRAO))))
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{len(dados)} municípios -> {SAIDA} ({os.path.getsize(SAIDA) / 1024:.0f} KB)")
