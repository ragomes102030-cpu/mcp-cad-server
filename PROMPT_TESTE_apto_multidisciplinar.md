> **Instrução ao agente: execute este prompt agora, do começo ao fim, sem pedir confirmação de nada.**
> Se uma ferramenta falhar, registre o erro e siga para a próxima etapa. AutoCAD 2025 já está aberto nesta máquina.

# PROMPT DE TESTE — APARTAMENTO 14,00 × 11,00 — ARQ + ELÉTRICA + HIDRÁULICA

> Versão **adaptada** do prompt do usuário para ser executada por um agente com as 48 ferramentas do
> `mcp-cad-server`. Todas as coordenadas abaixo já foram calculadas e conferidas; o agente **não precisa
> inventar nenhuma**. Leia a seção 0 (o que mudou) só para entender; o serviço começa na seção 1.

---

## 0. O que mudou em relação ao prompt original (e por quê)

| # | Problema no prompt original | Correção aplicada |
|---|------------------------------|-------------------|
| 1 | COZINHA (10–14 × 8–11), VARANDA (12–14 × 8–11) e BANHEIRO SUÍTE (10–12 × 8–11) ocupavam o mesmo retângulo: 24 m² de programa dentro de 12 m² de área. | A faixa superior (y 8–11) virou 5 ambientes que se encaixam: HALL, SUÍTE, BANHEIRO, COZINHA e VARANDA. Nenhuma sobreposição; soma fecha 154,00 m². |
| 2 | P1 (porta externa, x=0, y 8,5) caía **dentro** do vão de J1 (janela, y 7,5–9,5). | P1 foi para y 9,10–9,90; J1 saiu da fachada x=0 (lado da circulação do prédio) para a fachada y=0. |
| 3 | Drywall em x=6 de y=6 a y=11 atravessava a circulação. | x=6 só existe de y=8 a 11 (parede do banheiro). |
| 4 | Drywall em y=2 de x=0 a 4 cortava o QUARTO 2 ao meio (contra os 24,00 m²). | Removido. O QUARTO 2 é um ambiente único. |
| 5 | T-SA3 em (6,0; 11,4) estava fora da planta (y máximo = 11). | Todos os pontos estão dentro dos ambientes (conferido). |
| 6 | I-VA e I-BSU na mesma coordenada (12,2; 8,5) — dois dispositivos no mesmo ponto. | Não existe mais nenhum par de pontos a menos de 0,05 m (teste T10). |
| 7 | "INT_CONFLITO vermelho piscante". | Não existe piscante em CAD estático: a camada é vermelha **tracejada** (DASHED). |
| 8 | Prumadas em (9,0;2,5), (9,5;2,5) e (9,0;2,0) caíam no meio da sala. | Foram para a parede hidráulica x=8 (entre banheiro e cozinha), onde prumada faz sentido. |
| 9 | 11 portas e 9 janelas sem coordenadas executáveis. | P1–P11 e J1–J9 com vão, dobradiça e arco tabelados. |
| 10 | 3 dormitórios e apenas 1 banheiro (só o BANHEIRO SUÍTE do prompt). | Mantido 1 banheiro, como no original, mas ligado à suíte. Registrar no relatório como pendência de programa. |

**Área:** 9 ambientes somando exatamente **154,00 m² entre eixos** (14,00 × 11,00).

---

## 1. Objetivo

Desenhar, em **um único arquivo** e em **um único pavimento**, a planta baixa de um apartamento de
14,00 m × 11,00 m com **três disciplinas sobrepostas**, cada uma na sua própria camada:

- **Arquitetura** — paredes, portas, janelas, textos de ambiente e áreas.
- **Elétrica** — 45 pontos (12 de luz, 20 tomadas, 13 interruptores) + 1 quadro de distribuição.
- **Hidráulica** — 13 pontos (5 AF, 3 AQ, 5 ESG) + 3 prumadas.
- **Interferência** — conferência ELE × HID e marcação dos conflitos.

Escala de desenho **1:50**, unidades **metros** (INSUNITS = 6), caráter **PRELIMINAR**.
Entregar DWG + DXF + PDF e um relatório de execução.

**Tudo é preliminar.** O desenho serve para testar as ferramentas, não para construir.

---

## 2. Regras invioláveis

1. **Não invente coordenadas.** Use exatamente as tabelas A–H. Se algum número faltar, pare e escreva
   no relatório — não "chute".
2. **Use as ferramentas tipadas** do MCP (`entity_create_line`, `entity_create_rectangle`,
   `entity_create_circle`, `entity_create_arc`, `entity_create_text`, `dimension_linear`, …).
   **Não** desenhe geometria por `system_run_command` nem por `script`. O objetivo é testar as ferramentas
   tipadas; a única exceção autorizada é carregar o tipo de linha DASHED (passo 2.3).
3. **Parede é `entity_create_rectangle`** (polilinha fechada), não quatro linhas soltas. É isso que
   garante o vão fechado nas portas e janelas: cada retângulo já termina com o "batente" desenhado.
