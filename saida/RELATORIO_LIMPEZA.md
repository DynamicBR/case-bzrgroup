# Relatório de Limpeza e Conciliação de Precatórios

Este relatório descreve todas as transformações, descartes e divergências identificadas pelo pipeline em `src/case_python_bzrgroup/limpeza.py` (espelhado do estudo exploratório em `ScriptImplementacao.ipynb`).

Para preservar 100% da integridade dos arquivos originais em `dados/`, o pipeline lê as cópias de trabalho em `dados_implementacao/` (`hub_implementacao.csv`, `tribunal_implementacao.csv`, `apresentacoes_implementacao.json` e `pagamentos_implementacao.json`) e consolida o resultado em **`base_final.xlsx`** dividido em três abas:
- **`pagamentos_validos`** (8 eventos válidos contabilizados com saldo acumulado por processo)
- **`precatorios_consolidados`** (6 precatórios únicos conciliados entre Apresentações, Tribunal e Hub)
- **`eventos_descartados`** (3 eventos inválidos retidos em quarentena com motivo explícito)

---

## 1. O que foi corrigido (e por quê)

1. **Codificação e separador de `tribunal_implementacao.csv`:**
   - **Correção:** Lido com `encoding="ISO-8859-1"` e `sep=";"`.
   - **Por quê:** A `DOCUMENTACAO_TRIBUNAL.md` informava `UTF-8` separado por vírgula (`,`), o que causava erro de decodificação nos acentos (`Município`, `São Paulo`, `União`) e mantinha todas as colunas unidas.
2. **Padronização e formatação do número do processo (Padrão CNJ):**
   - **Correção:** Extraídos apenas os 20 dígitos numéricos (`limpar_processo`) para permitir o `merge` entre todas as bases, e reaplicada a máscara oficial `NNNNNNN-DD.AAAA.J.TR.OOOO` (`formatar_cnj`) na saída.
   - **Por quê:** O processo `0023456-21.2020.8.26.0053` veio sem pontuação (`00234562120208260053`) na linha 3 de `hub_implementacao.csv` e no evento `ev-005` de `pagamentos_implementacao.json`. Além disso, exportar 20 dígitos puros para o Excel corrompe o número em notação científica (`2.345621e+17`).
3. **Conversão segura de valores monetários mistos (`converter_valor_serie`):**
   - **Correção:** Removidos apenas pontos separadores de milhar (`r"\.(?=\d{3})"`) e convertida a vírgula decimal para ponto antes do `pd.to_numeric(..., errors="coerce")`.
   - **Por quê:** `tribunal_implementacao.csv` e o evento `ev-002` trouxeram strings no formato brasileiro (`"45.000,00"`, `"2.500,50"`), enquanto `hub_implementacao.csv` e os demais eventos já usavam ponto decimal (`45000.00`, `15000.0`).
4. **Padronização de `data_pagamento` (`padronizar_data_pagamento`):**
   - **Correção:** Data `"10/04/2025"` (`DD/MM/AAAA`) no evento `ev-002` convertida para `"2025-04-10"` (`AAAA-MM-DD`).
   - **Por quê:** Garante ordenação cronológica correta para o cálculo do saldo acumulado.
5. **Atualização por versão mais recente (`ev-001`):**
   - **Correção:** Ordenação por `atualizado_em` mantendo o último registro (`drop_duplicates(subset=["evento_id"], keep="last")`), adotando o valor retificado de **`R$ 15.500,00`** (`2025-03-11T09:00:00-03:00`) em lugar de `R$ 15.000,00` (`2025-03-10T10:00:00-03:00`).
   - **Por quê:** O tribunal reenviou o evento `ev-001` no dia seguinte com valor corrigido.
6. **Contabilização líquida de estorno (`ev-007`) e saldo acumulado por processo:**
   - **Correção:** Criada a coluna `valor_liquido` (positiva para `pagamento` e negativa `-5000.0` para `estorno`) e `total_pago_acumulado` via `.groupby("numero_processo")["valor_liquido"].cumsum()`.
   - **Por quê:** No processo `0034567-32.2018.8.26.0405`, o estorno `ev-007` (`R$ 5.000,00`) anula o pagamento `ev-006` (`R$ 5.000,00`), resultando em `total_pago = R$ 0,00` e `valor_restante = R$ 12.500,00`.
