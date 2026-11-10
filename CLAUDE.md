# CLAUDE.md – Global Solution (CitizenTech, ideia C: pequeno produtor rural)

Guia para sessões do Claude Code neste projeto.

## Contexto

- Trabalho da FIAP ON (Fase 7 – Advanced Models and AI), Grupo 12, individual ou em grupo.
- Prazo de entrega: **19/11/2026 às 23h59**. Não há entrega tardia.
- Idioma: tudo em **português do Brasil** (textos, comentários no notebook, nomes de variáveis em português quando fizer sentido para o pitch).
- Não invente dados, métricas ou resultados. Todo número no notebook ou na proposta sai de uma execução real.

## Escopo

- Ideia escolhida: **C – apoio ao pequeno produtor rural** (estimar produtividade ou preço de uma cultura e orientar plantio e venda).
- Decisões do usuário (ou decididas pelo assistente, quando o usuário deixou a escolha):
  - Projeto: **AgroPrevisao** (nome dos arquivos: `AgroPrevisao` no lugar de `<projeto>`).
  - Cultura: **soja**. Recorte: **Paraná** (estado com boa cobertura do INMET e forte produção de pequenos e médios produtores).
  - Variável-alvo: **produtividade** (kg/ha), por município e ano.
  - Preditoras: chuva e temperatura anuais por município (INMET), área plantada e uso do solo (MapBiomas).
  - Downloads de dados: permitidos pelo usuário.
  - Dados baixados: `data/pam_soja_pr.csv` (IBGE/SIDRA, tabela 1612, PAM, soja, todos os municípios do PR, 1974–2025). Colunas: municipio_cod, municipio, variavel (Quantidade produzida, Rendimento médio da produção, Área colhida), ano, valor, unidade. Variável-alvo: "Rendimento médio da produção" (kg/ha).
  - INMET (clima horário): `data/inmet/` tem os 461 arquivos CSV das estações do PR, de 2000 a 2025 (extraídos dos zips oficiais do portal do INMET, em `Downloads\<ano>.zip`, todos testados). Nome: `INMET_S_PR_<código>_<ESTAÇÃO>_<início>_A_<fim>.CSV`, um por estação por ano. Formato: `;`, decimal `,`, latin1, cabeçalho de metadados (REGIAO, UF, ESTACAO, CODIGO WMO, LATITUDE, LONGITUDE) antes da tabela. Colunas-chave: `PRECIPITAÇÃO TOTAL, HORÁRIO (mm)` e `TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)`.
  - Cobertura: antes de 2006 não há estações do PR no INMET; de 2008 em diante, 21 a 26 estações por ano. O treino deve começar em 2008 ou depois, para não misturar anos sem clima.
  - MapBiomas (uso do solo): **não baixado**. O link do Drive deu aviso "Virus scan warning" e o usuário pediu para não arriscar vírus. Não tentar de novo sem pedido explícito. Substituto: área colhida do IBGE.
  - Dataset de modelagem: `data/dataset_soja_pr.csv`, gerado por `ml/preparar_dados.py` (`python -I ml/preparar_dados.py`). 6.367 linhas, 392 municípios, 2008–2024. Alvo: `rendimento_kg_ha`. Preditoras: `precip_safra_mm` (chuva Oct–Abr estimada a partir das estações do PR), `temp_media_safra_c`, `area_colhida_ha`, `tendencia_ano`. Clima é do estado (mesmo valor para todos os municípios no mesmo ano), porque o IBGE não traz coordenadas. Isso é limitação a declarar no texto analítico.
  - Conferência: anos de seca (2009, 2012, 2022) aparecem com rendimento mediano baixo, o que indica que o clima está coerente.
- **Refeito do zero (v2):** clima por município (média das 3 estações mais próximas, centro do município pela malha do IBGE). Notebook `ml/produtividade_produtor_rural.ipynb` usa features de histórico do município (média e último rendimento, área do ano anterior, clima, tendência). Split cronológico: treino 2011–2019, teste 2020–2024. Referência (média histórica) RMSE 853 / R² 0,07; **Regressão Linear escolhida**: RMSE 796 / MAE 570 / R² 0,19; Random Forest RMSE 831 / R² 0,12.
- v1 (clima do estado) guardada em `ml/anterior/`, não usar.
- Entregáveis em `entrega/`: `GS_2TSCOA_ML_AgroPrevisao_Grupo12.zip` (notebook executado, CSV, figura) e a proposta em `proposta/GS_2TSCOA_Pitch_AgroPrevisao_Grupo12.pdf` (com o link do vídeo ainda pendente).
- Pendente do usuário: gravar o vídeo, publicar no YouTube, colar o link no PDF e no `linkvideo.txt`, e enviar no Portal FIAP ON. O PDF não usa o template oficial de slides (não foi baixado).
- Pacotes instalados no Python do usuário: pandas, scikit-learn, matplotlib, nbconvert, ipykernel.
  - ODS: 2, 8 e 13 (escolha do assistente, a revisar na proposta).
  - Pasta fica dentro do repositório Enxame, que o usuário pretende reorganizar.
- Equipe (Grupo 12, ordem alfabética, responsável: Matheus):
  - Ana Carolina Carvalho de Paula – RM 561917
  - Barbara Ayumi Leoni Kodama – RM 565513
  - Matheus Rodrigo da Silva Santos – RM 562378 (responsável)
- Fontes: INMET (clima), Conab (safras e preços), MapBiomas (uso do solo), IBGE/SIDRA (produção municipal).
- Não mudar a ideia sem pedido explícito do usuário.

## Estrutura da pasta

```
CLAUDE.md       este arquivo
data/           CSVs baixados (brutos, nunca editados à mão)
ml/             notebook .ipynb e saídas (figuras)
proposta/       rascunho e PDF da proposta executiva
video/          roteiro do pitch e linkvideo.txt
```

## Regras de trabalho

1. **Dados brutos não são editados.** Limpeza e transformação ficam no notebook, para o trabalho ser reprodutível.
2. **Sem vazamento:** divisão treino/teste antes de qualquer ajuste; imputação, normalização e codificação ajustadas só no treino; validação cruzada só no treino; se for série temporal, dividir por ordem cronológica.
3. **Pelo menos dois modelos supervisionados**, comparados com RMSE, MAE e R². Escolher o melhor pelas métricas e pelo contexto (ex.: erro grande na previsão de quebra de safra pesa mais que erro pequeno).
4. **Vieses:** citar no texto analítico quais regiões, culturas ou tamanhos de propriedade podem estar sub-representados nos dados.
5. **Notebook executado:** salvar com as saídas visíveis antes da entrega.
6. **Nomes de arquivos de entrega** seguem o padrão do enunciado:
   - `GS_2TSCOA_Pitch_<projeto>_<grupo>.pdf`
   - `GS_2TSCOA_ML_<projeto>_<grupo>.zip`
   - `linkvideo.txt` (nome da equipe, turma, RMs em ordem alfabética e o link do YouTube)
7. **Vídeo não é anexado como arquivo.** Só o link público vai no `linkvideo.txt` e na última página do PDF.

## O que não fazer

- Não enviar mensagens, publicar vídeo ou submeter nada no Portal FIAP ON. Isso é com o usuário.
- Não colocar dados pessoais (RM, e-mail) em arquivos que vão para fora sem o usuário pedir.
- Não escrever "resultado final" sem ter rodado o código que o gera.

## Pendências

Registre aqui só o que o usuário pedir. Antes de começar o notebook, confirmar a cultura, o estado e a disponibilidade dos CSVs.
