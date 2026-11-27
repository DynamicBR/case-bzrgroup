# Diagnóstico, Prevenção e Dúvidas — Case BZR Group

---
## 1. Diagnóstico (Ordenado do mais grave para o menos grave)

### 1.1. Multiplicação e duplicidade de pagamentos por falta de idempotência
* **Evidência:**
  * `ENUNCIADO.md` (Fluxo Operacional, etapas 1 e 2): o tribunal envia diariamente os eventos dos **últimos 7 dias** em `pagamentos.json`, o script soma cada valor ao total pago e, quando falha no meio, o operador **roda o script novamente com o mesmo arquivo**.
  * `schema.sql` (linha 11): a coluna `evento_id TEXT NOT NULL` na tabela `pagamento` **não possui restrição `UNIQUE`**.
  * `dados/pagamentos.json`: o evento `ev-002` aparece duplicado no mesmo arquivo (linhas 10–17 e 26–33), e o evento `ev-001` aparece duas vezes com valores diferentes (`15000.0` nas linhas 2–9 em `2025-03-10T10:00:00-03:00` e retificado para `15500.0` nas linhas 66–73 em `2025-03-11T09:00:00-03:00`).
* **Impacto para o negócio:** Crítico. Um mesmo pagamento válido enviado na janela móvel de 7 dias pode ser somado até **7 vezes** (ou mais em caso de falha e reprocessamento manual), além de somar `15000 + 15500 = 30500` no `ev-001` em vez de substituir pelo valor retificado (`15500`). Isso infla artificialmente o valor recebido e distorce completamente o saldo da carteira.
* **Relação de causalidade:** **Causa raiz** principal da divergência financeira entre os números da operação e os do tribunal.

---

### 1.2. Tratamento incorreto de estornos como pagamentos (ou descarte silencioso)
* **Evidência:**
  * `DOCUMENTACAO_TRIBUNAL.md` (linha 15): afirma que o campo `tipo` em `pagamentos.json` é *"Sempre 'pagamento'"*.
  * `dados/pagamentos.json` (linhas 58–65, registro `ev-007`, processo `0034567-32.2018.8.26.0405`): traz `"tipo": "estorno"` no valor de `5000`, revertendo o pagamento `ev-006` (linhas 50–57).
  * `ENUNCIADO.md` (etapa 2): diz que o script *"soma cada valor ao total pago do processo"*.
* **Impacto para o negócio:** Crítico. Se o script confia na documentação do tribunal e apenas soma `valor` sem verificar `tipo == "estorno"`, o processo `0034567-32.2018.8.26.0405` fica com R$ 10.000,00 dados como pagos quando o saldo pago líquido real é **R$ 0,00** (`+5.000 - 5.000`).
* **Relação de causalidade:** **Causa** direta de erro de saldo financeiro, agravada pela documentação desatualizada do tribunal.

---

### 1.3. Descarte silencioso de eventos com erro de formatação ou dados inválidos
* **Evidência:**
  * `ENUNCIADO.md` (etapa 5): *"Quando um evento não pode ser importado, o script ignora e segue. Ninguém é avisado."*
  * `dados/pagamentos.json`:
    * `ev-002` (linhas 13–14): `valor` como texto brasileiro `"2.500,50"` e `data_pagamento` como `"10/04/2025"` (`DD/MM/AAAA`), contrariando `DOCUMENTACAO_TRIBUNAL.md` (linhas 13–14).
    * `ev-004` (linha 37): `"valor": null`.
    * `ev-005` (linha 44): `"processo": "00234562120208260053"` sem pontuação CNJ (se o banco espera um formato diferente do buscado, falha a chave estrangeira `precatorio_id`).
    * `ev-009` (linha 85): `"valor": -200` com `"tipo": "pagamento"` (rejeitado pelo `CHECK (valor > 0)` em `schema.sql`, linha 13, e vinculado a processo inexistente em `tribunal.csv`).
    * `ev-010` (linha 92): `"processo": ""` em branco com `"valor": 750`.
    * `ev-011` (linhas 98–105): pagamento de `4000` para o processo `0067890-65.2016.8.26.0053`, que **não existe no `hub.csv`** (logo falha ao buscar o processo na base da operação).
* **Impacto para o negócio:** Alto. Pagamentos reais (`ev-002` de R$ 2.500,50, `ev-005` de R$ 1.200,00 e `ev-011` de R$ 4.000,00) deixam de ser contabilizados sem nenhum alerta para a equipe, enquanto anomalias reais (`ev-004`, `ev-009`, `ev-010`) ficam invisíveis.
* **Relação de causalidade:** **Consequência** da inconsistência nos arquivos de origem combinada com a **causa** arquitetural de ausência de logs, alertas e fila de quarentena no script.

---

### 1.4. Divergências cadastrais graves entre `hub.csv` e `tribunal.csv` (processos ausentes, valores e entes conflitantes)
* **Evidência:**
  * **Processo ausente no Hub:** `0067890-65.2016.8.26.0053` consta em `dados/tribunal.csv` (linha 6, `R$ 7.000,00`), em `dados/apresentacoes.json` (linhas 22–25) e já recebeu pagamento (`ev-011`), mas **não existe em `dados/hub.csv`**.
  * **Processo ausente no Tribunal:** `0056789-54.2017.4.03.6100` consta em `dados/hub.csv` (linha 6, `R$ 22.000,00`) e em `dados/apresentacoes.json` (linhas 18–21), mas **não existe em `dados/tribunal.csv`**.
  * **Conflito de Ente Devedor:** `0045678-43.2021.5.02.0011` aparece como **`União`** em `dados/tribunal.csv` (linha 5), mas como **`Município de Santos`** em `dados/hub.csv` (linha 5).
  * **Conflito de Valor de Face:** `0023456-21.2020.8.26.0053` tem `valor_face` de **`30.000,00`** em `dados/tribunal.csv` (linha 3), mas **`31000.00`** em `dados/hub.csv` (linha 3).