4. **Uma disciplina por camada.** Passe `layer=` em **todas** as criações. Antes de cada bloco, chame
   também `layer_set_current` para a camada da disciplina.
5. **Não apague, não mova, não rotacione** nada depois de criado. Se um teste falhar, registre; só
   corrija se o erro for de coordenada digitada errada (aí use `entity_erase` do id errado e refaça).
6. Se uma ferramenta devolver erro, **copie o texto do erro** no relatório e siga. Não tente
   contornar com ferramenta que não existe.
7. Texto: `entity_create_text` usa o **canto esquerdo da base** (não é centralizado). As tabelas já dão
   o x já descontado para o texto ficar centralizado. Use a altura indicada.

---

## 3. Ferramentas que serão usadas (assinaturas exatas)

```
drawing_new(name: str|None = None)
drawing_setup(unidades: int = 6, escala_cota: float = 0.1, ltscale: float = 0.2)
layer_create(name: str, color: int|str = 7, linetype: str = "CONTINUOUS")
layer_set_current(name: str)
layer_list()
linetype_load(nome: str, arquivo: str = "acad.lin")
entity_create_rectangle(x1, y1, x2, y2, layer=None)
entity_create_line(x1, y1, x2, y2, layer=None)
entity_create_circle(cx, cy, radius, layer=None)
entity_create_arc(cx, cy, radius, start_angle, end_angle, layer=None)
entity_create_text(x, y, text, height=2.5, rotation=0.0, layer=None)
dimension_linear(x1, y1, x2, y2, dim_x, dim_y)
entity_list(layer=None, tipo=None)
quantitativo(layer=None)
entity_erase(entity_id)
mirror_filter(layer=None, tipo=None, x1=None, y1=None, x2=None, y2=None)
rotate_filter(layer=None, tipo=None, x=0.0, y=0.0, angulo=0.0)
system_run_command(text)
drawing_info()
drawing_save(path=None)
drawing_save_as_dxf(path)
drawing_export_dxf(path)
drawing_export_pdf(path)
plot_pdf(path, folha=None, escala=None)
drawing_open(path)
view_zoom_extents()
view_render_png(path=None)
```

`mirror_filter` espelha e `rotate_filter` gira em bloco (**sem duplicar**) as entidades do
modelo que casarem com `layer=`/`tipo=`; `x1,y1,x2,y2` é o eixo do espelho e `x,y,angulo` o
centro e o ângulo (graus) do giro — os dois obedecem a esses parâmetros, então não gaste
tempo procurando o nome deles.

`plot_pdf(path, folha="A2", escala=50)` é o único jeito de sair **em escala real**: ele lê a
extensão do modelo, converte pelas unidades do desenho e escolhe a folha. `drawing_export_pdf`
segue existindo, mas plota "ajustar à folha" (escala imprevisível) — use só como comparação.

**Não** existe hachura por camada, criação em lote, nem "piscante". Não invente nomes: se
precisar de algo que não está aqui, registre no relatório.

---

## 4. Sequência de execução

### 4.1 Preparação
1. `drawing_new("apto_14x11_multidisciplinar")`
2. `drawing_setup(unidades=6, escala_cota=0.1)` → unidades em metros, texto de cota com 0,25 m
   (5 mm impressos em 1:50).
3. Criar as 15 camadas da Tabela de camadas (seção 5.1) com `layer_create`.
4. Testar DASHED: `linetype_load("DASHED")` e depois `layer_create("INT_CONFLITO", 1, "DASHED")`.
   Se o tipo de linha não entrar, crie a camada com `CONTINUOUS` e anote no relatório. **Não** use
   `system_run_command("_.-LINETYPE ...")`: no AutoCAD o `-LINETYPE _LOAD` pede um ENTER extra e
   trava o prompt (todas as chamadas seguintes voltam "Call was rejected by callee").

### 4.2 Arquitetura (camadas ARQ_*)
5. `layer_set_current("ARQ_PAREDE")` → **35 retângulos** da Tabela A.
6. `layer_set_current("ARQ_ESQUADRIA")` → **12 folhas de porta** (Tabela B, coluna "ponta da folha"),
   **12 arcos** (Tabela B, coluna do arco) e **18 linhas de peitoril** (Tabela C).
7. `layer_set_current("ARQ_TEXTO")` → **18 textos** de ambiente da Tabela F (9 nomes + 9 áreas) e os
   **3 textos fixos** de título/escala/normas (Tabela H).

### 4.3 Elétrica (camadas ELE_*)
8. `layer_set_current("ELE_ILUM")` → 12 círculos r=0,15 (Tabela D, linhas com camada ELE_ILUM).
9. `layer_set_current("ELE_TOMADA")` → 20 círculos r=0,10.
10. `layer_set_current("ELE_INT")` → 13 círculos r=0,08.
11. `layer_set_current("ELE_QUADRO")` → 1 retângulo (0,30;7,70)-(0,90;7,94) + 1 texto "QD" em
    (0,42;7,74), altura 0,12.

