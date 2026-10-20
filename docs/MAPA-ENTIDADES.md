# Mapa das entidades — campos DXF

Gerado de `ezdxf 1.4.4` (`DXFATTRIBS`, a tabela do formato DXF).
Vale para `entmake`/`entget` e para o arquivo DXF — **não** para as propriedades
COM, que têm outro nome (o COM está em `MAPA-COM.md`).

## Antes de tudo: ângulo

Códigos **50 e 51** são ângulo. No arquivo DXF ficam em **graus**; no
`entmake`/`entget` são **radianos**. Passar grau onde o `entmake` espera
radiano não dá erro — dá geometria errada (90° virou 116,62°).

## Campos que quase toda entidade tem

| código | nome | o que é |
|---|---|---|
| 0 | — | tipo da entidade |
| 5 | handle | identificador único no desenho |
| 8 | layer | camada |
| 6 | linetype | tipo de linha (`BYLAYER` se omitido) |
| 62 | color | cor ACI (256 = BYLAYER) |
| 370 | lineweight | espessura em centésimos de mm |
| 48 | ltscale | escala do tipo de linha |
| 67 | paperspace | 1 = espaço do papel |
| 410 | layout | nome do layout |
| 330 | owner | dono (bloco/espaço) |

## Outros campos com "angle" no nome

São ângulo, mas a regra de radiano foi confirmada só em 50/51. Se usar
algum destes, teste e registre no `historico/` — não assuma.

| entidade | código | campo |
|---|---|---|
| `ARC_DIMENSION` | 40 | `start_angle` |
| `ARC_DIMENSION` | 41 | `end_angle` |
| `ARC_DIMENSION` | 52 | `oblique_angle` |
| `DIMENSION` | 52 | `oblique_angle` |
| `EXTRUDEDSURFACE` | 42 | `draft_angle` |
| `EXTRUDEDSURFACE` | 45 | `twist_angle` |
| `EXTRUDEDSURFACE` | 49 | `align_angle` |
| `HATCH` | 52 | `pattern_angle` |
| `LARGE_RADIAL_DIMENSION` | 52 | `oblique_angle` |
| `LOFTEDSURFACE` | 41 | `start_draft_angle` |
| `LOFTEDSURFACE` | 42 | `end_draft_angle` |
| `MLEADER` | 174 | `text_angle_type` |
| `MLEADERSTYLE` | 40 | `first_segment_angle_constraint` |
| `MLEADERSTYLE` | 41 | `second_segment_angle_constraint` |
| `MLEADERSTYLE` | 175 | `text_angle_type` |
| `MLINESTYLE` | 52 | `end_angle` |
| `MPOLYGON` | 52 | `pattern_angle` |
| `MULTILEADER` | 174 | `text_angle_type` |
| `REVOLVEDSURFACE` | 40 | `revolve_angle` |
| `REVOLVEDSURFACE` | 41 | `start_angle` |
| `REVOLVEDSURFACE` | 43 | `draft_angle` |
| `REVOLVEDSURFACE` | 46 | `twist_angle` |
| `SWEPTSURFACE` | 42 | `draft_angle` |
| `SWEPTSURFACE` | 45 | `twist_angle` |
| `SWEPTSURFACE` | 49 | `align_angle` |
| `VISUALSTYLE` | 42 | `edge_crease_angle` |

**83** entidades mapeadas. Tabela completa em
`catalogo-entidades.json`.

## Entidades em destaque

### LINE

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `start` | ponto | (0.0, 0.0, 0.0) |
| 11 | `end` | ponto | (0.0, 0.0, 0.0) |
| 39 | `thickness` | real | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### LWPOLYLINE

