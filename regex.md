# Caractéres especiais REGEX
- `\d`	Qualquer dígito (número)	`[0-9] (e dígitos Unicode)`	`\d{4}` acha "2026"
- `\D`	Qualquer caractere que NÃO é dígito	`[^0-9]`	`\D+` remove pontuação/letras de um CNJ
- `\w`	Caractere de palavra (letras, números e `_`)	`[a-zA-Z0-9_]` + acentos no Python 3	`\w+` acha `"Sao_Paulo_1"`
- `\W`	Qualquer caractere que NÃO é de palavra	Pontuação, espaços, símbolos	`\W` acha `"-"`, `"."`, `" "`
- `\s`	Qualquer espaço em branco	Espaço, tab `(\t)`, quebra de linha `(\n)`	`\s+` acha vários espaços seguidos
- `\S`	Qualquer caractere que NÃO é espaço	Tudo que é visível	`\S+` acha `"R$100,00"`
- `\b`	Borda de palavra (início ou fim)	Não consome caractere, só marca posição	`\bSP\b` acha `"SP"`, mas não `"ESPECIAL"`
- `\B`	Não é borda de palavra	Dentro de uma palavra	`\BSP\B` acha `"SP"` em `"ESPECIAL"`
- `\A`	Início absoluto da string	Igual ao `^`, mas ignora modo multilinha	`\A000` exige começar com `"000"`
- `\Z`	Fim absoluto da string	Igual ao `$`, mas ignora modo multilinha	`0053\Z` exige terminar com `"0053"`
- `\1,` `\2...`	Retrovisor (backreference)	Repete o texto capturado no grupo `(...)`	`(\w+)\s+\1` acha palavras repetidas `("de de")`
- `\` + `símbolo`	Escape de caractere especial	Trata `.`, `-`, `+`, `?`, `\` como texto literal	`\.` acha um ponto de verdade (e não "qualquer coisa")

# Metacaractéres
- `[]` Um conjunto de caracteres
- `\` Indica uma sequência especial (também pode ser usado para escapar caracteres especiais)
- `.` Qualquer caractere (exceto o caractere de nova linha)
- `^` Começa com
- `$` Termina com
- `*` Zero ou mais ocorrências
- `+` Uma ou mais ocorrências
- `?` Zero ou uma ocorrências
- `{}` Exatamente o número especificado de ocorrências
- `|` Um ou outro
- `()` Capturar e agrupar
