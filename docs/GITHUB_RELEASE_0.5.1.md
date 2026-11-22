## CTRL_DEF v0.5.1

### Changes

- Rig Score now displays its panel when the active object is a mesh instead of an Armature.
- Naming Doctor now has a sidebar field for the rename map, with validation. An empty map does nothing.
- Rig Score skips checks marked n/d, so a healthy rig can reach the full score. It also fixes three false positives: `DEF` prefixes are matched case-insensitively, `use_deform` is checked against actual weights, and switch bones referenced by drivers count as active.
- The sidebar guide now has 7 steps.

### Video

Both videos show Bone Collections during Auto Collection and Character Picker.

| Format | Video |
|---|---|
| 16:9, 44 s, no audio | `CTRL_DEF_v0.5_trailer_v2_16x9.mp4` |
| 9:16, 37 s, with voiceover | `CTRL_DEF_v0.5_short_v2_9x16.mp4` |

The videos are attached to the release assets.

### Tests

Headless test suite on Blender 5.2.

[Blender Extensions](https://extensions.blender.org/add-ons/ctrl-def/) · [GitHub repository](https://github.com/PieroFra/def-controller-auto)