| código | campo | tipo | padrão |
|---|---|---|---|
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 43 | `const_width` | real | 0 |
| 70 | `flags` | inteiro | 0 |
| 90 | `count` | inteiro32 | — |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### POLYLINE

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `elevation` | ponto | (0.0, 0.0, 0.0) |
| 39 | `thickness` | real | 0 |
| 40 | `default_start_width` | real | 0 |
| 41 | `default_end_width` | real | 0 |
| 70 | `flags` | inteiro | 0 |
| 71 | `m_count` | inteiro | 0 |
| 72 | `n_count` | inteiro | 0 |
| 73 | `m_smooth_density` | inteiro | 0 |
| 74 | `n_smooth_density` | inteiro | 0 |
| 75 | `smooth_type` | inteiro | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### ARC

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `center` | ponto | (0.0, 0.0, 0.0) |
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 40 | `radius` | real | 1 |
| 50 | `start_angle` ⚠ | angulo | 0 |
| 51 | `end_angle` ⚠ | angulo | 360 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### CIRCLE

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `center` | ponto | (0.0, 0.0, 0.0) |
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 40 | `radius` | real | 1 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### ELLIPSE

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `center` | ponto | (0.0, 0.0, 0.0) |
| 11 | `major_axis` | ponto | (1.0, 0.0, 0.0) |
| 40 | `ratio` | real | 1.0 |
| 41 | `start_param` | real | 0 |
| 42 | `end_param` | real | 6.283185307179586 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### SPLINE

| código | campo | tipo | padrão |
|---|---|---|---|
| 12 | `start_tangent` | ponto | — |
| 13 | `end_tangent` | ponto | — |
| 42 | `knot_tolerance` | real | 1e-10 |
| 43 | `control_point_tolerance` | real | 1e-10 |
| 44 | `fit_tolerance` | real | 1e-10 |
| 70 | `flags` | inteiro | 0 |
| 71 | `degree` | inteiro | 3 |
| 72 | `n_knots` | inteiro | — |
| 73 | `n_control_points` | inteiro | — |
| 74 | `n_fit_points` | inteiro | — |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### POINT

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `location` | ponto | (0.0, 0.0, 0.0) |
| 39 | `thickness` | real | 0 |
| 50 | `angle` ⚠ | angulo | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### SOLID

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `vtx0` | ponto | (0.0, 0.0, 0.0) |
| 11 | `vtx1` | ponto | (0.0, 0.0, 0.0) |
| 12 | `vtx2` | ponto | (0.0, 0.0, 0.0) |
| 13 | `vtx3` | ponto | (0.0, 0.0, 0.0) |
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### HATCH

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `pattern_name` | texto | SOLID |
| 10 | `elevation` | ponto | (0.0, 0.0, 0.0) |
| 41 | `pattern_scale` | real | 1 |
| 47 | `pixel_size` | real | — |
| 52 | `pattern_angle` | real | 0 |
| 70 | `solid_fill` | inteiro | 1 |
| 71 | `associative` | inteiro | 0 |
| 75 | `hatch_style` | inteiro | 0 |
| 76 | `pattern_type` | inteiro | 1 |
| 77 | `pattern_double` | inteiro | 0 |
| 98 | `n_seed_points` | inteiro32 | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### TEXT

| código | campo | tipo | padrão |
|---|---|---|---|
| 1 | `text` | texto |  |
| 7 | `style` | texto | Standard |
| 10 | `insert` | ponto | (0.0, 0.0, 0.0) |
| 11 | `align_point` | ponto | — |
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 40 | `height` | real | 2.5 |
| 41 | `width` | real | 1 |
| 50 | `rotation` ⚠ | angulo | 0 |
| 51 | `oblique` ⚠ | angulo | 0 |
| 71 | `text_generation_flag` | inteiro | 0 |
| 72 | `halign` | inteiro | 0 |
| 73 | `valign` | inteiro | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### MTEXT

