# Cobertura — nós × autocad-mcp-pro 1.6.0

Gerado por `python tools/importar_acmpro.py`. Não editar à mão.

| | deles | nossos | mesmo nome |
|---|---|---|---|
| total | 247 | 119 | 108 |

**Mesmo nome não é a mesma ferramenta.** `drawing_save` deles e o nosso fazem
coisas diferentes nos detalhes. A comparação serve para achar **buraco**, não
para dizer que já temos.

## Por família

| família | deles | nossos | faltando |
|---|---|---|---|
| desenho | 31 | 19 | 12 |
| plot/arquivo | 30 | 24 | 6 |
| camada/estilo | 30 | 17 | 13 |
| edicao | 29 | 19 | 10 |
| consulta | 24 | 6 | 18 |
| sistema | 23 | 4 | 19 |
| arquitetura | 19 | 9 | 10 |
| mecanica | 13 | 0 | 13 |
| bloco | 11 | 6 | 5 |
| cota/anotacao | 9 | 5 | 4 |
| P&ID | 9 | 0 | 9 |
| 3D/solido | 8 | 0 | 8 |
| selecao | 5 | 4 | 1 |
| visualizacao | 3 | 2 | 1 |
| outros | 2 | 3 | 0 |
| texto | 1 | 1 | 0 |

## Nossas ferramentas, com o nome público

