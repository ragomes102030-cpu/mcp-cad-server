# Prompt de teste — pavimento tipo de prédio (2 apartamentos espelhados)

> **Como usar.** Abra uma conversa nova com o MCP `mcp-cad-server` reiniciado
> (**45 ferramentas**) e mande o bloco abaixo. O prompt é executável: cada coordenada,
> abertura e texto está definido. Não é para "interpretar" — é para cumprir.
>
> **Objetivo do teste:** provar as ferramentas de edição (`entity_copy`,
> `entity_copy_filter`, `entity_rotate`, `entity_mirror`, `entity_offset`), que não
> existiam na planta em L, num desenho com simetria — que é onde elas economizam de verdade.

---

## Prompt (copie daqui para baixo)

Você é um desenhista técnico operando o AutoCAD 2025 pelas ferramentas do MCP
`mcp-cad-server`. Desenhe o **pavimento tipo de um prédio residencial** com **dois
apartamentos espelhados** e um **núcleo central** (hall, escada, elevador e shaft).

**Regras que valem mais que a pressa:**

1. Use **somente** as ferramentas do MCP. Se faltar alguma capacidade, **pare antes de
   desenhar** e diga qual é — não invente nome de ferramenta, não invente parâmetro.
2. **Não redesenhe o que já existe** para corrigir. Use `entity_erase`, `entity_erase_filter`,
   `entity_move`, `entity_offset`, `entity_rotate`, `entity_mirror`, `entity_copy`.
3. `ok=true` não é prova. Prove pelo DXF (contagem por camada, coordenadas, mtime).
4. Unidade é **metro**. `drawing_setup(unidades=6, escala_cota=0.1)` **antes** de desenhar.

### 1. Arquivo

| Item | Valor |
|---|---|
| Pasta | `C:\Users\Correta Engenharia\Desktop\planta_apartamento` |
| Desenho | `pavimento_tipo.dwg` |
| Troca | `pavimento_tipo.dxf` |
| Impressão | `pavimento_tipo.pdf` |
| Log | `log_testes.md` (uma linha por teste, PASS/FAIL + número medido) |

### 2. Documento (ordem obrigatória)

1. `new_drawing` em `C:\Users\Correta Engenharia\Desktop\planta_apartamento\pavimento_tipo.dwg`
2. `drawing_setup(unidades=6, escala_cota=0.1)` → texto de cota = 0,25 m
3. Camadas da tabela do item 3
4. Só então desenhe

### 3. Camadas

| Camada | Cor | Uso |
|---|---|---|
| `PAREDE-EXT` | 7 | perímetro, espessura 0,20 |
| `PAREDE-INT` | 7 | divisórias, espessura 0,15 |
| `ESQUADRIA` | 4 | batentes, folhas e arcos de porta |
| `VAO` | 4 | peitoril/soleira das janelas |
| `ESCADA` | 8 | degraus e seta de subida |
| `TEXTO` | 2 | nomes de ambiente e áreas |
| `COTA` | 3 | linhas de cota (`dim_linear`) |
| `TITULO` | 7 | carimbo e escala |
| `EIXO` | 1 | eixos tracejados (opcional, só para conferência) |
| `TESTE` | 6 | camada descartável dos testes T5/T8 — apagar no fim |

### 4. Geometria — eixos (tudo em metro, origem no canto inferior esquerdo)

**Perímetro do pavimento: 21,60 × 12,00** (eixos). Parede externa 0,20.

| Zona | x | y | Observação |
|---|---|---|---|
| Apartamento A | 0,00 – 9,00 | 0,00 – 12,00 | desenhar primeiro |
| Núcleo | 9,00 – 12,60 | 0,00 – 12,00 | hall, escada, elevador, shaft |
| Apartamento B | 12,60 – 21,60 | 0,00 – 12,00 | **espelho de A em x = 10,80** |

**Apartamento A — ambientes (medidas entre eixos, todas retangulares):**

| # | Ambiente | x (de–até) | y (de–até) | Área |
|---|---|---|---|---|
| 1 | Sala de estar/jantar | 0,00 – 5,40 | 0,00 – 5,00 | 27,00 m² |
| 2 | Cozinha | 5,40 – 9,00 | 0,00 – 3,00 | 10,80 m² |
| 3 | Área de serviço | 5,40 – 9,00 | 3,00 – 5,00 | 7,20 m² |
| 4 | Circulação | 0,00 – 9,00 | 5,00 – 6,40 | 12,60 m² |
| 5 | Dormitório | 0,00 – 3,60 | 6,40 – 12,00 | 20,16 m² |
| 6 | Suíte | 3,60 – 6,60 | 6,40 – 12,00 | 16,80 m² |
| 7 | Banho social | 6,60 – 9,00 | 6,40 – 9,00 | 6,24 m² |
| 8 | Closet | 6,60 – 9,00 | 9,00 – 12,00 | 7,20 m² |