* **Impacto para o negócio:** Alto. Precatório pago pelo tribunal fora da carteira do Hub (`0067890...`), erro de exposição financeira por ente público (`União` vs `Município de Santos` têm riscos e regimes de pagamento distintos) e diferença de R$ 1.000,00 no valor de face.
* **Relação de causalidade:** **Causa** de divergência patrimonial e **consequência** de uma conciliação semanal manual e frágil no Excel (etapa 3 do fluxo).

---

### 1.5. Cálculo incorreto do prazo constitucional de pagamento (Regra de 2 de abril e Fuso Horário)
* **Evidência:**
  * `dados/hub.csv` (linha 2, processo `0012345-10.2019.8.26.0053`): `apresentado_em = 2025-04-02` e `prazo_pagamento = 2027-12-31`. Pela Constituição (`ENUNCIADO.md`, linha 11), precatórios apresentados **até** 2 de abril vencem em 31/12 do ano seguinte (**`2026-12-31`**). O sistema provavelmente usou `< 2 de abril` em vez de `<= 2 de abril`.
  * `dados/hub.csv` (linha 6, processo `0056789-54.2017.4.03.6100`): `apresentado_em = 2025-04-03T01:00:00Z` e `prazo_pagamento = 2027-12-31`. O sufixo `Z` indica UTC; convertido para o horário de Brasília (`UTC-3`), a apresentação ocorreu em **`2025-04-02 às 22:00`**, portanto dentro do limite de 2 de abril, com prazo correto em **`2026-12-31`**.
* **Impacto para o negócio:** Médio/Alto. Como a equipe usa o prazo para priorizar a carteira (`ENUNCIADO.md`, etapa 4), precatórios que vão receber um ano antes (`2026`) são jogados para o fim da fila (`2027`), prejudicando decisões de alocação e fluxo de caixa.
* **Relação de causalidade:** **Causa** de erro na priorização operacional da carteira (bug de fronteira `<=` e falta de normalização de fuso horário no sistema).

---

### 1.6. Leiaute real de `tribunal.csv` diverge da documentação + conferência manual por texto exato no Excel
* **Evidência:**
  * `DOCUMENTACAO_TRIBUNAL.md` (linhas 20–26): documenta `tribunal.csv` como `UTF-8`, separado por vírgula (`,`) e decimal com ponto (`.`). Na realidade, `dados/tribunal.csv` (linhas 1–6) está em **`ISO-8859-1` (`Latin-1`)**, separado por **ponto e vírgula (`;`)** e valores no formato **`45.000,00`**.
  * `dados/hub.csv` (linha 2 e linha 3): traz `"MUNICIPIO DE SAO PAULO"` (caixa alta sem acento) e `"00234562120208260053"` (sem máscara CNJ), enquanto `ENUNCIADO.md` (etapa 3) relata que o operador abre no Excel, salva (risco adicional de corromper números de 20 dígitos em notação científica e alterar encoding/separador) e compara procurando **texto exato**.
  * `schema.sql` (linha 3): define `numero_processo CHAR(20)`, que comporta apenas os 20 dígitos sem pontuação, enquanto a documentação especifica o padrão CNJ com máscara de 25 caracteres (`NNNNNNN-DD.AAAA.J.TR.OOOO`).
* **Impacto para o negócio:** Médio. O operador não encontra processos legítimos na conferência semanal porque `"MUNICIPIO DE SAO PAULO" != "Município de São Paulo"` e `"00234562120208260053" != "0023456-21.2020.8.26.0053"`, além de impedir automação direta baseada apenas na documentação.
* **Relação de causalidade:** **Causa** da falha na conciliação humana semanal e de erros de leitura/importação.

---
## 2. Prevenção
1. Sugiro que na etapa 2 do fluxo operacional. Quando à importação falhar, ao invés do script continuar ele faz um retrocesso tentando importar novamente. Após duas tentativas seguintes do erro não funcionar. Colocar o tipo e a justificativa referente ao erro. Dando instruções do que fazer.
2. Em relação ao banco colocar um campo de classificação e outro campo para o tipo do precatório
3. Em relação ao banco colocar um campo TIMESTAMP referente à saída do precatório no tribunal e outro campo com a chegada do precatório na operação
4. Em relação ao banco colocar uma validação de pagamento se é pagamento ou estorno e se ela veio vazia

---
## 3. Dúvidas (Antes de colocar a limpeza em produção)
1. Em relação ao script. São dois? Um para importar o arquivo e outro para importar o evento?
2. O sistema que vocês usam para calcular o prazo de pagamento dos precatórios. É da operação ou do tribunal?
3. Que tipos de precatórios estamos lidando? Federal? Estadual? Ou Municipal?
4. Quais são as classificações dos precatórios? Alimentares ou comuns?
5. O evento seria a efetuação do pagamento?
6. Poderia implementar este script direto no sistema de cálculo de prazo? Assim unificando as ferramentas reduzindo à curva de aprendizado consequentemente custo?
7. Qual arquivo deve ser usado de referência? O hub.csv ou os do tribunal? De acordo com o fluxo operacional na etapa 3 e minha interpretação irei admitir o arquivo hub.csb será usando como parâmetro principal.
