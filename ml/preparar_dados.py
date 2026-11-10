# -*- coding: utf-8 -*-
"""
Prepara o dataset de modelagem (AgroPrevisao, soja, Paraná).

Entradas (pasta data/):
  - pam_soja_pr.csv         IBGE/SIDRA, PAM, soja, municípios do PR (1974–2025)
  - malha_pr.json           IBGE, malha municipal do PR (API de malhas, para o centro de cada município)
  - inmet/*.CSV             INMET, estações do PR, horário (2000–2025)

Saída:
  - dataset_soja_pr.csv     uma linha por município e ano (2008–2024)

Decisões:
  - Alvo: rendimento médio da produção (kg/ha).
  - Janela da safra: outubro do ano anterior até abril do ano (Y-1 out ... Y abr).
  - Estação por estação: precipitação total estimada da janela (média horária × 24 × 212 dias)
    e temperatura média da janela.
  - Clima por município: média ponderada pelo inverso da distância das 3 estações mais próximas
    (centro do município até a estação) que têm dados naquele ano.

Executar com:  python -I ml/preparar_dados.py
"""
import csv
import glob
import json
import math
import os
import re
from collections import defaultdict

BASE = r"C:\Users\mathe\Enxame\global-solution-produtor-rural"
DATA = os.path.join(BASE, "data")
PAM = os.path.join(DATA, "pam_soja_pr.csv")
MALHA = os.path.join(DATA, "malha_pr.json")
INMET_DIR = os.path.join(DATA, "inmet")
SAIDA = os.path.join(DATA, "dataset_soja_pr.csv")

ANO_INI, ANO_FIM = 2008, 2024
MISSING = -9999.0
N_VIZINHOS = 3
DIAS_JANELA = 212  # outubro a abril


def num(txt):
    """Converte número no formato brasileiro ('910,3') ou None se vazio/ausente."""
    if txt is None:
        return None
    t = txt.strip().replace(",", ".")
    if t == "":
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return None if v <= MISSING + 0.1 else v