| nossa | exposta como | existe no deles | resumo deles |
|---|---|---|---|
| arch_dimension_chains | `arch_dimension_chains` | sim | Dimension the plan's facades: openings, walls and overall chains outsi |
| arch_grid | `arch_grid` | sim | Draw a structural grid: axis lines with numbered and lettered bubbles  |
| arch_room | `arch_room` | sim | Label a room with its name, number and measured area. |
| arch_rooms_detect | `arch_rooms_detect` | sim | Find the rooms of any plan and measure them; never modifies it. |
| arch_symbol | `arch_symbol` | sim | Draw a plan symbol: north arrow, section mark, level mark or elevation |
| batch_plot | `batch_plot` | sim | Plot every sheet (or the named ones) to PDF; each sheet size is read b |
| block_define | `block_define` | sim | Define a block from typed primitives and attribute definitions, on bot |
| block_get_attributes | `block_get_attributes` | sim | Read the tag/value pairs off a block reference. |
| block_insert | `block_insert` | sim | Place a block, filling in its attribute values as you go. |
| block_list | `block_list` | sim | List the block definitions the drawing already carries. |
| block_set_attributes | `block_set_attributes` | sim | Fill in a block reference's attributes, such as title-block fields. |
| cancel | `cancel` | **não** | só nossa |
| construction_xline | `construction_xline` | sim | Lay down an infinite guide line to build geometry against. |
| dimension_aligned | `dimension_aligned` | sim | Dimension the true distance between two points, along a slope. |
| dimension_angular | `dimension_angular` | sim | Dimension the included angle between two rays from a vertex. |
| dimension_linear | `dimension_linear` | sim | Dimension a horizontal or vertical size, with an ISO 129 tolerance or  |
| dimension_radius | `dimension_radius` | sim | Call out the radius of a circle or arc, optionally toleranced. |
| dimstyle_list | `dimstyle_list` | sim | List dimension styles with their ISO-25/ANSI variables and the current |
| document_close | `document_close` | sim | Close one open document by name; never drops unsaved work unless told  |
| drawing_apply_iso_layers | `drawing_apply_iso_layers` | sim | Set up a standard ISO layer set with the right colours and lineweights |
| drawing_apply_standard | `drawing_apply_standard` | sim | Put the drawing on ISO or ANSI in one call: dimstyle, text style, unit |
| drawing_audit | `drawing_audit` | sim | Scan the drawing for structural errors and repair what it finds. |
| drawing_close | `drawing_close` | sim | Close the drawing, saving first unless you say otherwise. |
| drawing_export_dwg | `drawing_export_dwg` | sim | Write the drawing as a real DWG at a chosen AutoCAD version. |
| drawing_export_dxf | `drawing_export_dxf` | sim | Write a DXF interchange copy of the drawing. |
| drawing_export_pdf | `drawing_export_pdf` | sim | Plot the drawing, or one paper-space layout, to PDF. |
| drawing_info | `drawing_info` | sim | Read the current drawing's name, path, extents and object counts. |
| drawing_new | `drawing_new` | sim | Start a drawing: blank with the engineering layers, or from a bundled/ |
| drawing_open | `drawing_open` | sim | Load an existing DXF from disk (DWG only on the live AutoCAD backend). |
| drawing_properties_get | `drawing_properties_get` | sim | Read the drawing's title, subject, author, keywords, comments and cust |
| drawing_properties_set | `drawing_properties_set` | sim | Set the drawing's summary fields and add, change or delete custom prop |
| drawing_purge | `drawing_purge` | sim | Strip unused layers, blocks, linetypes and styles out of the file. |
| drawing_redo | `drawing_redo` | sim | Reapply the operation you just undid. |
| drawing_save | `drawing_save` | sim | Write the drawing back to its file, or to a path you give. |
| drawing_save_as | `drawing_save_as` | sim | Save a copy under a new name; the extension picks DXF, DWG or DWT. |
| drawing_setup | `drawing_setup` | **não** | só nossa |
| drawing_undo | `drawing_undo` | sim | Step back one operation. |
| entity_array_polar | `entity_array_polar` | sim | Repeat an entity around a centre: a bolt circle or radial pattern. |
| entity_array_rectangular | `entity_array_rectangular` | sim | Repeat an entity in a grid of rows and columns. |
| entity_chamfer | `entity_chamfer` | sim | Bevel a corner between two lines by two setback distances. |
| entity_copy | `entity_copy` | sim | Duplicate an entity and offset the copy. |
| entity_copy_filter | `entity_copy_filter` | **não** | só nossa |
| entity_create_arc | `entity_create_arc` | sim | Draw a circular arc from a centre, a radius and two angles. |
| entity_create_circle | `entity_create_circle` | sim | Draw a circle: a hole, a bore, a pitch circle. |
| entity_create_ellipse | `entity_create_ellipse` | sim | Draw an ellipse from its centre, major axis vector and axis ratio. |
| entity_create_hatch | `entity_create_hatch` | sim | Fill a closed boundary with a section pattern such as ANSI31 or SOLID. |
| entity_create_line | `entity_create_line` | sim | Draw a straight line between two points. |
| entity_create_mtext | `entity_create_mtext` | sim | Place a wrapped paragraph note in a text box of a given width. |
| entity_create_point | `entity_create_point` | sim | Place a point marker (node) at a coordinate. |
| entity_create_polyline | `entity_create_polyline` | sim | Draw a connected outline or closed profile through a list of points. |
| entity_create_rectangle | `entity_create_rectangle` | sim | Draw a closed rectangle from two opposite corners. |
| entity_create_revcloud | `entity_create_revcloud` | sim | Draw a revision cloud around an area. |
| entity_create_spline | `entity_create_spline` | sim | Draw a smooth NURBS curve through fit points. |
| entity_create_table | `entity_create_table` | sim | Place a parts list, BOM or schedule as a table with headers and rows. |
| entity_create_text | `entity_create_text` | sim | Place a single-line text label. |
| entity_delete_many | `entity_delete_many` | sim | Erase a whole list of entities in one call. |
| entity_edit_text | `entity_edit_text` | sim | Reword a label, or change its height or rotation, keeping its handle. |
| entity_erase | `entity_erase` | **não** | só nossa |
| entity_erase_filter | `entity_erase_filter` | **não** | só nossa |
| entity_extend | `entity_extend` | sim | Lengthen a line until it meets a boundary line. |
| entity_fillet | `entity_fillet` | sim | Round a corner between two lines with a tangent arc. |
| entity_get | `entity_get` | sim | Inspect one entity by handle: type, layer, colour and geometry. |
| entity_list | `entity_list` | sim | Browse the drawing's entities and their handles, filtered by type or l |
| entity_mirror | `entity_mirror` | sim | Reflect an entity across a mirror line, keeping or dropping the origin |
| entity_mirror_filter | `entity_mirror_filter` | **não** | só nossa |
| entity_move | `entity_move` | sim | Shift an entity by a displacement vector. |
| entity_offset | `entity_offset` | sim | Make a parallel copy of a line, circle or polyline at a set distance. |
| entity_rotate | `entity_rotate` | sim | Turn an entity about a base point by an angle in degrees. |
| entity_rotate_filter | `entity_rotate_filter` | **não** | só nossa |
| entity_scale | `entity_scale` | sim | Resize an entity uniformly about a base point. |
| entity_set_properties | `entity_set_properties` | sim | Change an entity's layer, colour, linetype, lineweight or visibility. |
| entity_trim | `entity_trim` | sim | Cut a line back to where another crosses it, keeping the side you poin |
| hatch_edit | `hatch_edit` | sim | Change a hatch's pattern, scale, angle, colour or island style. |
| hatch_material | `hatch_material` | sim | Hatch a region with the ISO 128-50 section pattern for a named materia |
| image_attach | `image_attach` | sim | Attach a raster image (PNG/JPG) as an underlay. |
| layer_create | `layer_create` | sim | Add a layer with a colour, linetype and lineweight. |
| layer_delete | `layer_delete` | sim | Remove an empty layer from the drawing. |
| layer_freeze | `layer_freeze` | sim | Freeze a layer so it stops drawing and regenerating. |
| layer_hide | `layer_hide` | sim | Turn a layer off so its entities stop showing. |
| layer_isolate | `layer_isolate` | sim | Hide every layer except one, to work on it alone. |
| layer_linetype_load | `layer_linetype_load` | **não** | só nossa |
| layer_list | `layer_list` | sim | List every layer with its colour, linetype and visibility state. |
| layer_lock | `layer_lock` | sim | Lock a layer so its entities can be seen but not edited. |
| layer_modify | `layer_modify` | sim | Change an existing layer's colour, linetype or lineweight. |
| layer_set_current | `layer_set_current` | sim | Choose the layer that new geometry lands on. |
| layer_show | `layer_show` | sim | Turn a layer that was switched off back on. |
| layer_thaw | `layer_thaw` | sim | Bring a frozen layer back into view. |
| layer_unlock | `layer_unlock` | sim | Unlock a layer so its entities can be edited again. |
| layout_copy | `layout_copy` | sim | Duplicate a sheet with its page setup and geometry. |
| layout_create | `layout_create` | sim | Add a new paper-space sheet tab to the drawing. |
| layout_delete | `layout_delete` | sim | Delete a sheet tab and everything drawn on it. |
| layout_list | `layout_list` | sim | List the sheet tabs: Model plus every paper-space layout. |
| layout_rename | `layout_rename` | sim | Rename a sheet tab, keeping its geometry and handles. |
| layout_set_current | `layout_set_current` | sim | Switch to a sheet tab, or back to model space. |
| leader_create_mleader | `leader_create_mleader` | sim | Add a callout: an arrow with a note on the end. |
| linetype_list | `linetype_list` | sim | List the dash patterns currently loaded in the drawing. |
| page_setup_apply | `page_setup_apply` | sim | Set a sheet's paper, orientation, ctb, plot scale and device (PAGESETU |
| page_setup_list | `page_setup_list` | sim | Read each sheet's page setup: paper, orientation, ctb, scale, device. |
| plot_style_list | `plot_style_list` | sim | List the plot style tables (ctb): the AutoCAD catalogue, plus what is  |
| point_from_snap | `point_from_snap` | sim | Get an exact endpoint, midpoint, centre, quadrant or perpendicular foo |
| point_tangent | `point_tangent` | sim | Find where a line from an outside point touches a circle. |
| quantitativo | `quantitativo` | **não** | só nossa |
| script | `script` | **não** | só nossa |
| selection_window | `selection_window` | sim | Select entities inside or crossing a rectangle. |
| system_run_command | `system_run_command` | sim | Send a raw command string to the AutoCAD command line (COM only). |
| system_status | `system_status` | sim | Check the connection: which engine is live and what document is open. |
| textstyle_list | `textstyle_list` | sim | List text styles: font file, height, width factor, oblique angle. |
| user_pick_point | `user_pick_point` | sim | Ask the operator to pick a point on screen (live only; blocks until th |
| view_render_png | `view_render_png` | **não** | só nossa |
| view_screenshot | `view_screenshot` | sim | Capture a PNG picture of the drawing as it currently looks. |
| view_zoom_extents | `view_zoom_extents` | sim | Zoom out until every entity fits on screen. |
| view_zoom_window | `view_zoom_window` | sim | Zoom in on a rectangular region of the drawing. |
| viewport_create | `viewport_create` | sim | Put a scaled window onto model space on a sheet, at 1:1, 1:2 and so on |
| viewport_delete | `viewport_delete` | sim | Remove a viewport from a sheet. |
| viewport_list | `viewport_list` | sim | List the viewports on a sheet with their scales and locks. |
| viewport_lock | `viewport_lock` | sim | Lock a viewport so its scale cannot be zoomed away. |
| viewport_set_scale | `viewport_set_scale` | sim | Set a viewport's scale, e.g. 1:2 or 1:50. |
| xref_attach | `xref_attach` | sim | Attach a DWG/DXF as an external reference (attachment or overlay). |
| xref_manage | `xref_manage` | sim | List, reload, bind, detach or repath an external reference. |

## O que eles têm e nós não (candidatos, por família)

### desenho (13)

- `drawing_settings` — Read or change drawing units, precision, linetype and dimension scale by name.
- `keyway_draw_keyed_bore` — Draw a bore with a DIN 6885 keyway, auto-sized from the bore diameter.
- `keyway_draw_section` — Draw the side cross-section of a keyed bore.
- `drawing_finalize` — Finish the drawing: validate, critique, save, screenshot and score it.
- `drawing_deliver` — Hand the drawing off: a hashed, validated bundle of files plus a manifest.
- `drawing_preflight` — Check the brief before you draw: units, part type, tolerances, missing inputs.
- `drawing_plan` — Commit sheet size, scale, layer set and dimension style before any geometry.
- `drawing_critique` — Review the drawing for drafting mistakes: must come back empty before finalize.
- `drawing_refine` — Auto-repair what the critique found, then re-check, up to three rounds.
- `std_feature_draw` — Draw a standard feature - thread, undercut, ring or O-ring groove, centre hole - onto existing g
- `section_line` — Draw an ISO 128-40 cutting-plane line and return the plane the section view uses.
- `sheet_frame` — Draw an ISO 5457 sheet frame with the zone grid and centring marks.
- `drawing_topology_check` — Find dangling ends, near misses and unjoined crossings in a pipe or cable network.

### plot/arquivo (6)

- `titleblock_apply_iso_a3` — Stamp an ISO 7200 title block and sheet frame onto an A3 drawing.
- `drawing_template_save` — Save the current drawing as a template: .dwt on live AutoCAD, .dxf headlessly.
- `layer_state_save` — Save the layer table (on/frozen/locked/colour/linetype/lineweight/plot + current) under a name, 
- `view_named_save` — Save a named view: a centre and height (and width) to come back to.
- `titleblock_apply` — Stamp an ISO 7200 title block (and frame) on any sheet from A4 to A0.
- `revision_add` — Append a revision row, with optional revision clouds and triangular tags.

### camada/estilo (14)

- `linetype_load` — Load a linetype such as CENTER or HIDDEN, without the FILEDIA dialog trap.
- `analysis_select_by_layer` — Grab the handles of everything sitting on one layer.
- `analysis_layer_stats` — Report how many entities, and which types, sit on each layer.
- `template_apply_layers` — Create a standard layer set: architectural, mechanical, electrical or piping.
- `dimstyle_create` — Create a dimension style from the ISO-25 or ANSI preset, with per-variable overrides.
- `dimstyle_modify` — Change DIM* variables on an existing dimension style; reports only what moved.
- `dimstyle_set_current` — Make a dimension style current so new dimensions use it.
- `textstyle_create` — Create a text style from a bundled font (isocp, isocpeur, arial, romans) or any file.
- `textstyle_set_current` — Make a text style current so new text uses it.
- `mleaderstyle_list` — List multileader styles: arrow size, landing gap, text style and height.
- `mleaderstyle_create` — Create a multileader style from the ISO or ANSI preset, on both engines.
- `layer_state_restore` — Restore a saved layer state, all properties or a chosen subset.
- `layer_state_list` — List the layer states saved in this drawing.
- `layer_state_delete` — Delete one saved layer state from the drawing.

### edicao (11)

- `hatch_set_gradient` — Replace a hatch's fill with a two-colour gradient.
- `entity_delete` — Erase one entity by handle.
- `text_set_background` — Put an opaque background box behind an MTEXT.
- `entity_edit_geometry` — Change a circle's radius, a line's endpoints or an arc's angles in place.
- `entity_set_xdata` — Attach or replace extended data (XDATA) on an entity.
- `transaction_begin` — Open a rollback checkpoint before a risky edit.
- `transaction_commit` — Keep the changes and drop the checkpoint.
- `transaction_rollback` — Throw away every change made since transaction_begin.
- `construction_clear` — Wipe the construction scaffolding off the drawing before finalize.
- `entity_change_space` — Move entities between model space and a sheet through a viewport.
- `drawing_scale_check` — Is this drawing to scale against a reference? Tag distances, ratios, a verdict.

### consulta (18)

- `hatch_add_boundary` — Add a boundary path to a hatch, arcs and ellipses included.
- `selection_get` — Read what the user already picked in the AutoCAD viewport (COM backend).
- `entity_get_xdata` — Read an entity's extended data (XDATA) by application name.
- `boundary_trace` — Trace the closed boundary around a point, like BOUNDARY.
- `boundary_from_entities` — Join named entities into one closed boundary polyline.
- `analysis_list_properties` — Dump every DXF property of one entity, like LIST.
- `analysis_entity_stats` — Count the drawing's objects, broken down by type and by layer.
- `analysis_measure_distance` — Measure the gap between two points: distance, dx/dy and angle.
- `analysis_measure_area` — Measure a polygon's area and perimeter from its vertices.
- `analysis_measure_entity` — Area and perimeter of an existing entity, by handle.
- `analysis_bounding_box` — Get the overall extents of everything drawn.
- `analysis_select_by_type` — Grab the handles of every entity of one type: all the circles, all the lines.
- `template_list` — Show the available layer templates and the layers in each.
- `drawing_template_list` — List the five bundled drawing templates: standard, sheet, layers, styles, page setup.
- `view_named_list` — List the named views saved in this drawing.
- `std_part_list` — Search the standard-parts catalogue: ISO bolts, nuts, washers, cap screws, bearings.
- `drawing_understand` — Read a foreign drawing: units, extents, clusters, layers, tags, rooms, languages.
- `drawing_diff` — Compare two revisions of a drawing: what moved, changed, was added or removed.

### sistema (19)

- `cad_batch` — Run an ordered list of tool calls in one round trip, binding results between steps.
- `entity_batch_create` — Draw many entities in one call instead of one round trip each.
- `entity_batch_modify` — Move, rotate, scale, restyle or delete many entities in one call.
- `system_capabilities` — Ask the active backend which features it really supports.
- `system_get_variable` — Read one AutoCAD system variable, such as DIMSCALE or LTSCALE.
- `system_set_variable` — Set one AutoCAD system variable by name.
- `system_run_lisp` — Evaluate an AutoLISP expression inside AutoCAD (COM only).
- `system_about` — See what this server can do: version, tool groups and active profile.
- `document_list` — List the open documents: which is active, which have unsaved changes.
- `document_activate` — Switch which open document every later tool call targets.
- `ucs_list` — List the user coordinate systems, with the implicit world one.
- `ucs_set` — Define (or replace) a named UCS from an origin and two perpendicular axes, and make it current.
- `ucs_restore` — Make a saved UCS current, or `world` to reset to WCS.
- `system_launch` — Attach to the running AutoCAD or start it, optionally opening a file (live only).
- `system_preferences_get` — Read AutoCAD preferences from the whitelist (OPTIONS dialog values; live only).
- `system_preferences_set` — Change one whitelisted AutoCAD preference; reports old and new (live only).
- `system_prompt_message` — Print a message on AutoCAD's command line (live only).
- `system_variable_describe` — Explain a system variable: type, range, default, where it is saved, which engine honours it.
- `data_extract` — Write the bill of materials to a CSV file, or to XLSX when openpyxl is present.

### arquitetura (11)

- `bom_extract` — Read the bill of materials out of the drawing's block references.
- `bom_table` — Draw the parts list as a real TABLE above the title block.
- `arch_wall` — Add walls to the plan: clean L/T/X junctions, cut openings, material poché.
- `arch_opening` — Host a door or a window in a drawn wall by distance along it; the wall is cut.
- `arch_stair` — Draw a straight, L or U stair in plan and report its Blondel step rule.
- `arch_schedule` — Draw a door, window or room schedule from the plan records.
- `arch_catalogue_list` — Search the furniture and sanitary catalogue in English or Turkish.
- `arch_catalogue_insert` — Insert a furniture or sanitary item - bed, sofa, WC, basin, bathtub - as a block.
- `arch_plan_from_spec` — Draw a whole floor plan - walls, doors, windows, stairs, rooms, chains, schedules - in one trans
- `pipe_takeoff` — Pipe takeoff from a P&ID and its layout: rows by room, service and diameter.
- `cable_takeoff` — Cable takeoff: one row per load, Manhattan length to its panel, rounded up to the metre.

### mecanica (13)

- `gear_draw_helical_front_view` — Draw a helical gear front view: true involute teeth, circles, bore and keyway.
- `gear_draw_spur_front_view` — Draw a straight-tooth spur gear front view with true involute teeth.
- `gear_draw_section_aa` — Draw the hatched side cross-section A-A of a gear you already drew.
- `gd_frame` — Draw an ISO 1101 feature control frame: symbol, tolerance zone and datums.
- `datum_feature` — Mark a datum on a feature: filled triangle plus the boxed datum letter.
- `mech_part_draw` — Draw a machine part from a segment list or an outline plus typed features.
- `mech_view_add` — Add another view of a drawn part: side, top, section (full/half/offset) or detail.
- `mech_dimension_part` — Dimension a drawn part: ISO 129 dimensions, ISO 286 fits, a hole table.
- `mech_hole_pattern` — Draw a linear, grid or polar hole pattern with centre marks on any drawing.
- `mech_part_from_spec` — Draw a whole mechanical sheet - several parts and their views - in one transaction.
- `mech_part_inspect` — Read the part model back off the drawing: segments, features, views, omissions.
- `weld_symbol` — Draw an ISO 2553 weld symbol: reference line, identification line, size and pitch.
- `centre_marks` — Draw ISO 128-23 centre marks or centre lines on circles, read from the drawing.

### bloco (5)

- `entity_create_block_ref` — Drop an instance of an existing block definition into the drawing.
- `block_explode` — Break a block reference apart into its component entities.
- `block_create_from_entities` — Turn existing entities into a reusable block definition.
- `block_find_references` — Find every place a given block is inserted.
- `std_part_insert` — Insert an ISO standard part - hex bolt, nut, washer, cap screw or ball bearing - as a tagged blo

### cota/anotacao (4)

- `entity_create_wipeout` — Mask whatever is behind a closed polygon on the sheet.
- `dimension_diameter` — Call out a hole or shaft diameter, optionally to a fit such as H7.
- `dimension_auto` — Dimension a set of entities at once, as a chain, baseline or ordinate run.
- `balloon_add` — Add an ISO 6433 balloon linked to its item row.

### P&ID (9)

- `pid_symbol_list` — List the P&ID symbol catalogue: families, variants, ports, parameters.
- `pid_symbol_insert` — Place a P&ID symbol (valve, pump, vessel, instrument bubble, connector) as a tagged block with p
- `pid_line_draw` — Draw a P&ID line port-to-port: orthogonal route, ISA-5.1 class, line number, markers, arrow.
- `pid_graph` — Read the P&ID back as a graph: symbols, lines, junctions, dangling ends, confidence.
- `pid_instrument_index` — Instrument index derived from the P&ID graph (tag, function, loop, connections); optional CSV.
- `pid_line_list` — Line list derived from the P&ID graph (number, class, size, spec, from/to); optional CSV.
- `pid_equipment_list` — Equipment list derived from the P&ID graph (tag, kind, ports, connections); optional CSV.
- `pid_from_spec` — Draw a whole P&ID from one declarative spec in one transaction; returns graph + critique.
- `pid_tag_parse` — Parse an ISA-5.1 instrument tag or an equipment tag; explains every letter.

### 3D/solido (8)

- `analysis_find_in_region` — List everything that falls inside a rectangular window.
- `point_intersection` — Find where two lines or circles cross, exactly.
- `solid_box` — Create a 3D solid box (live AutoCAD, opt-in via ENABLE_3D).
- `solid_cylinder` — Create a 3D solid cylinder or shaft (live AutoCAD, opt-in via ENABLE_3D).
- `solid_extrude` — Pull a closed profile up into a 3D solid (live AutoCAD, opt-in via ENABLE_3D).
- `solid_revolve` — Spin a closed profile around an axis into a 3D solid (opt-in via ENABLE_3D).
- `solid_boolean` — Union, subtract or intersect two 3D solids; the tool solid is consumed.
- `surface_texture` — Draw an ISO 21920-1 surface-texture symbol: Ra/Rz, process, lay, allowance.

### selecao (5)

- `text_find_replace` — Find and replace text across the drawing.
- `selection_polygon` — Select entities inside or crossing an arbitrary polygon.
- `selection_filter` — Select entities by layer, type, colour, linetype or minimum area.
- `entity_select_smart` — Pick every entity matching a description: type, layer, colour, length, location.
- `user_select` — Ask the operator to select one entity or a set on screen (live only).

### visualizacao (2)

- `view_zoom_and_screenshot` — Fit the drawing on screen, then capture it: the quickest visual check.
- `view_named_restore` — Restore a named view.

### outros (1)

- `validation_check` — Sanity-check the drawing for empty layers, zero-length lines and duplicates.