### 4.4 Hidráulica (camadas HID_*)
12. `layer_set_current("HID_AF")` → 5 círculos r=0,10 (Tabela E).
13. `layer_set_current("HID_AQ")` → 3 círculos r=0,10.
14. `layer_set_current("HID_ESG")` → 5 círculos r=0,10.
15. `layer_set_current("HID_PRUMADA")` → 3 círculos r=0,15 + o "X" de 2 linhas por prumada.

### 4.5 Interferência (camada INT_CONFLITO)
16. Fazer a conferência da seção 6 **antes** de desenhar.
17. Para cada par com distância **< 0,50 m**: 1 círculo r=0,40 no ponto médio e 1 texto "CONFLITO"
    (altura 0,12) deslocado (0,10; +0,42) do centro.
18. Tabela G é a **resposta conferida** — use-a para validar o seu resultado. Se você encontrar um
    conjunto diferente, refaça a conta antes de desenhar e registre a divergência.

### 4.6 Cotas, legenda e carimbo
19. `layer_set_current("COTA")` → 9 cotas (seção 5.3).
20. `layer_set_current("LEGENDA")` → retângulo (15;4,5)-(22;10) + 12 textos da Tabela H.
21. `layer_set_current("CARIMBO")` → retângulo (15;0)-(22;3) + 8 textos da Tabela H.
22. `view_zoom_extents()` e `view_render_png()` (guarde o caminho da imagem).

### 4.7 Entrega

Salve **numa pasta só sua**, criada por você (nunca na pasta de entrega de outro agente — dois
agentes escrevendo no mesmo arquivo apagam o resultado um do outro). Use como `SAIDA`:

`C:\Users\Correta Engenharia\Desktop\Apto 14x11 - <tag da sua conversa>`

23. `drawing_save(SAIDA\apto_14x11_multidisciplinar.dwg)`
24. `drawing_export_dxf(SAIDA\apto_14x11_multidisciplinar.dxf)`
25. `plot_pdf(SAIDA\apto_14x11_multidisciplinar.pdf, folha="A2", escala=50)`
26. Rodar os testes T1–T12 e escrever o relatório dentro de `SAIDA`.

Se a pasta não existir e o `drawing_save` falhar, salve na Desktop
(`C:\Users\Correta Engenharia\Desktop\apto_14x11_multidisciplinar.dwg`) e **diga isso no relatório**.

---

## 5. Geometria (dados prontos)

### 5.1 Camadas — 15

| camada | cor | tipo de linha | conteúdo |
|--------|-----|---------------|----------|
| ARQ_PAREDE | 7 | CONTINUOUS | 35 retângulos de parede |
| ARQ_ESQUADRIA | 4 | CONTINUOUS | 30 linhas + 12 arcos |
| ARQ_TEXTO | 2 | CONTINUOUS | 21 textos |
| COTA | 3 | CONTINUOUS | 9 cotas |
| ELE_ILUM | 2 | CONTINUOUS | 12 círculos r=0,15 |
| ELE_TOMADA | 4 | CONTINUOUS | 20 círculos r=0,10 |
| ELE_INT | 3 | CONTINUOUS | 13 círculos r=0,08 |
| ELE_QUADRO | 6 | CONTINUOUS | 1 retângulo + 1 texto |
| HID_AF | 5 | CONTINUOUS | 5 círculos r=0,10 |
| HID_AQ | 1 | CONTINUOUS | 3 círculos r=0,10 |
| HID_ESG | 6 | CONTINUOUS | 5 círculos r=0,10 |
| HID_PRUMADA | 6 | CONTINUOUS | 3 círculos r=0,15 + 6 linhas |
| INT_CONFLITO | 1 | DASHED | 3 círculos r=0,40 + 3 textos |
| LEGENDA | 7 | CONTINUOUS | 1 retângulo + 12 textos |
| CARIMBO | 7 | CONTINUOUS | 1 retângulo + 8 textos |

### 5.2 Ambientes (para conferência das áreas e dos textos)

| ambiente | faces internas (x1;y1)–(x2;y2) | área entre eixos |
|----------|-------------------------------|------------------|
| QUARTO 2 | (0,20;0,20)–(3,94;5,94) | 24,00 m² |
| QUARTO 1 | (4,06;0,20)–(7,94;5,94) | 24,00 m² |
| CIRCULAÇÃO | (0,20;6,06)–(7,94;7,94) | 16,00 m² |
| SALA | (8,06;0,20)–(13,80;7,94) | 48,00 m² |
| HALL | (0,20;8,06)–(1,94;10,80) | 6,00 m² |
| SUÍTE | (2,06;8,06)–(5,94;10,80) | 12,00 m² |
| BANHEIRO | (6,06;8,06)–(7,94;10,80) | 6,00 m² |
| COZINHA | (8,06;8,06)–(11,94;10,80) | 12,00 m² |
| VARANDA | (12,06;8,06)–(13,80;10,80) | 6,00 m² |
| **TOTAL** | 14,00 × 11,00 | **154,00 m²** |

