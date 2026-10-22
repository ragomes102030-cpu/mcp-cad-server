# Auditoria ao vivo — o que o mcp-cad-server faz no AutoCAD

Medida em **2026-10-21** contra o **AutoCAD 2025** (`R25.0.162.0.0`,
`ACADVER 25.0s (LMS Tech)`) **aberto**, via backend COM (`autocad_com`).
Não é uma auditoria de código: cada afirmação abaixo tem chamada real.

Reprodutor: `codigo/tools/bateria_ao_vivo.py` (111 passos, um por ferramenta).
Evidência crua: `C:/temp/bateria_vivo.json`, `C:/temp/bateria_log2.txt`.

## Números

| | |
|---|---|
| ferramentas declaradas | 118 |
| passos executados ao vivo | 111 |
| ok | **86** |
| falha | 25 |

Das 25 falhas: **9 são lacuna real** (COM não implementa), **2 são o próprio
AutoCAD recusando** (correto), **1 travou**, e **13 são artefato do meu teste**
(argumento errado, handle falso, escala que não cabe) — não são defeito.

## Os 4 defeitos de código encontrados (e já corrigidos)

### 1. CRÍTICO — TRIM/EXTEND/FILLET estavam 100% mortos

`tools.py` chamava `Ponte()` e capturava `_PonteIndisponivel` **sem importar
nenhum dos dois**. Toda chamada levantava
`NameError: name '_PonteIndisponivel' is not defined`.

O plugin funciona: `Ponte().trim(...)` direto devolve
`{"ok": true, "resultados": [{"ok": true, "op": "trim", ...}]}`.
Ou seja: três ferramentas-cardeais (a razão de existir do plugin .NET) não
executavam nada.

**Correção:** uma linha em `codigo/src/cad_mcp/tools.py`:

```python
from .bridge import Ponte, PonteIndisponivel as _PonteIndisponivel
```

**Prova pós-correção (geometria, não contagem):** reta de (0,0) a (10,0),
cortada pela reta vertical em x=5 mantendo o lado x>5.
`entity_geometry` antes: `PONTOS: [0.0, 0.0]`; depois do trim: `[5.0, 0.0]`.

### 2. `drawing_apply_iso_layers` reportava 11 erros no AutoCAD

`layers.py:39` fazia `(r.payload or {}).get("existed")`. No COM, `layer_create`
devolve `payload = 1` (int) — `(1).get` levanta `AttributeError`. As camadas
**eram criadas**, mas a ferramenta dizia que as 11 falharam. Falso negativo que
faz o agente repetir o passo ou concluir que a padronização está quebrada.

**Correção:** só chama `.get` quando `payload` é `dict`.
**Prova:** `criadas=11`, `ja_existiam=0`, `erros=[]`.

### 3. `arch_room` e `entity_create_revcloud` quebravam no COM

Mesmo padrão: `(payload or {}).get("handle")`. O COM devolve o handle como
**string**, o ezdxf devolve **dict**. `AttributeError` nas duas.

**Correção:** aceita os dois formatos.
**Prova:** `arch_room` → `area=24, perimetro=20`, hachura e texto criados;
`revcloud` → 3 arcos, `falhas=0`.

## Lacunas reais de capacidade (COM não implementa) — FECHADAS no 2º turno

Na primeira medição (manhã de 21/10/2026) estas **devolviam "Not supported on
this backend"** no AutoCAD — só funcionavam no ezdxf headless:

`entity_create_ellipse`, `entity_scale`, `entity_chamfer`,
`entity_array_rectangular`, `dimension_angular`, `dimension_radius`,
`block_define`, `block_get_attributes`, `block_set_attributes`.

Ou seja: o contrato de 118 ferramentas incluía 9 que, no AutoCAD, não faziam nada.

> **Resolvido no segundo turno deste mesmo dia.** As 9 foram implementadas no
> `com_backend.py` e medidas uma a uma contra o AutoCAD aberto. Veja
> `# Segundo turno — as 9 lacunas fechadas`, no fim deste arquivo.

## Ressalvas medidas

