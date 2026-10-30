# CAD Cloud 0.4.2 — Reconciliação independente de paredes e vãos

## Por que esta etapa existe
Os 22 eixos de parede da versão 0.4.1 representam **trechos sólidos
segmentados nos vãos**. O somatório desses eixos não constitui metragem
bruta de paredes e sua redução por portas/janelas provocaria duplo
desconto. Esta versão adiciona **auditoria analítica de alinhamentos
contínuos**, obtidos diretamente das entidades DXF reais, sem buscar o
modelo usado pelo gerador.

## Interface MCP (compatível)
A ferramenta pública `quantitativo` continua retornando
`entities`, `by_type`, `by_layer` e
`quantitativos_construtivos`, sem alterar os argumentos existentes.
Adiciona `auditoria_paredes_continuas` com:
- `ok`, `status`, `erros`, `pendencias`, `versao_calculo`;
- `paredes[]`: ID do alinhamento, eixo, ordenada, comprimento
  bruto (m), comprimento dos trechos sólidos (m), handles de origem,
  `vaos[]`, área bruta e líquida quando existirem alturas explícitas,
  e volume geométrico **sempre nulo**;
- `vaos[]`: abertura identificada no intervalo entre trechos,
  tipo `PORTA`/`JANELA`/`VAO_SEM_IDENTIFICACAO`, largura,
  posições, handles dos símbolos reais e altura/área apenas quando
  declaradas;
- `resumo`: alinhamentos, comprimentos reconciliados, portas,
  janelas, aberturas sem identificação.

Os eixos precisam estar na camada `EIXOS-PAREDES` (DXF LINE).
As portas são comprovadas por **ARC + folha LINE** reais na camada
`PORTAS`, com centro, largura e comprimento da folha coerentes.
As janelas exigem **dois LINE de vidro**, equidistantes em lados
opostos do eixo, na camada `JANELAS`. Símbolos soltos/duplicados,
unidades erradas e janelas incompletas invalidam a auditoria.

**Nunca** tratar um vão sem símbolos como porta com 2,10 m de
altura. Aberturas de passagem sem folha exigem classificação e altura
explícitas **vinculadas ao vão**, ainda não disponível. O valor
genérico de altura de passagem, mesmo recebido pelo módulo, não é
atribuído automaticamente a aberturas sem identificação.

## Cálculos / limites
Comprimento bruto de alinhamento =
`comprimento dos trechos sólidos + soma dos vãos reconciliados`.
O algoritmo não une intervalos com gap maior que 1,60 m; nesses
casos informa pendência, em vez de fabricar uma parede contínua.
Altura de parede explícita permite `comprimento bruto × altura`.
Apenas se **todos** os vãos do alinhamento têm símbolos válidos e
alturas fornecidas, pode calcular `área bruta - soma(áreas vãos)`.
Nenhuma estimativa de materiais, custos, composições, BDI ou volume
em encontros é produzida.

Em particular, quando existe a passagem sem folha que liga a área
social ao hall na planta piloto, o alinhamento correspondente tem
`area_liquida_m2=null`. Não se adota altura de porta, pé-direito
nem de passagem como substituto.

A topologia é um algoritmo ortogonal 2D. Não resolve fachadas curvas,
cortes de portas que não apresentam a folha DXF esperada, eixo
estrutural, sobreposição tridimensional, encontros de alvenaria ou
critérios comerciais de medição. O relatório é preliminar e não
constitui projeto executivo, levantamento para compras ou
conformidade normativa.

## Testes de referência
- DXF sintético: parede 4,00 m × 3,00 m = 12,00 m²;
  porta 0,90 × 2,00 = 1,80 m²;
  janela 1,20 × 1,20 = 1,44 m²;
  área líquida independente = **8,76 m²**;
  volume continua nulo.
- Casos adversariais: arco órfão, folha órfã, folha ausente,
  dois arcos coincidentes, janela com uma única face de vidro,
  unidades incorretas, nenhum eixo mensurável.
- Cinco variantes válidas de residência compacta (8,7 a 9,1 m)
  demonstram a reconciliação de cinco portas, seis janelas e uma
  passagem sem identificação, sem mudança da geometria original.
- CI total + benchmark Engenharia 18/18 e corpus 40/40 são
  gates obrigatórios para publicação.

## Integração com MCP Custos
A saída é um **anexo geométrico** ao contrato
`cad-quantitativos-v1.schema.json` (que permanece válido).
Orquestradores podem consumir IDs de paredes e vãos, mas o MCP
Custos deve bloquear preços/quantidades finais quando o status
é `PARCIAL` ou houver falta de vínculo/altura/critério. O código
do MCP Custos que reside no computador do usuário **não foi
inspecionado** nesta etapa; não se afirma interoperabilidade real.
