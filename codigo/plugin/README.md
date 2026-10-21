# CadMcpBridge — o braço de edição

Plugin .NET 8 que roda **dentro** do AutoCAD e expõe uma ponte JSON-RPC em
`127.0.0.1`. É o que faltava para `TRIM`, `EXTEND`, `FILLET`, `CHAMFER`, `BOUNDARY`:
comandos que **não são métodos de API** e que, por COM, dependem de foco, sofrem
com espaço virando ENTER e travam em diálogo.

Dentro do processo, o comando roda por `SendStringToExecute` — o mesmo que digitar
na linha de comando, só que sem roubar o foco. Devolve `{ok, duracao_ms, desenho}`
na hora, com `FILEDIA`/`CMDDIA` em 0 e restaurados quando o comando fica ocioso.

**Não confirma o resultado.** Se o comando cortou, apagou ou falhou, a resposta
`ok: true` só diz que ele foi enviado. Para decidir alguma coisa, meça a geometria
depois (`GetBoundingBox`, contagem de entidades).

## Arquitetura

```
Python (MCP)  --TCP 127.0.0.1:8765, 1 linha JSON-->  CadMcpBridge.dll (no acad.exe)
   cad_mcp/bridge.py                                  ├ Ponte.Exec      (comando + pontos)
                                                      ├ Ponte.Transacao (handle: move/copy/erase/rotacao/prop)
                                                      └ Ponte.Info      (versao, desenho, INSUNITS)
```

- Porta 8765–8789 (a primeira livre). Token novo a cada carga, escrito em
  `%TEMP%\cad_mcp_bridge.json` junto com a porta. Sem HTTP, sem porta na rede.
- Trabalho sempre no thread principal (`ExecuteInApplicationContext`): o
  `Editor` só existe lá.
- Autoloader do AutoCAD (`.bundle`), **não** NETLOAD: nada de diálogo na carga.

## Instalar

```powershell
powershell -ExecutionPolicy Bypass -File plugin\deploy.ps1
```

Compila (SDK .NET 8 local, sem admin) e copia para
`%APPDATA%\Autodesk\ApplicationPlugins\CadMcpBridge.bundle` para o usuário.

**Feche e abra o AutoCAD UMA vez.** O `.bundle` só é carregado no início da sessão.

## Conferir

No AutoCAD: comando `MPCBRIDGE` → `CadMcpBridge: ativa em 127.0.0.1:8765`.

```powershell
$env:PYTHONPATH="src"
python -m cad_mcp.bridge ping
python -m cad_mcp.bridge exec "_.ZOOM _E"
python -m cad_mcp.bridge transacao '[{"op":"erase","handle":"1A2"}]'
```

No dia a dia é transparente: a ferramenta `system_run_command` usa a ponte
quando ela existe e cai para o modo headless quando não existe.

## Limites (honestos)

| limite | consequência |
|---|---|
| build por versão do AutoCAD | 2025 = net8.0-windows + `acdbmgd`/`acmgd` da pasta; 2026 refaz o build |
| roda no mesmo processo | se o plugin travar, leva o AutoCAD junto (por isso todo `catch` devolve erro em vez de subir) |
| comando é comando | `Editor.Command` ainda é linha de comando: seleção implícita pode pegar objeto errado; para previsibilidade total, geometria própria (`arch.py`) |
| texto com espaço | `exec` divide o comando por espaço; string com espaço (conteúdo de TEXT) não passa por aqui — use `entity_create_text` |
| primeiro comando depois do load | pode ser mais lento (JIT do assembly) |

## O que está testado

- **compila** contra o AutoCAD 2025 instalado (`dotnet build` limpo);
- **protocolo do cliente** (`tests/test_bridge.py`): uma linha, token errado,
  arquivo ausente, porta morta, resposta vazia;
- **instalação**: `.bundle` + `PackageContents.xml` no lugar, DLL copiada.

**Não testado ainda:** a carga real no AutoCAD e um `TRIM` de verdade — exige
reiniciar o AutoCAD (Autoloader). Primeiro teste depois do restart:

```powershell
python -m cad_mcp.bridge ping
```

Se `%TEMP%\cad_mcp_bridge.json` não aparecer, veja `%TEMP%\cad_mcp_bridge.log`
(erros de carga) e confira `SECURELOAD`/`TRUSTEDPATHS`.

## O que so apareceu com o AutoCAD de verdade (16/10/2026)

1. **`System.Text.Json` nao existe no runtime do `acad.exe`** (so em `BFMigrator`).
   A DLL carregava e morria calada: o JIT de `Iniciar()` estourava dentro do
   `try/catch` do `Initialize`. Agora o JSON e proprio (`Json.cs`) e o `catch`
   grava em `%TEMP%\cad_mcp_bridge.log`.
2. **`SECURELOAD=1` bloqueia DLL sem assinatura.** Aparece o dialogo
   *Security - Unsigned Executable File* e o AutoCAD **nao termina de subir** (COM
   incluso). Com `TRUSTEDPATHS` incluindo
   `%APPDATA%\Autodesk\ApplicationPlugins`, o Autoloader carrega sem perguntar.
   O `deploy.ps1` **nao** mexe nisso: e escolha do usuario.
3. **`Editor.Command` sincrono trava o AutoCAD** quando a entrada acaba antes do
   comando (TRIM esperando a proxima selecao). Nao volta, nao da erro, e o
   processo tem que ser morto. Por isso o `exec` passou a usar
   `SendStringToExecute` (assincrono).

### Estado real das partes

| parte | estado |
|---|---|
| carregar no AutoCAD | funciona (Autoloader + TRUSTEDPATHS) |
| `ping` / `info` | testado, responde |
| `exec` | envia o comando e volta; **nao confirma** se cortou/desenhou |
| `transaction` | implementado; **nao testado** com o AutoCAD aberto |
| TRIM/EXTEND/FILLET por comando | **nao confiavel** com ponto digitado (ver `historico/`) |