| ferramenta | comportamento real |
|---|---|
| `layer_freeze`/`layer_thaw` | recusadas pelo próprio AutoCAD quando a camada é a atual (`CLAYER`). Correto — não é defeito. |
| `cancel` | devolve erro no backend COM; só age em `file_ipc`. No COM, ESC é `win32_bridge.enviar_esc(hwnd, forcado=True)`. |
| `image_attach` | **travou 30 s** e deixou o AutoCAD em `RPC_E_CALL_REJECTED`. Usa `SendCommand` com `IMAGEATTACH`. Caminho não confiável. |
| `document_close`/`drawing_close` | "Drawing is busy" quando há comando pendente. |

## O que funciona de verdade (provado)

- **Desenho:** line, rectangle, circle, arc, polyline, text, mtext, point,
  spline, xline, hatch, revcloud (estes dois últimos após correção).
- **Camadas:** create, set_current, list, hide, show, freeze, thaw, lock,
  unlock, isolate, modify, linetype_load.
- **Estilos:** linetype_list, dimstyle_list, textstyle_list, plot_style_list.
- **Edição:** move, copy, rotate, mirror, offset, array_polar, set_properties,
  edit_text, erase, erase_filter, delete_many, copy_filter, mirror_filter,
  rotate_filter, **trim, extend, fillet**.
- **Consulta:** entity_list, entity_get, quantitativo (extents, INSUNITS,
  camadas, textos, cotas).
- **Blocos:** block_list, block_insert.
- **Arquivo:** new, open, save, save_as, export_dxf (AC1032 real),
  export_dwg, purge, undo, redo, properties get/set, audit.
- **Layout/plot:** layout create/list/set_current/rename/copy, page_setup
  list/apply, viewport create/list, batch_plot, **export_pdf** (PDF real).
- **Visual:** screenshot (PNG 72 748 bytes), zoom extents/window, render_png.
- **Arquitetura:** arch_grid, arch_symbol, arch_room, arch_rooms_detect,
  hatch_material, leader_create_mleader, dimension_linear, dimension_aligned.
- **Sistema:** script, system_run_command, user_pick_point, selection_window.

**Prova de que a geometria é real:** o DXF exportado do desenho do teste tem 363
entidades (`LINE`, `CIRCLE`, `ARC`, `LWPOLYLINE`, `TEXT`, `MTEXT`, `DIMENSION`,
`HATCH`), `$INSUNITS=6` (metros), e um círculo criado com raio 3.0 aparece com
raio 3.0 — medido no arquivo, não no retorno da ferramenta.

## Como reproduzir

```bash
cd "C:/Users/Correta Engenharia/Desktop/Mapeamento AutoCad/codigo"
# 1. abra o AutoCAD 2025 e deixe um desenho aberto
# 2. verifique a ponte: cat "$TEMP/cad_mcp_bridge.json"  (precisa existir)
# 3. rode a bateria
PYTHONPATH=src python3 tools/bateria_ao_vivo.py
```

Sem AutoCAD aberto o backend cai no ezdxf e **todos** os passos de edição
falham — a bateria não mede nada útil.

## O que esta auditoria NÃO provou

- **As 9 lacunas da seção acima podem existir no COM** e só não foram
  implementadas. O mapa `docs/MAPA-COM.md` diz que `IAcadBlock.AddEllipse` e
  `IAcadBlock.AddDimAngular` **existem** — então `entity_create_ellipse`,
  `dimension_angular` e `dimension_radius` são lacuna de implementação, não
  limite da API. Escalar isso é o próximo trabalho de maior valor.
- `image_attach` só foi medido uma vez; o travamento precisa ser reproduzido em
  contexto limpo antes de tratar como defeito permanente.
- As 13 falhas "artefato do meu teste" foram reprovadas com argumento errado,
  não re-testadas com o argumento certo (viewport/xref/pdf/page_setup funcionam
  quando chamados corretamente — ver `viewport_create` ok e `plot_pdf` ok com
  escala que cabe).

---

# Segundo turno — as 9 lacunas fechadas

Mesmo dia, após a auditoria acima. As 9 ferramentas que devolviam
`Not supported on this backend` foram implementadas no `com_backend.py`, cada uma
**medida contra o AutoCAD aberto**.

## Resultado

