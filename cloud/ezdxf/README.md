# MCP CAD Cloud — DXF headless

Servidor MCP HTTP para Render/Linux, baseado em `ezdxf`. Não controla
AutoCAD Windows, não edita DWG e não acessa arquivos do computador local.

## Acesso

Nesta versão de teste `/healthz` e `/mcp` são públicos, sem Bearer Token.
O estado é temporário em memória e compartilhado pelo processo. Antes de
usar dados sensíveis, adicionar autenticação e isolamento por projeto.

## Deploy no Render

- Branch: `cloud/ezdxf`
- Build: `pip install -e ./cloud/ezdxf`
- Start: `python -m mcp_cad_cloud.server`
- Health check: `/healthz`
- Endpoint MCP: `/mcp`

## Testes

```powershell
$env:PYTHONPATH = "cloud/ezdxf"
python -m pytest cloud/ezdxf/tests -q
```

Verificação pós-deploy:

```powershell
python tools/verify_cloud_release.py --url https://SEU-SERVICO.onrender.com/mcp
```

O comando verifica versão, revisão, backend, transporte e uma requisição real
de `initialize` sem Bearer Token.
