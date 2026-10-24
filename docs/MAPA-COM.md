# Mapa do COM do AutoCAD 2025 (type library oficial)

Fonte: `acax25enu.tlb` (lida com `comtypes`; o AutoCAD não precisa estar aberto).
Gerado por `tools/mapear_com.py` em 2026-10-23T22:50:22-03:00. Não editar à mão.

| | |
|---|---|
| interfaces | 148 |
| métodos | 632 |
| propriedades | 1713 |
| apelidos de comando (`acad.pgp`) | 411 |
| comandos citados em macro de menu | 630 |

## O teste que importa: existe método de edição?

| operação | método COM encontrado |
|---|---|
| `trim` | **nenhum** |
| `extend` | **nenhum** |
| `fillet` | **nenhum** |
| `chamfer` | **nenhum** |
| `offset` | `IAcadArc.Offset`, `IAcadCircle.Offset`, `IAcadEllipse.Offset`, `IAcadLWPolyline.Offset`, `IAcadLine.Offset`, `IAcadPolyline.Offset`, `IAcadSpline.Offset`, `IAcadXline.Offset` |
| `boundary` | `IAcadRasterImage.ClipBoundary`, `IAcadUnderlay.ClipBoundary` |
| `join` | **nenhum** |
| `explode` | `IAcad3DPolyline.Explode`, `IAcadBlockReference.Explode`, `IAcadLWPolyline.Explode`, `IAcadPolygonMesh.Explode`, `IAcadPolyline.Explode`, `IAcadRegion.Explode` |
| `mirror` | `IAcadEntity.Mirror`, `IAcadEntity.Mirror3D` |
| `rotate` | `IAcadBlock.AddDimRotated`, `IAcadEntity.Rotate`, `IAcadEntity.Rotate3D` |
| `move` | `IAcadDictionary.Remove`, `IAcadEntity.Move`, `IAcadGroup.RemoveItems`, `IAcadMLeader.RemoveLeader`, `IAcadMLeader.RemoveLeaderLine`, `IAcadPopupMenu.RemoveFromMenuBar`, `IAcadPopupMenus.RemoveMenuFromMenuBar`, `IAcadSection.RemoveVertex`, `IAcadSelectionSet.RemoveItems`, `IAcadSortentsTable.MoveAbove`, `IAcadSortentsTable.MoveBelow`, `IAcadSortentsTable.MoveToBottom`, `IAcadSortentsTable.MoveToTop`, `IAcadSummaryInfo.RemoveCustomByIndex`, `IAcadSummaryInfo.RemoveCustomByKey`, `IAcadTable.MoveContent`, `IAcadTable.RemoveAllOverrides` |
| `copy` | `IAcadDatabase.CopyObjects`, `IAcadDimStyle.CopyFrom`, `IAcadEntity.Copy`, `IAcadPlotConfiguration.CopyFrom`, `IAcadPreferencesProfiles.CopyProfile` |
| `erase` | `IAcadObject.Erase`, `IAcadSelectionSet.Erase` |
| `array` | `IAcadEntity.ArrayPolar`, `IAcadEntity.ArrayRectangular`, `IAcadUtility.CreateTypedArray` |
| `stretch` | **nenhum** |
| `scale` | `IAcadApplication.ZoomScaled`, `IAcadEntity.ScaleEntity`, `IAcadPlotConfiguration.GetCustomScale`, `IAcadPlotConfiguration.SetCustomScale`, `IAcadTable.GetAutoScale`, `IAcadTable.GetAutoScale2`, `IAcadTable.GetBlockScale`, `IAcadTable.GetScale`, `IAcadTable.SetAutoScale`, `IAcadTable.SetAutoScale2`, `IAcadTable.SetBlockScale`, `IAcadTable.SetScale` |

## Objetos que usamos de perto

ModelSpace e PaperSpace **são** `IAcadBlock` (não existe `IAcadModelSpace`).
Método herdado aparece só na interface base: `AddLine` está em `IAcadBlock`,
não em `IAcadDocument`.