| ferramenta | como foi implementada | prova |
|---|---|---|
| `entity_create_ellipse` | `entmakex` com ELLIPSE do DXF (grupo 11 = eixo maior, 40 = razao) | DXF de volta: tipo `ELLIPSE`, razao `0.5`, eixo `[6,0,0]` |
| `dimension_angular` | `IAcadBlock.AddDimAngular` | `DIMENSION` criado |
| `dimension_radius` | `IAcadBlock.AddDimRadial` | `DIMENSION` criado |
| `entity_scale` | `IAcadEntity.ScaleEntity` | reta 10 m -> 20 m (grupo 11 medido) |
| `entity_chamfer` | geometria propria: interseccao + `entmod` | reta (120,0)->(119,0) e (120,0)->(120,1), bisel criado |
| `entity_array_rectangular` | `IAcadEntity.ArrayRectangular` | contagem 8 -> 13 (+5 = 2x3 - 1) |
| `block_define` | `Blocks.Add` + `AddLine`/`AddCircle`/`AddAttribute` | bloco criado com `LINE|CIRCLE|ATTDEF` |
| `block_get_attributes` | ATTDEF da definicao do bloco, por `entget` | `{"COD": {"valor": "A1", "prompt": "Codigo", "altura": "0.5"}}` |
| `block_set_attributes` | `entmod` no ATTDEF da definicao | valor `A1` -> `Q7`, lido de volta |

**9/9 pelas ferramentas da camada MCP** (nao pelo backend), com o backend COM.

## O que mudou no comportamento

### `block_insert` agora seta `ATTDIA=0` e `ATTREQ=0`

Um bloco com ATTDEF pede o valor de cada atributo ao ser inserido. Sem
`ATTDIA=0` o AutoCAD abre dialogo modal; sem `ATTREQ=0` ele para no prompt de
linha de comando. **Nos dois casos a sessao trava inteira** — foi o que travou o
AutoCAD tres vezes durante este trabalho.

### Atributos de INSERT: por que ler da definicao e nao do INSERT

`IAcadBlockReference.GetAttributes` devolve um safearray em variant. Quando o
INSERT nao materializou atributos, o limite do array e' **-1** e qualquer
iteracao em LISP responde `bad argument type: VLA-object collection`. Como o
AutoLISP nao tem como distinguir "INSERT sem atributos" de "variant vazio",
`block_get_attributes`/`block_set_attributes` leem e escrevem os **ATTDEF da
definicao do bloco** — que e' o template, nao tem esse problema e atende o caso
de uso (saber/conferir o que o bloco carrega).

### CHAMFER nao da por comando

`CHAMFER` nao aceita as duas retas por argumento e a pre-selecao com
`sssetfirst` **nao e' consumida** por ele — medido: as retas ficam intactas e o
comando devolve ok. A implementacao e' geometrica: interseccao das duas retas,
`dist1`/`dist2` ao longo de cada uma, pontas reescritas com `entmod`, reta do
bisel criada.

## As armadilhas que este turno mediu

1. **`vla-GetAttributes` vazio trava a iteracao, nao o `vlax-for`.** Sintoma:
   `bad argument type: VLA-object collection: #<variant 8201 ...>`. O diagnostico
   e' medir `vlax-safearray-get-u-bound` — se der `-1`, o array esta' vazio.
2. **`(entlast)` devolve nil quando a criacao falha** e o erro seguinte e'
   `bad argument type: lentityp nil` — engana: parece erro de tipo, e' criacao
   que nao aconteceu.
3. **`vla-InsertBlock` com bloco de ATTDEF trava** se `ATTDIA`/`ATTREQ` nao
   estiverem em 0. Nao e' erro do metodo: e' prompt de atributo.
4. **`AddAttribute` aceita `(Height, Mode, Prompt, InsertionPoint, Tag, Value)`**
   — o `InsertionPoint` vem **depois** do `Prompt`, nao antes.
5. **A_ssinaturas se medem na type library, nao no catalogo gerado.**
   `docs/com-acad-2025.json` lista os nomes dos metodos mas nao os parametros.
   O caminho que funcionou: `comtypes.client.GetModule` em
   `C:\Program Files\Common Files\Autodesk Shared\acax25enu.tlb` e ler
   `paramflags` de cada `_ComMemberSpec`.

## Reprodutor das 9

`codigo/tools/sonda_lacuna.py <nome>` executa uma lacuna por vez com o AutoCAD
aberto. Os nomes: `ellipse`, `dimangular`, `dimradius`, `scale`, `chamfer`,
`array`, `blockdefine`, `attrs`.