def ler_pam():
    """Retorna {(cod, ano): {'municipio', 'rendimento', 'area', 'producao'}}."""
    rows = {}
    with open(PAM, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            ano = int(r["ano"])
            if not (ANO_INI <= ano <= ANO_FIM):
                continue
            v = num(r["valor"])
            if v is None:
                continue
            d = rows.setdefault((r["municipio_cod"], ano), {"municipio": r["municipio"]})
            var = r["variavel"]
            if var.startswith("Rendimento"):
                d["rendimento"] = v
            elif var.startswith("Área colhida"):
                d["area"] = v
            elif var.startswith("Quantidade"):
                d["producao"] = v
    return rows


def centros_municipios():
    """Retorna {codigo_ibge: (lat, lon)} com o centro aproximado (média dos vértices)."""
    with open(MALHA, encoding="utf-8") as f:
        geo = json.load(f)
    centros = {}
    for feat in geo["features"]:
        cod = feat["properties"]["codarea"]
        geom = feat["geometry"]
        anel = geom["coordinates"]
        pontos = []
        if geom["type"] == "Polygon":
            pontos = anel[0]
        elif geom["type"] == "MultiPolygon":
            pontos = max((p[0] for p in anel), key=len)
        lon = sum(p[0] for p in pontos) / len(pontos)
        lat = sum(p[1] for p in pontos) / len(pontos)
        centros[cod] = (lat, lon)
    return centros


def distancia(a, b):
    """Distância aproximada em km entre dois pontos (lat, lon)."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def ler_inmet():
    """Retorna (coords, dados): coords = {estacao: (lat, lon)};
    dados = {(estacao, safra_ano): {'precip': mm, 'temp': °C}}."""
    coords = {}
    acc = defaultdict(lambda: {"p_sum": 0.0, "p_n": 0, "t_sum": 0.0, "t_n": 0})
    for caminho in sorted(glob.glob(os.path.join(INMET_DIR, "*.CSV"))):
        with open(caminho, encoding="latin1", newline="") as f:
            linhas = f.read().splitlines()
        estacao = os.path.basename(caminho).split("_")[3]  # código WMO (ex.: A807)
        lat = lon = None
        for l in linhas[:9]:
            partes = l.split(";")
            if partes[0].startswith("LATITUDE"):
                lat = num(partes[1])
            elif partes[0].startswith("LONGITUDE"):
                lon = num(partes[1])
        if lat is not None and lon is not None:
            coords[estacao] = (lat, lon)
        # cabeçalho da tabela: "DATA (YYYY-MM-DD);..." (até 2020) ou "Data;Hora UTC;..." (2021+)
        cab = next(i for i, l in enumerate(linhas)
                   if l.lower().startswith("data (") or l.lower().startswith("data;"))
        for l in linhas[cab + 1:]:
            cols = l.split(";")
            if len(cols) < 8 or not cols[0]:
                continue
            try:
                y, m, d = (int(x) for x in re.split(r"[-/]", cols[0]))
            except ValueError:
                continue
            if not (m >= 10 or m <= 4):
                continue
            safra = y + 1 if m >= 10 else y
            if not (ANO_INI <= safra <= ANO_FIM):
                continue
            a = acc[(estacao, safra)]
            p = num(cols[2])
            t = num(cols[7])
            if p is not None:
                a["p_sum"] += p
                a["p_n"] += 1
            if t is not None:
                a["t_sum"] += t
                a["t_n"] += 1
    dados = {}
    for chave, a in acc.items():
        # exige cobertura de pelo menos ~150 dias de medidas na janela (evita estimativas de estação incompleta)
        if a["p_n"] >= 24 * 150 and a["t_n"] >= 24 * 150:
            dados[chave] = {
                "precip": a["p_sum"] / a["p_n"] * 24 * DIAS_JANELA,
                "temp": a["t_sum"] / a["t_n"],
            }
    return coords, dados


def clima_municipio(centro, ano, coords, dados):
    """Média ponderada (1/distância) das N estações mais próximas com dados no ano."""
    cand = []
    for est, (lat, lon) in coords.items():
        if (est, ano) in dados:
            cand.append((distancia(centro, (lat, lon)), est))
    if not cand:
        return None
    cand.sort()
    usados = cand[:N_VIZINHOS]
    pesos = [1.0 / max(d, 1.0) for d, _ in usados]
    soma = sum(pesos)
    precip = sum(w * dados[(e, ano)]["precip"] for w, (_, e) in zip(pesos, usados)) / soma
    temp = sum(w * dados[(e, ano)]["temp"] for w, (_, e) in zip(pesos, usados)) / soma
    return precip, temp, len(usados)


def main():
    pam = ler_pam()
    centros = centros_municipios()
    coords, dados = ler_inmet()
    print("estações com coordenadas:", len(coords), "| registros estação-safra:", len(dados))

    n = 0
    sem_clima = 0
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "municipio_cod", "municipio", "ano", "rendimento_kg_ha", "area_colhida_ha",
            "producao_t", "precip_safra_mm", "temp_media_safra_c", "n_estacoes_clima",
            "tendencia_ano",
        ])
        for (cod, ano), d in sorted(pam.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if "rendimento" not in d or cod not in centros:
                continue
            c = clima_municipio(centros[cod], ano, coords, dados)
            if c is None:
                sem_clima += 1
                continue
            precip, temp, k = c
            w.writerow([
                cod, d["municipio"], ano, round(d["rendimento"], 1),
                d.get("area", ""), d.get("producao", ""),
                round(precip, 1), round(temp, 2), k, ano - ANO_INI,
            ])
            n += 1
    print("linhas gravadas:", n, "| sem clima:", sem_clima, "->", SAIDA)


if __name__ == "__main__":
    main()
