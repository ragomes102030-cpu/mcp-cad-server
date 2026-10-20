# Mapa do CadMcpBridge — o plugin proprio, medido ao vivo

Gerado em **2026-10-20T19:17:16-03:00** por `tools/sonda_cadbridge.py`.
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

- AutoCAD aberto: **não**
- desenho ativo: `—`
- arquivo da ponte: `C:\Users\CORRET~1\AppData\Local\Temp\cad_mcp_bridge.json` — **ausente**
- plugin carregado nesta sessão: **não**

## 3. Superfície medida

Nada medido: o plugin não estava carregado nesta sessão.

O `%TEMP%\cad_mcp_bridge.json` só existe depois que o Autoloader carrega o
`.bundle` no início de uma sessão do AutoCAD — e o arquivo de uma sessão
antiga não responde na porta. **Ausência medida, não presumida.**

## 4. O que isto não cobre

- **As 7 tools do MCP oficial da Autodesk** não podem ser medidas aqui:
  `C:\Program Files\Autodesk\ApplicationPlugins` não existe e a máquina tem AutoCAD 2025 (o MCP oficial é do 2027). Ver
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

