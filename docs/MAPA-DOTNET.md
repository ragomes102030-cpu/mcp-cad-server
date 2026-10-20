# Mapa do .NET do AutoCAD — medido nas DLLs

Gerado em **2026-10-19** a partir da metadata de `acdbmgd.dll`, `acmgd.dll`, `accoremgd.dll`.

Não é documentação da Autodesk: é o que **existe de fato** nestas DLLs. Nomes de parâmetros não foram lidos (só a contagem) — o mapa diz que o membro existe, não a assinatura completa.

| assembly | tipos públicos com membros |
|---|---|
| `acdbmgd.dll` | 788 |
| `acmgd.dll` | 489 |
| `accoremgd.dll` | 295 |

**Total: 1572 tipos.**

## O que o COM não resolve (e o .NET resolve)

| fazer | membro | existe? | onde |
|---|---|---|---|
| Cortar curva por intersecoes | `Curve.GetSplitCurves` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Curve` |
| Onde a curva cruza outra | `Entity.IntersectWith` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Entity` |
| Ponto mais proximo na curva | `Curve.GetClosestPointTo` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Curve` |
| Parametro no ponto | `Curve.GetParameterAtPoint` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Curve` |
| Hatch com contorno proprio | `Hatch.AppendLoop` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Hatch` |
| Hatch: padrao | `Hatch.SetHatchPattern` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Hatch` |
| Tabela: escrever celula | `Table.SetTextString` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Table` |
| Tabela: celulas | `Table.Cells` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Table` |
| Bloco dinamico: propriedades | `BlockReference.DynamicBlockReferencePropertyCollection` | **sim** | `Autodesk.AutoCAD.DatabaseServices.BlockReference` |
| Atributos do bloco | `AttributeCollection.GetEnumerator` | **sim** | `Autodesk.AutoCAD.DatabaseServices.AttributeCollection` |
| Campo (Field) | `Field.GetFieldCode` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Field` |
| Layouts | `LayoutManager.CurrentLayout` | **sim** | `Autodesk.AutoCAD.DatabaseServices.LayoutManager` |
| Plotagem | `PlotEngine.BeginPlot` | **sim** | `Autodesk.AutoCAD.PlottingServices.PlotEngine` |
| Validar plot | `PlotSettingsValidator.SetPlotWindowArea` | **sim** | `Autodesk.AutoCAD.DatabaseServices.PlotSettingsValidator` |
| XData | `DBObject.GetXDataForApplication` | **sim** | `Autodesk.AutoCAD.DatabaseServices.DBObject` |
| Dicionario da entidade | `DBObject.ExtensionDictionary` | **sim** | `Autodesk.AutoCAD.DatabaseServices.DBObject` |
| Multi-leader | `MLeader.MText` | **sim** | `Autodesk.AutoCAD.DatabaseServices.MLeader` |
| Dimensao: medir | `Dimension.Measurement` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Dimension` |
| Regenerar | `Editor.Regen` | **sim** | `Autodesk.AutoCAD.EditorInput.Editor` |
| Selecionar por filtro | `Editor.SelectAll` | **sim** | `Autodesk.AutoCAD.EditorInput.Editor` |
| Transacao | `Transaction.Commit` | **sim** | `Autodesk.AutoCAD.DatabaseServices.Transaction` |

## As classes que vamos usar

### Curve  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.DatabaseServices.Entity` · assembly `acdbmgd.dll`

métodos: `GetPointAtParameter/1`, `GetParameterAtPoint/1`, `GetDistanceAtParameter/1`, `GetParameterAtDistance/1`, `GetDistAtPoint/1`, `GetPointAtDist/1`, `GetFirstDerivative/1`, `GetSecondDerivative/1`, `GetClosestPointTo/3`, `GetClosestPointTo/2`, `GetOrthoProjectedCurve/1`, `GetProjectedCurve/2`, `GetOffsetCurves/1`, `GetOffsetCurvesGivenPlaneNormal/2`, `GetSplitCurves/1`, `Extend/2`, `Extend/1`, `ReverseCurve/0` … (+8)

