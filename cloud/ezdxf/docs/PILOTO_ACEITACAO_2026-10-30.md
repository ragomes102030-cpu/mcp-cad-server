# Piloto CAD Cloud — critérios de aceitação e limites (30/10/2026)

Base auditada: branch `cloud/ezdxf`, commit `15fb019da3a77af20e3f1261bd08496f2ce034b5`. Esta revisão trata apenas da validação dos contornos de mobiliário DXF; não amplia tipologias aceitas.

## Escopo suportado

O fluxo `projetar_residencia(pedido)` aceita o piloto de residência térrea compacta com dois quartos comuns, banheiro social, sala, cozinha e lavanderia. Solicitações de três quartos ou de aprovação automática devem ser recusadas, sem reduzir silenciosamente o programa.

Entradas: descrição do programa, terreno e restrições conhecidas. Na ausência de áreas e recuos, os parâmetros usados devem aparecer como **premissas**, nunca como requisitos municipais. O município, endereço/zona e fontes normativas são pendências até que exista um perfil verificável com jurisdição, data, versão e método de conferência.

Entregáveis do fluxo piloto: DXF, PDF A3 e PNG, com URLs de curta duração. O pacote arquitetônico estendido é um conjunto de documentação preliminar para revisão profissional, não um projeto automaticamente aprovado.

## Evidências para aceitação

1. Reabrir o DXF serializado e executar auditoria `ezdxf` e auditoria geométrica.
2. Confrontar vértices e arestas reais de cada polilinha de mobiliário com o retângulo esperado. Quatro vértices corretos **não** bastam se a ordem produzir uma figura cruzada.
3. Reprovar móveis com pontos coincidentes, arestas cruzadas, contornos degenerados e entidades inesperadas na camada `MOBILIARIO`.
4. Manter regressões de paredes espessas, cantos e encontros sem arestas duplicadas, além de aberturas, cotas e conexão dos ambientes.
5. Revisar visualmente cada prancha PDF/PNG na escala indicada; validar proporção, cotas, textos, carimbo e correspondência com DXF. Teste automatizado isolado não equivale à inspeção visual.
6. Rodar `python -m pytest cloud/ezdxf/tests -q`, `python tools/run_plant_lab.py --output out/plant-lab` e `python tools/run_licensing_corpus.py --output out/licensing-corpus`; guardar logs e artefatos.

## Evidência de teste ao vivo pré-correção

- `cad_status`: backend `ezdxf`, versão publicada `0.3.6`, revisão `15fb019da3a77af20e3f1261bd08496f2ce034b5`.
- Uma residência compacta de dois quartos em terreno 10 x 20 m foi gerada; auditoria geométrica `ok=true`, DXF reaberto, 146 entidades, 7/7 ambientes conectados pela aproximação por malha.
- Pedido adversarial com três quartos em terreno 4 x 7 m foi recusado com `INVALID_INPUT` por tipologia não suportada.
- Defeito identificado por inspeção do código: auditoria de móveis comparava conjuntos de vértices, ignorando suas arestas e ordem. Três testes de mutação foram adicionados. **Não há evidência de execução da suíte do branch até o GitHub Actions concluir.**

## Limitações e pendências

A auditoria geométrica ainda partilha o extrator de faces de paredes com o gerador. Isso não equivale a verificação totalmente independente. Circulação é aproximação 2D, e não certificação de acessibilidade; não há declaração de cumprimento de NBR, Código de Obras ou aprovação/licenciamento municipal. Não inferir conformidade de campos vazios, testes verdes, PDFs visualmente corretos ou resposta `ok=true`. Análise por profissional habilitado e verificação das regras específicas de jurisdição são indispensáveis.
