# Mapa das ferramentas CAD (2D) — 131 tools

Fonte: `codigo/src/cad_mcp` @ HEAD `7cfbf39`. **Somente 2D** (nenhuma ferramenta 3D).

| categoria | tools |
|---|---|
| Desenho | 15 |
| Edicao | 22 |
| Consulta | 5 |
| Simbolos | 5 |
| Servicos | 1 |
| Camada/estilo | 16 |
| Bloco | 5 |
| Cota/anotacao | 6 |
| Arquitetura | 8 |
| Layout/plot | 14 |
| Arquivo/documento | 18 |
| Arquivo/xref/imagem | 4 |
| Visualizacao | 4 |
| Sistema | 5 |
| Quantitativo | 1 |
| **TOTAL** | **131** |

## Desenho (15)

| ferramenta | o que faz | parametros |
|---|---|---|
| `construction_xline` | Linha infinita de construcao (XLINE). Existe para apoiar o desenho, nao para plotar. | x, y, angle_deg, layer |
| `entity_create_arc` | Desenha um arco (abertura de porta, por exemplo). | cx, cy, radius, start_angle, end_angle, layer |
| `entity_create_circle` | Desenha um círculo. | cx, cy, radius, layer |
| `entity_create_ellipse` | Elipse pelo centro, vetor do eixo maior e razao entre os eixos. | cx, cy, major_x, major_y, ratio, layer |
| `entity_create_hatch` | Hachura uma entidade fechada (recebe o handle dela). | entity_id, pattern |
| `entity_create_line` | Desenha uma linha. | x1, y1, x2, y2, layer |
| `entity_create_mtext` | Escreve um texto multilinha. | x, y, width, text, height, layer |
| `entity_create_point` | Um ponto de marcacao (no). Nao e' geometria desenhavel. | x, y, layer |
| `entity_create_polyline` | Desenha uma polyline pelos pontos [[x,y], ...]. | points, closed, layer |
| `entity_create_rectangle` | Desenha um retângulo (polyline fechada). | x1, y1, x2, y2, layer |
| `entity_create_revcloud` | Nuvem de revisao: semicirculos tangentes ao longo do contorno. | points, segment_length, layer, closed |
| `entity_create_spline` | Spline (NURBS) por pontos de ajuste. Exige ao menos 2 pontos. | fit_points, layer |
| `entity_create_table` | Cria uma tabela com cabeçalhos e linhas. | x, y, rows, headers, column_widths, row_height, text_height, title, layer |
| `entity_create_text` | Escreve um texto simples. | x, y, text, height, rotation, layer |
| `hatch_material` | Hachura com o padrao ISO 128-50 do material (concreto, tijolo, terra...). | material, boundary, handles, scale, angle, layer |

## Edicao (22)

| ferramenta | o que faz | parametros |
|---|---|---|
| `entity_array_polar` | Repete uma entidade em torno de um centro (ARRAYPOLAR): roda de parafusos etc. | handle, count, fill_angle, center_x, center_y |
| `entity_array_rectangular` | Repete uma entidade numa grade de linhas x colunas (ARRAYRECT). | handle, rows, cols, row_spacing, col_spacing |
| `entity_chamfer` | Bisela o canto entre duas retas (CHAMFER). Geometria propria, sem comando. | handle1, handle2, dist1, dist2, trim |
| `entity_copy` | Copia UMA entidade e desloca a cópia (dx, dy). Devolve o handle da cópia. | entity_id, dx, dy |
| `entity_copy_filter` | Copia EM BLOCO tudo que casa com camada/tipo e desloca a cópia. | layer, tipo, dx, dy |
| `entity_delete` | Apaga UMA entidade pelo handle (alias para entity_erase). | entity_id |
| `entity_delete_many` | Apaga varias entidades de uma vez. DESTRUTIVO: so' apaga com `confirmar=True`. | handles, confirmar |
| `entity_edit_text` | Troca o texto, a altura ou a rotacao de um TEXT, mantendo o handle. | handle, text, height, rotation |
| `entity_erase` | Apaga UMA entidade pelo handle (ex.: o handle devolvido por query_entities). | entity_id |
| `entity_erase_filter` | Apaga em bloco por camada / tipo DXF / conteudo exato de texto. | layer, tipo, texto, confirmar |
| `entity_extend` | Estende a reta `alvo` ate' encontrar a reta `limite`. | alvo, limite, ponto |
| `entity_fillet` | Arredonda o canto entre duas retas com arco tangente de `raio`. | h1, h2, raio, trim, p1, p2 |
| `entity_mirror` | Espelha uma entidade em relação ao eixo (x1,y1)-(x2,y2), MANTENDO o original. | entity_id, x1, y1, x2, y2 |
| `entity_mirror_filter` | Espelha EM BLOCO tudo que casa com camada/tipo, em relação ao eixo (x1,y1)-(x2,y2). | layer, tipo, x1, y1, x2, y2 |
| `entity_move` | Move uma entidade pelo handle, em metros (vla-move, não trava o AutoCAD). | entity_id, dx, dy |
| `entity_offset` | Cria uma paralela a uma LINE, a `distance`, para um dos lados. | entity_id, distance, side |
| `entity_rotate` | Gira uma entidade em torno de (x, y). Ângulo em GRAUS (anti-horário). | entity_id, x, y, angulo |
| `entity_rotate_filter` | Gira EM BLOCO tudo que casa com camada/tipo em torno de (x, y). Ângulo em GRAUS. | layer, tipo, x, y, angulo |
| `entity_scale` | Redimensiona uma entidade uniformemente em torno de um ponto-base. | entity_id, base_x, base_y, factor |
| `entity_set_properties` | Muda camada, cor, tipo de linha, espessura ou visibilidade de uma entidade. | handle, layer, color, linetype, lineweight, visible |
| `entity_trim` | Corta a reta `alvo` na interseccao com `corte`, mantendo o lado de `keep`. | alvo, corte, keep |
| `hatch_edit` | Muda o padrao, a escala, o angulo, a cor ou o estilo de uma hachura. | handle, pattern, scale, angle, color, style |

