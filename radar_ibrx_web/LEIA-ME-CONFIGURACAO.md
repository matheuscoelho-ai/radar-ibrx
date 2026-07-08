# 📈 Radar IBRX — Configuração (só cliques, zero código)

Depois desta configuração de ~15 minutos, **tudo roda sozinho**: todo dia útil
às 18h40 um robô gratuito do GitHub baixa os preços, recalcula os scores,
atualiza as indicações e publica na sua página. Você só abre o link.

---

## Parte 1 — Criar a conta e o repositório (5 min)

1. Acesse **github.com** e clique em **Sign up** (é gratuito). Confirme o e-mail.
2. No canto superior direito, clique no **+** → **New repository**.
3. Preencha:
   - **Repository name:** `radar-ibrx` (ou outro nome discreto de sua escolha)
   - Marque **Public** (necessário para a página gratuita — veja a nota de
     privacidade no fim)
   - NÃO marque nenhuma outra opção.
4. Clique em **Create repository**.

## Parte 2 — Subir os arquivos (3 min)

1. No seu computador, **extraia o ZIP** (botão direito → Extrair tudo).
2. Na página do repositório recém-criado, clique no link
   **"uploading an existing file"**.
3. Abra a pasta extraída `radar_ibrx_web`, selecione **TODO o conteúdo**
   (Ctrl+A) e **arraste para a área de upload** do navegador.
   ⚠️ Confira se a pasta **`.github`** foi junto — ela contém os robôs.
   Se o seu Windows a esconder: no Explorador de Arquivos, aba **Exibir** →
   marque **Itens ocultos**.
4. Clique no botão verde **Commit changes**.

> A pasta `.github` não subiu? Sem problema: no repositório clique em
> **Add file → Create new file**, no nome digite exatamente
> `.github/workflows/atualizacao_diaria.yml`, cole o conteúdo do arquivo de
> mesmo nome que está no ZIP e dê **Commit**. Repita para
> `.github/workflows/backtest_mensal.yml`.

## Parte 3 — Ligar a página (2 min)

1. No repositório, clique em **Settings** (engrenagem) → menu lateral **Pages**.
2. Em **Source**, deixe "Deploy from a branch". Em **Branch**, selecione
   **main** e a pasta **/docs**. Clique em **Save**.
3. Em 1–2 minutos aparece o endereço da sua página, no formato:
   `https://SEU-USUARIO.github.io/radar-ibrx/`
   Salve esse link — é ele que você e a equipe vão usar todo dia.

## Parte 4 — Primeira rodada (2 cliques + espera)

1. Clique na aba **Actions** (topo do repositório). Se aparecer um botão verde
   pedindo para habilitar os workflows, clique nele.
2. No menu lateral, clique em **"Backtest e otimização de períodos"** →
   botão **Run workflow** → **Run workflow** (verde).
   Ele baixa 5 anos do IBRX, testa as combinações de períodos e grava a melhor.
   Leva de 20 a 60 minutos — pode fechar a página, ele continua sozinho.
3. Quando terminar (bolinha verde ✅), rode da mesma forma
   **"Atualização diária dos sinais"** (esse leva ~3 minutos).
4. Abra o link da sua página. **Login inicial:**
   - usuário: `matheus`
   - senha: `radar2026`

## Parte 5 — Troque a senha inicial (importante!)

1. Logado na página, abra a aba **⚙️ Acessos**.
2. Digite `matheus` e a sua nova senha → **Gerar cadastro** → copie o bloco.
3. No GitHub, abra `docs` → `usuarios.json` → lápis ✏️ → substitua a linha do
   `matheus` pelo bloco copiado, **trocando `"admin": false` por `"admin": true`**
   → **Commit changes**.

Para **cadastrar alguém da equipe**, o processo é o mesmo (mantendo
`"admin": false`) — a própria aba Acessos mostra o passo a passo. Para
**remover um acesso**, apague a linha da pessoa no `usuarios.json`.

---

## Pronto! Rotina daqui em diante

- **Nada.** Todo dia útil às 18h40 a página se atualiza sozinha. Todo dia 1º do
  mês o backtest reroda e revalida os períodos dos indicadores.
- Quiser atualizar fora de hora? Actions → "Atualização diária dos sinais" →
  Run workflow.
- **Rebalanceamento do IBRX** (jan/mai/set): abra `ibrx.py` no GitHub, clique
  no lápis ✏️, ajuste a lista de tickers e dê Commit. Depois rode o backtest.
- A página avisa sozinha se os dados ficarem mais de 4 dias sem atualizar.

## Nota sobre privacidade

O repositório é público (exigência da hospedagem gratuita), então alguém que
descubra o endereço conseguiria ver os arquivos de sinais — a senha da página
protege contra acesso casual, e as senhas nunca ficam expostas (só o hash).
Como o conteúdo são apenas tickers e pontuações (sem nenhum dado de cliente),
o risco é baixo. Se quiser blindar 100%, o plano **GitHub Pro (US$ 4/mês)**
permite deixar o repositório privado mantendo a página no ar.

## Aviso

Material de uso proprietário. Os sinais são saída de um modelo quantitativo e
não constituem recomendação de investimento. Resultados de backtest não
garantem resultados futuros (há risco de sobreajuste na otimização). Uso em
decisões com clientes deve observar o perfil do investidor (Res. CVM 178/2023).