Soma: **108,00 m²** (conferir: 27+10,80+7,20+12,60+20,16+16,80+6,24+7,20 = 108,00).

**Núcleo:**

| Ambiente | x (de–até) | y (de–até) | Área |
|---|---|---|---|
| Hall | 9,00 – 12,60 | 4,00 – 12,00 | 28,80 m² |
| Escada | 9,00 – 11,20 | 0,00 – 4,00 | 8,80 m² |
| Elevador | 11,20 – 12,60 | 0,00 – 2,00 | 2,80 m² |
| Shaft | 11,20 – 12,60 | 2,00 – 4,00 | 2,80 m² |

Soma do núcleo: **43,20 m²**. Total do pavimento: 108,00 + 43,20 + 108,00 = **259,20 m²**
(= 21,60 × 12,00). Se o seu desenho não fechar isso, pare e diga onde divergiu.

### 5. Paredes — segmentos de eixo

Cada parede é desenhada pelo **eixo**, com as duas faces em ±t/2. Nos vãos, **fechar a
espessura nas duas pontas** (ombreira) — vão aberto é o defeito nº 15 do histórico.

**`PAREDE-EXT` (t = 0,20):**

| Parede | De | Até | Vãos (posição ao longo do eixo) |
|---|---|---|---|
| E1 | (0,00; 0,00) | (21,60; 0,00) | J1 1,00–2,50 · J2 3,50–5,00 · J3 6,20–7,40 · J3' 14,20–15,40 · J2' 16,60–18,10 · J1' 19,10–20,60 |
| E2 | (21,60; 0,00) | (21,60; 12,00) | — (empena cega, espelho de E4) |
| E3 | (21,60; 12,00) | (0,00; 12,00) | J8' 13,20–14,40 · J6' 15,60–17,00 · J5' 19,20–20,80 · J5 0,80–2,40 · J6 4,60–6,00 · J8 7,20–8,40 |
| E4 | (0,00; 12,00) | (0,00; 0,00) | — (empena cega) |

> Atenção à ordem dos vãos em E3: o eixo corre de x = 21,60 para x = 0, então as
> posições são medidas a partir de 21,60. Confira com `query_entities` antes de apagar nada.

**`PAREDE-INT` (t = 0,15):**

| Parede | De | Até | Vãos |
|---|---|---|---|
| A1 | (9,00; 0,00) | (9,00; 12,00) | P1 5,55–6,35 · J4 3,50–4,50 · J7 7,00–8,00 |
| A2 | (12,60; 0,00) | (12,60; 12,00) | P1' 5,55–6,35 · J4' 3,50–4,50 · J7' 7,00–8,00 |
| B1 | (0,00; 5,00) | (9,00; 5,00) | P2 2,00–2,80 · P3 6,00–6,80 · P4 7,20–8,00 |
| B2 | (0,00; 6,40) | (9,00; 6,40) | P5 1,20–2,00 · P6 4,20–5,00 · P7 7,20–8,00 |
| C1 | (5,40; 0,00) | (5,40; 5,00) | — |
| C2 | (5,40; 3,00) | (9,00; 3,00) | — |
| D1 | (3,60; 6,40) | (3,60; 12,00) | — |
| D2 | (6,60; 6,40) | (6,60; 12,00) | P8 9,60–10,40 |
| D3 | (6,60; 9,00) | (9,00; 9,00) | — |
| N1 | (10,80; 0,00) | (10,80; 4,00) | — |
| N2 | (11,20; 2,00) | (12,60; 2,00) | — |
| N3 | (9,00; 4,00) | (12,60; 4,00) | abertura da escada 9,20–11,00 · porta do elevador 11,40–12,20 |

### 6. Portas (folha 0,90 / vão 0,80, arco de 90°, raio = largura)

| Porta | Onde | Vão | Abre para |
|---|---|---|---|
| P1 | A1 | y 5,55–6,35 | dentro do apartamento (circulação) |
| P2 | B1 | x 2,00–2,80 | sala |
| P3 | B1 | x 6,00–6,80 | cozinha |
| P4 | B1 | x 7,20–8,00 | área de serviço |
| P5 | B2 | x 1,20–2,00 | dormitório |
| P6 | B2 | x 4,20–5,00 | suíte |
| P7 | B2 | x 7,20–8,00 | banho social |
| P8 | D2 | y 9,60–10,40 | closet (a partir da suíte) |
| P9 | N3 | x 11,40–12,20 | elevador (folha de correr: só o batente) |

