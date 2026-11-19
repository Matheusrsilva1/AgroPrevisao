# AgroPrevisao – previsão de rendimento de soja no Paraná

Projeto do **Grupo 12 (turma 2TSCOA, FIAP)** para a Global Solution 2º Semestre – CitizenTech, ideia C: *apoio ao pequeno produtor rural*.

O AgroPrevisao estima, antes do plantio, quanto cada município do Paraná deve render de soja na próxima safra (em sacas por hectare). O produtor escolhe o município, informa a área e o preço esperado da saca, e vê a estimativa com faixa provável, o valor total da safra, cenários de preço, o histórico da cidade e o clima.

> A estimativa é apoio ao planejamento, não garantia de safra. O modelo tem ganho modesto sobre a média histórica (veja [Resultados](#resultados-e-limitações)).

## Integrantes

| Nome | RM |
|---|---|
| Ana Carolina Carvalho de Paula | 561917 |
| Barbara Ayumi Leoni Kodama | 565513 |
| Matheus Rodrigo da Silva Santos | 562378 |

## Como funciona

```
IBGE/SIDRA (PAM) ─┐
Malha municipal ──┼─► ml/preparar_dados.py ─► data/dataset_soja_pr.csv ─┬─► notebook (treino e avaliação)
INMET (horário) ──┘                                                     ├─► app_flask.py (painel web)
                                                                        ├─► app_streamlit.py (painel alternativo)
                                                                        └─► gerar_painel_offline.py ─► HTML único, sem internet
```

1. **Dados.** Produção agrícola municipal do IBGE (soja, 392 municípios do PR) e clima horário das estações automáticas do INMET.
2. **Preparação** (`ml/preparar_dados.py`). Para cada município e ano, calcula chuva total e temperatura média da safra (outubro a abril). O clima de cada município é a média das **3 estações mais próximas**, usando o centro do município na malha do IBGE. Resultado: uma linha por município e ano (2008–2024).
3. **Variáveis do modelo.** Todas usam só informação anterior ao ano previsto, para evitar vazamento:

   | Variável | Significado |
   |---|---|
   | `rend_media3` | rendimento médio dos 3 anos anteriores (kg/ha) |
   | `rend_ultimo` | rendimento do ano anterior (kg/ha) |
   | `area_anterior` | área colhida no ano anterior (ha) |
   | `precip_safra_mm` | chuva acumulada na safra (mm) |
   | `temp_media_safra_c` | temperatura média na safra (°C) |
   | `tendencia_ano` | contador de anos, para capturar a tendência de longo prazo |

   Alvo: `rendimento_kg_ha`.
4. **Modelagem.** Divisão **cronológica**: treino de 2011 a 2019, teste de 2020 a 2024. Comparam-se a média histórica (referência), a Regressão Linear e a Random Forest, por RMSE, MAE e R². A validação cruzada usa só o treino.
5. **Painel.** O app treina a Regressão Linear com os dados até 2019 e estima a próxima safra de cada município. A faixa provável é a estimativa ± o erro médio do teste (cerca de 9,5 sacas/ha).

## Resultados e limitações

Teste em 2020–2024, anos que o modelo não viu no treino:

| Modelo | RMSE (kg/ha) | MAE (kg/ha) | R² |
|---|---|---|---|
| Média histórica (referência) | 853 | 584 | 0,07 |
| **Regressão Linear (escolhida)** | **796** | **570** | **0,19** |
| Random Forest | 831 | — | 0,12 |

- O erro médio é de cerca de 570 kg/ha (9,5 sacas/ha), aproximadamente 7% menor que o da média histórica. Por isso o painel mostra uma **faixa**, e não um número único.
- Municípios distantes das estações do INMET têm clima menos confiável.
- Os dados do IBGE podem não refletir bem a agricultura familiar.
- Nos anos de seca (2009, 2012 e 2022 aparecem com rendimento mediano baixo) o erro tende a ser maior.
- O projeto não coleta dados pessoais: usa só dados públicos agregados por município, e o que o produtor digita não é gravado.

## Estrutura do repositório

```
data/
  pam_soja_pr.csv           IBGE/SIDRA, tabela 1612 (PAM), soja, municípios do PR, 1974–2025
  malha_pr.json             malha municipal do PR (IBGE), usada para o centro de cada município
  inmet/                    CSVs horários das estações do PR (INMET), 2000–2025
  dataset_soja_pr.csv       dataset de modelagem, gerado por preparar_dados.py
ml/
  preparar_dados.py         monta o dataset a partir de PAM, malha e INMET
  produtividade_produtor_rural.ipynb   análise, treino, avaliação e texto analítico (executado)
  app_flask.py              painel web (Flask)
  templates/index.html      página do painel Flask
  app_streamlit.py          painel alternativo (Streamlit)
  gerar_painel_offline.py   gera um único HTML que abre sem internet, inclusive no celular
requirements.txt
```

Os dados brutos (`pam_soja_pr.csv`, `malha_pr.json`, `inmet/`) não são editados à mão. Toda limpeza e transformação está em código.

## Como usar

Requer **Python 3.10 ou superior**.

```bash
git clone https://github.com/Matheusrsilva1/global-solution-produtor-rural.git
cd global-solution-produtor-rural
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

Os comandos abaixo são executados a partir da pasta `ml`:

```bash
cd ml
```

### 1. Regenerar o dataset (opcional)

O `data/dataset_soja_pr.csv` já está no repositório. Para recriá-lo a partir dos dados brutos:

```bash
python preparar_dados.py
```

Grava 6.367 linhas (392 municípios, 2008–2024) em `data/dataset_soja_pr.csv`.

### 2. Notebook de análise e modelos

```bash
jupyter notebook produtividade_produtor_rural.ipynb
```

O notebook cobre carregamento e descrição dos dados, pré-processamento, divisão treino/teste, modelo de referência, treino e avaliação, visualizações, conclusão e texto analítico (escolha de modelo, vieses e limitações). Já está salvo com as saídas. Ao reexecutar, ele grava a figura `figuras_modelos.png` na pasta `ml`.

### 3. Painel web (Flask)

```bash
python app_flask.py
```

Abra <http://localhost:5000>. Escolha o município, os hectares e o preço por saca e clique em **Ver estimativa**. O painel mostra:

- estimativa da próxima safra em sacas/ha, com faixa provável;
- situação da safra (comparação com a média de 3 e de 10 anos e com a última safra);
- total de sacas e valor estimado para a área informada;
- cenários de preço da saca (R$ 80 a R$ 160);
- posição do município no ranking do estado;
- chuva da safra e gráficos: histórico da cidade, cidade × média do Paraná e chuva da safra.

### 4. Painel offline (um único arquivo HTML)

```bash
python gerar_painel_offline.py
```

Gera `ml/AgroPrevisao_Offline.html`, com todos os municípios, o modelo já calculado e os gráficos embutidos. Não usa links externos nem servidor: abre com duplo clique no computador e pode ser enviado e aberto no celular, sem internet. Os valores são calculados pelo mesmo modelo do `app_flask.py`; nada é digitado à mão.

### 5. Painel alternativo (Streamlit)

```bash
python -m streamlit run app_streamlit.py
```

Mesma estimativa, em interface Streamlit.

## Fontes de dados

- **IBGE/SIDRA** – Produção Agrícola Municipal (PAM), tabela 1612, e malha municipal.
- **INMET** – dados horários das estações automáticas do Paraná.
- **Conab** – referência de safras e preços (contexto do projeto).

## Tecnologias

Python, pandas, scikit-learn (Regressão Linear, Random Forest), matplotlib, Jupyter Notebook, Flask e Streamlit.

## Sobre os dados no repositório

A pasta `data/inmet/` tem cerca de 460 arquivos. Se preferir não baixá-los, o `dataset_soja_pr.csv` já contém tudo o que o notebook e os painéis precisam: apenas o passo 1 depende dos dados brutos.