### 5.3 Cotas — 9 `dimension_linear`

| # | de | até | dim_x | dim_y |
|---|----|-----|-------|-------|
| 1 | (0;0) | (4;0) | 2 | −1,20 |
| 2 | (4;0) | (8;0) | 6 | −1,20 |
| 3 | (8;0) | (12;0) | 10 | −1,20 |
| 4 | (12;0) | (14;0) | 13 | −1,20 |
| 5 | (0;0) | (14;0) | 7 | −2,20 |
| 6 | (0;0) | (0;6) | −1,20 | 3 |
| 7 | (0;6) | (0;8) | −1,20 | 7 |
| 8 | (0;8) | (0;11) | −1,20 | 9,5 |
| 9 | (0;0) | (0;11) | −2,20 | 5,5 |

### Tabela A — paredes: 35 retângulos (camada ARQ_PAREDE)

| # | parede | x1 | y1 | x2 | y2 |
|---|--------|----|----|----|----|
| R01 | E1 | 0 | 0 | 1 | 0.2 |
| R02 | E1 | 2.5 | 0 | 4.8 | 0.2 |
| R03 | E1 | 6.3 | 0 | 9 | 0.2 |
| R04 | E1 | 11 | 0 | 11.6 | 0.2 |
| R05 | E1 | 13.6 | 0 | 14 | 0.2 |
| R06 | E2 | 13.8 | 0.2 | 14 | 2 |
| R07 | E2 | 13.8 | 5 | 14 | 9.1 |
| R08 | E2 | 13.8 | 9.9 | 14 | 10.8 |
| R09 | E3 | 0 | 10.8 | 2.6 | 11 |
| R10 | E3 | 4.4 | 10.8 | 6.4 | 11 |
| R11 | E3 | 7.6 | 10.8 | 8.8 | 11 |
| R12 | E3 | 10.4 | 10.8 | 12.4 | 11 |
| R13 | E3 | 13.6 | 10.8 | 14 | 11 |
| R14 | E4 | 0 | 0.2 | 0.2 | 9.1 |
| R15 | E4 | 0 | 9.9 | 0.2 | 10.8 |
| R16 | V1 | 3.94 | 0.2 | 4.06 | 5.94 |
| R17 | V2 | 7.94 | 0.2 | 8.06 | 6.6 |
| R18 | V2 | 7.94 | 7.4 | 8.06 | 7.94 |
| R19 | V3 | 1.94 | 8.06 | 2.06 | 10.8 |
| R20 | V4 | 5.94 | 8.06 | 6.06 | 9.1 |
| R21 | V4 | 5.94 | 9.9 | 6.06 | 10.8 |
| R22 | V5 | 7.94 | 8.06 | 8.06 | 10.8 |
| R23 | V6 | 11.94 | 8.06 | 12.06 | 9.1 |
| R24 | V6 | 11.94 | 9.9 | 12.06 | 10.8 |
| R25 | H1 | 0.2 | 5.94 | 0.6 | 6.06 |
| R26 | H1 | 1.4 | 5.94 | 4.6 | 6.06 |
| R27 | H1 | 5.4 | 5.94 | 7.94 | 6.06 |
| R28 | H2 | 0.2 | 7.94 | 0.6 | 8.06 |
| R29 | H2 | 1.4 | 7.94 | 1.94 | 8.06 |
| R30 | H3 | 2.06 | 7.94 | 2.6 | 8.06 |
| R31 | H3 | 3.4 | 7.94 | 5.94 | 8.06 |
| R32 | H4 | 6.06 | 7.94 | 7.94 | 8.06 |
| R33 | H5 | 8.06 | 7.94 | 9.5 | 8.06 |
| R34 | H5 | 10.3 | 7.94 | 12.4 | 8.06 |
| R35 | H5 | 13.6 | 7.94 | 13.8 | 8.06 |

### Tabela B — portas: 12 folhas + 12 arcos (camada ARQ_ESQUADRIA)

