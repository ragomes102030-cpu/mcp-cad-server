# Piloto — cotas horizontais e verticais do MCP CAD Cloud

Esta versão amplia a representação das dimensões livres dos ambientes da
residência térrea compacta de dois quartos. O desenho continua sendo **estudo
arquitetônico preliminar para revisão**; não é projeto executivo ou aprovação
de exigências municipais/NBR.

## Regra de medição

Para cada ambiente do modelo, a largura é `x2 - x1` e a profundidade é
`y2 - y1` (metros), medidas nos limites de ambiente disponibilizados pelo
modelo. As linhas de cota sempre preservam esses extremos. Não arredondar o
traçado para conseguir um número solicitado.

A rotina procura posições de cotas de **ambos os eixos**, considerando:
- contornos do mobiliário e caixas dos textos;
- segmentos dos símbolos de abertura das portas;
- proximidade das paredes e espaço disponível para o texto;
- interação entre as duas cotas de cada ambiente.

Se não houver posição suficientemente livre, a cota **não é forçada**:
a largura/profundidade continua no quadro de áreas/dimensões e a omissão fica
registrada no JSON, na resposta MCP e no relatório do pacote. Isso não
equivale a indicar a cota gráfica integral como concluída.

## Caso piloto 10 × 20 m

- Larguras gráficas: **7/7 ambientes**.
- Profundidades gráficas: **5/7 ambientes**.
- Profundidades ainda não posicionadas dentro dos ambientes:
  área de serviço (índice 2) e banheiro social (índice 5); os giros
  de portas e/ou obstáculos tornam inseguro o posicionamento atual.
- Dimensões numéricas no quadro de ambientes: **7/7** nos dois eixos.
- O relatório utiliza `graphic_status=partial`; não declara cotação
  completa.

Os identificadores seguem `dimension:room:{i}:width|depth` para a linha
e `dimension-label:room:{i}:width|depth` para o texto. Todas as entidades
estão na camada `COTAS-INTERIOR`.

## Auditorias e limitações

Testar amostras do DXF reaberto, A3 PDF e PNG, incluindo comprimento dos
segmentos, ausência de linhas sobre móveis e portas, coerência de etiquetas e
não-interferência dos textos pelo método de caixas estimadas.

As caixas aproximadas não medem glifos reais; a decisão sobre apresentação,
clareza gráfica, acesso e funcionalidade é de profissional habilitado. A
geometria do gerador não constitui verificação independente de dimensões
acabadas ou acessibilidade.

### Regressão reproduzível

```bash
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python -m pytest cloud/ezdxf/tests -q
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_plant_lab.py --output out/plant-lab
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_licensing_corpus.py --output out/licensing-corpus
```

**Critério de publicação:** CI completo, corpus e conferência de exportação;
merge no branch `cloud/ezdxf` só depois, seguido de comparação de SHA em
`/healthz`, MCP HTTP `initialize`, `tools/list` e teste do pacote.
