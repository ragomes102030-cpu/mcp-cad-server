# PROMPT — Planta em L 14 × 11 m (teste das ferramentas novas)

> Copie do título **"1. Papel"** até o fim. Ele foi escrito para ser colado numa conversa
> nova, com o MCP `mcp-cad-server` já reiniciado (45 ferramentas).

---

## 1. Papel e regra de ferro

Você é um agente de desenho técnico. Gere a planta baixa descrita abaixo no AutoCAD,
**usando exclusivamente as ferramentas do MCP**. Não invente nome de ferramenta nem
parâmetro: se algo pedido aqui não existir na lista real (confira com `system_status`
e com a documentação do servidor), **pare e diga o que falta antes de seguir** — não
improvise com `script`/`command_line` para contornar.

Antes de desenhar, leia (são curtas e cada linha custou uma reexecução):

- `C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad\skill\cad-planta-autocad\SKILL.md`
- `...\references\armadilhas.md` — 19 armadilhas medidas, inclusive as de hoje
- `...\references\falhas.md` — como registrar falha nova em `historico/ocorrencias.jsonl`

Regra que vale a partir de hoje: **errar uma entidade não autoriza refazer o desenho.**
Existe `entity_erase`, `entity_erase_filter` e `entity_move`. Use-os.

## 2. Arquivo de saída

