**🇬🇧 English | [🇮🇹 Italiano](README.it.md)**

# CTRL_DEF — DEF Controller Auto

[![Blender](https://img.shields.io/badge/Blender-4.2%20LTS%20%E2%80%94%205.2%2B-blueviolet)](https://www.blender.org)
[![Category](https://img.shields.io/badge/Category-Rigging-orange)](https://extensions.blender.org/)
[![Version](https://img.shields.io/badge/version-0.2.0-brightgreen)](https://github.com/PieroFra/def-controller-auto/releases)
[![License](https://img.shields.io/badge/License-GPL--3.0--or--later-blue)](LICENSE)
[![Blender Extensions](https://img.shields.io/badge/Blender_Extensions-ctrl--def-orange?logo=blender)](https://extensions.blender.org/add-ons/ctrl-def/)

Generate tracked, colored controller bones with **shared custom shapes** from the deformation chain (`DEF_`) in a single click — clean FK hierarchy, zero Dependency Cycles, a modular `ctrl_def_mods\` package (`v0.2.0`) and 1-click synergy with **A.C.T.D.** (Auto Copy Transforms DEF).

| | |
|---|---|
| **Compatibility** | **Blender 4.2 LTS — 5.2+** |
| **Category** | **Rigging** |
| **Version** | **0.2.0** |
| **Author** | **Pierfrancesco Diodato** |
| **Type** | Add-on (installable ZIP or folder) |
| **License** | GPL-3.0-or-later |
| **Official page** | [Blender Extensions — ctrl-def](https://extensions.blender.org/add-ons/ctrl-def/) |

---

## ⚡ Quick Start (under 60 seconds — 4 steps)

1. Select the armature, enter **Edit Mode** (`Tab`) and select the bones with the `DEF_` prefix.
2. Open the Sidebar (`N`) → **DEF Ctrl** tab and pick a preset (e.g. *Biped Arm (Cube)*) or customize shape, color and scale.
3. Click **Generate Controllers** (`ctrl_def.generate`): clean controllers (`hand.L`) are created in an FK chain inside the `"CTRLS"` Bone Collection.
4. Click **Bind DEF to CTRL (ACTD)** (`ctrl_def.bind_actd`): the `DEF_` bones instantly copy the controller transforms in Pose Mode with no Dependency Cycle.

> **Result:** rotate `arm.L` in Pose Mode and `DEF_arm.L` follows in real time — the mesh deforms through the DEF bones, control lives on the controllers.

---

## 🚀 Key Features

- **Clean naming by default**: controllers are named after the DEF bones without prefix (`DEF_hand.L` → `hand.L`, Blender/Rigify standard); the *Controller Prefix* field restores the classic naming (e.g. `CTRL_` → `CTRL_hand.L`).
- **Shared custom shapes per type** (`v0.1.2`): wireframe shapes are shared objects (`CTRL_DEF_SHAPE_CIRCLE`, `CTRL_DEF_SHAPE_CUBE`, `CTRL_DEF_SHAPE_SPHERE`, `CTRL_DEF_SHAPE_ARROW`, `CTRL_DEF_SHAPE_CROSS`) — one mesh per type, reused by every controller.
- **Instant generation**: controllers match the position, orientation and roll of their `DEF_` bones, with `use_deform = False` (they do not deform the mesh).
- **Default hierarchy "CTRL Chain (FK)"**: rebuilds the FK tree between controllers (`forearm.L` child of `arm.L`), keeping them independent from the DEF bones: **zero Dependency Cycles** with A.C.T.D., even with a `Root` parent.
- **Dedicated Bone Collection**: every controller is automatically isolated in the `"CTRLS"` collection (renamed from `"CTRL"` in `v0.2.0`).
- **Themed color palette**: quick assignment following the Blender theme (Red, Green, Blue).
- **Optional Bone Widget integration** (`v0.2.0`): the custom shape widgets of the generated controllers are delegated to the **Bone Widget** extension through `ctrl_def.create_widget` (built-in library picker); when the extension is not installed the panel warns and offers a **direct link** to its page.
- **Quick IK target** (`v0.2.0`): `ctrl_def.add_ik` adds an IK target (optional pole pointer, `use_deform = False`) on a selected chain of 2‑3 controllers, with zero Dependency Cycles with A.C.T.D.
- **Pre-Flight Diagnostics** (`v0.2.0`): `ctrl_def.diagnose` checks zero-length `DEF` bones, missing `.L`/`.R` mirrored counterparts (with mirror enabled), name collisions with non-DEF bones and warns when parenting to `"DEF"` together with A.C.T.D. (Dependency Cycle risk).
- **JSON/CSV export & user presets** (`v0.2.0`): `ctrl_def.export_json` / `ctrl_def.export_csv` export the CTRL→DEF registry with rig metadata; `ctrl_def.save_preset` / `ctrl_def.load_preset` save and reload your panel settings as `.json` files.
- **Modular package** (`v0.2.0`): the source of truth is the `ctrl_def_mods\` module package, assembled into the installable monolith by `scripts/build_monolith.py` (build step, never edited by hand).
- **Organized interface** (`v0.2.0`): the panel is split into 3 collapsible sections — `1 · Setup`, `2 · Controller`, `3 · Avanzate/Advanced` — plus an integrated **Guide** (closed by default), all localized in IT/EN including the section titles.
- **Flexible parenting**: `CTRL Chain (FK)` (default), `Parent Bone`, `Root`, `None (Free)` and `Same DEF` — the latter **only if the DEF bones do not copy the CTRL**, because it creates a Dependency Cycle with A.C.T.D.
- **1-click DEF→CTRL constraint**: the **"Bind DEF to CTRL (ACTD)"** button (`ctrl_def.bind_actd`) switches to Pose Mode, configures and runs **A.C.T.D.** automatically when installed (source = controllers, destination = `DEF_`); without A.C.T.D. it applies the same `COPY_TRANSFORMS` constraints natively (standalone fallback) from the proprietary registry.
- **L/R mirroring**: generates the mirrored counterpart at the same time (e.g. `.L` → `.R`), preserving the `_L`/`_R` separators.
- **Quick presets**: *Default*, *Biped Arm*, *Root Controller*, *Face*.
- **Bilingual IT/EN interface**: every label, panel and dropdown entry (`EnumProperty`) follows the Blender language preference, with automatic English fallback.
- **JSON registry & clean removal**: tracks every generated controller on the armature (`_ctrl_def_generated`), enabling safe full removal (`ctrl_def.remove`) without touching the existing rig.

---

## 📸 Previews (Screenshots & Demo GIF)

| File | Content |
|---|---|
| `docs/images/01_before_def_bones.png` | Armature with the `DEF_` bones selected and the **DEF Ctrl** panel open in the Sidebar (`N`). |
| `docs/images/02_after_ctrl_generated.png` | After **Generate Controllers** with the *Biped Arm (Cube/Red/Mirror)* preset: colored controllers in Pose Mode. |
| `docs/images/demo.gif` | Animated demo: rotation wave along the generated controller chain. |

![Armature with DEF bones selected and the DEF Ctrl panel](docs/images/01_before_def_bones.png)

*Figure 1 — Armature with the `DEF_` bones selected (names and axes visible) and the **Controller DEF** panel open in the Sidebar (`N`) → **DEF Ctrl** tab.*

![Generated controllers in Pose Mode](docs/images/02_after_ctrl_generated.png)

*Figure 2 — After **Generate Controllers** with the **Biped Arm** preset (Cube/Red/Mirror): colored shared custom shapes in Pose Mode and updated status box (`DEF found: 3 | CTRL generated: 3`).*

![Animated demo: controller chain rotation](docs/images/demo.gif)

*Figure 3 — Animated demo: rotation wave along the generated controller chain.*

---

## 🔄 Before / After Example (Names, Hierarchy and Attributes)

Sample chain (left arm) with the *Biped Arm (Cube)* preset:

| Aspect | Deform bones (before) | Default controllers (after) | Controllers with optional prefix (after) |
|---|---|---|---|
| **Names** | `DEF_arm.L` → `DEF_forearm.L` → `DEF_hand.L` | `arm.L` → `forearm.L` → `hand.L` | `CTRL_arm.L` → `CTRL_forearm.L` → `CTRL_hand.L` |
| **`use_deform`** | `True` | `False` | `False` |
| **Bone Collection** | — (original rig) | `CTRLS` | `CTRLS` |
| **Custom shape** | — | `CTRL_DEF_SHAPE_CUBE` (shared) | `CTRL_DEF_SHAPE_CUBE` (shared) |
| **Hierarchy** | Deform chain | FK chain (`forearm.L` child of `arm.L`) | FK chain (`CTRL_forearm.L` child of `CTRL_arm.L`) |
| **Dependency Cycle with A.C.T.D.** | — | **None** | **None** |

Controllers copy position, orientation and roll from their `DEF_` bones, but they do not deform the mesh (`use_deform = False`) and live in the dedicated `"CTRLS"` Bone Collection.

---

## 🔗 1-Click Synergy with Auto Copy Transforms DEF (A.C.T.D.)

CTRL_DEF is the natural companion of **A.C.T.D.** (Auto Copy Transforms DEF):

1. Use **CTRL_DEF** to build the armature controllers from the `DEF_` bones (clean naming, FK hierarchy, shared shapes).
2. Click the 1-click button **"Bind DEF to CTRL (ACTD)"** (`ctrl_def.bind_actd`):
   - if **A.C.T.D.** is installed, CTRL_DEF switches to Pose Mode, configures its settings (source = controllers, destination = `DEF_`) and runs the procedure automatically, with no manual step;
   - in **standalone** use (A.C.T.D. missing) it applies the same `COPY_TRANSFORMS` constraints natively, reading the proprietary registry of the generated controllers.

Both add-ons work in synergy while keeping registries and prefixes fully isolated.

**Empirical check (Blender 5.2 LTS):** with the default *CTRL Chain (FK)* and with a *Root* parent, Blender reports **0 dependency cycles**; rotating `arm.L` by 30° and `hand.L` by 20°, `DEF_arm.L` follows with a 0.0000° delta. (Avoid the *Same DEF* parenting together with A.C.T.D.: it creates cycles.)

**A.C.T.D. repository:** https://github.com/PieroFra/auto-copy-transforms-def

---

## 🧪 Headless Test Suite

The `tests/test_ctrl_def.py` suite runs from a terminal on any platform, with a clean Blender environment (`--factory-startup`).

**Windows PowerShell:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_tests.ps1
```

**Linux / macOS / Bash:**

```bash
./scripts/run_tests.sh
```

**Direct Blender command (any OS):**

```bash
blender --background --factory-startup --python scripts/run_ctrl_def_tests.py
```

The runners print the suite verdict: `VERDETTO: OK passati=<n> falliti=0 totale=<n>` (exit code 0) or `VERDETTO: FAIL ...` (exit code 1). Last local result on Blender 5.2.0 LTS: `passati=5 falliti=0 totale=5` (see `tests/test_out.txt`).

---

## 📦 Installable ZIP

The installable package for `v0.2.0` is the **modular package**: the generated monolith plus the `ctrl_def_mods\` module folder, with no wrapping folder:

```
def_controller_auto_v0.2.0.zip
├── __init__.py              (generated monolith)
├── blender_manifest.toml
├── README.md
└── ctrl_def_mods\
    ├── __init__.py
    ├── ctrl_def_generation.py
    ├── ctrl_def_i18n.py
    ├── ctrl_def_main.py
    ├── ctrl_def_operators.py
    ├── ctrl_def_properties.py
    ├── ctrl_def_registry.py
    ├── ctrl_def_shapes.py
    └── ctrl_def_ui.py
```

The release ZIP contains the English `README.md` only (the Italian version lives in the repository); each archive is accompanied by its `.sha256` checksum file in `dist\`.

**Alternatively:** download the package directly (with its `.sha256` checksum file) from the [Releases](https://github.com/PieroFra/def-controller-auto/releases) page.

**Official page on Blender Extensions:** <https://extensions.blender.org/add-ons/ctrl-def/> — the extension is approved and installable directly from Blender 4.2+: *Edit > Preferences > Get Extensions*, search **"DEF Controller Auto"** and click *Install*.

**Installing in Blender:** *Edit > Preferences > Add-ons > Install from Disk...*, select the ZIP (or the extracted folder), enable **DEF Controller Auto** and find the panel in the **3D Sidebar (`N` key) → "DEF Ctrl" tab**.

---

## 🧰 Operators Reference

All operation ids live in the `ctrl_def.*` namespace and are also reachable via *F3* search. UI labels and tooltips below match exactly what the add-on exposes (dynamically localized IT/EN):

| Operator `bl_idname` | UI Label (EN) | Description (tooltip) |
|---|---|---|
| `ctrl_def.generate` | Generate Controllers | Generate controller bones in the CTRLS collection from selected DEF bones |
| `ctrl_def.create_widget` | Create Widget | Assign the selected Bone Widget shape to the generated controllers |
| `ctrl_def.bind_actd` | Bind DEF to CTRL (ACTD) | Bind DEF bones to generated controllers via A.C.T.D. (if enabled) or native COPY_TRANSFORMS constraints |
| `ctrl_def.add_ik` | Add IK Target | Create an IK target bone and IK constraint on the selected 2-3 controller chain in Pose Mode |
| `ctrl_def.diagnose` | Diagnose Rig | Check selected DEF bones before generation (zero-length, missing mirror, collisions, cycles) |
| `ctrl_def.apply_preset` | Apply Preset | Apply the selected preset to the panel settings |
| `ctrl_def.export_json` | Export JSON | Export the active armature CTRL->DEF mapping to JSON |
| `ctrl_def.export_csv` | Export CSV | Export the active armature CTRL->DEF mapping to CSV |
| `ctrl_def.save_preset` | Save Preset JSON | Save current panel settings to a JSON preset file |
| `ctrl_def.load_preset` | Load Preset JSON | Load panel settings from a JSON preset file |
| `ctrl_def.remove` | Remove Generated | Remove generated controllers, optional IK targets, and their constraints |

---

## ⚠️ Known Limitations & Roadmap (post `v0.2.0`)

- Rigger-oriented workflows support **FK** chains; IK is covered by the quick target on 2‑3 controller chains (`ctrl_def.add_ik`), while an automatic **IK/FK switch** is planned for `v2`.
- Widgets rely on the optional **Bone Widget** extension (the plugin menu links directly to it); no built-in widget library.
- Automated verification covers generation, naming, FK hierarchy, presets, A.C.T.D. binding, IK targets, pre-flight diagnostics, JSON/CSV export, presets and registry entries; the full UI still needs manual interactive verification.

---

## 📋 Changelog

### `v0.2.0`
- **Modular package**: source of truth split into the `ctrl_def_mods\` package (9 modules) assembled into the installable monolith by `scripts/build_monolith.py`.
- **Panel redesigned**: 3 collapsible sections (`1 · Setup`, `2 · Controller`, `3 · Avanzate` — `3 · Advanced` in EN) plus an integrated `Guide` in 5 steps.
- **Bone Widget integration**: `ctrl_def.create_widget` delegates widget creation to the Bone Widget extension, with a direct install link when it is missing.
- **Quick IK target**: `ctrl_def.add_ik` on selected 2‑3 controller chains (`use_deform = False`, zero Dependency Cycles).
- **Pre-Flight Diagnostics**: `ctrl_def.diagnose` (zero-length DEF bones, missing mirrored `.L`/`.R`, name collisions, "DEF" parenting warning with A.C.T.D.).
- **Export JSON/CSV & user presets**: `ctrl_def.export_json`, `ctrl_def.export_csv`, `ctrl_def.save_preset`, `ctrl_def.load_preset` (round-trip tested).
- Custom shape orientation (`shape_rot` → `custom_shape_rotation_euler`).
- Bone Collection dedicated to controllers renamed `"CTRL"` → `"CTRLS"`.

### `v0.1.2`
- Shared custom shapes per type (`CTRL_DEF_SHAPE_*`): one mesh per shape, reused by every controller.
- Full dynamic IT/EN localization: labels, panels and buttons follow the Blender language, with automatic English fallback (`tr()`).
- Dynamic localization extended to the **dropdown menus** (`EnumProperty`): shape, color, parenting and presets use `_items_*` callbacks that re-translate the entries on every panel draw.
- Internal split of the generation operator into helper functions (`_collect_def_bones`, `_create_ctrl_edit_bones`, `_assign_ctrl_parents`, `_configure_ctrl_pose_bones`) for a more readable and testable flow.
- Compact UI labels with no IT/EN truncation.
- `_L`/`_R` separator preservation in mirroring.
- Cross-platform test scripts (`scripts/run_tests.ps1` and `.sh`).
- Screenshots/GIF free of the splash screen.
- 10 new edge-case tests.

### `v0.1.1`
- Clean naming without a default prefix.
- `CTRL Chain (FK)` hierarchy with zero Dependency Cycles.
- 1-click `ctrl_def.bind_actd` operator.

### `v0.1.0`
- Initial MVP release.

---

## 📄 License

GPL-3.0-or-later — see the [LICENSE](LICENSE) file.
