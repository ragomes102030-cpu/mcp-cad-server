# Mapa do AutoCAD — o que é durável

O mapa completo é gerado (`docs/MAPA-COM.md`, `docs/com-acad-2025.json`,
`docs/ALIASES.md`, `docs/COBERTURA.md`) e **não viaja com a skill**: são 1,8 MB e
mudam a cada versão. O que viaja é isto — as conclusões que não mudam.

## Números de referência (AutoCAD 2025, lido da type library)

| | |
|---|---|
| interfaces COM | 148 |
| métodos | 632 |
| propriedades | 1713 |
| apelidos (`acad.pgp`) | 411 |
| comandos citados em macro de menu | 630 |
| desses, usados com `-` (linha de comando) | 13 |

## A fronteira que decide o desenho do código

**Já é método COM** (não precisa de comando, nem de plugin, nem de foco):

`Offset` (Line/Arc/Circle/Ellipse/LWPolyline/Polyline), `Move`, `Copy`,
`Rotate`, `Mirror`, `Erase`, `ArrayPolar`, `ArrayRectangular`, `ScaleEntity`,
`TransformBy`, `Explode`, `GetBoundingBox`, `IntersectWith`.

**Não existe método nenhum** — só comando:

`TRIM`, `EXTEND`, `FILLET`, `CHAMFER`, `JOIN`, `STRETCH`.

Consequência prática: `TRIM`/`EXTEND` podem ser **calculados** com
`IntersectWith` + reescrever os pontos da entidade; `FILLET`/`CHAMFER`/`JOIN`
precisam de comando (plugin .NET, em processo) ou geometria própria.

## Fatos que evitam uma rodada perdida

- **`ModelSpace` e `PaperSpace` são `IAcadBlock`** — não existe `IAcadModelSpace`.
  `AddLine`, `AddCircle`, `AddText` moram em `IAcadBlock`.
- **Método herdado aparece só na interface base**: `GetBoundingBox` está em
  `IAcadEntity`, não em `IAcadLine`.
- **`AcadDocument.Wblock(path, selectionSet)` existe** — `WBLOCK` sem diálogo é
  API, não precisa de comando.
- **`AcadDocument.Export` / `Import`** cobrem DXF/DWG/PDF sem `-PLOT`.
- `PostCommand` = `SendCommand` (mesma semântica de espaço virando ENTER).
- Antes de qualquer chamada: `FILEDIA=0` e `CMDDIA=0`. `CMDACTIVE≠0` significa
  comando em andamento — não chamar COM agora.
- Variantes `-` comprovadamente usadas nos menus do próprio produto: `-ARRAY`,
  `-ATTEDIT`, `-BEDIT`, `-DIMSTYLE`, `-HATCHEDIT`, `-POINTCLOUDMANAGER`,
  `-PURGE`, `-SHADEMODE`, `-TOOLBAR`, `-VIEW`, `-VPOINT`, `-VPORTS`.

## Como regerar

```powershell
python tools\mapear_com.py      # sem AutoCAD: type library + pgp + cui
python tools\importar_acmpro.py # sem AutoCAD: cobertura 45 x 247
python tools\sonda_autocad.py   # com AutoCAD aberto: comandos reais + sysvars
```

O mapa envelhece: o `acadver` e o `quando` estão no JSON para não confundir
versão. Ao trocar de AutoCAD, rode de novo antes de confiar no número.

## Medido ao vivo (16/10/2026, AutoCAD 25.0)

`tools/sonda_autocad.py`, com o desenho aberto, gerou `docs/MAPA-AUTOCAD.md`:

- **863** comandos distintos (uniao de `C:` em LISP + macros do CUIX + apelidos do pgp);
  **13** so existem na forma `-COMANDO` no menu.
- **821** variaveis de sistema vivas, de 884 candidatas (as 63 restantes respondem `nil`).
- Sysvars **nao sao enumeraveis** por API. Os nomes vieram dos recursos da
  instalacao (`MsiKeyFile_<NOME>.dll`), do `$VARS` do DXF e de uma lista curta das
  classicas; o valor do `getvar` e que confirma a existencia.