Pasta (sem espaço, por causa da armadilha 3): `C:\Users\Correta Engenharia\Desktop\planta_L_14x11\`

- `planta_L_14x11.dwg`
- `planta_L_14x11.dxf` (exportar **depois** de salvar)
- `planta_L_14x11.pdf`
- `log_testes.md` (relatório dos testes da seção 12)

Crie a pasta antes de `drawing_new` (armadilha: `new_drawing` ignora caminho se a pasta
não existe). Trabalho temporário em `C:\temp\mcp_cad_com`.

## 3. Unidades, camadas e estilo

- Metro, `INSUNITS=6`. Cota e texto em metros.
- Criar as camadas **nesta ordem**, com `layer_create`:
  `PAREDE_EXT`, `PAREDE_INT`, `PORTA`, `JANELA`, `COTA`, `TEXTO`, `CARIMBO`.
- Alturas de texto: título 0,40 · nome de ambiente 0,24 (reduza até caber, mínimo 0,16) ·
  área 0,16 · código de vão (P1/J1) 0,20 · texto de cota 0,25 · carimbo 0,18.
- Largura de texto medida neste projeto: **0,9323 × altura por caractere** (texto criado
  por `drawing_new`). Centralize com essa conta, nunca com 0,6 nem 0,9 "de cabeça".
  Confira a centralização no DXF antes de considerar pronto.

## 4. Geometria — envelope em L

Contorno por **eixo** (paredes externas, espessura 0,15, face a ±0,075):

```
(0,0) → (14,0) → (14,8) → (9,8) → (9,11) → (0,11) → fecha
```

Ou seja: retângulo 14 × 11 com **recorte de 5 × 3** no canto superior direito
(x 9→14, y 8→11). Área do terreno construído = 139 m².

Paredes internas (espessura 0,10, faces a ±0,05):

| # | eixo | trecho |
|---|---|---|
| V1 | x = 4,50 | y 0 → 11 |
| V2 | x = 9,00 | y 0 → 8 |
| V3 | x = 12,00 | y 0 → 3,50 |
| V4 | x = 7,00 | y 7 → 9 |
| H1 | y = 4,00 | x 0 → 4,50 |
| H2 | y = 3,50 | x 4,50 → 14 |
| H3 | y = 7,00 | x 0 → 9 |
| H4 | y = 9,00 | x 7 → 9 |

Modelagem obrigatória (foi o defeito nº 1 da planta anterior):

1. Cada parede = **duas faces** paralelas ao eixo, afastadas de t/2 — nunca uma linha só.
2. Vão = **subtrair o trecho** das duas faces (`spans()`), nunca desenhar por cima.
3. Cada ponta de vão recebe uma **ombreira**: um segmento perpendicular fechando a
   espessura (t/2 de cada lado do eixo). Sem ombreira, sobram pontas soltas.
4. Nos cantos, a face externa vai de −0,075 a +comprimento+0,075 e a interna de +0,075
   a −0,075; conferir os quatro cantos (o canto trocado foi o defeito nº 2).

## 5. Ambientes (10)

Faixas por eixo. A área do rótulo é a **área útil** (face interna das paredes), calculada
como `(largura - meias-espessuras) × (altura - meias-espessuras)`, 2 casas decimais.
Exemplo: sala x 0→4,50 entre paredes externa (0,15) e interna (0,10) → largura útil
4,50 − 0,075 − 0,05 = 4,375.

| # | nome | x | y | obs |
|---|---|---|---|---|
| 1 | SALA DE ESTAR | 0 → 4,50 | 0 → 4,00 | entrada P1 |
| 2 | JANTAR | 0 → 4,50 | 4,00 → 7,00 | |
| 3 | COZINHA | 4,50 → 9,00 | 0 → 3,50 | |
| 4 | DESPENSA | 9,00 → 12,00 | 0 → 3,50 | |
| 5 | SERVICO | 12,00 → 14,00 | 0 → 3,50 | |
| 6 | HALL | 4,50 → 9,00 | 3,50 → 7,00 | |
| 7 | QUARTO 1 | 0 → 4,50 | 7,00 → 11,00 | |
| 8 | SUITE | 4,50 → 9,00 | 7,00 → 11,00 | menos o banheiro |
| 9 | BANHEIRO SUITE | 7,00 → 9,00 | 7,00 → 9,00 | dentro da suíte |
| 10 | QUARTO 2 | 9,00 → 14,00 | 3,50 → 8,00 | |

Nome centralizado no ambiente; área **abaixo** do nome, com 0,10 de folga. Se o nome não
couber na largura útil menos 0,24, reduza a altura de 0,01 em 0,01 até caber (mínimo 0,16)
— "BANHEIRO SUITE" é o caso crítico.

## 6. Portas (10) — folha 0,80; P1 = 0,90

Cada porta: vão na parede (ombreiras nas duas pontas), **folha** perpendicular ao eixo
partindo de uma ombreira, **arco de 90°** unindo a ponta da folha ao outro lado do vão.
Camada `PORTA`. Rótulo `Pn` na camada `TEXTO`, a 0,30 do vão, nunca sobre parede.

| código | parede | vão | abre para |
|---|---|---|---|
| P1 | y = 0 (externa) | x 2,00 → 2,90 | sala |
| P2 | y = 4,00 | x 1,20 → 2,00 | jantar |
| P3 | x = 4,50 | y 5,00 → 5,80 | hall |
| P4 | y = 3,50 | x 6,00 → 6,80 | cozinha |
| P5 | x = 9,00 | y 1,20 → 2,00 | despensa |
| P6 | x = 12,00 | y 1,20 → 2,00 | serviço |
| P7 | y = 7,00 | x 1,50 → 2,30 | quarto 1 |
| P8 | y = 7,00 | x 5,20 → 6,00 | suíte |
| P9 | y = 9,00 | x 7,60 → 8,40 | banheiro da suíte |
| P10 | x = 9,00 | y 5,00 → 5,80 | quarto 2 |

## 7. Janelas (12) — vidro 1,20 (J10 = 0,70; J12 = 1,00)

Camada `JANELA`: vão na parede + ombreiras + **duas linhas de vidro** paralelas ao eixo,
afastadas de ±0,025, com o comprimento do vão menos 0,10. Rótulo `Jn` a 0,30 do vão.

| código | parede | vão |
|---|---|---|
| J1 | y = 0 | x 0,50 → 1,70 |
| J2 | y = 0 | x 6,30 → 7,50 |
| J3 | y = 0 | x 10,10 → 11,30 |
| J4 | x = 0 | y 1,20 → 2,40 |
| J5 | x = 0 | y 5,10 → 6,30 |
| J6 | x = 0 | y 8,30 → 9,50 |
| J7 | y = 11 | x 1,30 → 2,50 |
| J8 | y = 11 | x 5,40 → 6,60 |
| J9 | x = 14 | y 4,50 → 5,70 |
| J10 | x = 14 | y 2,40 → 3,10 |
| J11 | y = 8 (recorte) | x 10,60 → 11,80 |
| J12 | x = 9 (recorte) | y 9,20 → 10,20 |

## 8. Cotas (camada COTA, texto 0,25)

Com `drawing_setup(escala_cota=0.1)` já rodado, `dim_linear` deve sair com texto de
**0,25 m** (DIMTXT 2,5 × DIMSCALE 0,1) e duas casas ("5,00"). Desenhe **uma** cota e
confira a altura no DXF antes de fazer as outras: se vier 2,5 m, o setup não pegou —
pare e reporte. Se vier certo, use `dim_linear` para todas; só caia para a cota manual
(linha de extensão + linha de cota + tick oblíquo + `draw_text` 0,25) se o setup falhar.

Cotas obrigatórias:

- total horizontal **14,00** em y = −1,50 (de x 0 a 14);
- total vertical **11,00** em x = −1,50 (de y 0 a 11);
- recorte: **5,00** em y = 7,60 (x 9→14) e **3,00** em x = 14,60 (y 8→11);
- larguras de ambiente em y = −0,80: 0→4,50, 4,50→9,00, 9,00→12,00, 12,00→14,00;
- larguras em x = −0,80: 0→4,00, 4,00→7,00, 7,00→11,00;
- alturas em x = 15,20: 0→3,50, 3,50→8,00.

Cada ambiente precisa de **pelo menos uma** medida que o delimite.

## 9. Textos

- Título "PLANTA BAIXA — CASA EM L", h = 0,40, centralizado em **x = 7,00**, y = 12,20.
- "ESCALA 1:50", h = 0,25, centralizado em x = 7,00, y = 11,60.
- Rótulos P1–P10 e J1–J12 conforme seções 6 e 7.
- Nada de texto sobre parede, sobre linha de cota ou sobre outro texto.

## 10. Carimbo (camada CARIMBO)

Retângulo x 15,00 → 21,00, y −5,00 → −2,00 (abaixo da cota de 14,00, sem cruzar com ela),
dividido em 6 campos com 2 linhas cada:
`PROJETO / CASA EM L 14 × 11`, `LOCAL / —`, `ESCALA / 1:50`, `DATA / 16/10/2026`,
`DESENHISTA / —`, `PRANCHA / PB-01 REV A`.

## 11. Ordem de execução

1. `system_status` e conferir que as 45 ferramentas existem (listar as novas).
2. Camadas (seção 3).
3. `drawing_new` na pasta da seção 2, **depois `drawing_setup(unidades=6,
   escala_cota=0.1)`** — é o que põe INSUNITS em metros e faz a cota sair com 0,25.
4. Paredes externas (envelope em L) + internas, com os vãos já subtraídos e ombreiras.
5. Portas e janelas + rótulos.
6. Nomes e áreas.
7. Cotas (teste do `dim_linear` primeiro).
8. Título, escala, carimbo.
9. `zoom_extents`, `drawing_save`, `drawing_export_dxf`, conferência (seção 13).
10. **`drawing_save` de novo** com sufixo `_v1` antes da fase de testes (seção 12) — é o
    ponto de retorno.

## 12. FASE DE TESTE — as ferramentas novas

Execute **nesta ordem**, anotando em `log_testes.md` uma linha por teste:
`# | ferramenta | argumentos | esperado | obtido | veredito`.

