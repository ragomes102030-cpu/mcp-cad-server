# Verificacoes NBR 6118 - o que conferir e o numero

## Estados-limites ultimos (esforcos)

`qd = max(1,25 g + 1,5 q  ;  1,4 (g + q))`

Para residencial com revestimento: `g = 3,0 (peso proprio) + 1,0 = 4,0 kN/m2`,
`q = 2,0 kN/m2` -> `qd = max(8,0 ; 8,4) = 8,4 kN/m2`.

## Armadura

| Verificacao | Formula | Valor de referencia |
|---|---|---|
| Armadura minima (CA-50) | `rho_min = 0,15 %` | `As_min = 0,0015 b h` -> 180 mm2/m para h=12 cm |
| Armadura minima (CA-60) | `rho_min = 0,10 %` | 120 mm2/m |
| Altura util | `d = h - cobr - phi/2` | 91 mm para h=12, cobr=2,5, phi=8 |
| Braco de alavanca | `z = 0,95 d` | 86,5 mm |
| Tensao de calculo do aco | `fsd = fyk / 1,15` | 434,8 MPa (CA-50) |
| Armadura | `As = Msd / (z fsd)` | - |

## Espacamento (o mais esquecido)

| Regra | Limite | Para h = 12 cm |
|---|---|---|
| `e_min` | 50 mm | - |
| `e_max` (laje macica) | `min(2h ; 200 mm)` | **200 mm** - phi8@200 fica *no limite* |
| `e_max` (nervurada) | `min(3h ; 400 mm)` | - |

Se o escritorio exigir margem em `e_max`, phi8@150 (335 mm2/m) custa ~8 % a mais.

## Ancoragem (NBR 6118 secao 9.4)

```
fctm     = 0,3 fck^(2/3)         # 2,896 MPa (C30)
fctk,inf = 0,7 fctm              # 2,027 MPa
fctd     = fctk,inf / 1,4        # 1,448 MPa
fbd      = eta1 eta2 fctd        # eta1 = 2,5 (boa aderencia, phi <= 32), eta2 = 1,0
l_b      = (phi / 4) (fyd / fbd)
```

CA-50/C30: `l_b` = **0,24 m** (phi8), **0,30 m** (phi10), **0,37 m** (phi12,5).

## Cobrimento nominal minimo (NBR 6118)

| Classe de agressividade | Laje | Viga/pilar |
|---|---|---|
| CA-2 (urbana interior) | 20 mm | 25 mm |
| CA-3 | **25 mm** | 30 mm |
| CA-4 (garagem, externa) | 30 mm | 35 mm |

## Extensao da armadura negativa

- Apoio interno (laje dos dois lados): `l_n/4` alem da face, em cada lado
- Apoio de borda: `l_b` (ancoragem) + `l_n/4`
- Checar sempre `l_n/4 >= l_b`

## Abertura em laje

- Barras interrompidas -> repor por barras laterais com **area >= interceptada**
- Cada barra lateral se estende **alem da abertura por `l_b`**
- Diagonais de 45 graus nos cantos

## Deflexao

Limite usual: `w/L <= 1/250`. Para laje bidirecional com borda engastada o valor e
muito menor (no exemplo: w = 0,165 mm -> `w/L = 1/15196`).

**Nao confunda com esbeltez `h/L`:** `h/L = 1/20,8` e esbelto para laje simplesmente
apoiada, mas a acao bidirecional engastada e bem mais rigida. Confira a deflexao, nao o
`h/L` de tabela.

## Cisalhamento

Para laje **sem carga concentrada** (so carga distribuida e apoiada em vigas), a
verificacao ao cisalhamento e **dispensada**. Se houver equipamento/patio sobre a
abertura ou carga concentrada, verificar punicao/cisalhamento no entorno.
