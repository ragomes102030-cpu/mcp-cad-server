# Avisos de terceiros

Este pacote usa ou inclui os componentes abaixo. Nenhum deles foi escrito por
Correta Engenharia.

| componente | versao | licenca | onde | uso |
|---|---|---|---|---|
| `autocad-mcp-pro` | 1.6.0 | MIT (© 2026 Umutcan Edizsalan) | `codigo/src/autocad_mcp/` (vendorizado) e `codigo/vendor/` (copia de referencia) | base do motor headless (`ezdxf`) e do IPC de arquivo |
| `puran-water/autocad-mcp` | — | MIT (© 2024 AutoCAD MCP Server Contributors) | `codigo/vendor/puran-water/` (cópia de referência) | scripts LISP e Python usados como referência; **não** é importado pelo pacote |
| `fastmcp` | nao fixada | MIT | dependencia (PyPI) | servidor MCP (stdio) |
| `mcp` | nao fixada | MIT | dependencia (PyPI) | protocolo MCP |
| `ezdxf` | nao fixada | MIT | dependencia (PyPI) | leitura/escrita de DXF headless |
| `shapely` | nao fixada | BSD-3-Clause | dependencia (PyPI) | geometria (offsets/booleans) |
| `matplotlib` | nao fixada | PSF-based (BSD-compativel) | dependencia (PyPI) | render PNG |
| `pillow` | nao fixada | MIT-CMU (HPND) | dependencia (PyPI) | imagem |
| `pywin32` | nao fixada | PSF (BSD-compativel) | dependencia (PyPI, so Windows) | COM com o AutoCAD |

## Texto da licenca do componente vendorizado

O `LICENSE` do `autocad-mcp-pro` esta reproduzido na integra em
`codigo/vendor/autocad-mcp-pro-1.6.0/LICENSE` e, resumido, no fim do
`LICENSE` deste projeto.

## Observacao sobre o pacote `autocad_mcp`

O pacote `autocad_mcp` e distribuido **dentro** da wheel `mcp_cad_server`
porque o backend headless o importa (`from autocad_mcp.backends...`). Se a
maquina ja tiver o `autocad-mcp-pro` instalado por pip, os dois disputam o
mesmo nome de import: desinstale um dos dois antes de rodar.
