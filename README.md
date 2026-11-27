# Case Técnico — Conciliação e Limpeza de Precatórios (BZR Group)

Solução de diagnóstico, limpeza, conciliação e prevenção para os dados operacionais de precatórios e eventos de pagamento enviados pelo tribunal.

## Requisitos

- Python **3.10+**
- Gerenciador de pacotes [`uv`](https://docs.astral.sh/uv/) (com `pandas`, `openpyxl` e `pytest`)

## Estrutura do Projeto

- `dados/` — Arquivos originais recebidos no case (mantidos 100% inalterados).
- `dados_implementacao/` — Cópias de trabalho utilizadas pelo notebook e pelo script de limpeza.
- `Diagnóstico.md` — Diagnóstico ordenado por criticidade (com evidências por arquivo/linha, impactos de negócio e relação de causa/consequência), propostas de prevenção e dúvidas para o tribunal e a operação.
- `schema.sql` e `schema-implementacao.sql` — Esquema original do banco e proposta de evolução PostgreSQL com restrições de integridade e rastreabilidade.
- `ScriptImplementacao.ipynb` — Notebook exploratório com o desenvolvimento passo a passo da lógica em Pandas.
- `src/case_python_bzrgroup/limpeza.py` — Pipeline de limpeza e conciliação em Python espelhando diretamente o notebook.
- `base_final.xlsx` — Base consolidada gerada pelo pipeline com três abas (`pagamentos_validos`, `precatorios_consolidados` e `eventos_descartados`).
- `saida/RELATORIO_LIMPEZA.md` — Relatório detalhando tudo o que foi corrigido, descartado ou ficou em dúvida e por quê.
- `tests/test_limpeza.py` — Suíte de **22 testes automatizados** com `pytest` (`@pytest.mark.parametrize`, `tmp_path` e `pytest.approx`).
- `tests/RELATORIO_TESTES.md` — Documentação detalhada dos cenários de teste, entradas, saídas esperadas e riscos de negócio cobertos.

## Como Rodar o Projeto

1. Instale as dependências no ambiente virtual:
   ```bash
   uv sync
   ```

2. Execute o pipeline de limpeza e geração do `base_final.xlsx`:
   ```bash
   uv run case-python-bzrgroup
   ```
   *(ou diretamente `uv run python src/case_python_bzrgroup/limpeza.py`)*

3. Execute os **22 testes automatizados** com `pytest`:
   ```bash
   uv run pytest -v
   ```
   A suíte valida:
   - **Fronteira constitucional de 2 de abril:** datas em `02/04` (`ano + 1`), `03/04` (`ano + 2`), ano bissexto (`29/02/2024`) e fim de ano (`31/12/2023`).
   - **Fuso horário de Brasília (`America/Sao_Paulo`):** conversão de timestamps em UTC (`2025-04-03T01:00:00Z` -> `02/04 às 22h BRT`) sem deslocar datas civis sem hora.
   - **Valores monetários mistos:** `float` (`15000.0`), inteiros, strings com ponto (`"45000.00"`), formato brasileiro (`"45.000,00"`, `"2.500,50"`), negativos e nulos.
   - **Normalização CNJ e datas de pagamento:** limpeza de 20 dígitos, máscara CNJ de 25 caracteres e conversão de `DD/MM/AAAA` para `AAAA-MM-DD`.
   - **Integração ponta a ponta e imutabilidade:** deduplicação por `atualizado_em` (`ev-001` e `ev-002`), abatimento líquido de `estorno` (`ev-007`), quarentena de inválidos (`ev-004`, `ev-009`, `ev-010`) e checagem por hash **SHA-256** garantindo que nenhum arquivo original em `dados/` foi modificado.

## Uso de IA e Como Conferi o Resultado

Utilizei IA como apoio de estudo e revisão técnica ao longo do case:

1. **Aprendizado da sintaxe do Pandas:** Após mapear manualmente a regra de negócio e montar uma planilha de referência (`base_implementacao.xlsx`), usei a IA para aprender como traduzir cada etapa (leitura de CSV/JSON, expressões regulares para CNJ, `.merge()`, `.drop_duplicates()` e soma acumulada com `.cumsum()`) para Pandas no `ScriptImplementacao.ipynb`, levando depois o mesmo código para `src/case_python_bzrgroup/limpeza.py`.
2. **Revisão crítica e detecção de casos de borda:** Usei a IA para revisar a base gerada (`base_final.xlsx`) contra o enunciado, o que ajudou a identificar armadilhas sutis — como datas sem hora (`2025-04-03`) sendo deslocadas para o dia anterior ao converter fuso UTC para Brasília, valores decimais com ponto (`45000.0`) multiplicados por 10 ao remover `.` indiscriminadamente e o abatimento líquido de eventos do tipo `estorno`.
3. **Como conferi o que a IA produziu:**
   - Inspecionei cada transformação intermediária nas células do `ScriptImplementacao.ipynb`.
   - Validei todas as regras críticas com os 22 casos de teste em `tests/test_limpeza.py` (documentados em `tests/RELATORIO_TESTES.md`).