| código | campo | tipo | padrão |
|---|---|---|---|
| -666 | `text` | outro | — |
| 7 | `style` | texto | Standard |
| 10 | `insert` | ponto | (0.0, 0.0, 0.0) |
| 11 | `text_direction` | ponto | (1.0, 0.0, 0.0) |
| 40 | `char_height` | real | 2.5 |
| 41 | `width` | real | — |
| 42 | `rect_width` | real | — |
| 43 | `rect_height` | real | — |
| 44 | `line_spacing_factor` | real | 1 |
| 45 | `box_fill_scale` | real | — |
| 46 | `defined_height` | real | — |
| 50 | `rotation` ⚠ | angulo | 0 |
| 63 | `bg_fill_color` | inteiro | — |
| 71 | `attachment_point` | inteiro | 1 |
| 72 | `flow_direction` | inteiro | 1 |
| 73 | `line_spacing_style` | inteiro | 1 |
| 90 | `bg_fill` | inteiro32 | — |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |
| 421 | `bg_fill_true_color` | outro | — |
| 431 | `bg_fill_color_name` | outro | — |
| 441 | `bg_fill_transparency` | outro | — |

### DIMENSION

| código | campo | tipo | padrão |
|---|---|---|---|
| 1 | `text` | texto |  |
| 2 | `geometry` | texto | — |
| 3 | `dimstyle` | texto | Standard |
| 10 | `defpoint` | ponto | (0.0, 0.0, 0.0) |
| 11 | `text_midpoint` | ponto | — |
| 12 | `insert` | ponto | (0.0, 0.0, 0.0) |
| 13 | `defpoint2` | ponto | (0.0, 0.0, 0.0) |
| 14 | `defpoint3` | ponto | (0.0, 0.0, 0.0) |
| 15 | `defpoint4` | ponto | (0.0, 0.0, 0.0) |
| 16 | `defpoint5` | ponto | (0.0, 0.0, 0.0) |
| 40 | `leader_length` | real | — |
| 41 | `line_spacing_factor` | real | — |
| 42 | `actual_measurement` | real | — |
| 50 | `angle` ⚠ | angulo | 0 |
| 51 | `horizontal_direction` ⚠ | angulo | 0 |
| 52 | `oblique_angle` | real | 0 |
| 53 | `text_rotation` | real | 0 |
| 70 | `dimtype` | inteiro | 0 |
| 71 | `attachment_point` | inteiro | 5 |
| 72 | `line_spacing_style` | inteiro | 1 |
| 73 | `unknown1` | inteiro | — |
| 74 | `flip_arrow_1` | inteiro | — |
| 75 | `flip_arrow_2` | inteiro | — |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 280 | `version` | outro | 0 |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### LEADER