| porta | dobradiça (x;y) | ponta da folha (x;y) | arco: centro (x;y) | raio | ângulo inicial → final |
|-------|-----------------|----------------------|--------------------|------|------------------------|
| P1 | (0.2; 9.1) | (1; 9.1) | (0.2; 9.1) | 0.8 | 0 → 90 |
| P2 | (0.6; 8.06) | (0.6; 8.86) | (0.6; 8.06) | 0.8 | 0 → 90 |
| P3 | (1.4; 5.94) | (1.4; 5.14) | (1.4; 5.94) | 0.8 | 180 → 270 |
| P4 | (5.4; 5.94) | (5.4; 5.14) | (5.4; 5.94) | 0.8 | 180 → 270 |
| P5 | (2.6; 8.06) | (2.6; 8.86) | (2.6; 8.06) | 0.8 | 0 → 90 |
| P6 | (6.06; 9.1) | (6.86; 9.1) | (6.06; 9.1) | 0.8 | 0 → 90 |
| P7 | (8.06; 6.6) | (8.86; 6.6) | (8.06; 6.6) | 0.8 | 0 → 90 |
| P8 | (9.5; 8.06) | (9.5; 8.86) | (9.5; 8.06) | 0.8 | 0 → 90 |
| P9 | (12.06; 9.1) | (12.86; 9.1) | (12.06; 9.1) | 0.8 | 0 → 90 |
| P10a | (12.4; 7.94) | (12.4; 7.34) | (12.4; 7.94) | 0.6 | 270 → 360 |
| P10b | (13.6; 7.94) | (13.6; 7.34) | (13.6; 7.94) | 0.6 | 180 → 270 |
| P11 | (13.8; 9.9) | (13; 9.9) | (13.8; 9.9) | 0.8 | 180 → 270 |

### Tabela C — janelas: 9 vãos, 2 linhas de peitoril por vão (camada ARQ_ESQUADRIA)

| janela | parede | vão de (x ou y) | até | linhas paralelas à face |
|--------|--------|------------------|-----|--------------------------|
| J1 | E1 | 1 | 2.5 | de (1; 0.06) a (2.5; 0.06)  e  de (1; 0.14) a (2.5; 0.14) |
| J2 | E1 | 4.8 | 6.3 | de (4.8; 0.06) a (6.3; 0.06)  e  de (4.8; 0.14) a (6.3; 0.14) |
| J3 | E1 | 9 | 11 | de (9; 0.06) a (11; 0.06)  e  de (9; 0.14) a (11; 0.14) |
| J4 | E1 | 11.6 | 13.6 | de (11.6; 0.06) a (13.6; 0.06)  e  de (11.6; 0.14) a (13.6; 0.14) |
| J5 | E3 | 2.6 | 4.4 | de (2.6; 10.86) a (4.4; 10.86)  e  de (2.6; 10.94) a (4.4; 10.94) |
| J6 | E3 | 6.4 | 7.6 | de (6.4; 10.86) a (7.6; 10.86)  e  de (6.4; 10.94) a (7.6; 10.94) |
| J7 | E3 | 8.8 | 10.4 | de (8.8; 10.86) a (10.4; 10.86)  e  de (8.8; 10.94) a (10.4; 10.94) |
| J8 | E3 | 12.4 | 13.6 | de (12.4; 10.86) a (13.6; 10.86)  e  de (12.4; 10.94) a (13.6; 10.94) |
| J9 | E2 | 2 | 5 | de (13.86; 2) a (13.86; 5)  e  de (13.94; 2) a (13.94; 5) |

### Tabela D — pontos elétricos: 45 círculos + 1 quadro (camadas ELE_*)

