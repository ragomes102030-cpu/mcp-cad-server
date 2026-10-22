# Projeto exemplo parametrizavel - `Laje-Exemplo-L01`

Projeto usado para validar o fluxo quando o pedido chega com os dados em branco.
Nada aqui e de um cliente: e um **exemplo** que serve de molde.

## Dados

| Item | Valor |
|---|---|
| Tipo | laje macica, h = 12 cm |
| Painel | 4,00 x 2,50 m, 4 paineis em 8,00 x 5,00 m |
| Vigas | 0,19 x 0,40 m (perimetro e internas) |
| Pilares | 0,20 x 0,20 m nos nos |
| Cobrimento | 2,5 cm (CA-3) |
| Concreto / aco | C30 / CA-50 |
| Abertura | shaft 0,60 x 0,80 m, painel 1 |
| Cargas | g = 4,0 kN/m2 (pp 3,0 + revest. 1,0) ; q = 2,0 kN/m2 |
| qd | 8,4 kN/m2 |
| Apoio | bordos engastados |

## Resultados

Momentos (kN.m/m, nu = 0,2, malha 0,05 m):

| | M+ centro | M- apoio | alfa = M/(qd L^2) |
|---|---|---|---|
| Direcao x (4,00 m) | 0,825 | -3,004 | +0,0061 / -0,0222 |
| Direcao y (2,50 m) | 1,960 | -3,734 | +0,0373 / -0,0679 |

Armadura: **minima governa em todas as posicoes** (180 mm2/m) -> phi8@200 = 251 mm2/m.

Comprimentos: N1 2,79 ; N2 4,29 ; N3 2,10 ; N4 1,35 ; N5 1,19 ; N6 0,82 ; N7/N8 1,08 ; N9/N10 0,85 m.

Quadro de ferros: **284 barras - 262,12 kg - 6,56 kg/m2**
(phi8: 292 barras / 657 m / 259,6 kg ; phi10: 4 / 4,32 / 2,67).

## Entrega

`DWG` (4 layouts) ; `DXF` ; `XLSX` do quadro ; `MD` do relatorio ; previas PNG.

## O que este exemplo NAO cobre

- Laje **nervurada** (capa, nervuras, ferragem tipo) - nao dimensionada aqui
- Laje **pre-moldada** (escoras, vigotas, lajotas) - nao dimensionada aqui
- Vigas e pilares - desenhados, **nao dimensionados**
- Punicao pilares-laje
