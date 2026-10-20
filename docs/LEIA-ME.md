# docs\ — o mapa, e quem gera cada pedaço

Nada aqui é escrito à mão. Cada arquivo tem um script em `tools/` e uma data
dentro. Mapa velho não é mapa errado: é mapa de outro dia.

| arquivo | gerado por | precisa do AutoCAD aberto? | responde |
|---|---|---|---|
| `MAPA-COM.md` | `tools/mapear_com.py` | não (lê `acax25enu.tlb`) | quais interfaces/métodos/propriedades o COM tem |
| `com-acad-2025.json` | idem | não | a mesma coisa, cru |
| `ALIASES.md` | idem (lê `acad.pgp`) | não | 411 apelidos → 321 comandos |
| `COBERTURA.md` | `tools/importar_acmpro.py` | não (lê o vendor) | nossas 40 ferramentas × as 247 do acmpro |
| `catalogo-acmpro.json` | idem | não | as 247, com família |
| `MAPA-AUTOCAD.md` | `tools/sonda_autocad.py` | **sim** | 863 comandos e 821 variáveis vivas, com o valor de agora |
| `catalogo-autocad.json` | idem | **sim** | a mesma coisa, cru |
| `MAPA-DOTNET.md` | `tools/MapaDotnet` + `tools/resumir_dotnet.py` | não (lê as DLLs) | 1572 tipos do .NET: `GetSplitCurves`, `Hatch.AppendLoop`, `Table`, `PlotEngine`… |
| `catalogo-dotnet.json` | `tools/MapaDotnet` | não | a metadata crua dos 3 assemblies |
| `MAPA-ENTIDADES.md` | `tools/mapear_entidades.py` | não (lê o ezdxf) | 83 entidades, 2054 campos DXF, com código e tipo |
| `catalogo-entidades.json` | idem | não | a mesma coisa, cru |

## O que ainda não tem mapa

- **A receita de cada comando** (o que ele pede, em ordem). O gravador existe
  (`tools/mapear_comandos.py`, em duas fases) mas ainda não rodou — precisa do
  AutoCAD aberto e é o que destrava TRIM/EXTEND/FILLET.
- **Impressão/layout**: pagesetup, escalas, CTB/STB, o que o `accoreconsole` ignora.
- **Estilos e arquivos de apoio**: `acad.lin`, `acad.pat`, CTB/STB.

## Regra de leitura

- `MAPA-COM.md` → o que dá para fazer **sem** comando.
- `MAPA-DOTNET.md` → o que só o .NET resolve (corte por geometria, tabela, hatch).
- `MAPA-ENTIDADES.md` → os campos de cada entidade (entmake/entget).
- `MAPA-AUTOCAD.md` → o que existe **nesta** instalação, com o valor de agora.
- `COBERTURA.md` → o que **nós** já embrulhamos, e o tamanho do que falta.
