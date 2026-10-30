# PrintReady AI — Benchmark Prompt Pack v0.1

Locked pack for phase-1 pipeline dry-runs. Core 10 never rotate; extended 10 rotate quarterly.  
Scale target after generation: longest bbox edge = **50 mm** (documented in PLAN.md).

---

## A. Text-to-3D prompts (20)

### Core 10 (permanent)

| ID | Prompt | Why it stresses printability |
| --- | --- | --- |
| T01 | `A simple coffee mug with a handle, solid ceramic style, no texture, watertight printable model` | Handle topology + open rim risk |
| T02 | `A low-poly fox figurine standing on four legs, solid, 3D printable, no base` | Thin legs / overhangs |
| T03 | `A hexagonal mechanical nut, M8 size proportions, clean threads, printable` | Threads = non-manifold / self-intersect risk |
| T04 | `A phone stand with a slot for a phone, minimal modern design, solid plastic` | Slot walls / thin sections |
| T05 | `A desktop business card holder with three vertical slots, solid, printable` | Repeated thin walls |
| T06 | `A small planter pot with drainage hole in the bottom center, cylindrical` | Intentional hole vs accidental holes |
| T07 | `A interlocking chain of three torus links, solid metal look, printable as one piece` | Self-intersections / inseparable topology |
| T08 | `A calibration XYZ 20mm cube with embossed X Y Z letters on faces` | Emboss depth / manifold lettering |
| T09 | `A wall hook with a flat mounting plate and two screw holes, sturdy` | Holes + flat plate warping cues |
| T10 | `A articulated flexible dragon with segmented body, print-in-place joints` | Joint clearances / fused vs loose |

### Extended 10 (rotate quarterly)

| ID | Prompt | Why |
| --- | --- | --- |
| T11 | `A spiral vase (vase mode friendly), smooth continuous wall, decorative` | Single-wall / thin-wall detection |
| T12 | `A gear with 20 teeth, flat, 5mm thick, center bore hole 8mm` | Tooth self-intersections |
| T13 | `A miniature benchy-style tugboat, solid hull, printable without supports if possible` | Classic overhang benchmark analogue |
| T14 | `A pair of eyeglasses frames, wearable scale proportions, solid` | Thin temples |
| T15 | `A screw-top jar with separate lid (two bodies if needed), printable` | Multi-body / thread mating |
| T16 | `A lattice phone grip pop-socket style, circular, hollow lattice` | Lattice non-manifold edges |
| T17 | `A low-poly tree with trunk and canopy, solid base for standing` | Branch thin walls |
| T18 | `A whistle with internal air channel, functional, printable` | Internal cavities / escape holes |
| T19 | `A cable clip that snaps onto a desk edge, living hinge optional` | Snap-fit tolerances |
| T20 | `A D20 twenty-sided die, sharp edges, numbered faces embossed` | Sharp manifold edges + emboss |

**Negative prompt (when the API supports it):**  
`non-manifold, open edges, paper thin walls, floating fragments, intersecting geometry, holes in solid parts, scan artifacts`

---

## B. Image-to-3D reference ideas (12)

Use public-domain / self-shot photos only. Store references under `samples/images/` when acquired (not bundled yet — no downloads that violate licenses).

| ID | Reference idea | Source guidance | Stress test |
| --- | --- | --- | --- |
| I01 | White ceramic mug, side view, plain background | Own photo or CC0 product shot | Handle attach |
| I02 | Orthographic front photo of a hex bolt | Own photo | Threads |
| I03 | Single sneaker side view | Own photo / CC0 | Thin sole / overhang |
| I04 | Toy rubber duck, three-quarter view | Own photo | Undercuts |
| I05 | House plant in a simple pot, front | Own photo | Organic thin leaves (expect fail) |
| I06 | Mechanical keyboard keycap (escape), top+side | Own photo | Stem geometry |
| I07 | Wooden chess pawn, side | Own photo / CC0 | Lathe-like solids (should pass) |
| I08 | Bicycle chain link close-up | Own photo | Thin metal / holes |
| I09 | Action-figure torso front | Own photo | Multi-part / thin limbs |
| I10 | Coffee pour-over dripper cone | Own photo | Thin cone walls |
| I11 | USB-C cable strain-relief boot | Own photo | Tiny features |
| I12 | Multi-view set: mug front / side / top (for multi-image models) | Own photo set | Multi-view consistency |

**Image rules:** 1024² or higher, subject centered, diffuse lighting, no heavy perspective distortion for single-image tests. Multi-view (I12) reserved for Meshy / Tripo / Rodin multi-image endpoints.

---

## C. Run protocol

1. Submit each prompt once per generator per week (no cherry-picking retries except documented vendor failures).
2. Download mesh-only when possible (textures ignored for print score).
3. Convert to STL via trimesh; normalize scale; run `pipeline/score_mesh.py`.
4. Archive prompt pack version string in week JSON (`prompt_pack: v0.1`).

---

## D. Deliberate negative controls (pipeline QA)

Not sent to generators — used to validate the scorer:

| ID | Description | Expected |
| --- | --- | --- |
| N01 | Closed unit cube | High score, slice OK |
| N02 | Cube missing one face (open) | Watertight fail |
| N03 | Two cubes sharing a face (non-manifold) | Non-manifold edges |
| N04 | Two intersecting tetrahedra | Self-intersection flag |
| N05 | Flat 0.2 mm plate 40×40 mm | Thin-wall flag |
