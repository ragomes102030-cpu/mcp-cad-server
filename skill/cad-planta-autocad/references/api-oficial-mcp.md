# A camada oficial: API da Autodesk e MCP oficial do AutoCAD

Este arquivo é o **resumo acionável**. A fonte completa, com evidência por afirmação,
está em `docs/MAPA-OFICIAL-MCP.md` (projeto `mcp-cad-server`).

## O que o AutoCAD expõe de oficial

| API | Linguagem | Onde roda | Nota |
|---|---|---|---|
| **ObjectARX** | C++ | dentro (CRX/DBX) | a base de tudo |
| **AutoCAD .NET API** | C#/VB | dentro (`acdbmgd`/`acmgd`/`accoremgd`) | mesmo modelo de objetos do COM |
| **AutoLISP / Visual LISP** | LISP | dentro | o que 90% das automações de DWG usam |
| **COM / ActiveX** | qualquer cliente COM | **fora**, Windows, AutoCAD aberto | é o motor deste projeto (`com_backend.py`) |

Nuvens oficiais: **AutoCAD JavaScript API** (web), **AutoCAD on the web + AutoLISP**
(browser), **APS Design Automation API** (`accoreconsole.exe` headless; **sem
verticais** — Civil 3D/Architecture/Mechanical não existem lá; **sem COM, sem UI**).

## MCP oficial Autodesk (AutoCAD e Civil 3D)

Existe, é oficial, roda **dentro** do AutoCAD/Civil 3D (Windows), status
**Tech Preview (Public Beta)**. Doc: `help.autodesk.com/view/ADSKMCP/ENU/`.

| Tool | Faz | Config |
|---|---|---|
| `discoverAutoCADTypes` | schema dos tipos — **chamar primeiro** | Default |
| `queryAutoCADObjects` | busca com filtro, paginação, level queries | Default |
| `aggregateAutoCADObjects` | count/sum/avg/min/max agrupado — **usar esta, não `query`** | Default |
| `manipulateDrawingCanvas` | `showme`, `select`, `unselect`, `getSelection`, `zoomExtents`… | Default |
| `checkAutoCADObjects` | compara o desenho com um **template** → padronização | Default |
| `updateAutoCADObjects` | modifica objetos | **Civil 3D only** |
| `civil3dQueryModifyStyles` | estilos Civil 3D | **Civil 3D only** |

Regras que quebram o agente se ignoradas:

- Filtro: `=`, `!=`, `<`, `>`, `contains`, `startswith`, `endswith`, `AND`, `OR`;
  `AND` tem precedência; **sem parênteses**; texto case-insensitive; `= null` filtra nulo.
- **`context` default é a seleção atual**, não o desenho inteiro. Sem
  `context: "drawing"` a estatística sai parcial e o agente não avisa.
- Sem parâmetro de locale: a língua vem do client. Valores voltam nas unidades do desenho
  (`LUNITS`/`AUNITS`) — reportar como veio.
- Handle é volátil: só vale na mesma sessão. Não persistir.

## O limite que decide projeto

**Em AutoCAD puro o MCP oficial é leitura/análise — não desenha geometria nova.**
Desde set/2026 ele também cria/apaga camadas, muda propriedade de camada, move objetos
de camada e seta variáveis de sistema. Ou seja: lê tudo, arruma camada, **não desenha**.

Consequência para este projeto: **o MCP oficial não substitui o COM do `com_backend.py`**.
Ele cobre auditoria e padronização; o desenho continua sendo COM, AutoLISP ou plugin
.NET.

## O que a Autodesk não suporta

| Restrição | Onde | Efeito |
|---|---|---|
| AutoLISP ausente | **AutoCAD LT for Mac** | suporte a AutoLISP começa no **AutoCAD LT 2024 (Windows)**; LT Mac nem LSP/FAS/VLX |
| Sem ActiveX/COM | **AutoCAD for Mac** | `vlax-*` não existe; `com_backend.py` é **Windows-only** |
| Sem verticais | Automation API (nuvem) | Civil 3D, Architecture, Mechanical, P&ID não existem no accoreconsole |
| Sem COM/UI | Automation API (nuvem) | nada de `ActiveDocument` nem foco de janela |
| Por arquivo, não por desenho vivo | Automation API (nuvem) | roda sobre um arquivo enviado |

## Veredito de instalação (medido 2026-10-20)

| item | resultado |
|---|---|
| AutoCAD | `C:\Program Files\Autodesk\AutoCAD 2025\acad.exe`, **R25.0.162.0.0** |
| `ACADVER` | `25.0s (LMS Tech)` |
| Plugin oficial `AutoCAD-MCP-Server` | **não existe** nesta máquina (é do 2027) |
| Único bundle MCP presente | `AppData\Roaming\Autodesk\ApplicationPlugins\CadMcpBridge.bundle` — **plugin próprio do projeto**, não o oficial |
| `accoreconsole.exe` | presente |

**Não invente cobertura do MCP oficial nesta máquina.** A camada oficial aqui é
documentada, não medida.

## Pitfalls

- **Não confunda "existe documentação" com "existe na minha instalação".** O MCP
  oficial é Tech Preview e depende de build; a doc descreve a intenção, não a sua máquina.
- **Não confunda MCP com API.** MCP não dá acesso novo ao AutoCAD; só padroniza a chamada.
- **CadMcpBridge ≠ MCP oficial.** Nomes parecidos, projetos diferentes.
- **`updateAutoCADObjects` / `civil3dQueryModifyStyles` são Civil 3D only.** Em AutoCAD
  puro a config Default só lê e analisa.
- **Accoreconsole não tem COM nem UI** — automação em nuvem não pode depender de
  `ActiveDocument`.