| # | camada | nome | x | y | ambiente |
|---|--------|------|----|----|----------|
| 1 | ELE_ILUM | L1 | 10.5 | 3.2 | SALA |
| 2 | ELE_ILUM | L2 | 12.5 | 5.5 | SALA |
| 3 | ELE_ILUM | L3 | 9.5 | 6 | SALA |
| 4 | ELE_TOMADA | T1 | 8.4 | 0.55 | SALA |
| 5 | ELE_TOMADA | T2 | 10.5 | 0.55 | SALA |
| 6 | ELE_TOMADA | T3 | 13.45 | 2.6 | SALA |
| 7 | ELE_TOMADA | T4 | 13.45 | 6.5 | SALA |
| 8 | ELE_TOMADA | T5 | 8.4 | 7.55 | SALA |
| 9 | ELE_INT | S6 | 8.4 | 6.2 | SALA |
| 10 | ELE_INT | S7 | 9.2 | 7.6 | SALA |
| 11 | ELE_ILUM | L7 | 2 | 3 | QUARTO 2 |
| 12 | ELE_TOMADA | T12 | 0.55 | 1.5 | QUARTO 2 |
| 13 | ELE_TOMADA | T13 | 0.55 | 5 | QUARTO 2 |
| 14 | ELE_TOMADA | T14 | 3.55 | 5.3 | QUARTO 2 |
| 15 | ELE_INT | S11 | 1.6 | 5.6 | QUARTO 2 |
| 16 | ELE_ILUM | L8 | 6 | 3 | QUARTO 1 |
| 17 | ELE_TOMADA | T15 | 7.55 | 1.5 | QUARTO 1 |
| 18 | ELE_TOMADA | T16 | 7.55 | 5 | QUARTO 1 |
| 19 | ELE_TOMADA | T17 | 4.45 | 5.3 | QUARTO 1 |
| 20 | ELE_INT | S12 | 5.2 | 5.6 | QUARTO 1 |
| 21 | ELE_ILUM | L12 | 4 | 7 | CIRCULAÇÃO |
| 22 | ELE_INT | S3 | 2.1 | 6.3 | CIRCULAÇÃO |
| 23 | ELE_INT | S4 | 5.9 | 6.3 | CIRCULAÇÃO |
| 24 | ELE_INT | S5 | 2.35 | 7.6 | CIRCULAÇÃO |
| 25 | ELE_ILUM | L11 | 1.05 | 9.4 | HALL |
| 26 | ELE_INT | S1 | 0.55 | 10.3 | HALL |
| 27 | ELE_INT | S2 | 1.6 | 8.4 | HALL |
| 28 | ELE_ILUM | L9 | 4 | 9.4 | SUÍTE |
| 29 | ELE_TOMADA | T18 | 2.35 | 10.5 | SUÍTE |
| 30 | ELE_TOMADA | T19 | 5.55 | 10.5 | SUÍTE |
| 31 | ELE_INT | S10 | 3.6 | 8.4 | SUÍTE |
| 32 | ELE_ILUM | L10 | 7 | 9.4 | BANHEIRO |
| 33 | ELE_TOMADA | T20 | 7.6 | 9.6 | BANHEIRO |
| 34 | ELE_INT | S13 | 6.3 | 9.3 | BANHEIRO |
| 35 | ELE_ILUM | L4 | 9.6 | 9.4 | COZINHA |
| 36 | ELE_ILUM | L5 | 11.2 | 9.4 | COZINHA |
| 37 | ELE_TOMADA | T6 | 8.4 | 10.55 | COZINHA |
| 38 | ELE_TOMADA | T7 | 9.8 | 10.55 | COZINHA |
| 39 | ELE_TOMADA | T8 | 11.55 | 10.55 | COZINHA |
| 40 | ELE_TOMADA | T9 | 8.4 | 8.4 | COZINHA |
| 41 | ELE_TOMADA | T10 | 10.4 | 8.4 | COZINHA |
| 42 | ELE_INT | S8 | 11.55 | 9 | COZINHA |
| 43 | ELE_ILUM | L6 | 13 | 9.4 | VARANDA |
| 44 | ELE_TOMADA | T11 | 13.45 | 8.4 | VARANDA |
| 45 | ELE_INT | S9 | 12.4 | 8.4 | VARANDA |

Quadro de distribuição QD: retângulo (0.3; 7.7) a (0.9; 7.94) na camada ELE_QUADRO.

### Tabela E — pontos hidráulicos: 13 círculos + 3 prumadas (camadas HID_*)

| # | camada | nome | x | y | ambiente |
|---|--------|------|----|----|----------|
| 1 | HID_AF | AF1 | 6.4 | 10.45 | BANHEIRO |
| 2 | HID_AQ | AQ1 | 6.4 | 10.15 | BANHEIRO |
| 3 | HID_AF | AF2 | 7.5 | 10.45 | BANHEIRO |
| 4 | HID_AQ | AQ2 | 7.5 | 10.15 | BANHEIRO |
| 5 | HID_ESG | ESG1 | 7.5 | 8.5 | BANHEIRO |
| 6 | HID_ESG | ESG2 | 6.4 | 8.5 | BANHEIRO |
| 7 | HID_AF | AF3 | 9.2 | 10.6 | COZINHA |
| 8 | HID_AQ | AQ3 | 9.2 | 10.3 | COZINHA |
| 9 | HID_ESG | ESG3 | 9.2 | 10 | COZINHA |
| 10 | HID_AF | AF4 | 13.45 | 10.55 | VARANDA |
| 11 | HID_ESG | ESG4 | 13.45 | 10.25 | VARANDA |
| 12 | HID_AF | AF5 | 12.55 | 10.55 | VARANDA |
| 13 | HID_ESG | ESG5 | 12.6 | 8.5 | VARANDA |

Prumadas (camada HID_PRUMADA): círculo r=0,15 + X de 0,30 (2 linhas) em
- PR-AQ: centro (8; 8.6); X de (7.85; 8.45) a (8.15; 8.75) e de (7.85; 8.75) a (8.15; 8.45)
- PR-AF: centro (8; 9.1); X de (7.85; 8.95) a (8.15; 9.25) e de (7.85; 9.25) a (8.15; 8.95)
- PR-ESG: centro (8; 9.6); X de (7.85; 9.45) a (8.15; 9.75) e de (7.85; 9.75) a (8.15; 9.45)

### Tabela F — textos dos ambientes: 18 (camada ARQ_TEXTO)

