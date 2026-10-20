# MAPA-OFICIAL-MCP.md — a API oficial Autodesk e o MCP oficial, como alvo de mapeamento

**Status:** alvo novo, **não mapeado ainda** (nenhum dos 4 mapas cobre isto).
**Data:** 2026-10-20
**Origem:** documentação oficial Autodesk (`help.autodesk.com/view/ADSKMCP/ENU/`,
`aps.autodesk.com`, `help.autodesk.com/view/OARX/2027/ENU/`) + relato de campo no
forum Autodesk. Ver `LEIA-ME-MCP.md` para a tabela de evidências por afirmação.

## Veredito de instalação — medido nesta máquina em 2026-10-20

Checagem direta, **antes** de qualquer afirmação sobre capacidade:

| item | resultado |
|---|---|
| AutoCAD instalado | `C:\Program Files\Autodesk\AutoCAD 2025\acad.exe`, file version **R25.0.162.0.0** |
| `ACADVER` (medido antes, `MAPA-AUTOCAD.md`) | `25.0s (LMS Tech)` |
| **Plugin oficial `AutoCAD-MCP-Server-2027.bundle`** | **não existe** — `C:\Program Files\Autodesk\ApplicationPlugins\` não existe; `find` por `*mcp*` em `Program Files\Autodesk` e em `AppData\Roaming\Autodesk` não acha nada |
| Único bundle MCP presente | `AppData\Roaming\Autodesk\ApplicationPlugins\CadMcpBridge.bundle` — **é o plugin próprio do projeto** (`plugin/CadMcpBridge` de `mcp-cad-server`), **não** o MCP oficial |
| `accoreconsole.exe` | presente em `C:\Program Files\Autodesk\AutoCAD 2025\` |

**Conclusão:** a máquina tem **AutoCAD 2025** e **não tem** o MCP oficial da Autodesk
(que é do 2027). Portanto **não é possível medir as 7 tools aqui** — a camada oficial é
documentada, não medida. Qualquer número de cobertura do MCP oficial nesta máquina seria
inventado.

**O que isto muda no plano:** `sonda_mcp_oficial.py` não tem alvo nesta instalação. O
trabalho que se faz aqui é (a) sondar **o que o plugin próprio expõe**, e (b) mapear a
superfície oficial como referência para quando houver AutoCAD 2027. Não confunda as duas
coisas — elas têm nomes parecidos e são projetos diferentes.

## Por que este arquivo existe

O projeto já mapeia o que o AutoCAD **faz**: `MAPA-COM` (632 métodos do COM),
`MAPA-DOTNET` (1572 tipos), `MAPA-ENTIDADES` (83 entidades / 2054 campos DXF),
`MAPA-AUTOCAD` (863 comandos / 821 variáveis vivas). Nada disso cobre **as portas de
entrada oficiais de fora**: qual superfície é *suportada pela Autodesk*, qual é
*documentada*, e o que mudou de versão para versão.

São perguntas de natureza diferente:

| pergunta | arquivo existente responde? | este arquivo responde |
|---|---|---|
| o que o COM consegue chamar? | **sim** (`MAPA-COM`) | — |
| o que cada entidade tem de campo? | **sim** (`MAPA-ENTIDADES`) | — |
| **qual API é oficial e suportada?** | **não** | **sim** |
| **o que o MCP oficial do AutoCAD cobre?** | **não** | **sim** |
| **o que a Autodesk *não* suporta?** | **não** | **sim** |

## As quatro APIs oficiais (e o que a Autodesk declara)

| API | Linguagem | Onde roda | Declaração oficial | Suporte |
|---|---|---|---|---|
| **ObjectARX** | C++ | dentro do AutoCAD (CRX/DBX) | "Create custom commands, manipulate entities, customize UI, access drawing data, integrate with external systems" | Completo |
| **AutoCAD .NET API** | C#/VB | dentro (assembly, `acdbmgd`/`acmgd`/`accoremgd`) | gerenciado, mesmo modelo de objetos | Completo |
| **AutoLISP / Visual LISP** | LISP | dentro | "Automate tasks, create custom commands, and extend software functionality" | Completo |
| **COM / ActiveX** | qualquer cliente COM | **fora**, Windows, AutoCAD aberto | ActiveX interface (a mesma da era VBA) | Completo |

Mais duas superfícies oficiais, de nuvem:

| Superfície | O que é | Limite oficial |
|---|---|---|
| **AutoCAD JavaScript API** | extensões no AutoCAD **web** | superfície menor que o COM/.NET |
| **AutoCAD on the web + AutoLISP** | roda AutoLISP no DWG aberto no browser | exige AutoCAD on the web |
| **APS Design Automation API for AutoCAD** | `accoreconsole.exe` na nuvem + plugin CRX/DBX, ou `.scr`/AutoLISP | "The Automation API does not provide access to commands or APIs of AutoCAD verticals (toolsets and products built on top of AutoCAD)" — **Civil 3D/Architecture/Mechanical não existem lá**; sem COM, sem UI, sessão não-interativa |

## O MCP oficial: Autodesk AutoCAD and Civil 3D MCP Server

**Existe, é oficial e roda localmente dentro do AutoCAD/Civil 3D (Windows).**
Status: **Tech Preview (Public Beta)**. Doc: `help.autodesk.com/view/ADSKMCP/ENU/`.
É um dos seis MCP servers oficiais (AutoCAD+Civil 3D, Revit, Fusion, Fusion Data,
Fusion Compute, Product Help).

Duas configurações de ferramentas — `MCPCONFIG` no AutoCAD mostra as habilitadas:

- **Default** — leitura/análise.
- **Civil 3D** — Default + modificação.

| Tool | Faz | Config |
|---|---|---|
| `discoverAutoCADTypes` | schema dos tipos do desenho (`line`, `circle`, `arc`, `text`, `mtext`, `polyline`, `dimension`, `layer`, `block`; Civil 3D com prefixo `civil3d_` como `civil3d_alignment`, `civil3d_surface`, `civil3d_corridor`, `civil3d_pipe`). **Chamar primeiro** | Default |
| `queryAutoCADObjects` | busca objetos com filtro, seleção de campos, paginação, level queries aninhadas | Default |
| `aggregateAutoCADObjects` | count, sum, avg, min, max, minabs, maxabs — opcionalmente agrupado (`rollupBy`). **Usar esta, não `query`, para estatística** | Default |
| `manipulateDrawingCanvas` | `showme`, `select`, `unselect`, `getSelection`, `zoomObjects`, `zoomExtents`, `zoomScale`, `zoomWindow`; alterna model/paper space | Default |
| `checkAutoCADObjects` | compara o desenho atual com um desenho-**template** e devolve as diferenças (padronização) | Default |
| `updateAutoCADObjects` | modifica objetos | **Civil 3D only** |
| `civil3dQueryModifyStyles` | lê/altera estilos Civil 3D (entidade, embutido, display); operações em lote com lista separada por vírgula | **Civil 3D only** |

Regras de uso que a Autodesk documenta e que um agente precisa saber:

- **Filtro**: `=`, `!=`, `<`, `>`, `contains`, `startswith`, `endswith`, `AND`, `OR`.
  `AND` tem precedência maior; **parênteses não são suportados**; texto é
  case-insensitive; `= null` / `!= null` filtra por nulo.
- **Contexto**: query e agregação caem por padrão no contexto da **seleção atual**.
  Para o desenho inteiro, passar `context: "drawing"`.
- **Língua**: o servidor não tem parâmetro de locale. A língua da resposta vem do
  client/assistente. Valores (coordenada, comprimento, ângulo) voltam nas unidades do
  desenho (`LUNITS`/`AUNITS`) — reportar **exatamente** como veio.
- **Não expõe MCP resources.**
- Ordem recomendada: `discoverAutoCADTypes` → `query`/`aggregate` → `manipulateCanvas`
  ou `update` ou `civil3dQueryModifyStyles`.

## O limite que muda projeto: em AutoCAD puro, o MCP oficial não desenha

A visão "At a glance" da Autodesk diz **read-only, com ferramentas de escrita no
Civil 3D**. As release notes de setembro/2026 (versão `26.0.516.6958`) somam, em
**AutoCAD e Civil 3D**: criar e apagar camadas, mudar propriedade de camada, mover
objetos entre camadas e setar variáveis de sistema.

Tradução honesta: **lê tudo; desde set/2026 arruma camada; não desenha geometria
nova.** As duas páginas oficiais divergem entre si — registre isso como divergência,
não escolha uma.

A consequência prática para este projeto: **o MCP oficial não substitui o COM** do
`com_backend.py`. Ele cobre auditoria e padronização; o desenho continua sendo COM /
AutoLISP / plugin .NET.

## Cliente suportado: o que a doc diz e o que o campo mostra

- A página do AutoCAD/Civil 3D nomeia **Autodesk Assistant** como cliente suportado.
- A página "About Autodesk MCP Servers" fala genericamente em "MCP-compatible AI
  applications (for example, Claude Desktop and Cursor)".
- Os servidores **Fusion** têm endpoint local documentado (`http://127.0.0.1:27182`).
- O AutoCAD tem **modo HTTP**, mas não é suportado — ver a próxima seção.

