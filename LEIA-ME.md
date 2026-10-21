# Mapeamento AutoCAD 2025

Tudo o que foi levantado para dirigir o AutoCAD **de verdade** — o COM da Autodesk,
o .NET por dentro, os campos de cada entidade, o plugin que cobre o que o COM não
faz, o MCP que usa isso e a skill que ensina a usar.

Origem: `C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad`
Atualizada em 19/10/2026.

## Para usar em outra máquina

1. Copie a pasta inteira (sem espaço no caminho de destino).
2. Siga **`instalacao\INSTALAR.md`** — roteiro passo a passo, escrito para um agente
   executar (venv, wheel, registro no cliente MCP, TRUSTEDPATHS, diagnóstico).
3. Prove que instalou: `instalacao\verificar_instalacao.py` → esperado `RESULTADO: OK`
   com **48 ferramentas**.

Licença **MIT** (`LICENSE`); componentes de terceiros em `THIRD_PARTY_NOTICES.md`.

## As três camadas do mapa (e o que cada uma responde)

| pergunta | arquivo | fonte |
|---|---|---|
| o que o COM sabe fazer sozinho? | `docs\MAPA-COM.md` | type library `acax25enu.tlb` |
| o que só o .NET resolve? | `docs\MAPA-DOTNET.md` | metadata de `acdbmgd`/`acmgd`/`accoremgd` |
| quais campos tem cada entidade? | `docs\MAPA-ENTIDADES.md` | tabela DXF do `ezdxf` |
| o que existe nesta instalação, com que valor? | `docs\MAPA-AUTOCAD.md` | `getvar` ao vivo |
| **qual API é oficial/suportada e o que o MCP oficial cobre?** | `docs\MAPA-OFICIAL-MCP.md` | doc oficial Autodesk + relato de campo |
| **evidência por afirmação + prompt para agente** | `docs\LEIA-ME-MCP.md` | idem |

Números: **632 métodos COM**, **1572 tipos .NET**, **2054 campos DXF** em 83
entidades, **863 comandos** e **821 variáveis** vivas.

> Os quatro primeiros mapas são **medidos ao vivo** no AutoCAD. Os dois últimos são a
> **superfície oficial documentada** — incluem o que a Autodesk *não* suporta e um
> veredito sobre o MCP oficial do AutoCAD. Não os trate como a mesma coisa: um descreve
> comportamento, o outro descreve contrato e suporte.

## O que essa rodada acrescentou

- **`MAPA-DOTNET.md`** — 21 capacidades que o COM não tem foram conferidas membro a
  membro no catálogo: `Curve.GetSplitCurves`, `Entity.IntersectWith`,
  `Hatch.AppendLoop`, `Table.SetTextString`, `PlotEngine.BeginPlot`,
  `BlockReference` dinâmico, `Field`, layouts. **Todas existem** — o mapa diz onde.
- **`MAPA-ENTIDADES.md`** — 83 entidades com código de grupo, nome e tipo
  (`ponto`, `real`, `inteiro`, `angulo`). É o que o `entmake`/`entget` aceita.
  Marca 50/51 como ângulo e avisa: no arquivo é grau, no `entmake` é radiano.
- **`ferramentas\mapear_comandos.py`** — o gravador de prompts (em duas fases:
  `--iniciar` e `--ler`), para descobrir o que cada comando pede. **Ainda não rodou.**

## Pastas

| pasta | o que é |
|---|---|
| `docs\` | os quatro mapas + os JSONs crus. Ver `docs\LEIA-ME.md`. |
| `ferramentas\` | os scripts que **geram** o `docs\` (inclusive o `MapaDotnet`, em C#). Ver `ferramentas\LEIA-ME.md`. |
| `historico\` | `ocorrencias.jsonl`: as falhas reais que já custaram tempo. É a memória que não depende de conversa. |
| `plugin\` | a ponte .NET (`CadMcpBridge`), DLL compilada. Estado de cada parte no fim do `README.md`. |
| `skill\cad-planta-autocad\` | a skill pronta. **Portátil**: copiar para a pasta de skills de qualquer ferramenta. |
| `instalacao\` | wheel, `INSTALAR.md` (inclui `TRUSTEDPATHS`) e `mcp-config.json`. |
| `exemplos\` | o que o MCP produz: `planta_3q.dwg`, `.dxf`, `.pdf`, `.png`. |
| `codigo\` | o projeto inteiro (`src`, `tests`, `tools`, `vendor`, `plugin`, `docs`). |
| `PROMPT_TESTE_planta_L.md` | teste já executado: casa em L, 14 × 11 m, 10 ambientes (provou erase/move/setup). |
| `PROMPT_TESTE_apartamento.md` | pavimento tipo 21,60 × 12,00 m, 2 apartamentos espelhados + núcleo (cobra mirror/copy_filter/offset). |
| `PROMPT_TESTE_apto_multidisciplinar.md` | **teste executado 19/10**: apto 14,00 × 11,00 m, ARQ + elétrica + hidráulica + prancha de interferência, 204 entidades, tabelas A–I geradas por script. 11 PASS / 1 FAIL (PNG do viewport). Divergências do prompt original explicadas na seção 0. **Defeitos do relatório corrigidos e testados** (48 tools: PNG no path, plot 1:50 real, quantitativo com guarda, linetype_load, mirror_filter/rotate_filter). |

## O que funciona, o que não

| parte | estado |
|---|---|
| MCP `ezdxf` (planta → DXF/PDF/PNG) | funciona, testado |
| MCP `com` (desenho aberto) | funciona, testado |
| plugin carregar + `ping`/`info` | funciona, testado |
| `exec` da ponte | envia e volta; **não confirma** o resultado |
| `transaction` da ponte | implementado; **não testado** |
| TRIM/EXTEND/FILLET por comando | **não confiável** com ponto digitado |

## O que falta mapear

1. **A receita de cada comando** — o gravador está escrito, falta rodar com o
   AutoCAD aberto (é o que destrava TRIM/EXTEND/FILLET de verdade).
2. **Impressão e layout** — pagesetup, escalas, viewports, CTB/STB, o que o
   `accoreconsole` ignora.
3. **Estilos e arquivos de apoio** — `acad.lin`, `acad.pat`, CTB/STB.

## O próximo passo técnico

Cortar por **geometria**, não por comando: `IntersectWith` + `GetSplitCurves`,
apagando o trecho que contém o ponto. O mapa do .NET já provou que os membros
existem; falta implementar no plugin e testar.

## Antes de compartilhar

- O código **não tem licença definida** — decidir antes de distribuir.
- `codigo\vendor\autocad-mcp-pro-1.6.0` é **MIT** (Umutcan Edizsalan); o `LICENSE` e o
  `ORIGEM.md` têm que acompanhar a redistribuição.
