# INSTALAR — mcp-cad-server (roteiro para agente)

> **Para o agente que vai executar isto:** rode os passos na ordem, no PowerShell.
> Cada passo tem um **esperado**. Se o esperado não bater, **pare** e reporte o erro
> literal — não invente caminho, não troque de Python, não "contorne" com outro pacote.
> Nada aqui exige administrador.

---

## 0. O que você está instalando

- Servidor MCP (stdio) com **48 ferramentas** para desenhar/editar no AutoCAD.
- Três motores, escolhidos automaticamente:
  - **COM** — fala com o AutoCAD aberto (precisa de AutoCAD 2025 + pywin32);
  - **headless** (`ezdxf`) — desenha e exporta sem AutoCAD;
  - **ponte .NET** (opcional) — plugin dentro do AutoCAD, para `TRIM`/`EXTEND`.
- Licença **MIT** (`LICENSE`); componentes de terceiros em `THIRD_PARTY_NOTICES.md`.

Estrutura da pasta que você recebeu:

```
instalacao\   wheel + este roteiro + verificar_instalacao.py + mcp-config.json
codigo\       fonte (src, tests, vendor, docs)
docs\         cobertura de ferramentas e catálogo
skill\        skill cad-planta-autocad (regras e armadilhas)
historico\    ocorrências já pagas (não apague: é a memória do projeto)
plugin\       ponte .NET opcional (deploy.ps1)
exemplos\     desenhos de exemplo
```

## 1. Pré-requisitos

| item | mínimo | como conferir |
|---|---|---|
| Windows | 10/11, 64 bits | `[Environment]::Is64BitOperatingSystem` |
| Python | **3.10+**, 64 bits | `py -3 --version` |
| AutoCAD | 2025 (opcional) | abrir uma vez e fechar |
| espaço | ~500 MB | — |

Se `py` não existir, instale de `python.org` marcando **"Add python.exe to PATH"** e
reabra o PowerShell.

## 2. Copiar o pacote

Destino sugerido (sem espaço e sem acento — espaço quebra o `SendCommand`):

```
C:\Ferramentas\mcp-cad-server
```

Copie o **conteúdo** da pasta recebida para lá. Esperado: existir
`C:\Ferramentas\mcp-cad-server\instalacao\mcp_cad_server-0.1.0-py3-none-any.whl`.

## 3. Criar o ambiente e instalar a wheel

```powershell
cd C:\Ferramentas\mcp-cad-server
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .\instalacao\mcp_cad_server-0.1.0-py3-none-any.whl
```

**Esperado:** a última linha contém `Successfully installed ... mcp-cad-server-0.1.0 ...`.
Se aparecer erro de rede, repita uma vez; se persistir, pare e reporte.

## 4. Verificar (não abra o AutoCAD)

```powershell
.\.venv\Scripts\python.exe .\instalacao\verificar_instalacao.py
```

**Esperado:** cada linha com `[OK]` e, no fim, `RESULTADO: OK`.
As quatro ferramentas `entity_erase`, `entity_erase_filter`, `entity_move` e
`drawing_setup` precisam aparecer como `[OK] ferramenta presente`.
`[AVISO]` (AutoCAD fechado, pywin32 ausente) não impede instalação headless.

| se aparecer | causa | ação |
|---|---|---|
| `ModuleNotFoundError: cad_mcp` | instalou no Python global, não no venv | use **sempre** `.\.venv\Scripts\python.exe` |
| `respondeu tools/list com 0` | servidor quebrado | rode `python -m cad_mcp.server` e copie o erro |
| `esperava 45, veio N` | wheel antiga | reinstale a wheel desta pasta |

## 5. Registrar no cliente MCP

Use o **caminho absoluto** do Python do venv (não confie no PATH, `cad-mcp` pode não
estar lá):

```powershell
(Resolve-Path .\.venv\Scripts\python.exe).Path
```

Cole no cliente (AionUi, Claude Desktop, Cursor — todos usam o mesmo formato), trocando
`CAMINHO_DO_PYTHON` pelo resultado acima:

```json
{
  "mcpServers": {
    "mcp-cad-server": {
      "command": "CAMINHO_DO_PYTHON",
      "args": ["-m", "cad_mcp.server"],
      "env": {
        "MCP_CAD_TEMP": "C:/temp/mcp_cad_com"
      }
    }
  }
}
```

`instalacao\mcp-config.json` já é um bloco pronto nesse formato.

**Reinicie o cliente.** Teste pedindo ao agente: *"chame system_status e liste as
ferramentas"*. **Esperado: 48 ferramentas.**