## O modo HTTP do MCP do AutoCAD: armadilha documentada (não é suportado)

Relato de campo no fórum Autodesk (AutoCAD 2027, build `26.0.460.2523`) sobre o plugin
`C:\Program Files\Autodesk\ApplicationPlugins\AutoCAD-MCP-Server-2027.bundle`:

1. **`ModelContextProtocol.AspNetCore.dll` falta** no `...\Contents\` → `MCPHTTPSTART`
   dá `FileNotFoundException`. Correção reportada: copiar a DLL do pacote NuGet
   `ModelContextProtocol.AspNetCore 0.4.0-preview.3` para dentro do `Contents\`.
2. **O servidor HTTP é desligado por padrão** → setar `ACMCP_TOOLS_CONFIG_FILE` com um
   config contendo `"toolsConfiguration": { "enableHttpServer": true }` (aninhado,
   camelCase) e carregar via `MCPCONFIG` → Load.
3. **O plugin não é carregado no boot** → `MCPCONFIG` e `MCPHTTPSTART` respondem
   "Unknown command" até `NETLOAD acmcp.dll`.

Funcionando: `MCPHTTPSTART` sobe em `http://localhost:5001/mcp` (Streamable HTTP).

**Tratar como gambiarra de comunidade, sem suporte da Autodesk.** Não prometer como
integração suportada; registrar como "funciona, sem garantia, quebrará na próxima
atualização".