| texto | x (canto esq.) | y (base) | altura |
|-------|----------------|----------|--------|
| QUARTO 2 | 1.4 | 3.37 | 0.18 |
| 24,00 m² | 1.59 | 2.62 | 0.13 |
| QUARTO 1 | 5.33 | 3.37 | 0.18 |
| 24,00 m² | 5.52 | 2.62 | 0.13 |
| CIRCULAÇÃO | 3.23 | 7.3 | 0.18 |
| 16,00 m² | 3.59 | 6.55 | 0.13 |
| SALA DE ESTAR/JANTAR | 9.25 | 4.37 | 0.18 |
| 48,00 m² | 10.45 | 3.62 | 0.13 |
| HALL | 0.77 | 9.73 | 0.16 |
| 6,00 m² | 0.65 | 8.98 | 0.13 |
| SUÍTE | 3.58 | 9.73 | 0.18 |
| 12,00 m² | 3.52 | 8.98 | 0.13 |
| BANHEIRO | 6.4 | 9.73 | 0.16 |
| 6,00 m² | 6.58 | 8.98 | 0.13 |
| COZINHA | 9.41 | 9.73 | 0.18 |
| 12,00 m² | 9.52 | 8.98 | 0.13 |
| VARANDA | 12.34 | 9.73 | 0.18 |
| 6,00 m² | 12.51 | 8.98 | 0.13 |

### Tabela G — interferências encontradas: 3

| # | ponto elétrico | ponto hidráulico | distância (m) | centro do círculo INT_CONFLITO |
|---|----------------|------------------|---------------|--------------------------------|
| 1 | S9 | ESG5 | 0.224 | (12.5; 8.45) |
| 2 | T20 | PR-ESG | 0.400 | (7.8; 9.6) |
| 3 | T9 | PR-AQ | 0.447 | (8.2; 8.5) |

### Tabela H — textos fixos: título, notas, legenda (12) e carimbo (8)

| camada | texto | x | y (base) | altura |
|--------|-------|---|----------|--------|
| ARQ_TEXTO | APARTAMENTO 14,00 x 11,00 - PLANTA BAIXA MULTIDISCIPLINAR | 0 | 12 | 0.3 |
| ARQ_TEXTO | ESCALA 1:50 - PRELIMINAR - MEDIDAS ENTRE EIXOS | 0 | 11.5 | 0.2 |
| ARQ_TEXTO | NORMAS: NBR 5410 (elétrica) / NBR 5626 (água) / NBR 8160 (esgoto) | 0 | -3.2 | 0.18 |
| LEGENDA | LEGENDA | 15.25 | 9.6 | 0.22 |
| LEGENDA | ARQ_PAREDE - paredes ext. 0,20 / int. 0,12 | 15.25 | 9.15 | 0.14 |
| LEGENDA | ARQ_ESQUADRIA - portas e janelas | 15.25 | 8.77 | 0.14 |
| LEGENDA | ELE_ILUM - ponto de luz (círculo r=0,15) | 15.25 | 8.39 | 0.14 |
| LEGENDA | ELE_TOMADA - tomada (círculo r=0,10) | 15.25 | 8.01 | 0.14 |
| LEGENDA | ELE_INT - interruptor (círculo r=0,08) | 15.25 | 7.63 | 0.14 |
| LEGENDA | ELE_QUADRO - quadro de distribuição | 15.25 | 7.25 | 0.14 |
| LEGENDA | HID_AF / HID_AQ / HID_ESG - água (r=0,10) | 15.25 | 6.87 | 0.14 |
| LEGENDA | HID_PRUMADA - prumada (r=0,15 + X) | 15.25 | 6.49 | 0.14 |
| LEGENDA | INT_CONFLITO - ELE x HID < 0,50 m | 15.25 | 6.11 | 0.14 |
| LEGENDA | círculo tracejado = interferência | 15.25 | 5.73 | 0.14 |
| LEGENDA | cotas em metros; áreas entre eixos | 15.25 | 5.35 | 0.14 |
| CARIMBO | PROJETO: APARTAMENTO TIPO - 3 DORMITÓRIOS | 15.25 | 2.55 | 0.14 |
| CARIMBO | DISCIPLINAS: ARQUITETURA / ELÉTRICA / HIDRÁULICA | 15.25 | 2.2 | 0.14 |
| CARIMBO | ESCALA 1:50   FOLHA A2   DATA 16/10/2026 | 15.25 | 1.85 | 0.14 |
| CARIMBO | REV 00 - PRELIMINAR | 15.25 | 1.5 | 0.14 |
| CARIMBO | NORMAS: NBR 5410 / NBR 5626 / NBR 8160 | 15.25 | 1.15 | 0.14 |
| CARIMBO | ÁREA (EIXOS): 154,00 m² | 15.25 | 0.8 | 0.14 |
| CARIMBO | DESENHADO POR AGENTE CAD (MCP) - CONFERIR | 15.25 | 0.45 | 0.14 |
| CARIMBO | PRANCHA 01/01 | 15.25 | 0.12 | 0.12 |

Molduras: LEGENDA (15;4.5)-(22;10)  e  CARIMBO (15;0)-(22;3), camada própria de cada uma.

### Tabela I — quantitativo previsto por camada

