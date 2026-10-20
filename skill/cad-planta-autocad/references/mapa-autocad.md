# Mapa do AutoCAD — o que é durável

O mapa completo é gerado (`docs/MAPA-COM.md`, `docs/com-acad-2025.json`,
`docs/ALIASES.md`, `docs/COBERTURA.md`) e **não viaja com a skill**: são 1,8 MB e
mudam a cada versão. O que viaja é isto — as conclusões que não mudam.

## Números de referência (AutoCAD 2025, lido da type library)

| | |
|---|---|
| interfaces COM | 148 |
| métodos | 632 |
| propriedades | 1713 |
| apelidos (`acad.pgp`) | 411 |
| comandos citados em macro de menu | 630 |
| desses, usados com `-` (linha de comando) | 13 |

## A fronteira que decide o desenho do código

**Já é método COM** (não precisa de comando, nem de plugin, nem de foco):

`Offset` (Line/Arc/Circle/Ellipse/LWPolyline/Polyline), `Move`, `Copy`,
`Rotate`, `Mirror`, `Erase`, `ArrayPolar`, `ArrayRectangular`, `ScaleEntity`,
`TransformBy`, `Explode`, `GetBoundingBox`, `IntersectWith`.

**Não existe método nenhum** — só comando:

`TRIM`, `EXTEND`, `FILLET`, `CHAMFER`, `JOIN`, `STRETCH`.

Consequência prática: `TRIM`/`EXTEND` podem ser **calculados** com
`IntersectWith` + reescrever os pontos da entidade; `FILLET`/`CHAMFER`/`JOIN`
precisam de comando (plugin .NET, em processo) ou geometria própria.

## Fatos que evitam uma rodada perdida

- **`ModelSpace` e `PaperSpace` são `IAcadBlock`** — não existe `IAcadModelSpace`.
  `AddLine`, `AddCircle`, `AddText` moram em `IAcadBlock`.
- **Método herdado aparece só na interface base**: `GetBoundingBox` está em
  `IAcadEntity`, não em `IAcadLine`.
- **`AcadDocument.Wblock(path, selectionSet)` existe** — `WBLOCK` sem diálogo é
  API, não precisa de comando.
- **`AcadDocument.Export` / `Import`** cobrem DXF/DWG/PDF sem `-PLOT`.
- `PostCommand` = `SendCommand` (mesma semântica de espaço virando ENTER).
- Antes de qualquer chamada: `FILEDIA=0` e `CMDDIA=0`. `CMDACTIVE≠0` significa
  comando em andamento — não chamar COM agora.
- Variantes `-` comprovadamente usadas nos menus do próprio produto: `-ARRAY`,
  `-ATTEDIT`, `-BEDIT`, `-DIMSTYLE`, `-HATCHEDIT`, `-POINTCLOUDMANAGER`,
  `-PURGE`, `-SHADEMODE`, `-TOOLBAR`, `-VIEW`, `-VPOINT`, `-VPORTS`.

## Como regerar

```powershell
python tools\mapear_com.py      # sem AutoCAD: type library + pgp + cui
python tools\importar_acmpro.py # sem AutoCAD: cobertura 45 x 247
python tools\sonda_autocad.py   # com AutoCAD aberto: comandos reais + sysvars
```

O mapa envelhece: o `acadver` e o `quando` estão no JSON para não confundir
versão. Ao trocar de AutoCAD, rode de novo antes de confiar no número.

## Medido ao vivo (16/10/2026, AutoCAD 25.0)

`tools/sonda_autocad.py`, com o desenho aberto, gerou `docs/MAPA-AUTOCAD.md`:

- **863** comandos distintos (uniao de `C:` em LISP + macros do CUIX + apelidos do pgp);
  **13** so existem na forma `-COMANDO` no menu.
- **821** variaveis de sistema vivas, de 884 candidatas (as 63 restantes respondem `nil`).
- Sysvars **nao sao enumeraveis** por API. Os nomes vieram dos recursos da
  instalacao (`MsiKeyFile_<NOME>.dll`), do `$VARS` do DXF e de uma lista curta das
  classicas; o valor do `getvar` e que confirma a existencia.

### O que isso muda na pratica

- **TRIM/EXTEND/FILLET por comando + ponto digitado nao e' confiavel.** O comando
  volta sem erro e nao corta. Ponto digitado nao substitui o clique. O caminho
  certo e' geometria: `IntersectWith` + `Curve.GetSplitCurves` e apagar o trecho.
- **Estado do AutoCAD nao e' o padrao de fabrica.** Nesta maquina `FILEDIA` e
  `CMDDIA` estavam `0` e `OSMODE` `0`. Nao assumir: ler antes.
- Comando que espera selecao **nao pode** ser chamado por `Editor.Command`
  sincrono: ele trava o AutoCAD inteiro. Usar `SendStringToExecute`.
