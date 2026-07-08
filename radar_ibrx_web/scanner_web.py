# -*- coding: utf-8 -*-
"""
Scanner diario do IBRX — versao para GitHub Actions.
Roda sozinho na nuvem todo dia util e grava os arquivos que a pagina le:

  docs/dados.json    -> panorama do dia (scores e indicadores de cada ativo)
  docs/sinais.json   -> livro de indicacoes (compras/vendas e ganho-perda)
  docs/estado.json   -> controle interno (ultima data processada)

Nao precisa ser executado manualmente.
"""

import json
import os
import time

import pandas as pd

import dados
import ibrx
import indicadores

PASTA = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(PASTA, "docs")
ARQ_DADOS = os.path.join(DOCS, "dados.json")
ARQ_SINAIS = os.path.join(DOCS, "sinais.json")
ARQ_ESTADO = os.path.join(DOCS, "estado.json")


def _ler_json(caminho, padrao):
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return padrao
    return padrao


def _gravar_json(caminho, obj):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def executar(log=print):
    params = indicadores.carregar_parametros()
    log(f"Parametros: MA {params['ma_curta']}/{params['ma_longa']} | "
        f"IFR {params['ifr_periodo']} | Preco x MA{params['ma_preco']} | "
        f"HiLo {params['hilo_periodo']}")

    dados_ohlc = dados.baixar_historico(ibrx.tickers_yahoo(), periodo="2y",
                                        forcar=True, log=log)

    sinais = _ler_json(ARQ_SINAIS, [])
    estado = _ler_json(ARQ_ESTADO, {})
    corte = pd.Timestamp(estado["ultima_data_processada"]) if estado.get(
        "ultima_data_processada") else None
    primeira_execucao = corte is None and not sinais

    scores = []
    n_compras = n_vendas = 0
    max_data = None

    def abertos_do(ticker):
        return [s for s in sinais if s["ticker"] == ticker and s["status"] == "ABERTO"]

    for ticker, df in dados_ohlc.items():
        calc = indicadores.calcular_tabela(df, params)
        u = calc.iloc[-1]
        data_u = calc.index[-1]
        max_data = data_u if max_data is None else max(max_data, data_u)
        preco = round(float(u["Close"]), 2)
        data_str = pd.Timestamp(data_u).strftime("%Y-%m-%d")

        scores.append({
            "ticker": ticker,
            "data": data_str,
            "preco": preco,
            "cruzamento": int(u["PTS_CRUZAMENTO"]),
            "ifr_valor": round(float(u["IFR"]), 1),
            "ifr_pts": int(u["PTS_IFR"]),
            "preco_media": int(u["PTS_PRECO_MA"]),
            "hilo": int(u["PTS_HILO"]),
            "hilo_stop": round(float(u["HILO_STOP"]), 2) if pd.notna(u["HILO_STOP"]) else None,
            "score": int(u["SCORE"]),
            "sinal": u["SINAL"] or "",
        })

        eventos = calc[calc["SINAL"] != ""]

        if primeira_execucao:
            # registra a tendencia em andamento (ultima COMPRA sem VENDA depois)
            if not eventos.empty and eventos.iloc[-1]["SINAL"] == "COMPRA":
                d_ev = eventos.index[-1]
                p_ev = round(float(eventos.iloc[-1]["Close"]), 2)
                sinais.append({
                    "ticker": ticker,
                    "data_sinal": pd.Timestamp(d_ev).strftime("%Y-%m-%d"),
                    "preco_sinal": p_ev, "status": "ABERTO",
                    "data_saida": None, "preco_saida": None,
                    "preco_atual": p_ev, "retorno_pct": 0.0, "dias": 0,
                })
                n_compras += 1
                log(f"  TENDENCIA EM ANDAMENTO: {ticker} desde "
                    f"{pd.Timestamp(d_ev).strftime('%d/%m/%Y')} a R$ {p_ev}")
        else:
            janela = eventos if corte is None else eventos[eventos.index > corte]
            for d_ev, ev in janela.iterrows():
                p_ev = round(float(ev["Close"]), 2)
                d_str = pd.Timestamp(d_ev).strftime("%Y-%m-%d")
                if ev["SINAL"] == "COMPRA" and not abertos_do(ticker):
                    sinais.append({
                        "ticker": ticker, "data_sinal": d_str,
                        "preco_sinal": p_ev, "status": "ABERTO",
                        "data_saida": None, "preco_saida": None,
                        "preco_atual": p_ev, "retorno_pct": 0.0, "dias": 0,
                    })
                    n_compras += 1
                    log(f"  NOVA COMPRA: {ticker} a R$ {p_ev} ({d_str})")
                elif ev["SINAL"] == "VENDA" and abertos_do(ticker):
                    for s in abertos_do(ticker):
                        s["status"] = "FECHADO"
                        s["data_saida"] = d_str
                        s["preco_saida"] = p_ev
                        s["preco_atual"] = p_ev
                        s["retorno_pct"] = round(100 * (p_ev / s["preco_sinal"] - 1), 2)
                        s["dias"] = int((pd.Timestamp(d_str)
                                         - pd.Timestamp(s["data_sinal"])).days)
                    n_vendas += 1
                    log(f"  VENDA/SAIDA: {ticker} a R$ {p_ev} ({d_str})")

        # marca a mercado o que segue aberto
        for s in abertos_do(ticker):
            s["preco_atual"] = preco
            s["retorno_pct"] = round(100 * (preco / s["preco_sinal"] - 1), 2)
            s["dias"] = int((pd.Timestamp(data_str)
                             - pd.Timestamp(s["data_sinal"])).days)

    scores.sort(key=lambda x: x["score"], reverse=True)
    _gravar_json(ARQ_DADOS, {
        "atualizado": time.strftime("%d/%m/%Y %H:%M") + " (Brasilia -3h de UTC)",
        "atualizado_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parametros": params,
        "scores": scores,
    })
    _gravar_json(ARQ_SINAIS, sinais)
    if max_data is not None:
        _gravar_json(ARQ_ESTADO, {
            "ultima_data_processada": pd.Timestamp(max_data).strftime("%Y-%m-%d")})

    n_abertos = sum(1 for s in sinais if s["status"] == "ABERTO")
    log(f"\nScan concluido: {len(scores)} ativos | {n_compras} compras | "
        f"{n_vendas} vendas | {n_abertos} indicacoes abertas.")


if __name__ == "__main__":
    executar()