> Se o cliente mostrar **0 ferramentas**, o problema é o handshake dele, não o servidor:
> o verificador do passo 4 já provou que o servidor responde 48. Confira o caminho do
> `command`, se o cliente não está "sandboxed" e reinicie-o.

## 6. AutoCAD (só se for usar o motor COM / editar o desenho aberto)

1. Abra o AutoCAD uma vez e feche. Sem isso o COM pode não responder na primeira vez.
2. **TRUSTEDPATHS** (obrigatório se for usar o plugin; recomendado sempre):
   `OPÇÕES` → `Arquivos` → `Locais confiáveis` → adicione:

   ```
   %APPDATA%\Autodesk\ApplicationPlugins
   %TEMP%\mcp_cad_com
   ```

   Sem isso o `SECURELOAD` bloqueia DLL não assinada, aparece o diálogo
   *Security - Unsigned Executable File* e o AutoCAD **não termina de subir**.
3. **Plugin opcional** (habilita `TRIM`/`EXTEND`/`FILLET`):

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\plugin\deploy.ps1
   ```

   Precisa do **.NET 8 SDK**. Depois **feche e abra o AutoCAD** (o `.bundle` só carrega
   no início da sessão). Confira:

   ```powershell
   .\.venv\Scripts\python.exe -m cad_mcp.bridge ping
   ```

   Esperado: JSON com `ok: true` e a porta. Se falhar, veja `%TEMP%\cad_mcp_bridge.log`.

**Limites honestos do plugin:** o `exec` só *envia* o comando — não confirma se cortou;
`TRIM`/`EXTEND` por linha de comando **não é confiável** com ponto digitado. Para
previsibilidade, use a geometria própria (ferramentas `arch_*`/`entity_*`).

## 7. Primeiro desenho (teste de fumaça)

No cliente, peça:

> "Crie uma linha de (0,0) a (5,0), salve em C:\temp\teste_instalacao.dwg e exporte o DXF.
> Depois me diga quantas entidades existem na camada 0."

**Esperado:** `ok` nas três chamadas, os dois arquivos no disco e `1` entidade.
Sem AutoCAD, o DXF ainda é gerado (headless) — abra-o num visualizador DXF.

## 8. Escolher o motor

Vazio/ausente = `auto`. Para forçar, acrescente ao bloco `env` do passo 5:

```json
"MCP_CAD_BACKEND": "com"
"MCP_CAD_BACKEND": "ezdxf"
```

`com` exige AutoCAD instalado e aberto; `ezdxf` desenha sem AutoCAD, mas o DWG só é
aberto depois, no AutoCAD.

## 9. Problemas comuns

| sintoma | causa provável | ação |
|---|---|---|
| 0 ferramentas no cliente | `command` aponta para Python errado | passo 5, caminho absoluto, reiniciar cliente |
| `ModuleNotFoundError` | rodou com Python global | use `.\.venv\Scripts\python.exe` |
| AutoCAD não responde / trava ao abrir | `SECURELOAD` sem TRUSTEDPATHS | passo 6.2 e reabrir |
| PDF não atualiza | arquivo aberto no visualizador | feche o PDF; a ferramenta agora devolve `ok=false` quando não regrava |
| erro ao salvar DWG | o desenho já está aberto em outra aba | feche a aba e repita |
| comando com caminho quebrado | pasta com espaço | use caminho sem espaço |
| DXF importa em mm | desenho sem `drawing_setup` | chame `drawing_setup(unidades=6, escala_cota=0.1)` após `drawing_new` |

## 10. Desinstalar

```powershell
.\.venv\Scripts\python.exe -m pip uninstall mcp-cad-server
Remove-Item -Recurse -Force C:\Ferramentas\mcp-cad-server
```

Remova o bloco do cliente MCP e, se instalou o plugin,
`%APPDATA%\Autodesk\ApplicationPlugins\CadMcpBridge.bundle`.

## 11. O que NÃO vem pronto (declarado)

- **versões de dependência não fixadas** — a instalação pega a última do PyPI; se o
  `fastmcp` mudar de major, pode quebrar. Gere um `requirements.lock` com
  `pip freeze` no ambiente que funcionou e reinstale a partir dele;
- **DLL do plugin não assinada** — depende de TRUSTEDPATHS;
- **testes automatizados** ficam em `codigo\tests\` e não vão na wheel;
- **`build\` e `dist\`** não são copiados (a wheel em `instalacao\` é a fonte).