Regras: antes de qualquer exclusão em bloco, rode com `confirmar=False` e **só depois**
com `confirmar=True`; depois de cada exclusão, reconte com `entity_list` e prove que a
diferença é exatamente o número apagado. Se uma ferramenta devolver `ok=false`, não
repita mais de 2× — registre e siga.

| # | teste | como | esperado |
|---|---|---|---|
| T1 | `entity_list(layer="TEXTO")` | listar handles | todos os textos, > 20 itens |
| T2 | `entity_list(tipo="ARC")` | filtrar por tipo | 10 arcos (um por porta) |
| T3 | `entity_erase_filter(layer="COTA", confirmar=False)` | só contagem | devolve N > 0 e **não** apaga nada |
| T4 | `entity_erase_filter(texto="DESPENSA", confirmar=False)` | prévia | 1 |
| T5 | `entity_erase_filter(texto="DESPENSA", confirmar=True)` | apagar | 1 apagado; `entity_list` cai 1; redesenhar "DESPENSA SECA" h 0,24 no mesmo centro |
| T6 | `entity_erase(handle)` | apagar o rótulo `P7` pelo handle | 1 apagado; redesenhar P7 0,05 acima |
| T7 | `entity_move(handle, dx=0,40, dy=0)` | mover o título | bbox do título desloca exatamente 0,40 (contar no DXF). **Se travar o AutoCAD**, anote FALHOU, reinicie e redesenhe no lugar certo |
| T8 | `entity_erase_filter(layer="CARIMBO", confirmar=True)` | limpar carimbo | apaga os ~14 itens; redesenhar com `PRANCHA / PB-01 REV B` |
| T9 | janela J11 removida do projeto | `entity_erase` nos 3 itens (2 vidros + rótulo), depois **fechar o vão** com 2 linhas na camada PAREDE_EXT e apagar as 2 ombreiras | parede contínua, 0 pontas soltas no DXF |
| T10 | `quantitativo` antes/depois | comparar | diferença = itens apagados em T5+T6+T8+T9 |

