# LEIA-ME — a camada oficial (API Autodesk + MCP oficial)

O que este arquivo é: a **ponte** entre o que o projeto já mapeou (COM, .NET,
entidades, instalação viva) e o que a **Autodesk declara como superfície oficial e
suportada** — inclusive o MCP oficial do AutoCAD.

Adicionado em **2026-10-20**.

## Os dois mapas novos

| arquivo | pergunta que responde |
|---|---|
| `MAPA-OFICIAL-MCP.md` | quais são as APIs oficiais, o que cada uma cobre, o que o MCP oficial do AutoCAD faz, e o que a Autodesk **não** suporta |
| `LEIA-ME-MCP.md` | evidência por afirmação + como pedir isto a um agente |

Os mapas antigos (`MAPA-COM`, `MAPA-DOTNET`, `MAPA-ENTIDADES`, `MAPA-AUTOCAD`)
continuam sendo a referência do **comportamento medido do AutoCAD**. Estes dois são a
referência da **superfície oficial e do que tem suporte**.

## A conclusão em uma linha

O MCP oficial do AutoCAD/Civil 3D é **real, oficial e local**, mas em AutoCAD puro é
praticamente **leitura e análise** (auditoria, padronização contra template,
estatística) — **não desenha geometria nova**. O desenho continua sendo COM/ActiveX,
AutoLISP ou plugin .NET. Portanto: **não substitui o `com_backend.py`**.

## Evidência — por afirmação

| afirmação | fonte | tipo |
|---|---|---|
| Quatro APIs oficiais (ObjectARX, .NET, AutoLISP, COM) + JavaScript + macOS | `aps.autodesk.com/developer/overview/autocad-api` | oficial |
| Seis MCP servers oficiais; AutoCAD+Civil 3D é local, **Tech Preview (Public Beta)**, Windows | `help.autodesk.com/view/ADSKMCP/ENU/` | oficial |
| As 7 tools, seus inputs e as duas configurações (Default / Civil 3D) | `help.autodesk.com/view/ADSKMCP/ENU/?guid=autocadcivil3dmcp_tools` | oficial |
| Regras de filtro, `context: "drawing"`, ausência de locale, ordem de encadeamento | idem | oficial |
| "Read-only, with write tools in Civil 3D" (visão geral) | `help.autodesk.com/view/ADSKMCP/ENU/?guid=ADSKMCP_AutoCADCivil3DMcp_...` | oficial |
| Release notes set/2026 (26.0.516.6958): camadas e variáveis de sistema em **AutoCAD e Civil 3D** | `help.autodesk.com/view/ADSKMCP/ENU/?guid=autocadcivil3dmcp_relnotes` | oficial |
| Cliente suportado do AutoCAD: Autodesk Assistant | `help.autodesk.com/view/ADSKMCP/ENU/` (visão do servidor) | oficial |
| "MCP-compatible AI applications (for example, Claude Desktop e Cursor)" | `help.autodesk.com/view/ADSKMCP/ENU/?guid=ADSKMCP_CommonContent_about_...` | oficial |
| Endpoint local documentado do Fusion MCP | `autodesk.com/products/fusion-360/blog/build-your-own-fusion-add-ins-with-the-fusion-mcp/` | oficial |
| Automation API não dá acesso a comandos/APIs de **verticais** | `aps.autodesk.com/en/docs/design-automation/v3` | oficial |
| AutoLISP só a partir do **AutoCAD LT 2024**; **LT for Mac não tem AutoLISP**; AutoCAD for Mac não tem ActiveX | `autodesk.com/support/technical/article/.../Unable-to-load-lisp-in-AutoCAD-LT.html` | oficial |
| AutoCAD 2026 trouxe "APIs for AutoCAD on the web: AutoLISP API" | `autodesk.com/products/autocad/features` | oficial |
| `MCPHTTPSTART` quebrado (DLL faltando, HTTP desligado, plugin não NETLOAD) | `forums.autodesk.com/t5/installation-licensing-forum/.../14294262` | **relato de campo** |
| "Não oficial, COM precisa de sessão viva; ezdxf headless não lê desenho existente" | `getleo.ai/blog/autocad-mcp-ai-agent-connection` | **análise de terceiros** |
| "Autodesk server: Autodesk Assistant only; não desenha em AutoCAD puro" | `meltflexai.com/blog/autocad-mcp` | **análise de terceiros** |

## Como pedir isto a um agente (prompt pronto)

> **Tarefa:** completar o mapeamento do AutoCAD no projeto `mcp-cad-server` com a
> camada que falta — as APIs oficiais da Autodesk e o MCP oficial — usando
> `docs/MAPA-OFICIAL-MCP.md` e `docs/LEIA-ME-MCP.md` como especificação.
>
> **Veredito já medido (2026-10-20):** esta máquina tem **AutoCAD 2025** (`R25.0.162.0.0`,
> `ACADVER 25.0s (LMS Tech)`) e **não tem** o plugin oficial `AutoCAD-MCP-Server`
> (que é do 2027). O único bundle MCP presente é `CadMcpBridge.bundle` — **o plugin
> próprio do projeto**, não o oficial. **Não invente cobertura do MCP oficial aqui.**
>
> **Regras:**
> 1. Distinga **medido** de **documentado**. Os mapas existentes (`MAPA-COM`,
>    `MAPA-DOTNET`, `MAPA-ENTIDADES`, `MAPA-AUTOCAD`) são medidos ao vivo. A camada
>    oficial é documentada — marque a origem de cada afirmação e **não apresente análise
>    de terceiros como fato oficial**.
> 2. **Confirme a instalação antes de afirmar capacidade.** O plugin oficial existe?
>    `MCPCONFIG` responde? Qual build? Se não existir, diga que não existe e pare.
> 3. Mantenha a tese central: **o MCP oficial não substitui o COM** para desenhar.
> 4. Registre lacunas em `## Lacunas deste mapa` em vez de preencher com suposição.
> 5. Se for ligar o modo HTTP (`MCPHTTPSTART`), trate como **gambiarra sem suporte**.
>
> **Entregáveis esperados (nesta máquina):**
> - `ferramentas/sonda_cadbridge.py` — sondar **o plugin próprio** (`CadMcpBridge`),
>   que é a superfície MCP que existe de fato aqui. É o par do `sonda_autocad.py`.
> - `ferramentas/mapear_comandos.py` **rodado de fato** (está pronto, nunca executado).
> - Um veredito escrito em `MAPA-OFICIAL-MCP.md` dizendo o que é medido aqui e o que
>   é só referência de documento oficial.
>
> **Entregável futuro (só com AutoCAD 2027):** `sonda_mcp_oficial.py` medindo as 7 tools.

## Pitfalls

- **Não confunda "existe documentação" com "existe na minha instalação".** O MCP oficial
  é Tech Preview e depende de build; a doc descreve a intenção, não a sua máquina.
- **Não confunda MCP com API.** MCP não concede acesso novo ao AutoCAD; só padroniza a
  chamada para quem já tem uma porta de entrada.
- **`updateAutoCADObjects` e `civil3dQueryModifyStyles` são Civil 3D only.** Em AutoCAD
  puro, a config Default só lê/analisa.
- **`context` default é a seleção atual**, não o desenho inteiro. Agente que não passar
  `context: "drawing"` reporta estatística parcial sem avisar.
- **Handle é volátil.** `getSelection` e handles só valem na mesma sessão; não persistir.
- **Accoreconsole não tem COM nem UI** — automação em nuvem não pode depender de
  `ActiveDocument`.