Todas com 0,80 de vão e arco de **90,000°** — o verificador confere o raio e o ângulo.

### 7. Janelas (vão de peitoril, peitoril 1,00, altura 1,20)

| Janela | Parede | Vão | Largura |
|---|---|---|---|
| J1 | E1 | 1,00–2,50 | 1,50 |
| J2 | E1 | 3,50–5,00 | 1,50 |
| J3 | E1 | 6,20–7,40 | 1,20 |
| J4 | A1 | 3,50–4,50 | 1,00 |
| J5 | E3 | 0,80–2,40 | 1,60 |
| J6 | E3 | 4,60–6,00 | 1,40 |
| J7 | A1 | 7,00–8,00 | 1,00 |
| J8 | E3 | 7,20–8,40 | 1,20 |

As janelas de B são o **espelho** destas em x = 10,80 (J1'…J8'). Não invente larguras novas.

### 8. Textos

Altura do nome **0,20**; da área **0,14**. Largura de cada texto = `0,9323 × altura ×
nº de caracteres` — **meça antes de posicionar** e não deixe texto encostar em parede.

| Texto | Posição (centro) |
|---|---|
| `SALA DE ESTAR/JANTAR` + `27,00 m²` | (2,70; 2,60) e (2,70; 2,10) |
| `COZINHA` + `10,80 m²` | (7,20; 1,60) e (7,20; 1,20) |
| `ÁREA DE SERVIÇO` + `7,20 m²` | (7,20; 4,10) e (7,20; 3,70) |
| `CIRCULAÇÃO` + `12,60 m²` | (2,60; 5,70) e (2,60; 5,30) |
| `DORMITÓRIO` + `20,16 m²` | (1,80; 9,40) e (1,80; 9,00) |
| `SUÍTE` + `16,80 m²` | (5,10; 9,40) e (5,10; 9,00) |
| `BANHO` + `6,24 m²` | (7,80; 7,60) e (7,80; 7,20) |
| `CLOSET` + `7,20 m²` | (7,80; 10,60) e (7,80; 10,20) |
| `HALL` + `28,80 m²` | (10,80; 8,00) e (10,80; 7,60) |
| `ESCADA` + `8,80 m²` | (10,10; 3,40) e (10,10; 3,00) |
| `ELEV.` + `2,80 m²` | (11,90; 1,30) e (11,90; 0,95) |
| `SH` | (11,90; 3,20) |

**Áreas dos apartamentos** (abaixo da cota geral):
`APTO A — 108,00 m²` em (4,50; −2,40) · `APTO B — 108,00 m²` em (17,10; −2,40).

### 9. Cotas

`dim_linear` só depois do `drawing_setup` do item 2 (senão o texto sai gigante).

- **Horizontal, y = −1,00**: 0,00 → 5,40 → 9,00 → 12,60 → 21,60
- **Vertical, x = −1,00**: 0,00 → 3,00 → 5,00 → 6,40 → 9,00 → 12,00
- **Gerais**: 21,60 (y = −2,00) e 12,00 (x = −2,00)
- Texto de cota **0,25 m**, duas casas, separador decimal vírgula (`5,40`)

### 10. Carimbo (camada `TITULO`, canto inferior direito)

| Linha | Texto | Posição (ponto de inserção, à esquerda) | Altura |
|---|---|---|---|
| 1 | `PAVIMENTO TIPO` | (12,00; −3,20) | 0,35 |
| 2 | `2 APARTAMENTOS + NÚCLEO` | (12,00; −3,70) | 0,20 |
| 3 | `ÁREA DO PAVIMENTO 259,20 m²` | (12,00; −4,00) | 0,20 |
| 4 | `ESCALA 1:50 — COTAS EM METROS` | (12,00; −4,30) | 0,18 |
| 5 | `CORRETA ENGENHARIA — 16/10/2026` | (12,00; −4,60) | 0,18 |

### 11. Ordem de execução (não troque a ordem)

1. documento + setup + camadas
2. perímetro E1–E4 com vãos
3. apartamento A: A1, B1, B2, C1, C2, D1, D2, D3
4. núcleo: N1, N2, N3 + degraus da escada (10 degraus de 0,28 m entre y 0,20 e 3,00)
5. portas P1–P9 (folha + arco)
6. janelas J1–J8 (batente + peitoril)
7. textos e áreas
8. cotas
9. carimbo
10. **espelhar A → B** — comece pelo bloco BANHO (T4) e depois espelhe o resto;
    confira os 10 pontos de T11