| código | campo | tipo | padrão |
|---|---|---|---|
| 3 | `dimstyle` | texto | Standard |
| 40 | `text_height` | real | 1 |
| 41 | `text_width` | real | 1 |
| 71 | `has_arrowhead` | inteiro | 1 |
| 72 | `path_type` | inteiro | 0 |
| 73 | `annotation_type` | inteiro | 3 |
| 74 | `hookline_direction` | inteiro | 1 |
| 75 | `has_hookline` | inteiro | 1 |
| 77 | `block_color` | inteiro | 7 |
| 210 | `normal_vector` | vetor | (0.0, 0.0, 1.0) |
| 211 | `horizontal_direction` | vetor | (1.0, 0.0, 0.0) |
| 212 | `leader_offset_block_ref` | vetor | (0.0, 0.0, 0.0) |
| 213 | `leader_offset_annotation_placement` | vetor | (0.0, 0.0, 0.0) |
| 284 | `shadow_mode` | outro | — |
| 340 | `annotation_handle` | texto/handle | 0 |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### MLEADER

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `block_scale_vector` | ponto | (1.0, 1.0, 1.0) |
| 41 | `dogleg_length` | real | 8 |
| 42 | `arrow_head_size` | real | 4 |
| 43 | `block_rotation` | real | 0 |
| 45 | `scale` | real | 1 |
| 90 | `property_override_flags` | inteiro32 | — |
| 91 | `leader_line_color` | inteiro32 | -1056964608 |
| 92 | `text_color` | inteiro32 | -1056964608 |
| 93 | `block_color` | inteiro32 | -1056964608 |
| 95 | `text_right_attachment_type` | inteiro32 | 1 |
| 170 | `leader_type` | inteiro16 | 1 |
| 171 | `leader_lineweight` | inteiro16 | -2 |
| 172 | `content_type` | inteiro16 | 2 |
| 173 | `text_left_attachment_type` | inteiro16 | 1 |
| 174 | `text_angle_type` | inteiro16 | 1 |
| 175 | `text_alignment_type` | inteiro16 | 2 |
| 176 | `block_connection_type` | inteiro16 | 0 |
| 178 | `text_IPE_align` | inteiro16 | 0 |
| 179 | `text_attachment_point` | inteiro16 | 1 |
| 270 | `version` | outro | 2 |
| 271 | `text_attachment_direction` | outro | 0 |
| 272 | `text_bottom_attachment_type` | outro | 9 |
| 273 | `text_top_attachment_type` | outro | 9 |
| 284 | `shadow_mode` | outro | — |
| 290 | `has_landing` | outro | 1 |
| 291 | `has_dogleg` | outro | 1 |
| 292 | `has_text_frame` | outro | 0 |
| 293 | `is_annotative` | outro | 0 |
| 294 | `is_text_direction_negative` | outro | 0 |
| 295 | `leader_extend_to_text` | outro | 0 |
| 340 | `style_handle` | texto/handle | — |
| 341 | `leader_linetype_handle` | texto/handle | — |
| 342 | `arrow_head_handle` | texto/handle | — |
| 343 | `text_style_handle` | texto/handle | — |
| 344 | `block_record_handle` | texto/handle | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### INSERT

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `name` | texto | — |
| 10 | `insert` | ponto | — |
| 38 | `elevation` | real | 0 |
| 41 | `xscale` | real | 1 |
| 42 | `yscale` | real | 1 |
| 43 | `zscale` | real | 1 |
| 44 | `column_spacing` | real | 0 |
| 45 | `row_spacing` | real | 0 |
| 50 | `rotation` ⚠ | angulo | 0 |
| 66 | `attribs_follow` | inteiro | 0 |
| 70 | `column_count` | inteiro | 1 |
| 71 | `row_count` | inteiro | 1 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### ATTRIB

| código | campo | tipo | padrão |
|---|---|---|---|
| 1 | `text` | texto |  |
| 2 | `tag` | texto |  |
| 7 | `style` | texto | Standard |
| 10 | `insert` | ponto | (0.0, 0.0, 0.0) |
| 11 | `align_point` | ponto | — |
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 40 | `height` | real | 2.5 |
| 41 | `width` | real | 1 |
| 50 | `rotation` ⚠ | angulo | 0 |
| 51 | `oblique` ⚠ | angulo | 0 |
| 70 | `flags` | inteiro | 0 |
| 71 | `text_generation_flag` | inteiro | 0 |
| 71 | `attribute_type` | inteiro | 1 |
| 72 | `halign` | inteiro | 0 |
| 73 | `field_length` | inteiro | 0 |
| 74 | `valign` | inteiro | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 280 | `lock_position` | outro | 0 |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### ATTDEF

| código | campo | tipo | padrão |
|---|---|---|---|
| 1 | `text` | texto |  |
| 2 | `tag` | texto |  |
| 3 | `prompt` | texto |  |
| 7 | `style` | texto | Standard |
| 10 | `insert` | ponto | (0.0, 0.0, 0.0) |
| 11 | `align_point` | ponto | — |
| 38 | `elevation` | real | 0 |
| 39 | `thickness` | real | 0 |
| 40 | `height` | real | 2.5 |
| 41 | `width` | real | 1 |
| 50 | `rotation` ⚠ | angulo | 0 |
| 51 | `oblique` ⚠ | angulo | 0 |
| 70 | `flags` | inteiro | 0 |
| 71 | `text_generation_flag` | inteiro | 0 |
| 71 | `attribute_type` | inteiro | 1 |
| 72 | `halign` | inteiro | 0 |
| 73 | `field_length` | inteiro | 0 |
| 74 | `valign` | inteiro | 0 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 280 | `lock_position` | outro | 0 |
| 284 | `shadow_mode` | outro | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### TABLE

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `name` | texto | — |
| 70 | `count` | inteiro | 0 |

### VIEWPORT

