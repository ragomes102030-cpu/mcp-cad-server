# Cortes e fachadas — níveis geométricos verificáveis (piloto)

A versão preliminar de residência térrea compacta inclui agora referências
verticais originadas exclusivamente do envelope geométrico especificado
pelo solicitante.

## O que aparece nas vistas

- **Cortes A e B**: cota de piso, nível do topo das paredes, elevação da
  cumeeira, distância vertical piso–parede e distância parede–cumeeira.
- **Fachadas frontal/fundos/laterais**: piso e topo das paredes. A
  elevação da cumeeira só é anotada quando o perfil triangular do telhado
  aparece realmente naquela projeção: nas laterais para cumeeira no eixo X,
  na frente/fundos para cumeeira no eixo Y. Não se desenha uma cumeeira
  fictícia nas fachadas paralelas à água.
- **Identificação das aberturas em fachadas**: P01… para portas e J01…
  para janelas efetivamente projetadas naquela fachada, com índice igual
  ao da planta baixa.

## Fonte dos números

- Piso: `BuildingEnvelope.floor_level_m`.
- Topo de parede: `floor_level_m + wall_height_m`.
- Cumeeira: topo de parede +
  `(vão transversal/2 + beiral) × tan(inclinação)`.
- Diferenças verticais são medidas diretamente entre ordenadas do
  modelo. O desenho utiliza segmentos reais na camada `COTAS-NIVEIS` e
  rótulos com `source_id` de origem.
- O conjunto MCP contém `cotas_niveis` e o ZIP contém
  `vertical_datum_checks`, com seis vistas, marcas verificáveis,
  visibilidade da cumeeira e contagem de identificadores de esquadrias.

## Limites técnicos

São referências geométricas **para revisão profissional**. Não há
dimensionamento de estrutura do telhado, representação executiva de
camadas/espessuras, verificação de pé-direito livre acabado ou projeto
legal aprovado. Normas locais, ventilação, acessibilidade e licenciamento
devem ser checados separadamente. O código não deve declarar aprovação
municipal/NBR pelo fato de um desenho estar consistente.

## Testes

`test_niveis_cortes_fachadas.py` testa os dois eixos da cumeeira,
marcas e rótulos, ausência de cumeeira visível indevidamente e
identificadores das esquadrias projetadas.

Gates: testes completos e corpus 40/40 no GitHub Actions, abertura real
das quatro pranchas DXF e renderização A3 PDF/PNG, depois merge/deploy
no Render com `/healthz`, `initialize`, `tools/list` e pacote real.