T9 é o teste que importa: é a correção que ontem custava redesenhar a planta inteira.

## 13. Verificação (independente, no DXF com `ezdxf`)

Não confie no "ok" das ferramentas. Leia o DXF e prove:

1. contagem por camada (informe a tabela);
2. **pontas de parede soltas = 0** (ponto que não pertence a nenhum segmento, tol. 1e-6);
3. 10 arcos, abertura 90,00° ± 0,01;
4. folha de porta com 0,80 (P1 0,90) ± 0,01; vidro = vão − 0,10 ± 0,02;
5. texto × parede = 0, texto × texto = 0, texto × linha de cota = 0 (caixa de tinta com
   largura `0,9323 × h × len(texto)`, rotação 90 tratada);
6. título centralizado em x = 7,00 ± 0,02;
7. `14.00` e `11.00` aparecem **uma vez cada** na camada COTA;
8. PDF com tamanho > 10 KB e data de modificação de agora (se não, feche o Acrobat e
   replote em `_v2.pdf`);
9. nenhuma entidade fora da faixa x −2,5 → 22, y −6 → 12,5.

Se o verificador acusar algo, **desconfie primeiro dele** (armadilha 11) antes de corrigir
o desenho — mas se confirmar, corrija com `entity_erase`/`entity_erase_filter`, não
refazendo a planta.

## 14. Resposta final

1. plano numerado com as chamadas reais (ferramenta + argumentos);
2. tabela de contagens por camada;
3. tabela dos 10 testes (T1–T10) com veredito;
4. verificação da seção 13, item por item;
5. **pendências e falhas**, sem maquiar: o que não deu, o que ficou fora de escala, o que
   travou;
6. se encontrou falha nova, uma linha em `historico/ocorrencias.jsonl` via
   `cad_mcp.historico.registrar()` (sintoma literal + evidência numérica) e cite a chave.

Se algo pedido aqui não existir nas 45 ferramentas, **pare antes de desenhar** e diga o
que falta. Se uma etapa falhar, descreva o erro real e siga para a próxima — planta
incompleta com relatório honesto vale mais que planta "pronta" com defeito escondido.
