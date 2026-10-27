# MCP CAD Cloud — DXF verificado (ezdxf)

MCP HTTP headless, privado, single-user, para Render/Linux. Não controla AutoCAD Windows, não edita DWG, não exporta PDF.

**Autenticação obrigatória:** configure a variável secreta `CAD_MCP_AUTH_TOKEN` (mínimo 24 caracteres) no Render antes do deploy. A rota `/healthz` é pública, o protocolo `/mcp` exige Bearer Token.

As únicas ferramentas publicadas são as de `mcp_cad_cloud.tools_verified.TOOLS`.
O catálogo `tools.py` é histórico e experimental, porque inclui stubs que indicam sucesso sem modificar o desenho.

Render (serviço Python):
- Branch: cloud/ezdxf
- Build command: `pip install -e ./cloud/ezdxf`
- Start command: `python -m mcp_cad_cloud.server`
- Health check: `/healthz`
- HTTP bind: `0.0.0.0:$PORT` (definido pelo Render)

Testes: `PYTHONPATH=cloud/ezdxf pytest -q cloud/ezdxf/tests/test_verified.py`

**Limites:** estado em memória compartilhada, sem persistência ou isolamento multiusuário. Reinício ou `new_drawing` apagam o desenho não exportado. Para uso em produção ampliada, implementar persistência por projeto, versionamento e auditoria.
