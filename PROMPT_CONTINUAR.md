# PROMPT — continuar o mapeamento (camada oficial + ferramentas do MCP Pro)

Cole isto na conversa com o agente. É autocontido: estado medido, duas frentes de
trabalho, regras e entregáveis.

---

## Contexto do projeto

**Projeto:** `mcp-cad-server` — servidor MCP que desenha e lê plantas no AutoCAD
(48 ferramentas expostas; `entity_create_*`, `drawing_*`, `dimension_*`, `layer_*`,
`block_*`, `arch_room`, `quantitativo`).

**Dois locais — e um está na frente do outro:**

| local | o que é |
|---|---|
| `C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad\` | **pacote de entrega** (novo). Tem `codigo/`, `instalacao/`, `exemplos/`, `ferramentas/`, `historico/`, `plugin/`, `skill/`, `docs/` |
| `C:\Users\Correta Engenharia\mcp-cad-server\` | fonte do projeto (mais antigo) |

Os mapas de `docs\` são **byte a byte iguais** entre os dois, **exceto `COBERTURA.md`**:
o da Desktop é de **20/10 15:11** (novo), o do server é de **19/10 10:06** (velho).
O da Desktop diz **76 nossas / 65 mesmo nome**; o do server diz 40/33. **A Desktop
está à frente — é ela a referência.** O `docs/` do `mcp-cad-server` precisa ser
atualizado a partir da Desktop no fim.

**Máquina (medido em 20/10/2026):**

| item | valor |
|---|---|
| AutoCAD | `C:\Program Files\Autodesk\AutoCAD 2025\acad.exe`, **R25.0.162.0.0** |
| `ACADVER` | `25.0s (LMS Tech)` |
| `accoreconsole.exe` | presente em `C:\Program Files\Autodesk\AutoCAD 2025\` |
| Plugin MCP oficial (`AutoCAD-MCP-Server-2027.bundle`) | **não existe** nesta máquina |
| Único bundle MCP | `AppData\Roaming\Autodesk\ApplicationPlugins\CadMcpBridge.bundle` — **é o plugin próprio do projeto**, não o oficial |
| Área de trabalho | `C:\temp\mcp_cad_com` (env `MCP_CAD_TEMP`; **sem espaço no caminho** — `SendCommand` trata espaço como ENTER) |

**Estado do git:** `mcp-cad-server` tem `.git` mas **zero commits**
(`git log` → *"your current branch 'master' does not have any commits yet"*).
Sem commit, edição não é rastreável.

---

## Frente 1 — completar a camada oficial (API da Autodesk + MCP oficial)

**Especificação pronta:** `docs/MAPA-OFICIAL-MCP.md` e `docs/LEIA-ME-MCP.md`.
Leia os dois antes de começar.

**Veredito já medido:** a máquina tem **AutoCAD 2025** e **não tem** o MCP oficial
(que é do 2027). Portanto **não é possível medir as 7 tools do MCP oficial aqui** —
a camada oficial é **documentada**, não medida. **Não invente cobertura.**

**Regras desta frente:**

1. Distinga **medido** de **documentado**. `MAPA-COM` (632 métodos), `MAPA-DOTNET`
   (1572 tipos), `MAPA-ENTIDADES` (83 entidades / 2054 campos DXF) e `MAPA-AUTOCAD`
   (863 comandos / 821 variáveis) são **medidos ao vivo**. A camada oficial é
   documentada — marque a origem de cada afirmação e **não apresente análise de
   terceiros como fato oficial**.
2. **Confirme a instalação antes de afirmar capacidade.** O plugin oficial existe?
   `MCPCONFIG` responde? Se não existir, diga que não existe e pare.
3. Mantenha a tese central: **o MCP oficial não substitui o COM** para desenhar.
   Em AutoCAD puro ele é leitura/análise (auditoria, padronização contra template,
   estatística); desde set/2026 também cria/apaga camadas e seta variáveis de sistema
   — **não desenha geometria nova**.
4. Registre lacunas em `## Lacunas deste mapa` em vez de preencher com suposição.
5. Se ligar o modo HTTP (`MCPHTTPSTART`), trate como **gambiarra sem suporte**
   (DLL faltando, HTTP desligado por padrão, plugin não NETLOAD — tudo relato de
   campo, não contrato).

**Entregáveis desta frente (nesta máquina):**

- `ferramentas/sonda_cadbridge.py` — sondar **o plugin próprio** (`CadMcpBridge`),
  que é a superfície MCP que existe de fato aqui. É o par do `sonda_autocad.py`.
- **Rodar `ferramentas/mapear_comandos.py` de fato.** Está pronto, **nunca foi
  executado** — o gravador de prompts em duas fases (`--iniciar` / `--ler`).
- Veredito escrito em `docs/MAPA-OFICIAL-MCP.md` separando o que é medido aqui do que
  é só referência de documento oficial.

**Entregável futuro (só com AutoCAD 2027):** `sonda_mcp_oficial.py` medindo as 7 tools.

---

## Frente 2 — trazer as ferramentas do MCP Pro para o nosso mapeamento

**Fonte:** `autocad-mcp-pro 1.6.0` (MIT, `U-C4N/Autocad-MCP`), vendorizado em
`vendor/autocad-mcp-pro-1.6.0/server.py`. Catálogo extraído em
`docs/catalogo-acmpro.json`: **247 ferramentas**.