| camada | entidades | o que é |
|--------|-----------|---------|
| ARQ_PAREDE | 35 | retângulos (polilinhas fechadas) |
| ARQ_ESQUADRIA | 30 | linhas (12 folhas + 18 peitoris) |
| ARQ_ESQUADRIA | 12 | arcos de porta |
| ARQ_TEXTO | 21 | textos (18 ambientes + título + escala + normas) |
| COTA | 9 | cotas lineares |
| ELE_ILUM | 12 | círculos r=0,15 |
| ELE_TOMADA | 20 | círculos r=0,10 |
| ELE_INT | 13 | círculos r=0,08 |
| ELE_QUADRO | 2 | 1 retângulo + 1 texto |
| HID_AF | 5 | círculos r=0,10 |
| HID_AQ | 3 | círculos r=0,10 |
| HID_ESG | 5 | círculos r=0,10 |
| HID_PRUMADA | 9 | 3 círculos r=0,15 + 6 linhas (X) |
| INT_CONFLITO | 6 | 3 círculos r=0,40 tracejados + 3 textos |
| LEGENDA | 13 | 1 retângulo + 12 textos |
| CARIMBO | 9 | 1 retângulo + 8 textos |

Total de entidades: 204.


---

## 6. Conferência de interferência ELE × HID

Critério: **ponto elétrico × ponto hidráulico com distância < 0,50 m**.
Prumadas contam como ponto hidráulico. Só precisam ser calculados os pares abaixo (o resto está longe):

| conjunto | pontos elétricos | pontos hidráulicos | pares |
|----------|------------------|--------------------|-------|
| BANHEIRO | L10, T20, S13 (3) | AF1, AQ1, AF2, AQ2, ESG1, ESG2 (6) | 18 |
| COZINHA | L4, L5, T6, T7, T8, T9, T10, S8 (8) | AF3, AQ3, ESG3 (3) | 24 |
| VARANDA | L6, T11, S9 (3) | AF4, ESG4, AF5, ESG5 (4) | 12 |
| contra prumadas | L10, T20, S13, L4, L5, T6, T7, T8, T9, T10, S8 (11) | PR-AQ, PR-AF, PR-ESG (3) | 33 |

Total: 87 distâncias. Calcule com 3 casas decimais, liste **todos** os pares < 0,50 m no relatório
(nome dos dois pontos, distância) e desenhe um marcador por par. Espera-se um número pequeno
(entre 1 e 5); se der muito mais, refaça a conta.

Antes de marcar, confira também que **nenhum** par de pontos (ELE ou HID) está a menos de 0,05 m —
isso indicaria dispositivo duplicado.

---

## 7. Testes de aceitação

| # | teste | critério de PASS |
|---|-------|------------------|
| T1 | `drawing_info()` | INSUNITS = 6; nome do arquivo = apto_14x11_multidisciplinar |
| T2 | `layer_list()` | as 15 camadas existem, com as cores da Tabela 5.1 |
| T3 | `quantitativo()` por camada | igual à Tabela I, entidade por entidade; total = 204 |
| T4 | `entity_list(layer="ARQ_PAREDE")` | 35 polilinhas fechadas |
| T5 | `entity_list(layer="ARQ_ESQUADRIA")` | 12 ARC + 30 LINE |
| T6 | `quantitativo` de ELE_* | 12 + 20 + 13 + 2 |
| T7 | `quantitativo` de HID_* | 5 + 3 + 5 + 9 |
| T8 | `quantitativo` de INT_CONFLITO | 3 círculos + 3 textos = 6 (ou igual ao nº de pares do relatório) |
| T9 | `view_zoom_extents` + `view_render_png` | a imagem mostra a planta fechada (0–14 × 0–11), legenda e carimbo, sem nada solto |
| T10 | duplicidade | nenhum par de pontos a menos de 0,05 m |
| T11 | DXF e PDF | os dois arquivos existem e têm mais de 0 byte; o PDF tem 1 página em **A2 paisagem (594 × 420 mm)** e a escala **medida** (conteúdo em mm ÷ extensão do modelo) fica em 1:50 ±2 %, não "ajustar à folha" |
| T12 | `drawing_open` no DXF exportado | abre e o quantitativo total continua 204 |

---

## 8. Relatório final (formato)

1. **Resultado por teste**: tabela T1–T12 com PASS/FAIL e o número que você leu (não "ok").
2. **Interferências**: tabela com os pares < 0,50 m e a distância calculada.
3. **Divergências**: qualquer entidade que não bateu com a Tabela I, com o motivo.
4. **Falhas de ferramenta**: comando, argumento, mensagem de erro exata e o que você fez.
5. **Ferramentas que faltaram** (ex.: batch de criação, hachura por camada).
6. **Contagem de chamadas** de ferramenta usadas e tempo aproximado.
7. **Caminhos** dos arquivos gerados (DWG, DXF, PDF, PNG).

Seja literal. Um PASS que não foi medido é pior que um FAIL bem descrito.