## O que a Autodesk *não* suporta (e que quebra automação)

| Restrição | Onde se aplica | Consequência |
|---|---|---|
| **AutoLISP ausente no AutoCAD LT for Mac** | LT Mac | suporte a AutoLISP começa no **AutoCAD LT 2024 (Windows)**; LT Mac não tem — nem LSP, nem FAS, nem VLX |
| **Sem ActiveX/COM no AutoCAD for Mac** | AutoCAD Mac | `vlax-*` não existe; COM/`SendCommand` do `com_backend.py` é **Windows-only** |
| **Automation API sem verticais** | nuvem | Civil 3D, Architecture, Mechanical, P&ID não existem no accoreconsole |
| **Automation API sem COM/UI** | nuvem | nada de `ActiveDocument`, foco de janela, interação |
| **Automation API é por arquivo, não por desenho vivo** | nuvem | roda em cima de um arquivo enviado; não "vê" o desenho aberto na tela |

## Lacunas deste mapa (medidas, não presumidas)

1. **Ainda não existe sonda do MCP oficial** em `ferramentas/`. Contraste com o que já
   existe: `sonda_autocad.py` (getvar/comandos ao vivo), `mapear_com.py` (type
   library), `resumir_dotnet.py` (metadata). **MCP oficial = zero sonda** — e agora se
   sabe **o porquê**: não há alvo (AutoCAD 2025, sem o bundle 2027). A lacuna real nesta
   máquina é sondar **o plugin próprio** (`CadMcpBridge`), que é outra coisa.
2. **`mapear_comandos.py` ainda não rodou** (consta no LEIA-ME do projeto) — o
   gravador de prompts em duas fases (`--iniciar`/`--ler`) segue parado.
3. **Nada cobre `.scr`** como superfície: o que o AutoCAD aceita de script sequencial, e
   por que não serve para lógica (só para orquestrar).
4. **Nada cobre DXF/DWG como formato** de troca para agentes (grupo de código, versões
   de DXF, o que o `ezdxf` já cobre vs. o que só o AutoCAD resolve).
5. **Nada cobre o plugin .NET oficial** (`plugin/CadMcpBridge`) como *superfície
   suportada* — o mapa do projeto o trata como implementação própria, não como API.

## Ordem sugerida para a próxima rodada de mapeamento

1. `sonda_cadbridge.py` — sondar **o plugin próprio** (`CadMcpBridge.bundle`): o que ele
   expõe, que protocolo fala (`tools/test_bridge.py` já cobre parte), e o que falta.
   É o par do `sonda_autocad.py` para a superfície que **existe aqui**.
2. `mapear_comandos.py` — rodar de fato (está pronto, só não executado).
3. Mapa de formato (DXF/DWG) — o que um agent pode ler sem abrir o AutoCAD.
4. `.scr` — o que é seguro automatizar e o que não é.
5. `sonda_mcp_oficial.py` — **só faz sentido quando houver AutoCAD 2027**. Até lá,
   documentar a superfície oficial (que é o que este arquivo faz) sem pretender medir.
