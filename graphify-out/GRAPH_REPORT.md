# Graph Report - anime_look_director  (2026-10-26)

## Corpus Check
- 39 files · ~104,443 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 1, .toml 1)

## Summary
- 968 nodes · 1948 edges · 73 communities (49 shown, 24 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 36 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Palette & World Gradient
- UI Panels & Shared Draw
- Compositor Stack & Layers
- Shadow Tint & Materials
- Geometry Nodes FX Groups
- Gate: P1/P2/P3 Checks
- FX Builders & Particles
- FX Creation & Compile
- FX Diagnostics
- FX Material & Hash Helpers
- Scene Settings & Callbacks
- Snapshot & Restore Lifecycle
- FX Motion & Meteor Solver
- Gate: Pixels & Render
- Blender Operators
- FX Registry & Handlers
- FX Ownership & Cleanup
- Gate: FX Behaviour
- Timeline Shot Markers
- Camera Overrides & Handlers
- Gate: World & Transforms
- FX Architecture (Docs)
- FX Clock & Time
- Test Fixtures
- Look Concepts (README)
- Atmospheric Smoke
- FX Benchmarks
- Audit & Diagnose Tools
- FX Look-Dev
- Palette Look-Dev
- Operator UI Helpers
- Milestone Definition of Done
- Baseline Recorder
- Class Registration
- UI Probe
- Gate: FX Age & GN Parity
- Gate: Render & Identity
- Verification & API Concepts
- Compositor Contracts (Docs)
- P0 Baseline Concepts
- init .py
- update fireworks()
- scene collections()
- ALD | World Gradient
- os
- lookdev families.py
- End-to-End User Workflow (7
- ALD Benchmark Render (128x72)
- Reference Art Study for
- on fx style()
- detach()
- check fx gn python
- check fx occlusion()
- ALD OT apply material
- ALD OT build
- check fx gn fallback()
- check ui parity()
- ALD OT fx clear
- ALD OT fx ground
- ALD OT fx select
- ALD OT smoke create
- ALD OT smoke remove
- check fx failed build()
- check fx new file()
- check fx persistent model()
- check fx reversibility()
- check fx scene duplicate()
- check fx ui screenshots()
- check fx undo redo()
- check p3()
- check scene actions()
- check world time seconds()
- Clipboard Concatenation One-Liner for

## God Nodes (most connected - your core abstractions)
1. `check()` - 65 edges
2. `main()` - 53 edges
3. `Anime Look Director (v2.30.1)` - 27 edges
4. `_build_fireworks()` - 23 edges
5. `_scene_id()` - 22 edges
6. `build()` - 19 edges
7. `_build_meteors()` - 18 edges
8. `_collection()` - 16 edges
9. `compile_system()` - 16 edges
10. `rebuild_registry()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Anime Look Director Project Skill` --conceptually_related_to--> `Anime Look Director (v2.30.1)`  [INFERRED]
  .opencode/skills/anime-look-director/SKILL.md → README.md
- `Read-Only Diagnostic Ending in UNKNOWN` --references--> `FX 3D Particle Systems (fx.py / ALD | FX)`  [EXTRACTED]
  preset_dev/P0_BASELINE.md → AGENTS.md
- `Anime Look Director Project Skill` --cites--> `AGENTS.md Project Instructions`  [EXTRACTED]
  .opencode/skills/anime-look-director/SKILL.md → AGENTS.md
- `baseline.json (version, hashes, schemas, flows)` --references--> `Headless Verification Gate (preset_dev/verify.py)`  [EXTRACTED]
  preset_dev/P0_BASELINE.md → AGENTS.md
- `Anime Look Director Project Skill` --references--> `ALD | Compositor Stack`  [EXTRACTED]
  .opencode/skills/anime-look-director/SKILL.md → AGENTS.md

## Import Cycles
- 3-file cycle: `__init__.py -> panels.py -> diagnostics.py -> __init__.py`
- 3-file cycle: `__init__.py -> operators.py -> diagnostics.py -> __init__.py`

## Hyperedges (group relationships)
- **ALD Compositor Stack Pipeline** — agents_compositor_stack, agents_kuwahara_painterly, agents_light_wrap, agents_anime_ink_lines, agents_aerial_haze, agents_god_rays, agents_fx_compositing_contract [EXTRACTED 1.00]
- **ALD FX 3D System Architecture** — agents_fx_particles, agents_geometry_nodes_backend, agents_fx_particle_solver, agents_fx_persistent_schema, agents_fx_material_contract, agents_fx_clock, agents_fx_compositing_contract [EXTRACTED 1.00]
- **ALD Verification and Evidence Tooling** — agents_verification_gate, changelog_ui_probe_tool, changelog_milestone_tool, changelog_benchmark_tool, preset_dev_p0_baseline_baseline_record [EXTRACTED 1.00]

## Communities (73 total, 24 thin omitted)

### Community 0 - "Palette & World Gradient"
Cohesion: 0.06
Nodes (39): ALD_OT_apply_palette, ALD_OT_stage_backlight, angles_from_direction(), angles_syncing(), _apply_gradient(), apply_palette(), apply_preset_style(), apply_sun_angles() (+31 more)

### Community 1 - "UI Panels & Shared Draw"
Cohesion: 0.06
Nodes (28): ALD_PT_compositor, ALD_PT_fx, ALD_PT_scene, ALD_PT_view3d, ALD_PT_view3d_compositor, ALD_PT_view3d_fx, ALD_PT_view3d_world, ALD_PT_world (+20 more)

### Community 2 - "Compositor Stack & Layers"
Cohesion: 0.06
Nodes (28): _aerial_haze(), build(), _depth_edges(), ensure_fx_base_layer(), ensure_fx_only_layer(), _fx_collection(), _get_transparent_world(), _glare_color() (+20 more)

### Community 3 - "Shadow Tint & Materials"
Cohesion: 0.10
Nodes (27): apply(), apply_preset_to_selected(), _build_group(), clear_scene(), count_scene(), _ensure_socket(), _group(), _look() (+19 more)

### Community 4 - "Geometry Nodes FX Groups"
Cohesion: 0.09
Nodes (20): attach_burst_modifier(), attach_trail_modifier(), _attribute(), build_burst_group(), _build_group(), build_trail_group(), _create_burst_group(), _create_trail_group() (+12 more)

### Community 5 - "Gate: P1/P2/P3 Checks"
Cohesion: 0.06
Nodes (20): check(), check_aerial_haze(), check_fx_anchor_clock(), check_fx_backend(), check_fx_decay_curve(), check_fx_future_event(), check_fx_gn_children(), check_fx_gn_determinism() (+12 more)

### Community 6 - "FX Builders & Particles"
Cohesion: 0.09
Nodes (17): _atmospheric_fade(), _build_curve(), _build_fireworks(), _build_meteors(), _build_particle_mesh(), _build_python_objects(), _collection(), _energy_powers() (+9 more)

### Community 7 - "FX Creation & Compile"
Cohesion: 0.09
Nodes (15): _anchor(), apply_backend(), _burst_center(), _camera_basis(), compile_system(), create_fireworks(), create_meteors(), _derive_key() (+7 more)

### Community 8 - "FX Diagnostics"
Cohesion: 0.10
Nodes (12): diagnose_event(), diagnose_scene(), event_state(), format_report(), _head_position(), _material_states(), _objects_of_event(), _projection() (+4 more)

### Community 9 - "FX Material & Hash Helpers"
Cohesion: 0.10
Nodes (13): _attribute_node(), _bind_energy(), _empty_position(), _event_drag(), _gn_flash_particles(), _map_range(), _material(), _mix_color() (+5 more)

### Community 10 - "Scene Settings & Callbacks"
Cohesion: 0.11
Nodes (16): style_syncing(), ALD_FX_Event, ALD_FX_System, ALD_Settings, _in_maintenance(), _on_custom_color(), _on_fx_backend(), _on_fx_clock() (+8 more)

### Community 11 - "Snapshot & Restore Lifecycle"
Cohesion: 0.13
Nodes (15): _compositor_state(), ensure(), is_inactive(), is_maintenance(), restore(), _restore_compositor(), _restore_neutral_world(), _restore_sun() (+7 more)

### Community 12 - "FX Motion & Meteor Solver"
Cohesion: 0.11
Nodes (13): burst_population(), _fibonacci_direction(), _gn_star_data(), _gn_trail_particles(), _hash_range(), _hash_unit(), _meteor_population(), _particle() (+5 more)

### Community 13 - "Gate: Pixels & Render"
Cohesion: 0.10
Nodes (12): background_node(), build_test_materials(), check_fx_diagnostics(), check_fx_solver_stability(), check_multiscene(), check_pixels(), check_versions(), diff_stats() (+4 more)

### Community 14 - "Blender Operators"
Cohesion: 0.09
Nodes (11): ALD_OT_clear_shadow_tint, ALD_OT_fx_anchor_create, ALD_OT_fx_clear, ALD_OT_fx_duplicate_system, ALD_OT_fx_remove_system, ALD_OT_fx_select_system, ALD_OT_fx_update, ALD_OT_remove (+3 more)

### Community 15 - "FX Registry & Handlers"
Cohesion: 0.13
Nodes (11): _event_config(), _find_objects(), _on_frame_change(), _on_load_post(), _on_undo_redo(), _one_object(), rebuild_registry(), register() (+3 more)

### Community 16 - "FX Ownership & Cleanup"
Cohesion: 0.14
Nodes (10): _cleanup_orphans(), clear(), _object_count(), _prune_claims(), _remove_kind(), remove_system(), _remove_system_objects(), runtime_by_uid() (+2 more)

### Community 17 - "Gate: FX Behaviour"
Cohesion: 0.11
Nodes (9): check_fx_bolide(), check_fx_burst_centers(), check_fx_camera_evaluated(), check_fx_event_continuity(), check_fx_gn_meteors(), check_fx_kamuro(), check_fx_meteor_timing(), check_fx_meteor_travel() (+1 more)

### Community 18 - "Timeline Shot Markers"
Cohesion: 0.16
Nodes (9): ALD_OT_mark_shot, _on_shots(), active_marker(), apply_for_frame(), marker_name(), _on_frame_change(), palette_from_marker(), register() (+1 more)

### Community 19 - "Camera Overrides & Handlers"
Cohesion: 0.18
Nodes (9): ALD_CameraSettings, _evaluated_matrix(), _on_camera(), _on_depsgraph(), _on_load_post(), register(), _transform_state(), unregister() (+1 more)

### Community 20 - "Gate: World & Transforms"
Cohesion: 0.26
Nodes (16): check_camera_override(), check_custom_colors(), check_god_rays(), check_live_transforms(), check_material_exclusion(), check_material_presets(), check_shadow_tint(), check_shot_markers() (+8 more)

### Community 21 - "FX Architecture (Docs)"
Cohesion: 0.17
Nodes (15): ALD Sky/FX Anchor, Atmospheric Smoke (ALD | Smoke volume), Per-System FX Clock (Timeline / Preview / Burst Age), FX Particle Material Contract, Analytic FX Particle Solver, FX 3D Particle Systems (fx.py / ALD | FX), Geometry Nodes FX Backend (ALD | FX Burst GN / Trail GN), preset_dev/bench_fx.py Five-Cost Benchmark (+7 more)

### Community 22 - "FX Clock & Time"
Cohesion: 0.17
Nodes (8): _age_offset(), _fps(), refresh_clock(), set_age(), system_clock(), system_time(), update(), _on_fx_age()

### Community 23 - "Test Fixtures"
Cohesion: 0.18
Nodes (7): build(), _camera_at(), _clean_scene(), main(), single_firework(), single_meteor(), user_scene()

### Community 24 - "Look Concepts (README)"
Cohesion: 0.19
Nodes (14): Cel Terminator (N.L + AO), God Rays (Glare Sun Beams), Rim Emission wiring, Rim Light (Fresnel band), ALD | Shadow Tint group (v2), Anime Look Director (v2.30.1), Auto Sun, preset_dev/lookdev.py Look-Dev Contact Sheet (+6 more)

### Community 25 - "Atmospheric Smoke"
Cohesion: 0.23
Nodes (7): _collection(), create(), exists(), _place(), remove(), sync(), _volume_material()

### Community 26 - "FX Benchmarks"
Cohesion: 0.23
Nodes (5): clean_scene(), count_memory(), enable_addon(), main(), setup()

### Community 27 - "Audit & Diagnose Tools"
Cohesion: 0.23
Nodes (5): has(), main(), read(), main(), parse_args()

### Community 28 - "FX Look-Dev"
Cohesion: 0.29
Nodes (9): apply_look(), build_scene(), enable_addon(), load_rgba(), main(), make_occluder(), make_sheet(), parse_args() (+1 more)

### Community 29 - "Palette Look-Dev"
Cohesion: 0.36
Nodes (8): build_scene(), enable_addon(), load_rgba(), main(), make_material(), make_sheet(), parse_args(), render_stats()

### Community 30 - "Operator UI Helpers"
Cohesion: 0.24
Nodes (6): ALD_OT_fx_bolide, ALD_OT_fx_fireworks, ALD_OT_fx_meteors, ALD_OT_fx_show, _scene_time(), _show_in_viewport()

### Community 31 - "Milestone Definition of Done"
Cohesion: 0.31
Nodes (8): build_scene(), check(), enable_addon(), inspect_source(), load_rgba(), main(), make_strip(), parse_args()

### Community 32 - "Baseline Recorder"
Cohesion: 0.33
Nodes (6): enable_addon(), file_hashes(), flows(), group_schemas(), main(), objects_of()

### Community 33 - "Class Registration"
Cohesion: 0.20
Nodes (7): register(), unregister(), register(), unregister(), register_class(), register_classes(), unregister_class()

### Community 34 - "UI Probe"
Cohesion: 0.33
Nodes (7): find_area(), main(), maximize(), parse_args(), scroll(), shot(), step()

### Community 35 - "Gate: FX Age & GN Parity"
Cohesion: 0.20
Nodes (6): check_fx(), check_fx_age_no_rebuild(), check_fx_gn_parity(), compare(), _fx_orphans(), _fx_signature()

### Community 36 - "Gate: Render & Identity"
Cohesion: 0.20
Nodes (4): check_fx_fixture(), check_fx_foreign_emission(), check_fx_identity(), check_render()

### Community 37 - "Verification & API Concepts"
Cohesion: 0.28
Nodes (7): Anime Look Director Project Skill, AGENTS.md Project Instructions, Headless Verification Gate (preset_dev/verify.py), preset_dev/ui_probe.py UI Verification Tool, v2.30.1 Verification Pass, Blender 5.1 Node-Group Compositor API, TECH_NOTES.md Blender 5.1.2 Spike Results

### Community 38 - "Compositor Contracts (Docs)"
Cohesion: 0.31
Nodes (8): Aerial Haze, Anime Ink Lines (depth + Normal), ALD | Compositor Stack, Kuwahara Painterly Filter (geometry-masked), Light Wrap, Bypass / Remove ALD / Detach and Keep Result, Snapshot / Restore Lifecycle (ald_snapshot, REMOVED state), In-Place Slider Updates (0.34 ms vs 5.28 ms)

### Community 39 - "P0 Baseline Concepts"
Cohesion: 0.25
Nodes (7): Persistent FX Schema (ALD_FX_System / ALD_FX_Event), baseline.json (version, hashes, schemas, flows), P0 Baseline — Evidence and Expected Failures, N01 Occlusion Leak (particle drawn through wall), N02 Zero FX Is Not the Identity, Read-Only Diagnostic Ending in UNKNOWN, Persistent Scene UUID Identity (ald_fx_id)

### Community 40 - "init .py"
Cohesion: 0.25
Nodes (3): camera_override(), apply_world(), effective_palette()

### Community 41 - "update fireworks()"
Cohesion: 0.31
Nodes (7): _evaluate(), _particle_state(), _unit_sphere(), _update_fireworks(), _update_meteors(), _update_system(), _write_particle_mesh()

### Community 42 - "scene collections()"
Cohesion: 0.25
Nodes (5): _retag_scene(), _scene_collections(), walk(), _shared_with_other_scene(), _remove_orphans()

### Community 43 - "ALD | World Gradient"
Cohesion: 0.29
Nodes (8): ALD | World Gradient group, Four-Zone Sky Gradient, Perspective Planar Anime Clouds, Three-Tier Clustered Painterly Starfield, Visible-Sky / Ambient Split, Gnomonic Contrail Coordinates (X/Z, Y/Z), _sample_cloud_density (rho, envelope, warped_pos), Horizon Offset (shifted_z = Z - 0.22 * Horizon Offset)

### Community 44 - "os"
Cohesion: 0.43
Nodes (5): clean_scene(), enable_addon(), main(), metrics(), setup_scene()

### Community 45 - "lookdev families.py"
Cohesion: 0.43
Nodes (6): build_scene(), enable_addon(), load_rgba(), main(), make_sheet(), parse_args()

### Community 46 - "End-to-End User Workflow (7"
Cohesion: 0.38
Nodes (5): Material Presets (Skin/Hair/Fabric/Metal/Emission), Per-Camera Palette Overrides, ALD:<PALETTE> Shot Markers, View3D Sidebar N Panel (Anime Look), End-to-End User Workflow (7 steps)

### Community 47 - "ALD Benchmark Render (128x72)"
Cohesion: 0.47
Nodes (6): Absent FX Particles (No Firework or Meteor Visible), ALD Benchmark Render (128x72), Flat Dark-Gray Field, No Geometry Silhouette or Horizon Line, Render-Cost Benchmark Frame (128x72), Subtle Top-to-Bottom Value Gradient

### Community 48 - "Reference Art Study for"
Cohesion: 0.40
Nodes (5): Seven Atmosphere Presets, Palette Character Table, Oga Kazuo Art Collection, Reference Art Study for Palette and Cloud Calibration, Persona 3 Official Artbook

## Ambiguous Edges - Review These
- `ALD Benchmark Render (128x72)` → `Absent FX Particles (No Firework or Meteor Visible)`  [AMBIGUOUS]
  preset_dev/bench_render.png · relation: references
- `ALD Benchmark Render (128x72)` → `No Geometry Silhouette or Horizon Line`  [AMBIGUOUS]
  preset_dev/bench_render.png · relation: references
- `Absent FX Particles (No Firework or Meteor Visible)` → `Render-Cost Benchmark Frame (128x72)`  [AMBIGUOUS]
  preset_dev/bench_render.png · relation: rationale_for

## Knowledge Gaps
- **26 isolated node(s):** `Shadow Hue Lift`, `Auto Sun`, `Two-Lobe Sun Glow (Mie)`, `One-Click Viewport Compositor`, `preset_dev/lookdev.py Look-Dev Contact Sheet` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 346 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_scene_id()` connect `FX Ownership & Cleanup` to `Compositor Stack & Layers`, `FX Builders & Particles`, `FX Creation & Compile`, `FX Diagnostics`, `FX Material & Hash Helpers`, `scene collections()`, `Snapshot & Restore Lifecycle`, `FX Registry & Handlers`, `FX Clock & Time`, `Atmospheric Smoke`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **What connects `Shadow Hue Lift`, `Auto Sun`, `Two-Lobe Sun Glow (Mie)` to the rest of the system?**
  _26 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Palette & World Gradient` be split into smaller, more focused modules?**
  _Cohesion score 0.05573770491803279 - nodes in this community are weakly interconnected._
- **Why does `register_classes()` connect `Class Registration` to `UI Panels & Shared Draw`, `Scene Settings & Callbacks`, `Camera Overrides & Handlers`, `Blender Operators`?**
  _High betweenness centrality (0.007) - this node is a cross-community bridge._
- **Should `UI Panels & Shared Draw` be split into smaller, more focused modules?**
  _Cohesion score 0.06397306397306397 - nodes in this community are weakly interconnected._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `ALD Benchmark Render (128x72)` and `Absent FX Particles (No Firework or Meteor Visible)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `ALD Benchmark Render (128x72)` and `No Geometry Silhouette or Horizon Line`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._