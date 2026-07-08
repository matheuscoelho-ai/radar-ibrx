# -*- coding: utf-8 -*-
"""
Calculo dos indicadores tecnicos e do score composto (0 a 100).

Indicadores (25 pontos cada):
  1. Cruzamento de medias  -> media curta acima da media longa
  2. IFR (RSI de Wilder)   -> forca relativa em zona compradora
  3. Preco x media         -> fechamento acima da media de referencia
  4. HiLo Activator (Gann) -> stop dinamico em modo de compra

Os periodos de cada indicador vem de parametros.json (gerado pelo otimizador
do backtest). Se o arquivo nao existir, usa os padroes classicos da literatura.
"""

import json
import os

import numpy as np
import pandas as pd

# Padroes classicos (usados ate o otimizador rodar):
# - Cruzamento 9/21 (swing trade classico)
# - IFR 14 (padrao de Wilder)
# - Preco x SMA 50 (tendencia intermediaria)
# - HiLo 8 periodos
PARAMETROS_PADRAO = {
    "ma_curta": 9,
    "ma_longa": 21,
    "ifr_periodo": 14,
    "ifr_nivel": 50,
    "ma_preco": 50,
    "hilo_periodo": 8,
    "score_compra": 75,
    "score_venda": 40,
}

ARQ_PARAMETROS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parametros.json")


def carregar_parametros():
    p = dict(PARAMETROS_PADRAO)
    if os.path.exists(ARQ_PARAMETROS):
        try:
            with open(ARQ_PARAMETROS, "r", encoding="utf-8") as f:
                salvo = json.load(f)
            p.update({k: salvo[k] for k in p if k in salvo})
        except Exception:
            pass
    return p


def salvar_parametros(params):
    with open(ARQ_PARAMETROS, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------- indicadores

def sma(serie, periodo):
    return serie.rolling(periodo).mean()


def ifr_wilder(fechamento, periodo=14):
    """IFR (RSI) com suavizacao de Wilder (EWM alpha=1/n)."""
    delta = fechamento.diff()
    ganho = delta.clip(lower=0.0)
    perda = (-delta).clip(lower=0.0)
    media_ganho = ganho.ewm(alpha=1.0 / periodo, min_periods=periodo, adjust=False).mean()
    media_perda = perda.ewm(alpha=1.0 / periodo, min_periods=periodo, adjust=False).mean()
    rs = media_ganho / media_perda.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def hilo_activator(maxima, minima, fechamento, periodo=8):
    """
    Gann HiLo Activator.
    - Linha de compra: SMA das minimas; linha de venda: SMA das maximas.
    - Quando o fechamento cruza acima da SMA das maximas -> modo COMPRA (+1),
      e o stop passa a ser a SMA das minimas.
    - Quando o fechamento cruza abaixo da SMA das minimas -> modo VENDA (-1),
      e o stop passa a ser a SMA das maximas.
    Retorna (direcao, linha_stop).
    """
    sma_max = maxima.rolling(periodo).mean()
    sma_min = minima.rolling(periodo).mean()

    n = len(fechamento)
    direcao = np.zeros(n)
    stop = np.full(n, np.nan)

    fc = fechamento.values
    smx = sma_max.values
    smn = sma_min.values

    atual = 0
    for i in range(n):
        if np.isnan(smx[i]) or np.isnan(smn[i]):
            direcao[i] = 0
            continue
        if atual <= 0 and fc[i] > smx[i]:
            atual = 1
        elif atual >= 0 and fc[i] < smn[i]:
            atual = -1
        elif atual == 0:
            atual = 1 if fc[i] > smx[i] else -1
        direcao[i] = atual
        stop[i] = smn[i] if atual == 1 else smx[i]

    return (
        pd.Series(direcao, index=fechamento.index),
        pd.Series(stop, index=fechamento.index),
    )


# ------------------------------------------------------------------- score

def calcular_tabela(df, params=None):
    """
    Recebe um DataFrame OHLC de um ativo (colunas: Open, High, Low, Close)
    e devolve o mesmo DataFrame com colunas de indicadores, pontos e score.
    """
    if params is None:
        params = carregar_parametros()

    out = df.copy()
    close = out["Close"]

    out["MA_CURTA"] = sma(close, params["ma_curta"])
    out["MA_LONGA"] = sma(close, params["ma_longa"])
    out["IFR"] = ifr_wilder(close, params["ifr_periodo"])
    out["MA_PRECO"] = sma(close, params["ma_preco"])
    out["HILO_DIR"], out["HILO_STOP"] = hilo_activator(
        out["High"], out["Low"], close, params["hilo_periodo"]
    )

    out["PTS_CRUZAMENTO"] = np.where(out["MA_CURTA"] > out["MA_LONGA"], 25, 0)
    out["PTS_IFR"] = np.where(out["IFR"] > params["ifr_nivel"], 25, 0)
    out["PTS_PRECO_MA"] = np.where(close > out["MA_PRECO"], 25, 0)
    out["PTS_HILO"] = np.where(out["HILO_DIR"] > 0, 25, 0)

    out["SCORE"] = (
        out["PTS_CRUZAMENTO"] + out["PTS_IFR"] + out["PTS_PRECO_MA"] + out["PTS_HILO"]
    )

    # Sinais: compra quando o score cruza para cima do gatilho de compra;
    # venda quando cai para o gatilho de venda ou abaixo.
    score = out["SCORE"]
    score_ant = score.shift(1)
    out["SINAL"] = ""
    out.loc[(score >= params["score_compra"]) & (score_ant < params["score_compra"]), "SINAL"] = "COMPRA"
    out.loc[(score <= params["score_venda"]) & (score_ant > params["score_venda"]), "SINAL"] = "VENDA"

    return out
