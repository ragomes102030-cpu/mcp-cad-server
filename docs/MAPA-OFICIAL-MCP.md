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
| AutoCAD instalado | `C:\Program Files\Autodesk\AutoCAD 2025cad.exe`, file version **R25.0.162.0.0** |
| `ACADVER` (medido na sessão, `sonda_cadbridge.py`) | `25.0s (LMS Tech)` |
| **Plugin oficial `AutoCAD-MCP-Server-2027.bundle`** | **não existe** — `C:\Program Files\Autodesk\ApplicationPlugins\` não existe; `find` por `*mcp*` em `Program Files\Autodesk` e em `AppData\Roaming\Autodesk` não acha nada |
| Único bundle MCP presente | `AppData\Roaming\Autodesk\ApplicationPlugins\CadMcpBridge.bundle` — **é o plugin próprio do projeto** (`plugin/CadMcpBridge`), **não** o MCP oficial |
| `accoreconsole.exe` | presente em `C:\Program Files\Autodesk\AutoCAD 2025\` |

**Conclusão:** a máquina tem **AutoCAD 2025** e **não tem** o MCP oficial da Autodesk
(que é do 2027). Portanto **não é possível medir as 7 tools aqui** — a camada oficial é
documentada, não medida. Qualquer número de cobertura do MCP oficial nesta máquina seria
inventado.

### O que foi medido aqui (20/10/2026) — e o que é só documento

| afirmação | origem | como foi obtida |
|---|---|---|
| AutoCAD 2025 `R25.0.162.0.0`, `ACADVER 25.0s (LMS Tech)` | **medido** | `sonda_cadbridge.py` (COM + leitura de `$TEMP%\cad_mcp_bridge.json`) |
| Plugin próprio `CadMcpBridge` v1.0 **carregado** em 25.0, porta 8765, pid = o do `acad.exe` | **medido** | `ping`/`info` pela ponte; `pid` bate com o `acad.exe` |
| O plugin expõe `ping`, `info`, `exec`, `transaction` (JSON-RPC, 1 linha, 127.0.0.1) | **medido** | respostas ao vivo; `plugin/README.md` descreve o mesmo |
| `TRUSTEDPATHS` cobre o bundle | **medido** | leitura do registro (`HKCU\Software\Autodesk\AutoCAD\R25.0\ACAD-8101:409\Profiles\<<Unnamed Profile>>\Variables`) |
| MCP oficial **ausente** | **medido** | `C:\Program Files\Autodesk\ApplicationPlugins\` não existe |
| As 7 tools do MCP oficial, seus inputs, as duas configurações | **documentado** | `help.autodesk.com/view/ADSKMCP/ENU/` — **não medido nesta máquina** |
| Regras de filtro, `context: "drawing"`, ausência de locale | **documentado** | idem |
| Release notes set/2026 (camadas e sysvars) | **documentado** | idem |
| `MCPHTTPSTART` quebrado (DLL faltando, HTTP desligado, não NETLOAD) | **relato de campo** | fórum Autodesk — **não reproduzido aqui** |
| "Não oficial; COM precisa de sessão viva" | **análise de terceiros** | blog — **não é fato oficial** |

### O que a medição do plugin próprio revelou (e não estava no plano)

1. **O plugin carrega e responde.** `ping` em 242 ms na primeira carga e 25,8 ms na
   segunda; `info` devolveu `produto`, `versao`, `acad`, `desenho`, `INSUNITS=4`,
   `FILEDIA=0`, `CMDDIA=0`. Ou seja: o Autoloader funcionou sem diálogo de
   segurança (o `TRUSTEDPATHS` estava certo).
2. **`exec` é assíncrono de verdade** — `_.LINE` voltou em 3 ms com
   `aviso: "enviado; o comando termina sozinho (assincrono)"`. É o que permite
   iniciar um comando que espera ponto sem travar o chamador.
3. **Mas `LASTPROMPT` não é capturável de forma confiável.** Ver
   `ferramentas/mapear_comandos.py`: a leitura dentro do processo usa um prazo de
   500 ms e dá `TimeoutException` enquanto o comando espera seleção. Medido: uma
   rodada devolveu os prompts reais, a seguinte devolveu `None`/eco, e uma
   terceira **deixou o AutoCAD travado** (thread principal ocupada, COM
   recusando `RPC_E_CALL_REJECTED`, sem responder a ESC). O processo teve de ser
   encerrado.
4. **`exec` não confirma resultado** — `ok: true` diz que o comando foi *enviado*.
   Isto vale para o `CadMcpBridge` e é o mesmo limite que o MCP oficial tem
   quando apenas lê.

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

1. **`sonda_mcp_oficial.py` ainda não existe** — e agora se sabe **o porquê**:
   não há alvo (AutoCAD 2025, sem o bundle 2027). O que existe é
   `ferramentas/sonda_cadbridge.py`, que sonda **o plugin próprio** (`CadMcpBridge`)
   — a superfície MCP que existe de fato aqui. Rodou em 20/10/2026 e está
   registrada em `docs/MAPA-CADBRIDGE.md`.
2. **`mapear_comandos.py` rodou** (estava pronto e parado). Resultado medido:
   funciona **intermitentemente** — a captura de `LASTPROMPT` depende de a thread
   principal estar ociosa. Uma varredura longa **travou o AutoCAD** e o processo
   teve de ser encerrado. Ver o docstring da ferramenta; antes de varrer, salve o
   desenho.
3. **Nada cobre `.scr`** como superfície: o que o AutoCAD aceita de script
   sequencial, e por que não serve para lógica (só para orquestrar).
4. **Nada cobre DXF/DWG como formato** de troca para agentes (grupo de código,
   versões de DXF, o que o `ezdxf` já cobre vs. o que só o AutoCAD resolve).
5. **`transaction` do plugin não foi exercitado ao vivo** — só o protocolo do
   cliente tem teste (`tests/test_bridge.py`, com um servidor falso). A ponte
   respondeu `ping`/`info`; `transaction` ficou por fazer.

## Ordem sugerida para a próxima rodada de mapeamento

1. ~~`sonda_cadbridge.py`~~ — **feito** (20/10/2026): o plugin próprio foi medido
   ao vivo e `docs/MAPA-CADBRIDGE.md` registra o que ele expõe e o que não prova.
2. ~~`mapear_comandos.py` rodar de fato~~ — **feito**, com o resultado de que a
   captura é intermitente e pode travar o AutoCAD.
3. **Repetir a captura de prompts com o AutoCAD recém-aberto** (thread ociosa) e
   gravar em `historico/prompts.jsonl` — o que se tem hoje veio de uma rodada que
   funcionou. Cada varredura deve ser curta e precedida de `enviar_esc`.
4. **`transaction` ao vivo** — a única superfície do plugin que continua sem
   medição.
5. Mapa de formato (DXF/DWG) — o que um agent pode ler sem abrir o AutoCAD.
6. `.scr` — o que é seguro automatizar e o que não é.
7. `sonda_mcp_oficial.py` — **só faz sentido quando houver AutoCAD 2027**. Até lá,
   documentar a superfície oficial (que é o que este arquivo faz) sem pretender
   medir.