propriedades: `Area`, `Spline`, `EndPoint`, `StartPoint`, `EndParam`, `StartParam`, `IsPeriodic`, `Closed`

### Hatch  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.DatabaseServices.Entity` · assembly `acdbmgd.dll`

métodos: `LoopTypeAt/1`, `GetLoopAt/1`, `AppendLoop/3`, `AppendLoop/2`, `AppendLoop/1`, `InsertLoopAt/3`, `InsertLoopAt/2`, `RemoveLoopAt/1`, `GetAssociatedObjectIdsAt/1`, `GetAssociatedObjectIds/0` … (+10)

propriedades: `Origin`, `Area`, `NumberOfHatchLines`, `HatchStyle`, `NumberOfPatternDefinitions`, `PatternDouble`, `PatternScale`, `PatternSpace`, `PatternAngle`, `PatternName` … (+16)

### Table  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.DatabaseServices.BlockReference` · assembly `acdbmgd.dll`

métodos: `ColumnWidth/1`, `SetColumnWidth/1`, `SetColumnWidth/2`, `RowHeight/1`, `SetRowHeight/1`, `SetRowHeight/2`, `MinimumColumnWidth/1`, `MinimumRowHeight/1`, `Alignment/2`, `Alignment/1`, `SetAlignment/3`, `SetAlignment/2` … (+195)

propriedades: `Cells`, `Rows`, `Columns`, `BreakOptions`, `BreakFlowDirection`, `BreakEnabled`, `HasSubSelection`, `SubSelection`, `IsHeaderSuppressed`, `TableStyleName`, `IsTitleSuppressed`, `FlowDirection` … (+10)

### BlockReference  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.DatabaseServices.Entity` · assembly `acdbmgd.dll`

métodos: `GeometryExtentsBestFit/0`, `GeometryExtentsBestFit/1`, `ExplodeToOwnerSpace/0`, `ResetBlock/0`, `ConvertToStaticBlock/1`, `ConvertToStaticBlock/0`

propriedades: `UnitFactor`, `BlockUnit`, `Name`, `AnonymousBlockTableRecord`, `DynamicBlockTableRecord`, `IsDynamicBlock`, `DynamicBlockReferencePropertyCollection`, `TreatAsBlockRefForExplode`, `AttributeCollection`, `BlockTransform` … (+5)

### Editor  ·  `Autodesk.AutoCAD.EditorInput`

herda de `System.MarshalByRefObject` · assembly `accoremgd.dll`

métodos: `GetViewportNumber/1`, `PointToScreen/2`, `PointToWorld/2`, `PointToWorld/1`, `WriteMessage/2`, `WriteMessage/1`, `GetSelection/2`, `GetSelection/1`, `GetSelection/0`, `SelectAll/1`, `SelectAll/0`, `SelectCrossingWindow/4` … (+55)

propriedades: `MouseHasMoved`, `CurrentUserCoordinateSystem`, `UseCommandLineInterface`, `IsDragging`, `IsQuiescentForTransparentCommand`, `IsQuiescent`, `CurrentViewportObjectId`, `ActiveViewportId`, `Document`

### Database  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.Runtime.RXObject` · assembly `acdbmgd.dll`

métodos: `RuntimeId/0`, `IdFromDb/1`, `DbFromId/1`, `AddDBObject/1`, `MarkObjectNonPersistent/2`, `IsObjectNonPersistent/2`, `ReclaimMemoryFromErasedObjects/1`, `Purge/1`, `CountHardReferences/2`, `GetObjectId/3` … (+67)

propriedades: `HomeView`, `GeoDataObject`, `UpdateThumbnail`, `MsOleScale`, `LayerNotify`, `LayerEval`, `Indexctl`, `PdfFrame`, `DgnFrame`, `DwfFrame` … (+312)

### Transaction  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.Runtime.RXObject` · assembly `acdbmgd.dll`