11. conferência no DXF
12. salvar DWG, exportar DXF, imprimir PDF

### 12. Testes obrigatórios (registre PASS/FAIL e o número medido em `log_testes.md`)

| # | Teste | Como provar |
|---|---|---|
| T1 | `entity_copy` de uma linha auxiliar na camada `TESTE`, de (0,00;0,00) a (0,00;12,00), com dx = 21,60, dy = 0 | DXF: duas linhas, Δx = 21,600000 |
| T2 | `entity_offset` da parede C1 com 0,075 e depois 0,075 do outro lado | DXF: faces em x = 5,325 e x = 5,475 → espessura 0,150000 |
| T3 | `entity_rotate` de um texto qualquer 90° sobre o próprio centro | DXF: rotação 90, ponto de inserção inalterado |
| T4 | `entity_mirror` do bloco BANHO (paredes + porta + janela + textos) em x = 10,80 | DXF: handle novo; x' = 21,60 − x; **texto NÃO espelhado** (`MIRRTEXT=0`) |
| T5 | `entity_copy_filter(layer="TESTE", dx=10)` com 3 linhas na camada | contagem 3 → 6 |
| T6 | `entity_move` da parede D3 com dy = 0,15 e de volta | DXF: Δy = 0,150000 nas duas vezes |
| T7 | `entity_erase` de uma porta por handle | DXF: handle sumiu, contagem −1 |
| T8 | `entity_erase_filter(layer="TESTE")` sem `confirmar` (prévia) e depois com | prévia não apaga; commit apaga 6; camada fica com 0 |
| T9 | `quantitativo` antes e depois de T7/T8 | número bate com o DXF |
| T10 | arquivos | DWG/DXF/PDF existem, bytes > 0, mtime posterior ao início |

**T11 — o teste de verdade.** O apartamento B **tem** que ser o espelho exato de A.
Confira 10 pontos (4 cantos de ambiente, 3 portas, 3 janelas): para cada ponto `(x,y)` de A,
deve existir `(21,60−x, y)` em B com o mesmo tipo de entidade. Se não existir, **não
"conserte" desenhando por cima**: diga qual ponto falhou.

### 13. Conferência no DXF (obrigatória, com `ezdxf`)

1. contagem por camada (`PAREDE-EXT`, `PAREDE-INT`, `ESQUADRIA`, `VAO`, `TEXTO`, `COTA`, `TITULO`)
2. **nenhuma ponta solta** de parede (ponta que não encosta em outra parede nem em ombreira), tolerância 1e-6
3. **nenhum texto sobre parede, cota ou outro texto** (caixa do texto com `F = 0,9323 × h`)
4. arcos de porta: raio 0,80 (±1e-6) e ângulo 90,00° (±0,01°)
5. vãos de janela com a largura da tabela do item 7
6. espelho: os 10 pontos de T11
7. somas de área do item 4

### 14. Relatório final (não maquie)

- arquivos gerados, com bytes e hora
- testes T1–T11 com o número medido
- **o que não deu para fazer** e por quê
- **o que faltou de ferramenta** (ex.: "espelhar 60 entidades exigiu 60 chamadas; falta um `mirror_filter`")
- se algo foi corrigido com `entity_*`, dizer qual handle e qual era o defeito

## Fim do prompt

---

## Por que este teste (nota para quem for avaliar)

| Ferramenta | Onde ela é exigida aqui |
|---|---|
| `entity_copy` | T1 — duplicar eixo com deslocamento exato |
| `entity_copy_filter` | T5 — copiar 3 linhas de uma camada de uma vez |
| `entity_offset` | T2 — as duas faces da parede a partir do eixo (o desenho inteiro depende disso) |
| `entity_rotate` | T3 — rótulo vertical sem mexer na posição |
| `entity_mirror` | T4 e T11 — o apartamento B é o espelho de A; texto não pode sair espelhado |
| `entity_move` | T6 — ajuste fino de parede sem redesenhar |
| `entity_erase` / `_filter` | T7/T8 — corrigir sem redesenhar (o pedido original do usuário) |
| `drawing_setup` | item 2 — sem ele a cota sai com texto gigante e o DXF sai em mm |

**O que este teste provavelmente vai revelar como faltando** (já registrado no histórico,
não é surpresa): não existe `entity_mirror_filter` nem `entity_rotate_filter`. Espelhar o
apartamento inteiro entidade por entidade é possível, mas caro — o agente deve dizer isso
em vez de fingir que foi barato.
