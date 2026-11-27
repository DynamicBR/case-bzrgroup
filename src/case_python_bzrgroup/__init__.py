from case_python_bzrgroup.limpeza import executar_limpeza


def main() -> None:
    resultado = executar_limpeza()
    print("Limpeza concluída com sucesso!")
    print(f"- Precatórios consolidados: {len(resultado['precatorios'])}")
    print(f"- Pagamentos válidos: {len(resultado['pagamentos_validos'])}")
    print(f"- Eventos descartados: {len(resultado['eventos_descartados'])}")
    print("- Planilha gerada: base_final.xlsx")
