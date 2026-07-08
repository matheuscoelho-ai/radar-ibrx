# -*- coding: utf-8 -*-
"""
Download e cache do historico de precos (Yahoo Finance).
Os dados ficam salvos em ./cache_dados/ para acelerar as proximas execucoes.
"""

import os
import time

import pandas as pd
import yfinance as yf

PASTA = os.path.dirname(os.path.abspath(__file__))
PASTA_CACHE = os.path.join(PASTA, "cache_dados")
os.makedirs(PASTA_CACHE, exist_ok=True)


def baixar_historico(tickers_sa, periodo="5y", forcar=False, log=print):
    """
    Baixa o historico OHLC de todos os tickers (lista com sufixo .SA).
    Retorna dict {ticker_sem_sufixo: DataFrame OHLC}.
    Usa cache do dia: se ja baixou hoje, reaproveita (a menos que forcar=True).
    """
    hoje = time.strftime("%Y-%m-%d")
    arq_cache = os.path.join(PASTA_CACHE, f"ohlc_{periodo}_{hoje}.pkl")

    if os.path.exists(arq_cache) and not forcar:
        log("Usando dados ja baixados hoje (cache).")
        return pd.read_pickle(arq_cache)

    log(f"Baixando historico de {len(tickers_sa)} ativos ({periodo})...")
    bruto = yf.download(
        tickers_sa,
        period=periodo,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )

    dados = {}
    for t in tickers_sa:
        nome = t.replace(".SA", "")
        try:
            df = bruto[t][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            if len(df) >= 60:
                dados[nome] = df
            else:
                log(f"  {nome}: historico insuficiente, ignorado.")
        except Exception:
            log(f"  {nome}: falha no download, ignorado.")

    log(f"OK: {len(dados)} ativos com dados validos.")
    pd.to_pickle(dados, arq_cache)

    # limpa caches de dias anteriores
    for f in os.listdir(PASTA_CACHE):
        if f.startswith("ohlc_") and f != os.path.basename(arq_cache):
            try:
                os.remove(os.path.join(PASTA_CACHE, f))
            except OSError:
                pass

    return dados