7. **Recálculo do prazo constitucional de pagamento (Regra de 2 de abril no fuso de Brasília):**
   - **Correção:** Datas com fuso (`Z` ou `-03:00`) foram convertidas para `America/Sao_Paulo` e datas civis sem hora (`AAAA-MM-DD`) foram localizadas diretamente em `America/Sao_Paulo`, corrigindo o prazo de dois processos que estavam como `2027-12-31` no Hub:
     - `0012345-10.2019.8.26.0053` (apresentado em `2025-04-02`, dentro do limite `<= 02/04`): corrigido para **`2026-12-31`**.
     - `0056789-54.2017.4.03.6100` (apresentado em `2025-04-03T01:00:00Z`, que equivale a **`2025-04-02 22:00 BRT`**): corrigido para **`2026-12-31`**.
8. **Unificação da grafia do ente devedor (`0012345-10.2019.8.26.0053`):**
   - **Correção:** Adotado `Município de São Paulo` (padrão de `tribunal_implementacao.csv`) em vez de `MUNICIPIO DE SAO PAULO` (caixa alta sem acentuação em `hub_implementacao.csv`).

---

## 2. O que foi descartado ou substituído (e por quê)

### Substituídos na deduplicação por `evento_id` (2 registros brutos):
- **`ev-001` (1ª ocorrência, linha 3 de `pagamentos_implementacao.json`):** versão antiga (`valor: 15000.0`, `2025-03-10T10:00:00-03:00`) substituída pela retificação mais recente (`valor: 15500.0`, `2025-03-11T09:00:00-03:00`).
- **`ev-002` (1ª cópia duplicada, linhas 10–17 / 26–33 de `pagamentos_implementacao.json`):** registro duplicado exatamente igual no mesmo arquivo.

### Movidos para a aba `eventos_descartados` em quarentena (3 eventos únicos):
- **`ev-004` (`0023456-21.2020.8.26.0053`):** descartado porque o campo `valor` veio nulo (`null`).
- **`ev-009` (`0056789-54.2017.4.03.6100`):** descartado porque veio com `tipo: "pagamento"` e valor negativo (`-200.0`), violando a regra `valor > 0`.
- **`ev-010` (processo vazio):** descartado porque o campo `processo` veio em branco (`""`), impossibilitando vincular os `R$ 750,00` a um precatório.

---

## 3. O que ficou em dúvida (exposto em `precatorios_consolidados` e para validação externa)

Na aba `precatorios_consolidados` de `base_final.xlsx`, mantivemos lado a lado os campos do Tribunal (`ente_devedor`, `valor_a_pagar`) e do Hub (`ente`, `valor_a_pagar_hub`, `prazo_hub_original`) justamente para evidenciar as divergências que exigem confirmação humana:

1. **Conflito de valor de face (`0023456-21.2020.8.26.0053`):** consta **`R$ 30.000,00`** no Tribunal, mas **`R$ 31.000,00`** no Hub (adotado `R$ 30.000,00` do Tribunal como referência provisória, restando `R$ 20.800,00` após `ev-003` e `ev-005`).
2. **Conflito de ente devedor (`0045678-43.2021.5.02.0011`):** consta **`União`** no Tribunal, mas **`Município de Santos`** no Hub.
3. **Processo ausente no Tribunal (`0056789-54.2017.4.03.6100`):** consta no Hub (`Estado de São Paulo`, `R$ 22.000,00`) e em `apresentacoes_implementacao.json`, mas não apareceu em `tribunal_implementacao.csv` (preenchido via `fillna` com os dados do Hub na aba `precatorios_consolidados` para não perder visibilidade da carteira).
4. **Processo ausente no Hub (`0067890-65.2016.8.26.0053`):** consta no Tribunal (`Município de São Paulo`, `R$ 7.000,00`), em `apresentacoes_implementacao.json` (`2023-12-31`, prazo `2025-12-31`) e já recebeu pagamento válido (`ev-011` de `R$ 4.000,00`), mas não está cadastrado no Hub (`ente` e `valor_a_pagar_hub` nulos).
5. **Pagamento anterior à apresentação (`0012345-10.2019.8.26.0053`):** o evento `ev-001` possui `data_pagamento = 2025-03-10`, anterior a `apresentado_em = 2025-04-02`.
6. **Destino dos eventos em quarentena (`ev-004`, `ev-009` e `ev-010`):** aguarda esclarecimento do tribunal sobre valor real (`ev-004`), possível estorno mal classificado (`ev-009`) e número do processo (`ev-010`).
