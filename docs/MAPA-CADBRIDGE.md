# Mapa do CadMcpBridge — o plugin proprio, medido ao vivo

Gerado em **2026-10-20T19:48:04-03:00** por `tools/sonda_cadbridge.py`.
É o par do `sonda_autocad.py`: aquele mede o AutoCAD, este mede a **superfície**
que o projeto expõe dentro dele.

## 1. Instalação

| item | valor |
|---|---|
| bundle | `C:\Users\Correta Engenharia\AppData\Roaming\Autodesk\ApplicationPlugins\CadMcpBridge.bundle` |
| PackageContents.xml | ok |
| nome / versão | CadMcpBridge / 1.0 |
| série | `R25.0` .. `R25.9` |
| load no startup | `True` |
| DLL | `C:\Users\Correta Engenharia\AppData\Roaming\Autodesk\ApplicationPlugins\CadMcpBridge.bundle\Contents\Windows\CadMcpBridge.dll` (45568 bytes) |
| TRUSTEDPATHS cobre o bundle | sim |

> Sem `TRUSTEDPATHS` o `SECURELOAD` bloqueia DLL não assinada e o AutoCAD
> **não termina de subir** (relato de campo do projeto, `plugin/README.md`).

## 2. Sessão

- AutoCAD aberto: **sim** (versão 25.0s (LMS Tech))
- desenho ativo: `Drawing1.dwg`
- arquivo da ponte: `C:\Users\CORRET~1\AppData\Local\Temp\cad_mcp_bridge.json` — presente
- plugin carregado nesta sessão: **sim**

## 3. Superfície medida

| método | resposta | latência |
|---|---|---|
| `ping` | `{"ok": true, "produto": "CadMcpBridge", "versao": "1.0", "acad": "25.0.0.0", "desenho": "Drawing1.dwg", "insunits": 4, "` | 424.6 ms |
| `info` | `{"ok": true, "produto": "CadMcpBridge", "versao": "1.0", "acad": "25.0.0.0", "desenho": "Drawing1.dwg", "insunits": 4, "filedia": 0, "cmddia": 0}` | 677.8 ms |
| `exec _.ZOOM _E` | `ok=True` | 414.6 ms |

Protocolo: **uma linha JSON por requisição** em `127.0.0.1`, resposta em uma
linha. Porta e token em `%TEMP%\cad_mcp_bridge.json`, escritos pelo plugin a
cada carga. Métodos: `ping`, `info`, `exec`, `transaction`.

> **`exec` não confirma resultado.** `ok: true` diz que o comando foi
> *enviado*; não diz se cortou, apagou ou desenhou. Para decidir, meça a
> geometria depois (contagem de entidades, `GetBoundingBox`).

## 4. O que isto não cobre

- **As 7 tools do MCP oficial da Autodesk** não podem ser medidas aqui:
  `C:\Program Files\Autodesk\ApplicationPlugins` não existe e a máquina tem 25.0s (LMS Tech) (o MCP oficial é do 2027). Ver
  `MAPA-OFICIAL-MCP.md`.
- **Se um comando enviado alterou o desenho** — o plugin não confirma.
- **Cobertura do `.bundle` em outras versões** — o `PackageContents.xml` declara
  `SeriesMin/SeriesMax`; isto não é medição de comportamento.

## Lacunas deste mapa

1. **`transaction` não foi exercitado ao vivo** — só o protocolo do cliente tem
   teste (`tests/test_bridge.py`, com um servidor falso).
2. **A carga real do `.bundle` não está provada por este script** — ele lê o
   `PackageContents.xml` e o registro, não o processo do AutoCAD.
3. **`MPCBRIDGE` (comando no AutoCAD) não é consultado** — é confirmação visual.

