import hashlib
from pathlib import Path

import pandas as pd
import pytest

from case_python_bzrgroup.limpeza import (
    calcular_prazo_pagamento,
    converter_valor_serie,
    executar_limpeza,
    formatar_cnj,
    limpar_processo,
    padronizar_data_pagamento,
)


@pytest.mark.parametrize(
    ("apresentado_em", "prazo_esperado"),
    [
        # Fronteira exata de 2 de abril -> 31/12 do ano seguinte (ano + 1)
        ("2025-04-02", "2026-12-31"),
        # Dia 3 de abril sem hora (data local) -> 31/12 do ano subsequente ao seguinte (ano + 2)
        ("2025-04-03", "2027-12-31"),
        # Ano bissexto antes de abril -> ano + 1
        ("2024-02-29", "2025-12-31"),
        # Fim do ano (após 2 de abril de 2023) -> 2023 + 2 = 2025
        ("2023-12-31", "2025-12-31"),
    ],
)
def test_prazo_constitucional_fronteira_2_de_abril(
    apresentado_em: str, prazo_esperado: str
) -> None:
    serie = pd.Series([apresentado_em])
    assert calcular_prazo_pagamento(serie).iloc[0] == prazo_esperado


@pytest.mark.parametrize(
    ("apresentado_em_iso", "prazo_esperado"),
    [
        # 2025-04-03T01:00:00Z em UTC equivale a 2025-04-02 22:00 em Brasília (até 2 de abril)
        ("2025-04-03T01:00:00Z", "2026-12-31"),
        # Já no fuso de Brasília (-03:00) dentro do dia 2 de abril
        ("2025-04-02T23:30:00-03:00", "2026-12-31"),
        # 2025-04-03T04:00:00Z equivale a 2025-04-03 01:00 em Brasília (após 2 de abril)
        ("2025-04-03T04:00:00Z", "2027-12-31"),
    ],
)
def test_prazo_constitucional_fusos_horarios(
    apresentado_em_iso: str, prazo_esperado: str
) -> None:
    serie = pd.Series([apresentado_em_iso])
    assert calcular_prazo_pagamento(serie).iloc[0] == prazo_esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (15000.0, 15000.0),
        (8000, 8000.0),
        ("45000.00", 45000.0),
        ("45.000,00", 45000.0),
        ("2.500,50", 2500.5),
        (-200, -200.0),
        (None, None),
        ("None", None),
        ("", None),
    ],
)
def test_conversao_valores_monetarios_mistos(
    entrada: object, esperado: float | None
) -> None:
    resultado = converter_valor_serie(pd.Series([entrada], dtype=object)).iloc[0]
    if esperado is None:
        assert pd.isna(resultado)
    else:
        assert resultado == pytest.approx(esperado)


def test_normalizacao_e_formatacao_cnj() -> None:
    serie = pd.Series(["0012345-10.2019.8.26.0053", "", None])
    limpa = limpar_processo(serie)
    assert limpa.iloc[0] == "00123451020198260053"
    assert limpa.iloc[1] == ""
    assert limpa.iloc[2] == ""
    assert formatar_cnj("00234562120208260053") == "0023456-21.2020.8.26.0053"


@pytest.mark.parametrize(
    ("data_bruta", "data_iso"),
    [
        ("2025-03-10", "2025-03-10"),
        ("10/04/2025", "2025-04-10"),
        ("data-invalida", None),
        (None, None),
    ],
)
def test_padronizacao_data_pagamento(data_bruta: str | None, data_iso: str | None) -> None:
    resultado = padronizar_data_pagamento(pd.Series([data_bruta], dtype=object)).iloc[0]
    if data_iso is None:
        assert pd.isna(resultado)
    else:
        assert resultado == data_iso


def test_pipeline_completo_e_integridade_arquivos_originais(tmp_path: Path) -> None:
    pasta_dados = Path("dados")
    pasta_implementacao = Path("dados_implementacao")
    hashes_antes = {
        arq.name: hashlib.sha256(arq.read_bytes()).hexdigest()
        for arq in pasta_dados.iterdir()
        if arq.is_file()
    }

    resultado = executar_limpeza(
        pasta_entrada=pasta_implementacao,
        caminho_excel=tmp_path / "base_final.xlsx",
    )

    df_prec = resultado["precatorios"].set_index("numero_processo")
    df_pag = resultado["pagamentos_validos"]
    df_desc = resultado["eventos_descartados"]

    # 6 precatórios consolidados
    assert len(df_prec) == 6

    # ev-001 retificado para 15500.0 + ev-002 (2500.5) = 18000.5 pagos
    assert df_prec.loc["0012345-10.2019.8.26.0053", "total_pago"] == pytest.approx(18000.5)
    assert df_prec.loc["0012345-10.2019.8.26.0053", "valor_restante"] == pytest.approx(26999.5)
    assert df_prec.loc["0012345-10.2019.8.26.0053", "prazo_pagamento"] == "2026-12-31"

    # Estorno (ev-007) anula o pagamento (ev-006) de 5000 -> total_pago = 0.0
    assert df_prec.loc["0034567-32.2018.8.26.0405", "total_pago"] == pytest.approx(0.0)
    assert df_prec.loc["0034567-32.2018.8.26.0405", "valor_restante"] == pytest.approx(12500.0)

    # 8 eventos válidos e 3 eventos em quarentena (ev-004 nulo, ev-009 negativo, ev-010 sem processo)
    assert len(df_pag) == 8
    assert set(df_desc["evento_id"]) == {"ev-004", "ev-009", "ev-010"}
    assert (tmp_path / "base_final.xlsx").exists()

    # Garante que nenhum arquivo original em dados/ foi modificado
    hashes_depois = {
        arq.name: hashlib.sha256(arq.read_bytes()).hexdigest()
        for arq in pasta_dados.iterdir()
        if arq.is_file()
    }
    assert hashes_antes == hashes_depois
