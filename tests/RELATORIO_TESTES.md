# Relatório de Testes Automatizados (`pytest`)

Este documento detalha a cobertura e os resultados da suíte de testes automatizados localizada em `tests/test_limpeza.py`, criada para validar as regras de negócio mais críticas e propensas a falhas silenciosas no pipeline `src/case_python_bzrgroup/limpeza.py`.

---

## 1. Ambiente e Resumo da Execução

- **Comando executado:** `uv run pytest -v`
- **Interpretador:** Python `3.10.21`
- **Framework:** `pytest 9.2.0`
- **Total de casos executados:** **22 testes**
- **Resultado:** **22 aprovados (`PASSED`) / 0 falhas (`FAILED`)**

---

## 2. Regras Críticas Cobertas pelos Testes

### 2.1. `test_prazo_constitucional_fronteira_2_de_abril` (4 casos parametrizados)
Valida o cálculo do vencimento constitucional de precatórios (Art. 100, § 5º da CF/88) em datas civis locais:
| Entrada (`apresentado_em`) | Saída Esperada | Risco coberto | Status |
| :--- | :--- | :--- | :--- |
| `"2025-04-02"` | `"2026-12-31"` | Bug de fronteira (`< 2` em vez de `<= 2` que existia no `hub.csv`) | `PASSED` |
| `"2025-04-03"` | `"2027-12-31"` | Virada imediata após 2 de abril (ano + 2) sem regressão de fuso | `PASSED` |
| `"2024-02-29"` | `"2025-12-31"` | Validação de dia 29 de fevereiro em ano bissexto | `PASSED` |
| `"2023-12-31"` | `"2025-12-31"` | Apresentação no último dia do ano (após 02/04/2023 -> 2023 + 2) | `PASSED` |

---

### 2.2. `test_prazo_constitucional_fusos_horarios` (3 casos parametrizados)
Valida a conversão correta de timestamps ISO 8601 (`UTC` vs `America/Sao_Paulo`) antes de avaliar o dia de corte:
| Entrada (`apresentado_em`) | Horário em Brasília | Saída Esperada | Risco coberto | Status |
| :--- | :--- | :--- | :--- | :--- |
| `"2025-04-03T01:00:00Z"` | `2025-04-02 22:00 BRT` | `"2026-12-31"` | Evita classificar como 03/04 um protocolo feito às 22h de 02/04 no Brasil | `PASSED` |
| `"2025-04-02T23:30:00-03:00"` | `2025-04-02 23:30 BRT` | `"2026-12-31"` | Evita que conversão indevida para UTC jogue o protocolo para 03/04 | `PASSED` |
| `"2025-04-03T04:00:00Z"` | `2025-04-03 01:00 BRT` | `"2027-12-31"` | Confirma que após meia-noite em Brasília o prazo avança para `ano + 2` | `PASSED` |

---

### 2.3. `test_conversao_valores_monetarios_mistos` (9 casos parametrizados)
Valida `converter_valor_serie` contra colunas mistas contendo `float`, `int`, formato brasileiro (`"2.500,50"`) e valores nulos:
| Entrada | Saída Esperada | Risco coberto | Status |
| :--- | :--- | :--- | :--- |
| `15000.0` | `15000.0` | Impede que `.replace(".", "")` transforme `15000.0` em `150000.0` (10x maior) | `PASSED` |
| `8000` | `8000.0` | Inteiros puros vindos do JSON | `PASSED` |
| `"45000.00"` | `45000.0` | Strings com ponto decimal (padrão `hub.csv`) | `PASSED` |
| `"45.000,00"` | `45000.0` | Strings com milhar e vírgula decimal (padrão `tribunal.csv`) | `PASSED` |
| `"2.500,50"` | `2500.5` | Preservação exata de centavos em texto brasileiro (`ev-002`) | `PASSED` |
| `-200` | `-200.0` | Preserva sinal negativo para posterior bloqueio na validação (`ev-009`) | `PASSED` |
| `None`, `"None"`, `""` | `NaN` | Converte vazios sem disparar `ValueError: could not convert string to float` | `PASSED` (3 casos) |

---

### 2.4. `test_normalizacao_e_formatacao_cnj` (1 caso com múltiplas asserções)
- Verifica a remoção de caracteres não numéricos (`"0012345-10.2019.8.26.0053"` -> `"00123451020198260053"`), o tratamento seguro de `""` e `None`, e a reconstrução da máscara CNJ de 25 caracteres (`"00234562120208260053"` -> `"0023456-21.2020.8.26.0053"`).
- **Status:** `PASSED`

---

### 2.5. `test_padronizacao_data_pagamento` (4 casos parametrizados)
- Verifica a conversão de datas ISO (`"2025-03-10"`) e brasileiras (`"10/04/2025"` -> `"2025-04-10"`), retornando `NaN` para textos inválidos ou `None`.
- **Status:** `PASSED`

---

### 2.6. `test_pipeline_completo_e_integridade_arquivos_originais` (Teste de Integração End-to-End)
Executa `executar_limpeza` de ponta a ponta em diretório temporário (`tmp_path`) e verifica:
1. **Consolidação total:** exatamente **6 precatórios** únicos consolidados.
2. **Deduplicação e retificação (`0012345-10.2019.8.26.0053`):** `ev-001` retificado (`15500.0`) + `ev-002` deduplicado (`2500.5`) = `total_pago` de **`18000.5`** e `valor_restante` de **`26999.5`**, com prazo corrigido para `2026-12-31`.
3. **Abatimento de estorno (`0034567-32.2018.8.26.0405`):** pagamento `ev-006` (`+5000.0`) anulado pelo estorno `ev-007` (`-5000.0`) -> `total_pago` = **`0.0`** e `valor_restante` = **`12500.0`**.
4. **Quarentena de inválidos:** exatamente **8 eventos válidos** e **3 eventos descartados** (`{"ev-004", "ev-009", "ev-010"}`).
5. **Imutabilidade dos arquivos originais (`dados/`):** calcula o hash **SHA-256** de todos os arquivos da pasta `dados/` antes e depois da execução, comprovando que nenhum arquivo original foi alterado.
- **Status:** `PASSED`

---

## 3. Como Reproduzir

```bash
uv run pytest -v
```
