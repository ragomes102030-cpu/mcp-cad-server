# Multifamily floor engine — four-unit MVP contract

Status: design specification, NOT implemented or validated.

## Scope
Generate one typical floor with four independently addressable dwelling units (A01–A04), a shared circulation core, stair enclosure and reserved elevator shaft. No structural or code-compliance certification.

## Input contract (proposed)
- floor_outline: closed polygon, coordinates in metres
- units: exactly 4, each with stable id and program: 2 bedrooms, 1 bathroom, combined living/kitchen, laundry
- common_core: stair footprint, optional lift footprint, corridor and entrance
- wall_thicknesses: exterior, interior and party-wall values
- door/window rules and minimum preliminary clearances as explicit parameters
- drawing: scale, A3 sheet and output formats DXF/PDF

## Geometric invariants
1. Every room polygon is closed, non-self-intersecting, positive area and inside the floor outline.
2. Unit interiors do not overlap one another or common circulation.
3. Shared walls are represented once with references to adjacent spaces; no duplicate coincident wall geometry.
4. All four apartment entry doors connect to the common circulation graph.
5. Each habitable room has an accessible route to its apartment entry; no route crosses a wall or a window.
6. Door leaf and swing geometry use the existing validated door engine, with collision checks.
7. The stair, elevator reservation and corridor cannot overlap private rooms.
8. Net private areas, common areas and gross floor area are computed and reported with explicit conventions.
9. Every entity carries floor/unit/room IDs to support auditing and quantity takeoff.
10. A failed invariant blocks a 'validated' drawing, but retains diagnostic outputs.

## Delivery phases
1. Add schema + fixture for four units and common core.
2. Add deterministic partition and circulation graph generation.
3. Reuse door/window geometry, collision checks and geometric auditing.
4. Add A3 DXF/PDF export and per-unit area schedules.
5. Run unit tests, regression corpus, benchmark, CI, deploy health and MCP handshake.

## Acceptance fixtures
- Regular rectangular floor with four units and central corridor.
- Narrow corridor: must fail clearance validation.
- Apartment entrance blocked by wall: must fail reachability.
- Duplicate shared wall: must fail deduplication.
- Door swing intersects furniture: must report collision.
- Nonrectangular outline: deterministic result or explicit unsupported diagnostic.

## Engineering guardrails
Do not claim compliance with Brazilian building, accessibility or fire standards without a project-specific licensed review. Preserve the existing residential generator and its door correction. No production deployment before CI, benchmark, corpus and live MCP verification.