| código | campo | tipo | padrão |
|---|---|---|---|
| 1 | `plot_style_name` | texto |  |
| 10 | `center` | ponto | (0.0, 0.0, 0.0) |
| 12 | `view_center_point` | ponto | (0.0, 0.0, 0.0) |
| 13 | `snap_base_point` | ponto | (0.0, 0.0, 0.0) |
| 14 | `snap_spacing` | ponto | (10.0, 10.0) |
| 15 | `grid_spacing` | ponto | (10.0, 10.0) |
| 16 | `view_direction_vector` | ponto | (0.0, 0.0, 1.0) |
| 17 | `view_target_point` | ponto | (0.0, 0.0, 0.0) |
| 40 | `width` | real | 1 |
| 41 | `height` | real | 1 |
| 42 | `perspective_lens_length` | real | 50 |
| 43 | `front_clip_plane_z_value` | real | 0 |
| 44 | `back_clip_plane_z_value` | real | 0 |
| 45 | `view_height` | real | 1 |
| 50 | `snap_angle` ⚠ | angulo | 0 |
| 51 | `view_twist_angle` ⚠ | angulo | 0 |
| 61 | `grid_frequency` | inteiro | — |
| 63 | `ambient_light_color_1` | inteiro | — |
| 68 | `status` | inteiro | 0 |
| 69 | `id` | inteiro | 2 |
| 71 | `ucs_per_viewport` | inteiro | 0 |
| 72 | `circle_zoom` | inteiro | 100 |
| 74 | `ucs_icon` | inteiro | 0 |
| 79 | `ucs_ortho_type` | inteiro | 0 |
| 90 | `flags` | inteiro32 | 0 |
| 91 | `ref_vp_object_4` | inteiro32 | — |
| 110 | `ucs_origin` | outro | (0.0, 0.0, 0.0) |
| 111 | `ucs_x_axis` | outro | (1.0, 0.0, 0.0) |
| 112 | `ucs_y_axis` | outro | (0.0, 1.0, 0.0) |
| 141 | `view_brightness` | outro | — |
| 142 | `view_contrast` | outro | — |
| 146 | `elevation` | outro | 0 |
| 170 | `shade_plot_mode` | inteiro16 | — |
| 281 | `render_mode` | outro | 0 |
| 282 | `default_lighting_type` | outro | 0 |
| 284 | `shadow_mode` | outro | — |
| 292 | `default_lighting_flag` | outro | 1 |
| 332 | `background_handle` | texto/handle | — |
| 333 | `shade_plot_handle` | texto/handle | — |
| 335 | `ref_vp_object_1` | texto/handle | — |
| 340 | `clipping_boundary_handle` | texto/handle | 0 |
| 343 | `ref_vp_object_2` | texto/handle | — |
| 344 | `ref_vp_object_3` | texto/handle | — |
| 345 | `ucs_handle` | texto/handle | — |
| 346 | `base_ucs_handle` | texto/handle | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 348 | `visual_style_handle` | texto/handle | — |
| 361 | `sun_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |
| 421 | `ambient_light_color_2` | outro | — |
| 431 | `ambient_light_color_3` | outro | — |

### IMAGE

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `insert` | ponto | — |
| 11 | `u_pixel` | ponto | — |
| 12 | `v_pixel` | ponto | — |
| 13 | `image_size` | ponto | — |
| 70 | `flags` | inteiro | 3 |
| 71 | `clipping_boundary_type` | inteiro | 1 |
| 90 | `class_version` | inteiro32 | 0 |
| 91 | `count_boundary_points` | inteiro32 | — |
| 280 | `clipping` | outro | 0 |
| 281 | `brightness` | outro | 50 |
| 282 | `contrast` | outro | 50 |
| 283 | `fade` | outro | 0 |
| 284 | `shadow_mode` | outro | — |
| 290 | `clip_mode` | outro | 0 |
| 340 | `image_def_handle` | texto/handle | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### WIPEOUT

| código | campo | tipo | padrão |
|---|---|---|---|
| 10 | `insert` | ponto | — |
| 11 | `u_pixel` | ponto | — |
| 12 | `v_pixel` | ponto | — |
| 13 | `image_size` | ponto | — |
| 70 | `flags` | inteiro | 3 |
| 71 | `clipping_boundary_type` | inteiro | 1 |
| 90 | `class_version` | inteiro32 | 0 |
| 91 | `count_boundary_points` | inteiro32 | — |
| 280 | `clipping` | outro | 0 |
| 281 | `brightness` | outro | 50 |
| 282 | `contrast` | outro | 50 |
| 283 | `fade` | outro | 0 |
| 284 | `shadow_mode` | outro | — |
| 290 | `clip_mode` | outro | 0 |
| 340 | `image_def_handle` | texto/handle | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

### LAYER

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `name` | texto | — |
| 70 | `flags` | inteiro | 0 |
| 290 | `plot` | outro | 1 |
| 348 | `unknown1` | texto/handle | — |
| 390 | `plotstyle_handle` | texto/handle | — |

### LTYPE

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `name` | texto | — |
| 3 | `description` | texto |  |
| 70 | `flags` | inteiro | 0 |

### STYLE

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `name` | texto | Standard |
| 3 | `font` | texto | txt |
| 4 | `bigfont` | texto |  |
| 40 | `height` | real | 0 |
| 41 | `width` | real | 1 |
| 42 | `last_height` | real | 2.5 |
| 50 | `oblique` ⚠ | angulo | 0 |
| 70 | `flags` | inteiro | 0 |
| 71 | `generation_flags` | inteiro | 0 |

### DIMSTYLE

| código | campo | tipo | padrão |
|---|---|---|---|
| -666 | `dimtxsty` | outro | — |
| -666 | `dimldrblk` | outro | — |
| -666 | `dimltype` | outro | — |
| -666 | `dimltex2` | outro | — |
| -666 | `dimltex1` | outro | — |
| 2 | `name` | texto | Standard |
| 3 | `dimpost` | texto |  |
| 4 | `dimapost` | texto |  |
| 7 | `dimblk2` | texto |  |
| 40 | `dimscale` | real | 1 |
| 41 | `dimasz` | real | 2.5 |
| 42 | `dimexo` | real | 0.625 |
| 43 | `dimdli` | real | 3.75 |
| 44 | `dimexe` | real | 1.25 |
| 45 | `dimrnd` | real | 0 |
| 46 | `dimdle` | real | 0 |
| 47 | `dimtp` | real | 0 |
| 49 | `dimfxl` | real | 2.5 |
| 50 | `dimjogang` ⚠ | angulo | 90 |
| 69 | `dimtfill` | inteiro | 0 |
| 70 | `flags` | inteiro | 0 |
| 70 | `dimtfillclr` | inteiro | 0 |
| 71 | `dimtol` | inteiro | 0 |
| 72 | `dimlim` | inteiro | 0 |
| 73 | `dimtih` | inteiro | 0 |
| 74 | `dimtoh` | inteiro | 0 |
| 75 | `dimse1` | inteiro | 0 |
| 76 | `dimse2` | inteiro | 0 |
| 77 | `dimtad` | inteiro | 1 |
| 78 | `dimzin` | inteiro | 8 |
| 79 | `dimazin` | inteiro | 3 |
| 90 | `dimarcsym` | inteiro32 | — |
| 140 | `dimtxt` | outro | 2.5 |
| 141 | `dimcen` | outro | 2.5 |
| 142 | `dimtsz` | outro | 0 |
| 143 | `dimaltf` | outro | 0.03937007874 |
| 144 | `dimlfac` | outro | 1 |
| 145 | `dimtvp` | outro | 0 |
| 146 | `dimtfac` | outro | 1 |
| 147 | `dimgap` | outro | 0.625 |
| 148 | `dimaltrnd` | outro | 0 |
| 170 | `dimalt` | inteiro16 | 0 |
| 171 | `dimaltd` | inteiro16 | 3 |
| 172 | `dimtofl` | inteiro16 | 1 |
| 173 | `dimsah` | inteiro16 | 0 |
| 174 | `dimtix` | inteiro16 | 0 |
| 175 | `dimsoxd` | inteiro16 | 0 |
| 176 | `dimclrd` | inteiro16 | 0 |
| 177 | `dimclre` | inteiro16 | 0 |
| 178 | `dimclrt` | inteiro16 | 0 |
| 179 | `dimadec` | inteiro16 | 2 |
| 270 | `dimunit` | outro | — |
| 271 | `dimdec` | outro | 2 |
| 272 | `dimtdec` | outro | 2 |
| 273 | `dimaltu` | outro | 2 |
| 274 | `dimalttd` | outro | 3 |
| 275 | `dimaunit` | outro | 0 |
| 276 | `dimfrac` | outro | 0 |
| 277 | `dimlunit` | outro | 2 |
| 278 | `dimdsep` | outro | 44 |
| 279 | `dimtmove` | outro | 0 |
| 280 | `dimjust` | outro | 0 |
| 281 | `dimsd1` | outro | 0 |
| 282 | `dimsd2` | outro | 0 |
| 283 | `dimtolj` | outro | 0 |
| 284 | `dimtzin` | outro | 8 |
| 285 | `dimaltz` | outro | 0 |
| 286 | `dimalttz` | outro | 0 |
| 287 | `dimfit` | outro | — |
| 288 | `dimupt` | outro | 0 |
| 289 | `dimatfit` | outro | 3 |
| 290 | `dimfxlon` | outro | 0 |
| 340 | `dimtxsty_handle` | texto/handle | — |
| 341 | `dimldrblk_handle` | texto/handle | — |
| 342 | `dimblk_handle` | texto/handle | — |
| 343 | `dimblk1_handle` | texto/handle | — |
| 344 | `dimblk2_handle` | texto/handle | — |
| 345 | `dimltype_handle` | texto/handle | — |
| 346 | `dimltex1_handle` | texto/handle | — |
| 371 | `dimlwd` | outro | -2 |
| 372 | `dimlwe` | outro | -2 |

### BLOCK_RECORD

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `name` | texto | — |
| 70 | `units` | inteiro | 0 |
| 280 | `explode` | outro | 1 |
| 281 | `scale` | outro | 0 |
| 340 | `layout` | texto/handle | 0 |

### MLINE

| código | campo | tipo | padrão |
|---|---|---|---|
| 2 | `style_name` | texto | Standard |
| 10 | `start_location` | ponto | — |
| 40 | `scale_factor` | real | 1 |
| 70 | `justification` | inteiro | 0 |
| 71 | `flags` | inteiro | 1 |
| 72 | `count` | inteiro | — |
| 73 | `style_element_count` | inteiro | 2 |
| 210 | `extrusion` | vetor | (0.0, 0.0, 1.0) |
| 284 | `shadow_mode` | outro | — |
| 340 | `style_handle` | texto/handle | — |
| 348 | `visualstyle_handle` | texto/handle | — |
| 380 | `plotstyle_enum` | outro | 1 |
| 390 | `plotstyle_handle` | texto/handle | — |

## Todas as entidades

| DXF | classe ezdxf | campos |
|---|---|---|
| `3DFACE` | `Face3d` | 22 |
| `3DSOLID` | `Solid3d` | 21 |
| `ACAD_PROXY_ENTITY` | `ACADProxyEntity` | 17 |
| `ACAD_TABLE` | `AcadTableBlockContent` | 30 |
| `ACDBDICTIONARYWDFLT` | `DictionaryWithDefault` | 5 |
| `ACDBPLACEHOLDER` | `Placeholder` | 2 |
| `APPID` | `AppID` | 4 |
| `ARC` | `Arc` | 24 |
| `ARC_DIMENSION` | `ArcDimension` | 45 |
| `ATTDEF` | `AttDef` | 37 |
| `ATTRIB` | `Attrib` | 36 |
| `BLOCK` | `Block` | 9 |
| `BLOCK_RECORD` | `BlockRecord` | 7 |
| `BODY` | `Body` | 20 |
| `CIRCLE` | `Circle` | 22 |
| `CLASS` | `DXFClass` | 7 |
| `DGNUNDERLAY` | `DgnUnderlay` | 27 |
| `DICTIONARY` | `Dictionary` | 4 |
| `DICTIONARYVAR` | `DictionaryVar` | 4 |
| `DIMENSION` | `Dimension` | 42 |
| `DIMSTYLE` | `DimStyle` | 87 |
| `DWFUNDERLAY` | `DwfUnderlay` | 27 |
| `DXFENTITY` | `DXFTagStorage` | 2 |
| `DXFGFX` | `Underlay` | 27 |
| `ELLIPSE` | `Ellipse` | 23 |
| `ENDBLK` | `EndBlk` | 4 |
| `EXTRUDEDSURFACE` | `ExtrudedSurface` | 39 |
| `GEODATA` | `GeoData` | 22 |
| `HATCH` | `Hatch` | 29 |
| `HELIX` | `Helix` | 38 |
| `IDBUFFER` | `IDBuffer` | 2 |
| `IMAGE` | `Image` | 32 |
| `IMAGEDEF` | `ImageDef` | 8 |
| `INSERT` | `Insert` | 30 |
| `LARGE_RADIAL_DIMENSION` | `RadialDimensionLarge` | 40 |
| `LAYER` | `Layer` | 12 |
| `LAYOUT` | `DXFLayout` | 50 |
| `LEADER` | `Leader` | 31 |
| `LIGHT` | `Light` | 35 |
| `LINE` | `Line` | 21 |
| `LOFTEDSURFACE` | `LoftedSurface` | 35 |
| `LTYPE` | `Linetype` | 5 |
| `LWPOLYLINE` | `LWPolyline` | 23 |
| `MATERIAL` | `Material` | 85 |
| `MESH` | `Mesh` | 20 |
| `MLEADER` | `MLeader` | 51 |
| `MLEADERSTYLE` | `MLeaderStyle` | 48 |
| `MLINE` | `MLine` | 26 |
| `MLINESTYLE` | `MLineStyle` | 8 |
| `MPOLYGON` | `MPolygon` | 33 |
| `MTEXT` | `MText` | 38 |
| `MULTILEADER` | `MultiLeader` | 51 |
| `OLE2FRAME` | `OLE2Frame` | 17 |
| `PDFUNDERLAY` | `PdfUnderlay` | 27 |
| `POINT` | `Point` | 21 |
| `POLYLINE` | `Polymesh` | 28 |
| `RAY` | `Ray` | 19 |
| `REGION` | `Region` | 20 |
| `REVOLVEDSURFACE` | `RevolvedSurface` | 33 |
| `SEQEND` | `SeqEnd` | 17 |
| `SHAPE` | `Shape` | 26 |
| `SOLID` | `Solid` | 24 |
| `SORTENTSTABLE` | `SortEntsTable` | 3 |
| `SPATIAL_FILTER` | `SpatialFilter` | 9 |
| `SPLINE` | `Spline` | 28 |
| `STYLE` | `Textstyle` | 11 |
| `SUN` | `Sun` | 14 |
| `SURFACE` | `Surface` | 22 |
| `SWEPTSURFACE` | `SweptSurface` | 39 |
| `TABLE` | `TableHead` | 4 |
| `TEXT` | `Text` | 31 |
| `TOLERANCE` | `Tolerance` | 22 |
| `TRACE` | `Trace` | 24 |
| `UCS` | `UCSTableEntry` | 7 |
| `UNDERLAYDEFINITION` | `UnderlayDefinition` | 4 |
| `VBA_PROJECT` | `VBAProject` | 2 |
| `VIEW` | `View` | 28 |
| `VIEWPORT` | `Viewport` | 65 |
| `VISUALSTYLE` | `VisualStyle` | 37 |
| `VPORT` | `VPort` | 51 |
| `WIPEOUT` | `Wipeout` | 32 |
| `XLINE` | `XLine` | 19 |
| `XRECORD` | `XRecord` | 3 |

