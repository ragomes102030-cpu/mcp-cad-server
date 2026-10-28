# Manual do agente para o MCP CAD

Versao do contrato: 0.2.5

Este manual define como escolher as ferramentas do MCP CAD. As primitivas ficam
disponiveis no perfil `full`, mas uma planta nao deve ser montada como uma
colecao de retangulos independentes.

## 1. Escolha do fluxo

| Situacao | Fluxo correto |
|---|---|
| Planta residencial compatível com template | `planta_templates` -> `planta_criar_validada(preview)` -> `planta_criar_validada(desenhar, preview_token)` |
| Planta com programa ou geometria fora do template | modelo paramétrico -> `validar_planta` -> primitivas sequenciais |
| Edicao de desenho existente | `system_status`/`cad_status` -> `drawing_info`/`inspect_drawing` -> consulta por camada/handle -> edicao pontual -> auditoria |
| Cloud | usar DXF/ezdxf; nunca prometer controle de AutoCAD ou DWG local |
| Local | usar AutoCAD COM quando `system_status` confirmar `autocad_com` |

Se `planta_criar_validada` existir, ela tem prioridade sobre `entity_create_*`
ou `draw_*` para a planta correspondente.

## 2. Fluxo parametrico obrigatório

### Local

1. `system_status`
2. `planta_templates`
3. `planta_criar_validada(modo="preview", programa={...})`
4. Conferir `ok=true`, `validacao`, áreas, dimensões e `preview_token`.
5. `planta_criar_validada(modo="desenhar", programa={...}, preview_token="...")`
6. `drawing_info`, `quantitativo`, `drawing_audit`, `view_render_png`.
7. `drawing_save`, `drawing_export_dxf` e `drawing_export_pdf` quando solicitados.

### Cloud

O cloud é **headless**: `ezdxf` em Render/Linux, sem AutoCAD, COM, ActiveX,
janela ou acesso ao desktop/DWG local. Não chame `system_status`, não passe
`abrir_autocad`, não peça para abrir o AutoCAD e não trate a ausência do
AutoCAD como falha.

Use a sequência cloud:

1. `cad_status` — deve retornar `backend=ezdxf`, `autocad_available=false` e
   `execution_mode=cloud_headless`.
2. `planta_templates`.
3. `planta_criar_validada(modo="preview")`.
4. `planta_criar_validada(modo="desenhar", preview_token="...")`.
5. `export_dxf`.

Para edições primitivas, use `new_drawing`, `layer_create`, `draw_*`,
`drawing_audit` e `export_dxf`. Não tente abrir um DWG do computador local.

Use a mesma sequência de validação, trocando apenas os nomes de consulta/exportação:
`cad_status`, `inspect_drawing`, `drawing_audit`, `quantitativo` e
`export_dxf`. O cloud é headless e não abre o AutoCAD do usuário.

O token de preview deve ser repassado exatamente como retornado. Não altere o
programa entre preview e desenho. Se o servidor retornar
`WORKFLOW_REQUIRED` ou `PREVIEW_TOKEN_INVALID`, pare e corrija a sequência.

## 3. Fluxo primitivo para tipologia sem template

Use-o somente quando o template não atende ao pedido ou quando o usuário pediu
explicitamente CAD avançado. Execute uma etapa por vez; não envie operações
dependentes em paralelo.

1. Confirme o backend e o documento.
2. Abra um desenho novo ou o arquivo indicado.
3. Configure unidades: metros (`INSUNITS=6`), escala de cotas e `LTSCALE`.
4. Crie e confirme as camadas: `TERRENO`, `PAREDES`, `PORTAS`, `JANELAS`,
   `MOBILIARIO`, `COTAS`, `TEXTOS`.
5. Construa um modelo com eixos, espessuras, ambientes e vãos. Rode
   `validar_planta(modelo, estrito=true)` antes de criar entidades.
6. Desenhe paredes por segmentos. Cada vão deve ser uma interrupção real da
   parede; nunca desenhe uma parede contínua e coloque a porta por cima.
7. Desenhe portas somente nos vãos. Arco de abrir tem 90 graus, raio igual à
   largura da folha e quadrante voltado para o ambiente indicado.
8. Desenhe janelas como duas linhas paralelas dentro do vão externo.
9. Adicione mobiliário, cotas e textos somente depois da geometria principal.
10. Audite, releia entidades por camada, renderize PNG e confira visualmente.
11. Só depois salve e exporte os arquivos.

## 4. Matriz de ferramentas

### Local / AutoCAD COM

- Estado: `system_status`, `drawing_info`, `entity_list`, `layer_list`.
- Preparação: `drawing_new`, `drawing_open`, `drawing_setup`.
- Geometria: `entity_create_line`, `entity_create_polyline`,
  `entity_create_rectangle`, `entity_create_arc`.
- Apresentação: `entity_create_text`, `entity_create_mtext`,
  `dimension_linear`, `dimension_aligned`.
- Correção: `entity_erase` por handle, `entity_move`, `entity_offset`.
- Verificação: `drawing_audit`, `quantitativo`, `view_zoom_extents`,
  `view_render_png`.
- Entrega: `drawing_save`, `drawing_export_dxf`, `drawing_export_pdf`.

### Cloud / ezdxf

- Estado: `cad_status`, `inspect_drawing`, `query_entities`.
- Preparação: `new_drawing`, `layer_create`, `layer_list`.
- Geometria: `draw_line`, `draw_polyline`, `draw_rectangle`, `draw_arc`.
- Texto/cota: `draw_text`, `dim_aligned`.
- Verificação: `drawing_audit`, `quantitativo`.
- Entrega: `export_dxf`.

## 5. Regras que bloqueiam a entrega

Pare e corrija se ocorrer qualquer um destes casos:

- parede colinear sobreposta ou encontro duplicado;
- porta sem vão correspondente;
- arco diferente de 90 graus;
- porta ou janela fora do perímetro;
- ambiente com área negativa, sobreposta ou divergente da especificação;
- mobiliário sobre porta, janela ou texto de ambiente;
- cotas em milímetros quando o projeto é em metros;
- texto ou selo fora da folha;
- desenho entregue sem auditoria e sem PNG de conferência;
- cloud apresentado como se fosse AutoCAD COM.

## 6. Resposta mínima do agente

Ao finalizar, informe backend, versão, perfil, documento, validações realizadas,
quantidade de entidades por camada e os caminhos dos arquivos. Se uma etapa não
for possível, informe o código/causa e pare; não substitua o fluxo por desenho
improvisado.
