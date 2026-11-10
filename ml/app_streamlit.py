"""
AgroPrevisao – painel para o produtor (Global Solution, Grupo 12).

Executar a partir da pasta ml:
    python -m streamlit run app_streamlit.py

Usa o mesmo dataset e as mesmas variáveis do notebook produtividade_produtor_rural.ipynb.
"""
import os

import numpy as np
import pandas as pd
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CAMINHO = os.path.join(os.path.dirname(__file__), "..", "data", "dataset_soja_pr.csv")
FEATURES = ["rend_media3", "rend_ultimo", "area_anterior",
            "precip_safra_mm", "temp_media_safra_c", "tendencia_ano"]
ALVO = "rendimento_kg_ha"
ANO_CORTE = 2019          # modelo treinado até 2019
KG_POR_SACA = 60          # a saca de soja tem 60 kg
PRECO_PADRAO = 120.0      # valor de referência, editável pelo produtor (R$ por saca)


@st.cache_data
def carregar():
    bruto = pd.read_csv(CAMINHO)
    df = bruto.sort_values(["municipio_cod", "ano"]).copy()
    g = df.groupby("municipio_cod")
    df["rend_ultimo"] = g[ALVO].shift(1)
    df["rend_media3"] = g[ALVO].transform(lambda s: s.shift(1).rolling(3).mean())
    df["area_anterior"] = g["area_colhida_ha"].shift(1)
    return df.dropna(subset=FEATURES + [ALVO]).copy()


@st.cache_resource
def treinar(df):
    treino = df[df["ano"] <= ANO_CORTE]
    modelo = make_pipeline(StandardScaler(), LinearRegression())
    modelo.fit(treino[FEATURES], treino[ALVO])
    return modelo


def para_sacas(kg_ha):
    return kg_ha / KG_POR_SACA


def classificar(previsto, media):
    """Compara a estimativa com a média recente do município."""
    if previsto >= media * 1.05:
        return "Safra acima da média", "#2e7d32"
    if previsto <= media * 0.95:
        return "Safra abaixo da média", "#c62828"
    return "Safra na média", "#8a6d00"


st.set_page_config(page_title="AgroPrevisao", layout="centered")

st.markdown(
    """
    <style>
    .bloco {background:#fbf6ea;border-radius:12px;padding:18px 20px;margin:8px 0;}
    .grande {font-size:2.1rem;font-weight:700;margin:0;}
    .legenda {color:#555;font-size:0.95rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AgroPrevisao")
st.write("Uma estimativa da sua safra de soja, para ajudar a decidir o plantio e a venda.")

df = carregar()
modelo = treinar(df)
municipios = sorted(df["municipio"].unique())

# --- Passo 1: escolher a cidade e o tamanho da lavoura
st.subheader("1. Onde fica sua lavoura?")
cidade = st.selectbox("Escolha o município", municipios,
                      index=municipios.index(next((m for m in municipios if "Londrina" in m), municipios[0])))
hectares = st.number_input("Quantos hectares você planta de soja?", min_value=1.0, value=50.0, step=1.0)

historico = df[df["municipio"] == cidade].sort_values("ano")
ultimos = historico.tail(3)
media_recente_kg = ultimos[ALVO].mean()
media_recente_sc = para_sacas(media_recente_kg)

# --- Passo 2: previsão para a próxima safra, usando a última linha conhecida da cidade
ultimo = historico.iloc[[-1]]
ano_prox = int(ultimo["ano"].iloc[0]) + 1
entrada = pd.DataFrame({
    "rend_media3": [historico[ALVO].tail(3).mean()],
    "rend_ultimo": [historico[ALVO].iloc[-1]],
    "area_anterior": [historico["area_colhida_ha"].iloc[-1]],
    "precip_safra_mm": [ultimo["precip_safra_mm"].iloc[0]],
    "temp_media_safra_c": [ultimo["temp_media_safra_c"].iloc[0]],
    "tendencia_ano": [ultimo["tendencia_ano"].iloc[0] + 1],
})
previsto_kg = float(modelo.predict(entrada[FEATURES])[0])
previsto_sc = para_sacas(previsto_kg)
texto, cor = classificar(previsto_kg, media_recente_kg)

st.subheader(f"2. Sua estimativa para a safra de {ano_prox}")
st.markdown(
    f"""
    <div class="bloco">
      <p class="legenda">Produtividade estimada em {cidade}</p>
      <p class="grande">{previsto_sc:,.0f} sacas por hectare</p>
      <p style="color:{cor};font-weight:600;margin:6px 0 0 0;">{texto}
        (média dos últimos 3 anos: {media_recente_sc:,.0f} sacas/ha)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Passo 3: quanto isso dá no total
st.subheader("3. Quanto isso dá na sua lavoura?")
preco = st.number_input("Preço que você espera por saca (R$)", min_value=10.0, value=PRECO_PADRAO, step=5.0,
                        help="Use o preço que você costuma ver na sua região. Não é uma previsão de preço.")
total_sacas = previsto_sc * hectares
total_reais = total_sacas * preco

c1, c2 = st.columns(2)
c1.markdown(f'<div class="bloco"><p class="legenda">Sacas na lavoura inteira</p>'
            f'<p class="grande">{total_sacas:,.0f}</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="bloco"><p class="legenda">Valor estimado da safra</p>'
            f'<p class="grande">R$ {total_reais:,.0f}</p></div>', unsafe_allow_html=True)

# --- Passo 4: histórico simples em sacas por hectare
st.subheader("4. Como foram as safras da sua cidade")
hist_sc = historico.set_index("ano")[[ALVO]].copy()
hist_sc[ALVO] = hist_sc[ALVO] / KG_POR_SACA
hist_sc = hist_sc.rename(columns={ALVO: "Sacas por hectare"})
st.bar_chart(hist_sc, height=260)
st.caption("Cada barra é uma safra já colhida. Quanto mais alta, mais soja por hectare.")

# --- Explicação em linguagem simples
with st.expander("Como a estimativa é feita"):
    st.write(
        "Olhamos o que a sua cidade colheu nos últimos anos, a chuva e a temperatura da época de plantio e colheita "
        "(outubro a abril) e a área plantada no ano anterior. Com isso, um modelo estima quantas sacas por hectare "
        "a lavoura deve render."
    )
    st.write(
        "A estimativa **não garante** a safra. Ela erra, em média, cerca de 10 sacas por hectare, e nos anos de seca "
        "o erro costuma ser maior. Use como um sinal para planejar, junto com a sua experiência e com a orientação "
        "da cooperativa ou da extensão rural."
    )

with st.expander("Detalhes técnicos (para o grupo)"):
    st.write(f"Modelo: Regressão Linear, treinado com safras até {ANO_CORTE}.")
    st.write(f"Base: {len(df)} linhas, {df['municipio_cod'].nunique()} municípios, anos {df['ano'].min()}–{df['ano'].max()}.")
    st.write("Erro no teste (2020–2024): RMSE de 796 kg/ha (cerca de 13 sacas/ha); R² de 0,19.")