## Consulta (5)

| ferramenta | o que faz | parametros |
|---|---|---|
| `entity_get` | Inspeciona UMA entidade: tipo, camada e geometria (pontos, centro, raio, angulos). | entity_id |
| `entity_list` | Lista entidades, com filtro opcional por camada e por tipo DXF (LINE, TEXT, ARC, LWPOLYLINE...). | layer, tipo |
| `point_from_snap` | Ponto exato de uma entidade: endpoint, midpoint, center, quadrant ou perpendicular. | handle, snap, ref_x, ref_y |
| `point_tangent` | Ponto de tangencia de uma reta que sai de um ponto externo ate' um circulo/arco. | circle_handle, from_x, from_y, ref_x, ref_y |
| `selection_window` | Lista o que cai dentro (ou cruza) uma janela retangular. Nao seleciona de fato. | x1, y1, x2, y2, modo, entity_type, layer |

## Simbolos (5)

| ferramenta | o que faz | parametros |
|---|---|---|
| `place_symbol` | Coloca um simbolo do catalogo num ponto livre (rotacao em GRAUS). | symbol, x, y, rotation, scale, layer |
| `place_symbol_on_wall` | Coloca um simbolo NA PAREDE: a `offset` do inicio do eixo, deslocado `side` | wall, offset, symbol, side, distance, rot_offset, scale, layer |
| `symbol_counts` | Contagem dos simbolos colocados na sessao (relatorio/quantitativo). |  |
| `symbol_legend` | Legenda de simbolos (amostra + nome), opcional por disciplina. | x, y, discipline, scale, passo |
| `symbol_schedule` | Quadro de quantitativos: contagem por tipo dos simbolos colocados. | x, y, layer |

## Servicos (1)

| ferramenta | o que faz | parametros |
|---|---|---|
| `service_run` | Desenha um trecho de servico (fiacao/eletroduto/tubo) por uma polilinha. | points, service, diameter, label, closed, layer |

## Camada/estilo (16)

| ferramenta | o que faz | parametros |
|---|---|---|
| `layer_create` | Cria uma camada. | name, color, linetype |
| `layer_delete` | Apaga a camada. Precisa estar vazia; as camadas '0' e atual nao saem. | name |
| `layer_freeze` | Congela a camada (invisivel e nao selecionavel; mais rapido no regen). | name |
| `layer_hide` | Desliga a camada (entidades ficam invisiveis, mas continuam no desenho). | name |
| `layer_isolate` | Isola: desliga TODAS as camadas menos `name` (o alvo fica ligado). | name |
| `layer_linetype_load` | Carrega um tipo de linha (LTYPE) do .lin e confirma que entrou na tabela. | nome, arquivo |
| `layer_list` | Lista as camadas do desenho. |  |
| `layer_lock` | Trava a camada: entidades visiveis, mas nao selecionaveis. | name |
| `layer_modify` | Muda cor (1-255), tipo de linha e/ou espessura (1/100 mm) de uma camada. | name, color, linetype, lineweight |
| `layer_set_current` | Define a camada corrente. | name |
| `layer_show` | Religa uma camada que estava desligada. | name |
| `layer_thaw` | Descongela a camada. | name |
| `layer_unlock` | Destrava a camada. | name |
| `linetype_list` | Nomes de todos os tipos de linha carregados no desenho. |  |
| `plot_style_list` | Lista os arquivos .ctb/.stb instalados (monochrome, acad, grayscale...). |  |
| `textstyle_list` | Nomes de todos os estilos de texto (STYLE) do desenho. |  |

