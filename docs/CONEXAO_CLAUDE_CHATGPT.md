# Conexão dos MCPs CAD

## MCP local

Use `instalacao/mcp-config.json` no cliente local. Ele inicia o servidor
`cad-mcp` por `stdio` e pode usar AutoCAD 2025 quando ele estiver aberto.
Esse servidor é o único que opera por COM e salva DWG.

## MCP cloud

No Claude ou ChatGPT compatível com MCP, informe a URL pública do serviço
Render terminando em `/mcp` e selecione **sem login** nesta versão de teste.
O cloud usa `ezdxf`, gera DXF e mantém estado temporário em memória. Ele não
abre AutoCAD, não lê o computador local e não deve receber dados sensíveis.

## Conferência da versão

Na pasta-mãe, execute:

```powershell
python tools/verify_cloud_release.py --url https://SEU-SERVICO.onrender.com/mcp
```

O comando verifica versão, revisão, backend, transporte e uma requisição real
de `initialize` sem Bearer Token. Se a revisão não coincidir, o Render ainda
está servindo uma implantação antiga.
