# MCP CAD Cloud 0.4.1 — Camadas de medição do DXF residencial

## Objetivo

Um projeto feito por `projetar_residencia` / `planta_criar_validada`
no modelo compacto de 2 quartos agora contém **evidências geométricas
mensuráveis dentro do próprio DXF**, sem exigir que o MCP Custos ou o
agente Arquimedes reconstrua quantidades a partir de frases.

## Camadas reais adicionadas, não imprimíveis

- `EIXOS-PAREDES`: entidades LINE no **eixo de cada TRECHO SÓLIDO
  de parede**, já interrompido em portas/janelas. Uma parede com dois
  vãos é representada por segmentos separados.
- `PISOS`: LWPOLYLINE fechadas para os **retângulos de zonas
  preliminares** mapeadas na planta, inclusive hall. Não têm
  especificação de acabamento, nem necessariamente demonstram
  área útil legal ou superfície pronta para compra de piso.
- Layers têm `off` e `plot=0`; ficam no DXF para medição e **não
  alteram a aparência da planta A3**.

O extrator de quantitativos v1.0 (introduzido em 0.4.0) lê esses
elementos reabertos de DXF. Uma residência piloto 10 × 20 m gerou
**22 eixos de trechos sólidos de parede** e **7 polígonos fechados de
zonas de ambientes**. O comprimento agregado nesse estudo é de
**46,665529 m de eixos de trechos sólidos**, e a soma das áreas
geométricas mapeadas foi de **62,507959 m²**. Esses valores NÃO
representam comprimento bruto de paredes antes de desconto de
aberturas, volume de alvenaria ou quantidade comercial de pisos.

## Auditoria independente

`camadas_medicao.auditar_evidencias_de_medicao`:
- compara os eixos e polígonos reais com o programa apenas como
  uma verificação de correspondência;
- **além disso**, verifica se cada eixo físico está apoiado pelas
  faces reais DXF `PAREDES`, amostrando seções transversais
  nos próprios segmentos, sem chamar `wall_boundary_segments`;
- rejeita entidades faltantes/extras, polígonos abertos/degenerados,
  áreas não retangulares, sobreposição física de zonas e
  eixos sem suporte nos contornos DXF;
- roda dentro de `auditar_dxf_serializado` depois de gravar e
  reabrir o arquivo DXF. Se falhar, a exportação da planta
  por prompt é bloqueada.
- não substitui auditoria completa da topologia de vãos,
  conectividade de toda a rede de paredes e aspectos normativos.

## Evidência / testes

- Testes introduzidos antes da implementação falhavam em **5/5**
  por falta das camadas.
- Após implementação, 31 testes de regressão direcionados passaram.
- Cinco variantes válidas de largura 8,7 a 9,1 m testadas com
  auditoria geométrica real, circulação e medições; mutação
  adversarial removeu todas as faces físicas mantendo eixos, e a
  auditoria independente rejeitou os eixos sem suporte.
- Regressão completa e corpus de licenciamento continuam sendo
  gates obrigatórios de CI para publicação.

## Limites contratuais e próximos passos

- Não há vinculação geométrica auditada de uma porta/janela a uma
  parede **contínua**, nem alturas construtivas verificadas.
  É proibido descontar a mesma abertura uma segunda vez de um
  trecho sólido já segmentado. Os valores de área líquida/volume
  devem permanecer `null` com `DADOS_INSUFICIENTES` até que
  um modelo de paredes brutas e vãos associados seja auditado.
- A área `PISOS` é **preliminar** de zoneamento retangular;
  sem revestimentos, rodapés, materiais, critérios contratuais ou
  identificação de ambiente auditada. Não enviar para compras
  ou orçamento de piso automaticamente.
- Nenhuma alteração de autenticação, URLs ou sessões é feita neste
  PR. O serviço público de testes não deve receber desenhos
  privados; a issue #22 documenta a pendência de segurança.
- Versão `0.4.1` não equivale a projeto executivo ou
  levantamento profissional definitivo.
