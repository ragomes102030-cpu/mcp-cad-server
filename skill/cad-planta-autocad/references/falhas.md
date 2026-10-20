# Falhas que viram experiência (e não viram folclore)

> "O que não dá certo vira experiência" — mas só se ficar registrado.
> O objetivo desta página não é documentar o AutoCAD: é **capturar o resíduo**
> de cada tentativa que falhou, para não depender da memória de quem estava na
> conversa.

## O mecanismo, em três peças

| Peça | O que faz | Onde |
|---|---|---|
| **Registro** | cada falha vira uma linha: sintoma, contexto, sugestão, o modelo mínimo que reproduz | `historico/ocorrencias.jsonl` |
| **Promoção** | sintoma **só** vira verificação de código na **3ª ocorrência** | `historico.promovidos()` |
| **Verificação** | os sintomas promovidos rodam em ~1 ms, antes do AutoCAD | `cad_mcp/validar_modelo.py` |

Por que 3 e não 1: a primeira ocorrência pode ser ambiente, typo de quem chamou,
ou um caso único. A terceira é padrão. Promover na primeira enche o validador de
regra inútil e a gente passa a ignorar o relatório — o pior resultado possível.

## Como registrar (durante a tarefa, não depois)

```python
from cad_mcp.historico import registrar
registrar(
    "porta-sem-vao",                          # chave estável, minúscula, com hífen
    "arco da porta desenhado sobre parede fechada",  # sintoma COMO APARECEU
    modelo=recorte_do_modelo,                 # o menor dict que reproduz
    contexto={"arquivo": "planta_3q.dwg", "o_que_eu_achei"},  # evidência, não opinião
    sugestao="abrir o vão no eixo (dois trechos), não desenhar por cima",
)
```

Regras do registro:
- **sintoma literal** ("saiu 116,62°", "Error saving the document"), não paráfrase
  ("problema de ângulo"). Paráfrase impede a busca. 
- **evidência numérica** quando houver (medida, nome do arquivo, número do DXF);
- **o que foi feito para corrigir** — se não foi corrigido, escreva isso também;
- uma linha por ocorrência. Contar = contar linhas. Nunca reescrever o passado.

```bash
python -m cad_mcp.historico                  # tabela: ocorrências por sintoma
python -m cad_mcp.historico --chave X        # histórico de um sintoma
python -m cad_mcp.historico --json           # para processar
```

## Como o validador usa isso

Cada verificação tem a **mesma chave** do histórico. O relatório mostra
`(já ocorreu Nx)` ao lado do erro:

```
VALIDACAO: 1 erro(s), 0 aviso(s) | area util 119.56 m2
  ERRO  selo-transborda  selo y=-7.00  'XXX...' ocupa 23,76 m e passa de x=23,76 (já ocorreu 1x)
```

Se um sintoma aparece e **não** tem verificação, ainda não é hora de escrevê-la
(ou é questão de código, não de modelo — ver abaixo).

## O que é verificável no modelo, e o que não é

| Sintoma | Dá para pegar no JSON? | Onde |
|---|---|---|
| porta sem vão, arco sobre parede | sim — `porta-sem-vao` | validador |
| texto/selo maior que o espaço | sim — `texto-transborda`, `selo-transborda` | validador |
| ambiente invertido/sobreposto | sim | validador |
| área ≠ m² pedido | sim — `area-total-diverge` | validador |
| graus passados onde entmake quer radianos | **não** — é bug de código | `planta._rad`, `angtof` |
| DXF sem os arcos recém-criados | **não** — é ordem de pipeline | salvar antes de exportar |
| DWG não sobrescreve arquivo aberto | **não** — é comportamento do AutoCAD | nomes com sufixo |

Os não-verificáveis ficam no histórico como **regra de código** com
`contexto.corrigido_em` apontando o arquivo. O histórico guarda sintoma de
qualquer nível; o validador só expressa o que é expressável em dados.

## Primeiras entradas (16/10/2026, todas reais)

| chave | sintoma | virou |
|---|---|---|
| `arco-graus-em-radianos` | arco de 90° saiu 116,620156177409° | regra de código (`_rad`) |
| `selo-transborda` | selo de ~130 chars a 0,22 m esmagou o A3 | verificação + regra de texto 0,9 |
| `dwg-nao-sobrescreve` | "Error saving the document" | fallback `_2`, `_3` |
| `dxf-antes-de-salvar` | DXF sem arcos; falso diagnóstico | ordem do pipeline |
| `load-lsp-trava-com` | `(load)` + SECURELOAD → RPC_E_CALL_REJECTED | LISP inline |

Todas com 1 ocorrência = **observar**, não promover. Elas já foram corrigidas no
código; a contagem serve para detectar reincidência (se o mesmo sintoma voltar
duas vezes, algo regrediu — e aí sim vira teste).

## Regressão

`tests/validar_modelo_teste.py` roda o modelo real (deve passar limpo) e uma
mutação por sintoma conhecido (deve reprovar com a chave certa). Um caso por
linha, sem AutoCAD:

```bash
python tests/validar_modelo_teste.py
```

Se um "conserto" fizer o modelo real reprovar, o teste acusa antes de gastar
um ciclo COM → DXF → PDF.