## Bloco (5)

| ferramenta | o que faz | parametros |
|---|---|---|
| `block_define` | Define um bloco a partir de entidades ja' existentes (lista de handles). | name, entities |
| `block_get_attributes` | Lê os atributos de um bloco inserido (largura de porta, tipo de janela...). | entity_id |
| `block_insert` | Insere um bloco. | name, x, y, scale, rotation |
| `block_list` | Lista os blocos definidos no desenho. |  |
| `block_set_attributes` | Altera um atributo de bloco. | entity_id, tag, value |

## Cota/anotacao (6)

| ferramenta | o que faz | parametros |
|---|---|---|
| `dimension_aligned` | Cota alinhada entre dois pontos, com afastamento. | x1, y1, x2, y2, offset |
| `dimension_angular` | Cota angular entre dois raios a partir de um vertice. | cx, cy, x1, y1, x2, y2 |
| `dimension_linear` | Cota linear entre dois pontos, com a linha de cota em (dim_x, dim_y). | x1, y1, x2, y2, dim_x, dim_y |
| `dimension_radius` | Cota de raio de um circulo/arco, em (cx, cy) com `radius`. | cx, cy, radius, angle |
| `dimstyle_list` | Nomes de todos os estilos de cota (DIMSTYLE) do desenho. |  |
| `leader_create_mleader` | Callout: seta na primeira marca e nota no fim (QLEADER simplificado). | points, text, height, layer |

## Arquitetura (8)

| ferramenta | o que faz | parametros |
|---|---|---|
| `arch_dimension_chains` | Cotas encadeadas nas fachadas da planta (sul e oeste, por padrao). | sides, scale, first_offset, step |
| `arch_grid` | Malha estrutural: eixos rotulados com bolhas nas duas pontas. | x_axes, y_axes, labels, extension |
| `arch_opening` | Host a door or a window in a drawn wall by distance along it; the wall is cut. | wall, offset, width, kind, swing, hand, sill, height, tag, opening_id, lang, poc |
| `arch_room` | Desenha um ambiente como contorno fechado em PAREDES + hachura + texto com nome e área. | nome, x, y, largura, altura, com_hachura, com_texto, altura_texto, padrao_hachur |
| `arch_rooms_detect` | Descobre ambientes de uma planta: polilineas fechadas com area >= min_area. | layers, min_area, tol |
| `arch_stair` | Escada reta/L/U em planta; Blondel. tipo=reta|L|U, n1. | x, y, largura, degraus, piso, altura_total, angulo, seta, rotulo, camada, lang, tipo, n1 |
| `floor_copy` | Copia entidades cujo ponto caia em bbox para (dx,dy). Duplicar pavimento. | x1, y1, x2, y2, dx, dy, layer |
| `prumada` | Prumada (shaft) em planta: circulo com cruz + texto nome/nivel. | x, y, nome, nivel, diametro, camada |
| `arch_symbol` | Simbolo de planta: norte, marcador de corte ou marcador de nivel. | kind, x, y, params, lang, scale |
| `arch_wall` | Desenha paredes de uma planta baixa. | walls, poche |

## Layout/plot (14)

| ferramenta | o que faz | parametros |
|---|---|---|
| `batch_plot` | Plota varias abas em PDF de uma vez (o PUBLISH do AutoCAD, sem dialogo). | layouts, out_dir, media, escala, padrao |
| `layout_copy` | Copia a aba (page setup + geometria) e renomeia a copia. | origem, novo |
| `layout_create` | Cria uma aba de layout (paper space) nova. | name |
| `layout_delete` | Apaga a aba de layout e tudo que estiver nela. | name |
| `layout_list` | Lista as abas de layout (Model + paper space) na ordem em que aparecem. |  |
| `layout_rename` | Renomeia a aba. Os handles das entidades nao mudam. | antigo, novo |
| `layout_set_current` | Ativa uma aba de layout (o que o CTAB faz). | name |
| `page_setup_apply` | Aplica o page setup de uma vez (equivalente ao PAGESETUP do AutoCAD). | layout, device, paper, orientation, plot_style, centered |
| `page_setup_list` | Le o page setup salvo na aba: device, papel, rotacao, CTB e centralizacao. | layout |
| `viewport_create` | Cria viewport de modelo no paper space via MVIEW, centrado em (cx, cy) mm. | layout, cx, cy, largura, altura, escala |
| `viewport_delete` | Apaga um viewport pelo handle. O viewport 1 (a folha) nao pode sair. | layout, handle |
| `viewport_list` | Lista viewports do paper space: handle, numero, tamanho, escala e trava. | layout |
| `viewport_lock` | Trava/destrava a escala do viewport (DisplayLocked). | layout, handle, travar |
| `viewport_set_scale` | Recalibra o viewport: 1:50 => escala 50 (CustomScale). | layout, handle, escala |

