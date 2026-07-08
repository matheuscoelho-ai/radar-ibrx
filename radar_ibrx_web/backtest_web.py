# -*- coding: utf-8 -*-
"""
Backtest e otimizacao de periodos — versao para GitHub Actions.
Roda sozinho uma vez por mes (e sempre que voce clicar em "Run workflow").

O que faz:
  1. Baixa 5 anos de historico de todo o IBRX.
  2. Testa as combinacoes de periodos dos 4 indicadores (grades classicas da
     literatura) e escolhe a de melhor fator de lucro historico.
  3. Grava parametros.json (o scanner diario passa a usar esses periodos)
     e docs/backtest.json (resultado completo exibido na pagina).

Simulacao: compra quando SCORE >= 75, vende quando SCORE <= 40, entrada e
saida no fechamento do dia do sinal, custo de 0,10% por lado.
"""

import itertools
import json
import os
import time

import numpy as np
import pandas as pd

import dados
import ibrx
import indicadores

PASTA = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(PASTA, "docs")

GRADE_MA = [(5, 20), (9, 21), (20, 50), (50, 200)]
GRADE_IFR = [2, 7, 14, 21]
GRADE_MA_PRECO = [20, 50, 100, 200]
GRADE_HILO = [3, 5, 8, 13]

CUSTO_POR_LADO = 0.001  # 0,10% por operacao
N_AMOSTRA_OTIMIZACAO = 40  # ativos usados na busca de periodos (agiliza)


def simular_ativo(df_calc):
    trades = []
    em_posicao = False
    preco_ent = data_ent = None
    sinais = df_calc["SINAL"].values
    closes = df_calc["Close"].values
    datas = df_calc.index

    for i in range(len(df_calc)):
        if not em_posicao and sinais[i] == "COMPRA":
            em_posicao, preco_ent, data_ent = True, closes[i], datas[i]
        elif em_posicao and sinais[i] == "VENDA":
            ret = closes[i] / preco_ent - 1.0 - 2 * CUSTO_POR_LADO
            trades.append((data_ent, preco_ent, datas[i], closes[i], ret, "FECHADO"))
            em_posicao = False
    if em_posicao:
        ret = closes[-1] / preco_ent - 1.0 - 2 * CUSTO_POR_LADO
        trades.append((data_ent, preco_ent, datas[-1], closes[-1], ret, "ABERTO"))
    return trades


def avaliar(dados_ohlc, params):
    retornos = []
    for df in dados_ohlc.values():
        calc = indicadores.calcular_tabela(df, params)
        retornos.extend(tr[4] for tr in simular_ativo(calc))
    if len(retornos) < 100:
        return None
    r = np.array(retornos)
    ganhos = r[r > 0].sum()
    perdas = -r[r <= 0].sum()
    return {
        "n_trades": len(r),
        "taxa_acerto": float((r > 0).mean()),
        "retorno_medio": float(r.mean()),
        "fator_lucro": float(min(ganhos / perdas if perdas > 0 else 99.0, 99.0)),
    }


def otimizar(dados_ohlc, log=print):
    combos = list(itertools.product(GRADE_MA, GRADE_IFR, GRADE_MA_PRECO, GRADE_HILO))
    log(f"Testando {len(combos)} combinacoes em {len(dados_ohlc)} ativos...")
    melhor, melhor_chave = None, (-1.0, -1.0)
    inicio = time.time()

    for k, ((mc, ml), ifr_p, map_p, hilo_p) in enumerate(combos, 1):
        params = dict(indicadores.PARAMETROS_PADRAO)
        params.update({"ma_curta": mc, "ma_longa": ml, "ifr_periodo": ifr_p,
                       "ma_preco": map_p, "hilo_periodo": hilo_p})
        m = avaliar(dados_ohlc, params)
        if m is None:
            continue
        chave = (m["fator_lucro"], m["retorno_medio"])
        if chave > melhor_chave:
            melhor_chave, melhor = chave, params
        if k % 32 == 0:
            log(f"  {k}/{len(combos)} ({time.time() - inicio:.0f}s)")
    return melhor


def backtest_detalhado(dados_ohlc, params):
    todas = []
    for ticker, df in dados_ohlc.items():
        calc = indicadores.calcular_tabela(df, params)
        for (d_ent, p_ent, d_sai, p_sai, ret, status) in simular_ativo(calc):
            todas.append({
                "ticker": ticker,
                "entrada": pd.Timestamp(d_ent).strftime("%Y-%m-%d"),
                "preco_entrada": round(float(p_ent), 2),
                "saida": pd.Timestamp(d_sai).strftime("%Y-%m-%d"),
                "preco_saida": round(float(p_sai), 2),
                "retorno_pct": round(100 * ret, 2),
                "status": status,
            })
    r = np.array([t["retorno_pct"] for t in todas]) / 100.0
    ganhos = r[r > 0].sum()
    perdas = -r[r <= 0].sum()
    resumo = {
        "n_ativos": len(dados_ohlc),
        "n_trades": int(len(todas)),
        "taxa_acerto_pct": round(100 * float((r > 0).mean()), 1),
        "retorno_medio_pct": round(100 * float(r.mean()), 2),
        "ganho_medio_pct": round(100 * float(r[r > 0].mean()), 2) if (r > 0).any() else 0.0,
        "perda_media_pct": round(100 * float(r[r <= 0].mean()), 2) if (r <= 0).any() else 0.0,
        "fator_lucro": round(float(ganhos / perdas) if perdas > 0 else 99.0, 2),
        "parametros": params,
        "executado_em": time.strftime("%d/%m/%Y %H:%M"),
    }
    todas.sort(key=lambda t: t["saida"], reverse=True)
    return todas, resumo


def executar(log=print):
    dados_ohlc = dados.baixar_historico(ibrx.tickers_yahoo(), periodo="5y",
                                        forcar=True, log=log)

    chaves = sorted(dados_ohlc.keys())[:N_AMOSTRA_OTIMIZACAO]
    amostra = {k: dados_ohlc[k] for k in chaves}
    melhores = otimizar(amostra, log=log)
    if melhores is None:
        log("ERRO: nenhuma combinacao valida. Mantendo parametros atuais.")
        return

    log("\nMelhores periodos encontrados:")
    for k in ["ma_curta", "ma_longa", "ifr_periodo", "ma_preco", "hilo_periodo"]:
        log(f"  {k}: {melhores[k]}")

    trades, resumo = backtest_detalhado(dados_ohlc, melhores)

    indicadores.salvar_parametros(melhores)
    with open(os.path.join(DOCS, "backtest.json"), "w", encoding="utf-8") as f:
        json.dump({"resumo": resumo, "trades": trades}, f, ensure_ascii=False, indent=1)

    log(f"\nBacktest: {resumo['n_trades']} trades | acerto {resumo['taxa_acerto_pct']}% | "
        f"retorno medio {resumo['retorno_medio_pct']}% | fator de lucro {resumo['fator_lucro']}")


if __name__ == "__main__":
    executar()
