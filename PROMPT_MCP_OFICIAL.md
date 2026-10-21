# PROMPT — peça isto ao seu agente

Cole isto na conversa com o agente que faz o mapeamento do AutoCAD
(`mcp-cad-server` / `Desktop\Mapeamento AutoCad`).

---

**Tarefa:** completar o mapeamento do AutoCAD no projeto `mcp-cad-server` com a camada
que falta — as **APIs oficiais da Autodesk** e o **MCP oficial do AutoCAD** — usando
`docs/MAPA-OFICIAL-MCP.md` e `docs/LEIA-ME-MCP.md` como especificação.

**Veredito já medido (2026-10-20) — leia antes de começar:** esta máquina tem
**AutoCAD 2025** (`R25.0.162.0.0`, `ACADVER 25.0s (LMS Tech)`) e **não tem** o plugin
oficial `AutoCAD-MCP-Server` (que é do 2027). O único bundle MCP presente é
`CadMcpBridge.bundle` — **o plugin próprio do projeto**, não o oficial. **Não invente
cobertura do MCP oficial aqui.**

**Regras:**

1. Distinga **medido** de **documentado**. Os mapas existentes (`MAPA-COM`,
   `MAPA-DOTNET`, `MAPA-ENTIDADES`, `MAPA-AUTOCAD`) são medidos ao vivo. A camada
   oficial é documentada — marque a origem de cada afirmação e **não apresente análise
   de terceiros como fato oficial**.
2. **Confirme a instalação antes de afirmar capacidade.** O plugin oficial existe?
   `MCPCONFIG` responde? Qual build? Se não existir, diga que não existe e pare.
3. Mantenha a tese central: **o MCP oficial não substitui o COM** para desenhar.
4. Registre lacunas em `## Lacunas deste mapa` em vez de preencher com suposição.
5. Se for ligar o modo HTTP (`MCPHTTPSTART`), trate como **gambiarra sem suporte**.

**Entregáveis esperados (nesta máquina):**

- `ferramentas/sonda_cadbridge.py` — sondar **o plugin próprio** (`CadMcpBridge`), que é
  a superfície MCP que existe de fato aqui. É o par do `sonda_autocad.py`.
- `ferramentas/mapear_comandos.py` **rodado de fato** (está pronto, nunca executado).
- Um veredito escrito em `MAPA-OFICIAL-MCP.md` dizendo o que é medido aqui e o que é só
  referência de documento oficial.

**Entregável futuro (só com AutoCAD 2027):** `sonda_mcp_oficial.py` medindo as 7 tools.

---

## O que o agente vai encontrar pronto

| arquivo | papel |
|---|---|
| `docs/MAPA-OFICIAL-MCP.md` | a especificação: APIs oficiais, as 7 tools do MCP oficial, regras de filtro/contexto, o que a Autodesk não suporta, veredito de instalação, lacunas |
| `docs/LEIA-ME-MCP.md` | evidência por afirmação (oficial × relato de campo × análise de terceiros) + pitfalls |
| `skill/cad-planta-autocad/references/api-oficial-mcp.md` | resumo acionável, carregado pela skill |
| `LEIA-ME.md` | índice do projeto — já aponta os dois mapas novos |

## Antes de pedir, duas decisões

1. **Onde a skill vive.** `cad-planta-autocad` hoje existe só em
   `Desktop\Mapeamento AutoCad\skill\` — **não** está em `config/skills` do Arquimedes nem
   em `hermes/skills`. Se o agente não estiver lendo essa pasta, o `references/` novo não
   chega a ele. Confirme de onde o agente carrega skills antes de cobrar.
2. **O `mcp-cad-server` não tem git** (`git log` → "your current branch 'master' does not
   have any commits yet"). Sem commit, qualquer edição do agente não é rastreável. Vale
   `git add -A && git commit` antes de mandar ele mexer.