**Hoje nós temos 76** (65 com o mesmo nome). **Mesmo nome não é a mesma ferramenta** —
`drawing_save` deles e o nosso fazem coisas diferentes nos detalhes. A comparação serve
para achar **buraco**, não para dizer que já temos.

**Buracos por família** (`docs/COBERTURA.md`, versão da Desktop):

| família | deles | nossos | faltando |
|---|---|---|---|
| desenho | 31 | 8 | **23** |
| plot/arquivo | 30 | 15 | **15** |
| camada/estilo | 30 | 17 | **13** |
| edicao | 29 | 11 | **18** |
| consulta | 24 | 4 | **20** |
| sistema | 23 | 3 | **20** |
| arquitetura | 19 | 2 | **17** |
| mecanica | 13 | 0 | **13** |
| bloco | 11 | 4 | **7** |
| cota/anotacao | 9 | 2 | **7** |
| P&ID | 9 | 0 | **9** |
| 3D/solido | 8 | 0 | **8** |
| selecao | 5 | 4 | 1 |
| visualizacao | 3 | 2 | 1 |
| outros | 2 | 3 | 0 |
| texto | 1 | 1 | 0 |

Por custo: **68 read, 122 mutate, 18 destructive, 37 safe, 2 escape**.

**Onde implementar:** funções `async` em `codigo/src/cad_mcp/tools.py` (665 linhas),
registradas em `codigo/src/cad_mcp/server.py` (54 linhas). Motores disponíveis:
`com` (AutoCAD aberto, não rouba foco), `file_ipc` (AutoCAD LT), `ezdxf` (headless),
`accoreconsole` (DXF/PDF).

**Regras desta frente:**

1. **Não copie o `server.py` deles.** Ele exige Python 3.11 e é código de terceiros
   (MIT, com aviso em `THIRD_PARTY_NOTICES.md`). Extraia o **contrato** (nome,
   argumentos, o que promete) e implemente no nosso motor.
2. **Priorize por valor de desenho, não por número.** Para planta baixa de obra, as
   famílias que mais faltam e mais importam são **desenho (23)**, **edicao (18)** e
   **arquitetura (17)**. Mecânica/P&ID/3D são domínio diferente — **não implemente
   por implementar**; registre como fora de escopo com justificativa.
3. **`TRIM`, `EXTEND`, `FILLET`, `CHAMFER`, `JOIN` são comandos, não métodos de API.**
   O caminho é o plugin .NET (`plugin/CadMcpBridge`) ou geometria própria. Não
   prometa como método.
4. **`destructive` (18) exige confirmação.** Ferramenta que apaga precisa de guarda
   explícita — o agente nunca deve rodar destrutivo sem confirmação do usuário.
5. **Toda ferramenta nova precisa de teste.** Siga o padrão de `tests/test_bridge.py`
   e `tests/validar_modelo_teste.py`. Ferramenta sem teste não entra.
6. **A regra de promoção de falhas vale:** sintoma só vira verificação de código na
   **3ª ocorrência** — nunca na primeira (a primeira pode ser typo).
7. Ao fim, **regenere `docs/COBERTURA.md`** e **sincronize `docs/` da Desktop para o
   `mcp-cad-server`** (a Desktop está à frente).

**Entregáveis desta frente:**

- Ferramentas implementadas em `codigo/src/cad_mcp/tools.py` + registradas em
  `server.py`, com teste cada.
- `docs/COBERTURA.md` regenerado com os novos números.
- `docs/` do `mcp-cad-server` sincronizado com a Desktop.
- Relatório: o que entrou, o que ficou de fora e por quê.

---

## Antes de começar

**Já feito em 20/10/2026 (não refazer):**

- `git add -A && git commit` — o repo agora tem **2 commits** e **351 arquivos**,
  working tree limpo. Existe ponto de retorno.
- `docs/` sincronizado da Desktop — **14 de 14 idênticos**. `COBERTURA.md` estava na
  versão velha (40/33); agora está na nova (**76/65**).
- `skill/cad-planta-autocad/` copiada para dentro do repo (o repo não a tinha).

**Ainda falta (verificar antes de mexer):**

1. **Confirme de onde a skill `cad-planta-autocad` é carregada.** Ela existe em
   `Desktop\Mapeamento AutoCad\skill\` e em `mcp-cad-server\skill\` — mas **não** está
   em `config/skills` do Arquimedes nem em `hermes/skills`. Aponte o agente para
   `C:\Users\Correta Engenharia\mcp-cad-server\skill\cad-planta-autocad`, senão o
   `references/api-oficial-mcp.md` novo não chega a ele.
2. **Prove a instalação antes de afirmar:** `instalacao\verificar_instalacao.py` deve
   devolver `RESULTADO: OK` com 48 ferramentas.

## Ordem sugerida

1. Frente 1: `sonda_cadbridge.py` + rodar `mapear_comandos.py` + veredito no mapa.
2. Frente 2: implementar as ferramentas de **desenho**, depois **edicao**, depois
   **arquitetura** — com teste cada.
3. Regenerar `COBERTURA.md` e commitar.

## Regra de ouro do projeto

**Contagem de entidades e "0 erros" não provam nada.** O AutoCAD erra em silêncio.
Todo resultado termina com conferência de **propriedade** (abertura de arco, unidades,
extensão, folha), nunca só de existência.
