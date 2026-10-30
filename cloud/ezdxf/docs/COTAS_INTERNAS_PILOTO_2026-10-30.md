# MVP 1.3 — cotas internas gráficas (primeira faixa)

Esta entrega adiciona cotas **horizontais** de largura aos ambientes que
tenham área livre suficiente para acomodar linhas, marcas e texto sem
interferir com mobiliário e rótulos do modelo. O restante continua no
quadro de ambientes (largura × profundidade) já publicado.

## Critério de medição

- Ponta inicial e final da linha usam `x1` e `x2` da face interna
  mapeada do cômodo, em metros, sem encurtar para facilitar o desenho.
- O texto da cota representa exatamente `x2-x1`, com duas casas decimais.
- Ao escolher a posição da linha são avaliados os móveis e rótulos
  já existentes; se a área estiver congestionada, a dimensão gráfica
  é **omitida** e a pendência fica explícita no relatório.
- As linhas usam layer `COTAS-INTERIOR` e identificadores
  `dimension:room:N:width`; o texto usa
  `dimension-label:room:N:width`. Isso permite conferir DXF reaberto.
- No caso-piloto 10 × 20 m, o detector preliminar posiciona **4/7**
  cotas gráficas horizontais, sem atravessar os móveis; as sete dimensões
  continuam no quadro de ambientes. A cobertura insuficiente não é
  escondida ou declarada completa.

## Evidência e limitações

A resposta MCP contém `cotas_internas`, e o JSON do ZIP contém
`interior_dimensions` com `width_dimensions_drawn`,
`width_dimensions_in_schedule` e `omitted_graphic_room_indices`.

A posição é preliminar; precisa de revisão visual do PDF A3 em tamanho de
impressão, especialmente junto a vãos de portas, mobiliário e cotas externas.
A rotina ainda **não** desenha todas as cotas verticais de profundidade,
não certifica as faces acabadas e não substitui medição profissional,
projeto executivo, análise de acessibilidade ou conformidade legal.

## Regressões

```bash
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python -m pytest cloud/ezdxf/tests -q
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_plant_lab.py --output out/plant-lab
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_licensing_corpus.py --output out/licensing-corpus
```
