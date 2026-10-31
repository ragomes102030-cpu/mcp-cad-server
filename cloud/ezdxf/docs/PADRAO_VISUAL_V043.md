# MCP CAD Cloud 0.4.3 — hierarquia gráfica e folhas duplas

Atualização implementada **no DXF real**, não por geração de imagem.

- Camadas arquitetônicas recebem cores RGB pouco saturadas e lineweight
  em centésimos de milímetro. PAREDES: 0,50 mm; PORTAS,
  PORTAS-DETALHE, JANELAS, COTAS e TEXTOS: 0,18–0,20 mm;
  MOBILIARIO: 0,13 mm.
- Cada porta no modelo de residência compacta mantém o ARC e LINE
  originais no layer PORTAS, necessários à auditoria física e circulação.
  Uma segunda LINE rigorosamente paralela, deslocada 0,035 m
  perpendicularmente, é criada em PORTAS-DETALHE. Dessa forma o
  desenho apresenta uma folha dupla, sem duplicar a folha física
  usada pelos algoritmos de reconhecimento.
- Cinco portas geram cinco novas entidades gráficas: 180 entidades,
  incluindo 175 originais. As 146 entidades gráficas antigas permanecem.
- Regressão confirma separação perpendicular, paralelismo, 
  manutenção de cinco arcos/folhas reais e topologia DXF reaberta.
- O documento permanece um estudo preliminar. A distância 0,035 m
  é uma **representação gráfica** da folha e não uma especificação de
  porta certificada. Verificar manufatura, ferragens, vãos de passagem
  e norma em projeto executivo.

O código da função `planta_assistida` e os layers são a fonte das
mudanças. O exportador DXF/PDF/PNG não foi substituído.