## Arquivo/documento (18)

| ferramenta | o que faz | parametros |
|---|---|---|
| `drawing_apply_iso_layers` | Cria o conjunto padrão de camadas (PAREDES, PORTAS, JANELAS, COTAS, TEXTOS, HACHURA...). |  |
| `drawing_apply_standard` | Deixa o desenho num padrao (ISO ou ANSI) numa chamada: camadas + unidades + cota. | standard, layers, unidades |
| `drawing_audit` | Roda o AUDIT e conserta os problemas estruturais que ele conseguir. |  |
| `drawing_close` | Alias de document_close com o default do mcp-pro (salva ao fechar). | salvar, forcar |
| `drawing_export_dwg` | Grava o desenho como DWG nativo (nao DXF renomeado). | path |
| `drawing_export_dxf` | Exporta o desenho atual para DXF. | path |
| `drawing_export_pdf` | Plota o desenho em PDF. | path, folha, escala |
| `drawing_info` | Estado do desenho: variáveis, contagem de entidades e camadas. |  |
| `drawing_new` | Cria um desenho novo. | name |
| `drawing_open` | Abre um DXF/DWG existente. | path |
| `drawing_properties_get` | Campos de resumo do desenho (DWGPROPS): titulo, autor, palavras-chave... |  |
| `drawing_properties_set` | Grava os campos de resumo do desenho. No motor headless vira header custom var. | title, subject, author, keywords, comments, custom |
| `drawing_purge` | Purga do desenho tudo que nao esta em uso (camadas, blocos, tipos de linha). |  |
| `drawing_redo` | Refaz a última operação desfeita. |  |
| `drawing_save` | Salva o desenho (SAVEAS se path for informado). | path |
| `drawing_save_as` | Salva o desenho com outro nome/caminho (SAVEAS; a extensao decide DWG/DXF). | path |
| `drawing_setup` | Ajusta unidades e escala de cota do desenho ATUAL (chame após new_drawing). | unidades, escala_cota, ltscale |
| `drawing_undo` | Desfaz a última operação. |  |

## Arquivo/xref/imagem (4)

| ferramenta | o que faz | parametros |
|---|---|---|
| `document_close` | Fecha o documento ativo; recusa fechar o ultimo desenho sem forcar=True. | salvar, forcar |
| `image_attach` | Anexa imagem raster (PNG/JPG/TIF) no ponto (x, y). | path, x, y, scale, rotation |
| `xref_attach` | Anexa um DWG/DXF como referencia externa no ponto (x, y). | path, x, y, scale, rotation |
| `xref_manage` | Uma operacao sobre uma xref: reload \| unload \| detach \| path. | name, operacao, novo_path |

## Visualizacao (4)

| ferramenta | o que faz | parametros |
|---|---|---|
| `view_render_png` | Gera PNG do desenho e grava EXATAMENTE em `path` (se informado). | path |
| `view_screenshot` | Captura a janela do CAD (mesmo que render_png no modo headless). | path |
| `view_zoom_extents` | Zoom para os limites do desenho. |  |
| `view_zoom_window` | Zoom numa regiao retangular da tela (Z00M _W). So' existe com AutoCAD aberto. | x1, y1, x2, y2 |

## Sistema (5)

| ferramenta | o que faz | parametros |
|---|---|---|
| `cancel` | Envia ESC ao AutoCAD (cancela comando em execução / limpa seleção). |  |
| `script` | Executa vários comandos em sequência. | linhas |
| `system_run_command` | Executa UM comando do AutoCAD (ex.: 'LINE 0,0 10,0 10,5 C'). | text |
| `system_status` | Qual motor está ativo (AutoCAD vivo ou headless) e o que ele suporta. |  |
| `user_pick_point` | Pede um ponto ao operador na tela do AutoCAD. So' existe no motor COM. | prompt |

## Quantitativo (1)

| ferramenta | o que faz | parametros |
|---|---|---|
| `quantitativo` | Lê o desenho atual e devolve quantitativos por camada (comprimentos, áreas, blocos, textos, cotas). | layer |

## Lacunas para disciplinas (eletrica / hidraulica)

P1 (catalogo+place_symbol), P2 (service_run) e P3 (symbol_legend/symbol_schedule/symbol_counts) IMPLEMENTADOS. Falta: P4 multi-pavimento (2D por andar).
