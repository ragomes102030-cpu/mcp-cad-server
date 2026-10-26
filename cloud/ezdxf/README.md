# mcp-cad-cloud

Versão **cloud-ready** do `mcp-cad-server`: expõe as ferramentas de mapeamento
planta/quantitativo do AutoCAD via **MCP HTTP** (FastMCP), sem depender de
AutoCAD, COM, pywin32 ou Windows.

Tecnologia: `ezdxf` headless (luz, sem licença) + `FastMCP` (HTTP). Rodável
em Linux (Render, Docker, Ubuntu, etc.).

## Arquitetura

```
Claude Code / LibreChat / MCP client
   │  HTTP POST http://<host>:8000/mcp
   ▼
mcp-cad-cloud (FastMCP, transport=http, port=8000)
   │  chamadas das ferramentas (ex: draw_line, query_entities, quantitativo)
   ▼
ezdxf (headless) → desenho em memória → DXF/DWG → PDF/PNG
```

## Dependências

```
fastmcp>=2.0      # MCP HTTP server
ezdxf>=1.0        # motor headless de leitura/escrita DXF
```

## Rodar localmente

```bash
cd mcp-cad-cloud
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .      # pyp사와의 설치
.venv\Scripts\python.exe -m mcp_cad_cloud.server  # HTTP 127.0.0.1:8000
```

## Deploy no Render

Arquivo `render.yaml` (Render's MCP config):

```yaml
services:
  - type: web
    name: mcp-cad-cloud
    env: python
    buildCommand: pip install -e .
    startCommand: python -m mcp_cad_cloud.server
    envVars:
      - key: PORT
        value: 8000
      - key: CAD_BACKEND
        value: ezdxf
```

No Render Dashboard:
1. Criar um novo service → `mcp-cad-cloud` (Git branch: `cloud/ezdxf`).
2. A build e o start rodam automaticamente.
3. O MCP fica disponível em `https://mcp-cad-cloud.onrender.com/mcp`.

## Ferramentas disponíveis (resumo)

| Categoria | Ferramentas |
|---|---|
| Desenho | `draw_line`, `draw_rectangle`, `draw_polyline`, `draw_circle`, `draw_arc`, `draw_text`, `draw_mtext`, `draw_hatch` |
| Dimensionamento | `dim_linear`, `dim_aligned` |
| Camadas | `layer_list`, `layer_create`, `layer_set_current`, `ensure_standard_layers` |
| Blocos | `block_list`, `block_insert`, `block_attributes`, `block_set_attribute` |
| Estampa | `export_dxf`, `plot_pdf`, `render_png`, `screenshot` |
| Undo/Redo | `undo`, `redo`, `zoom_extents` |
| Quantitativo | `quantitativo` (contagem de entidades por tipo) |

> O contrato completo está em `cad_mcp.CONTRATO` (versão original). Esta soma
> mantém a compatibilidade com os prompts/stills do CADCraft.