### IAcadApplication — 19 métodos, 21 propriedades

`Eval`, `GetAcadState`, `GetInterfaceObject`, `ListArx`, `LoadArx`, `LoadDVB`, `Quit`, `RunMacro`, `UnloadArx`, `UnloadDVB`, `Update`, `Zoom`, `ZoomAll`, `ZoomCenter`, `ZoomExtents`, `ZoomPickWindow`, `ZoomPrevious`, `ZoomScaled`, `ZoomWindow`

### IAcadDocument — 19 métodos, 30 propriedades

`Activate`, `AuditInfo`, `Close`, `EndUndoMark`, `Export`, `GetVariable`, `Import`, `LoadShapeFile`, `New`, `Open`, `PostCommand`, `PurgeAll`, `Regen`, `Save`, `SaveAs`, `SendCommand`, `SetVariable`, `StartUndoMark`, `Wblock`

### IAcadDatabase — 3 métodos, 22 propriedades

`CopyObjects`, `HandleToObject`, `ObjectIdToObject`

### IAcadBlock — 58 métodos, 14 propriedades

`Add3DFace`, `Add3DMesh`, `Add3DPoly`, `AddArc`, `AddAttribute`, `AddBox`, `AddCircle`, `AddCone`, `AddCustomObject`, `AddCylinder`, `AddDim3PointAngular`, `AddDimAligned`, `AddDimAngular`, `AddDimArc`, `AddDimDiametric`, `AddDimOrdinate`, `AddDimRadial`, `AddDimRadialLarge`, `AddDimRotated`, `AddEllipse`, `AddEllipticalCone`, `AddEllipticalCylinder`, `AddExtrudedSolid`, `AddExtrudedSolidAlongPath`, `AddHatch`, `AddLeader`, `AddLightWeightPolyline`, `AddLine` …

### IAcadBlocks — 2 métodos, 2 propriedades

`Add`, `Item`

### IAcadEntity — 14 métodos, 13 propriedades

`ArrayPolar`, `ArrayRectangular`, `Copy`, `GetBoundingBox`, `Highlight`, `IntersectWith`, `Mirror`, `Mirror3D`, `Move`, `Rotate`, `Rotate3D`, `ScaleEntity`, `TransformBy`, `Update`

### IAcadLine — 1 métodos, 7 propriedades

`Offset`

### IAcadArc — 1 métodos, 11 propriedades

`Offset`

### IAcadCircle — 1 métodos, 7 propriedades

`Offset`

### IAcadLWPolyline — 7 métodos, 10 propriedades

`AddVertex`, `Explode`, `GetBulge`, `GetWidth`, `Offset`, `SetBulge`, `SetWidth`

### IAcadPolyline — 7 métodos, 11 propriedades

`AppendVertex`, `Explode`, `GetBulge`, `GetWidth`, `Offset`, `SetBulge`, `SetWidth`

### IAcadText — 1 métodos, 16 propriedades

`FieldCode`

### IAcadMText — 1 métodos, 13 propriedades

`FieldCode`

### IAcadHatch — 6 métodos, 21 propriedades

`AppendInnerLoop`, `AppendOuterLoop`, `Evaluate`, `GetLoopAt`, `InsertLoopAt`, `SetPattern`

### IAcadDimension — 0 métodos, 29 propriedades

### IAcadDimRotated — 0 métodos, 64 propriedades

### IAcadDimAligned — 0 métodos, 66 propriedades

### IAcadSelectionSet — 12 métodos, 4 propriedades

`AddItems`, `Clear`, `Delete`, `Erase`, `Highlight`, `Item`, `RemoveItems`, `Select`, `SelectAtPoint`, `SelectByPolygon`, `SelectOnScreen`, `Update`

### IAcadSelectionSets — 2 métodos, 3 propriedades

`Add`, `Item`

### IAcadLayout — 0 métodos, 2 propriedades

### IAcadLayouts — 2 métodos, 2 propriedades

`Add`, `Item`

### IAcadPlot — 5 métodos, 4 propriedades