métodos: `GetObject/4`, `GetObject/3`, `GetObject/2`, `GetAllObjects/0`, `Commit/0`, `Abort/0` … (+1)

propriedades: `TransactionManager`, `NumberOfOpenedObjects`

### LayoutManager  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.Runtime.RXObject` · assembly `acdbmgd.dll`

métodos: `SetCurrentLayoutId/1`, `GetLayoutId/1`, `CopyLayout/2`, `DeleteLayout/1`, `CreateLayout/1`, `RenameLayout/2` … (+3)

propriedades: `LayoutCount`, `CurrentLayout`, `Current`

### PlotEngine  ·  `Autodesk.AutoCAD.PlottingServices`

herda de `Autodesk.AutoCAD.Runtime.DisposableWrapper` · assembly `accoremgd.dll`

métodos: `BeginPlot/2`, `EndPlot/1`, `BeginDocument/6`, `EndDocument/1`, `BeginPage/4`, `EndPage/1` … (+3)

propriedades: `IsBackgroundPackaging`

### Polyline  ·  `Autodesk.AutoCAD.DatabaseServices`

herda de `Autodesk.AutoCAD.DatabaseServices.Curve` · assembly `acdbmgd.dll`

métodos: `ConvertFrom/2`, `ConvertTo/1`, `GetPoint3dAt/1`, `GetSegmentType/1`, `GetLineSegment2dAt/1`, `GetArcSegment2dAt/1`, `GetLineSegmentAt/1`, `GetArcSegmentAt/1`, `OnSegmentAt/4`, `AddVertexAt/5`, `RemoveVertexAt/1`, `GetPoint2dAt/1` … (+10)

propriedades: `Length`, `HasWidth`, `HasBulges`, `NumberOfVertices`, `IsOnlyLines`, `Normal`, `ConstantWidth`, `Thickness`, `Elevation`, `Plinegen`, `Closed`

### Polyline  ·  `Autodesk.AutoCAD.GraphicsInterface`

herda de `Autodesk.AutoCAD.Runtime.DisposableWrapper` · assembly `acdbmgd.dll`


propriedades: `BaseSubEntMarker`, `Normal`, `Points`

## Onde ficam as coisas

| namespace | tipos |
|---|---|
| `Autodesk.AutoCAD.DatabaseServices` | 499 |
| `Autodesk.AutoCAD.Internal` | 150 |
| `Autodesk.AutoCAD.EditorInput` | 131 |
| `Autodesk.AutoCAD.Windows.Data` | 113 |
| `Autodesk.AutoCAD.Geometry` | 104 |
| `Autodesk.AutoCAD.ApplicationServices` | 85 |
| `Autodesk.AutoCAD.GraphicsInterface` | 75 |
| `Autodesk.AutoCAD.Runtime` | 63 |
| `Autodesk.AutoCAD.Windows` | 60 |
| `(sem namespace)` | 36 |
| `Autodesk.AutoCAD.Internal.Reactors` | 36 |
| `Autodesk.AutoCAD.PlottingServices` | 34 |
| `Autodesk.AutoCAD.Publishing` | 32 |
| `Autodesk.AutoCAD.GraphicsSystem` | 24 |
| `Autodesk.AutoCAD.Internal.Calculator` | 17 |

## O corte por geometria — o que substitui o TRIM

O comando TRIM precisa de clique e não devolve resultado (ver `historico/`).
Com os membros acima o corte vira conta, dentro de uma transação:

1. `Entity.IntersectWith` entre a curva e cada corte → pontos de interseção;
2. `Curve.GetParameterAtPoint` em cada ponto → parâmetros ordenados;
3. `Curve.GetSplitCurves(pontos)` → as N partes;
4. `Curve.GetClosestPointTo(ponto_do_clique)` em cada parte → a parte clicada;
5. apagar essa parte e adicionar as outras, tudo no mesmo `Transaction.Commit`.

Isso resolve TRIM e EXTEND sem tela, sem prompt e sem depender de `TRIMEXTENDMODE`.
Falta implementar no plugin e testar com o AutoCAD aberto.