### O que isso muda na pratica

- **TRIM/EXTEND/FILLET por comando + ponto digitado nao e' confiavel.** O comando
  volta sem erro e nao corta. Ponto digitado nao substitui o clique. O caminho
  certo e' geometria: `IntersectWith` + `Curve.GetSplitCurves` e apagar o trecho.
- **Estado do AutoCAD nao e' o padrao de fabrica.** Nesta maquina `FILEDIA` e
  `CMDDIA` estavam `0` e `OSMODE` `0`. Nao assumir: ler antes.
- Comando que espera selecao **nao pode** ser chamado por `Editor.Command`
  sincrono: ele trava o AutoCAD inteiro. Usar `SendStringToExecute`.

## Frescor: o mapa envelhece em silêncio

`MAPA-*.md`, `COBERTURA.md` e `catalogo-*.json` sao **artefatos gerados**. O codigo
muda mais rapido que eles e **nao existe checagem automatica** — o mapa envelhece sem
ninguem perceber. Antes de citar um numero do mapa, compare o `mtime`:

| papel | arquivo |
|---|---|
| fonte da verdade | `codigo/src/cad_mcp/com_backend.py`, `tools_geo.py`, `tools*.py` |
| derivado (pode estar velho) | `docs/MAPA-COM.md`, `docs/COBERTURA.md`, `docs/catalogo-*.json` |

Derivado mais velho que a fonte => **o numero esta velho**, regenere antes de usar.
O `MAPA-COM.md` que diz "`chamfer` nao tem metodo COM" e correto e enganoso ao
mesmo tempo: e' verdade que nao ha metodo, mas o codigo implementa por **geometria
propria** (`entmod`). O mapa nao reflete o mecanismo real.

Quando o pedido for "a pasta esta atualizada?", a resposta se mede em tres passos:
(1) `git status` do repo, (2) `mtime` dos derivados contra a fonte, (3) contagem de
ferramentas lida do fonte.

### Contar ferramentas do fonte (nao confie no numero escrito)

```bash
cd <repo>/codigo && PYTHONPATH=src python -c "from cad_mcp import tools; print(len(tools.TOOLS), len(tools._publicos))"
```

`TOOLS` e a lista declarada em `tools.py` + `tools_ext.py` + `tools_plot.py` +
`tools_geo.py`; `_publicos` aplica `NOMES` (o vocabulario `autocad-mcp-pro`). Os dois
devem ser iguais e sem duplicados — se diferirem, ha nome publico colidindo.

### Auditar cobertura de backend

```bash
PYTHONPATH=src python tools/auditar_cobertura_real.py   # grava auditoria_backend.json
```

`ModuleNotFoundError: No module named 'ezdxf'` = voce esta no python errado. Ache o
interpretador que o servidor MCP **usa de fato** no processo em execucao:

```powershell
Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
  Where-Object { $_.CommandLine -like '*cad_mcp*' } | Select CommandLine
```

O `CommandLine` traz o `sys.path` injetado pelo launcher — use aquele python, nao o
`python` do PATH (que nao tem as dependencias do servidor).

### A auditoria e estatica e subnotifica

`auditar_cobertura_real.py` le o codigo, nao executa. Ferramentas implementadas
**pela ponte .NET** (`entity_trim`, `entity_extend`, `entity_fillet`) aparecem como
"sem backend" mesmo funcionando — o caminho sai do `com_backend.py` e vai para
`Ponte()`. O mesmo vale para qualquer implementacao que delegue. Trate `sem_backend`
como **suspeita**, nao como lacuna provada: confirme ao vivo antes de registrar.

### Lacuna real se confirma por grep no backend

Antes de dar uma ferramenta por existente, procure o nome da funcao no
`com_backend.py`. `layer_modify`, `plot_style_list` e `arch_rooms_detect` (este usa
`_area_fechada`, so no ezdxf) nao tem implementacao COM. Registre a lacuna no mapa
**e** no `historico/ocorrencias.jsonl` — sem os dois o mapa volta a mentir.