`DisplayPlotPreview`, `PlotToDevice`, `PlotToFile`, `SetLayoutsToPlot`, `StartBatchMode`

### IAcadPlotConfiguration — 12 métodos, 20 propriedades

`CopyFrom`, `GetCanonicalMediaNames`, `GetCustomScale`, `GetLocaleMediaName`, `GetPaperMargins`, `GetPaperSize`, `GetPlotDeviceNames`, `GetPlotStyleTableNames`, `GetWindowToPlot`, `RefreshPlotDeviceInfo`, `SetCustomScale`, `SetWindowToPlot`

### IAcadAttributeReference — 1 métodos, 25 propriedades

`UpdateMTextAttribute`

### IAcadBlockReference — 7 métodos, 15 propriedades

`ConvertToAnonymousBlock`, `ConvertToStaticBlock`, `Explode`, `GetAttributes`, `GetConstantAttributes`, `GetDynamicBlockProperties`, `ResetBlock`

### IAcadGroup — 5 métodos, 12 propriedades

`AppendItems`, `Highlight`, `Item`, `RemoveItems`, `Update`

### IAcadGroups — 2 métodos, 2 propriedades

`Add`, `Item`

### IAcadLayer — 0 métodos, 14 propriedades

### IAcadLayers — 3 métodos, 2 propriedades

`Add`, `GenerateUsageData`, `Item`

### IAcadAcCmColor — 4 métodos, 8 propriedades

`Delete`, `SetColorBookColor`, `SetNames`, `SetRGB`

### IAcadRegion — 2 métodos, 9 propriedades

`Boolean`, `Explode`

### IAcadTable — 166 métodos, 28 propriedades

`ClearSubSelection`, `ClearTableStyleOverrides`, `CreateContent`, `DeleteCellContent`, `DeleteColumns`, `DeleteContent`, `DeleteRows`, `EnableMergeAll`, `FormatValue`, `GenerateLayout`, `GetAlignment`, `GetAttachmentPoint`, `GetAutoScale`, `GetAutoScale2`, `GetBackgroundColor`, `GetBackgroundColorNone`, `GetBlockAttributeValue`, `GetBlockAttributeValue2`, `GetBlockRotation`, `GetBlockScale`, `GetBlockTableRecordId`, `GetBlockTableRecordId2`, `GetBreakHeight`, `GetCellAlignment`, `GetCellBackgroundColor`, `GetCellBackgroundColorNone`, `GetCellContentColor`, `GetCellDataType` …

### IAcadPreferences — 0 métodos, 10 propriedades

### IAcadUtility — 30 métodos, 0 propriedades

`AngleFromXAxis`, `AngleToReal`, `AngleToString`, `CreateTypedArray`, `DistanceToReal`, `GetAngle`, `GetCorner`, `GetDistance`, `GetEntity`, `GetInput`, `GetInteger`, `GetKeyword`, `GetObjectIdString`, `GetOrientation`, `GetPoint`, `GetReal`, `GetRemoteFile`, `GetString`, `GetSubEntity`, `InitializeUserInput`, `IsRemoteFile`, `IsURL`, `LaunchBrowserDialog`, `PolarPoint`, `Prompt`, `PutRemoteFile`, `RealToString`, `SendModelessOperationEnded` …

### IAcadState — 0 métodos, 2 propriedades

## Os 15 objetos com mais métodos

| objeto | métodos |
|---|---|
| `IAcadTable` | 166 |
| `IAcadBlock` | 58 |
| `IAcadTableStyle` | 56 |
| `IAcadUtility` | 30 |
| `IAcadApplication` | 19 |
| `IAcadDocument` | 19 |
| `IAcadEntity` | 14 |
| `IAcadMLeader` | 14 |
| `IAcadPlotConfiguration` | 12 |
| `IAcadSelectionSet` | 12 |
| `IAcadSpline` | 12 |
| `IAcadSortentsTable` | 9 |
| `IAcadDictionary` | 8 |
| `IAcadSummaryInfo` | 8 |
| `IAcadBlockReference` | 7 |
