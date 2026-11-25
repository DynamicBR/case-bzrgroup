# Diagnóstico Case BZR-Group
## Dúvidas
1.	Em relação ao script. São dois? Um para importar o arquivo e outro para importar o evento?
2.	O sistema que vocês usam para calcular o prazo de pagamento dos precatórios. É da operação ou do tribunal?
3.	Que tipos de precatórios estamos lidando? Federal? Estadual? Ou Municipal?
4.	Quais são as classificações dos precatórios? Alimentares ou comuns?
5.	O evento seria a efetuação do pagamento?
6.	Poderia implementar este script direto no sistema de cálculo de prazo? Assim unificando as ferramentas reduzindo à curva de aprendizado
    consequentemente custo?
7. Qual arquivo deve ser usado de referência? O hub.csv ou os do tribunal? De acordo com o fluxo operacional na etapa 3 e minha interpretação irei admitir o arquivo hub.csb será usando como parâmetro principal.
## Prevenção
1. Sugiro que na etapa 2 do fluxo operacional. Quando à importação falhar, ao invés do script continuar ele faz um retrocesso tentando importar novamente.
   Após duas tentativas seguintes do erro não funcionar. Colocar o tipo e a justificativa referente ao erro. Dando instruções do que fazer.
2. Em relação ao banco colocar um campo de classificação e outro campo para o tipo do precatório
3. Em relação ao banco colocar um campo TIMESTAMP referente à saída do precatório no tribunal e
   outro campo com a chegada do precatório na operação
## Diagnóstico
1. O arquivo tribunal.csv não estava suportando acentos. Então tive que colocar no formato `ISO-8859-1`. Não pude colocar o padrão `utf-8`. Pois não conseguia abrir o arquivo dentro da pasta.
2.  O número  do processo `0012345-10.2019.8.26.0053`. Estavá com o prazo errado.
   Prazo antigo: `2027-12-31`, prazo novo: `2026-12-31`. À alteração foi feita por que a data de apresentação foi `2025-04-02`. De acordo com o pdf na aba contexto. Os precatórios apresentados até o dia 2 de abril. Só acrescentam um ano.
3.  Em todos os arquivos .csv e .json fiz um tratamento no campo processo, unificando os nomes e removendo a formatação CNJ. Para que no futuro eu consiga mesclar todas estes dados em uma única base.
4. Em todos os arquivos .csv e o arquivo pagamentos_implementacao.json realizei o tratamento de unificação dos números para se adaptar ao formato brasileiro e evitar erros de caractéres no futuro.
5. `
