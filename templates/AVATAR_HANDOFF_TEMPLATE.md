# Avatar Modding Handoff Template

Copy this file into your own private workspace (outside any public Git repository) to keep long multi-session VRChat avatar projects organized and easy to resume across AI sessions.

> **Privacy reminder**: Never commit personal paths, VRChat Blueprint IDs (`avtr_...`), account info, or commercial avatar assets to a public repository.

---

## 1. Project Snapshot

| Field | Value |
| --- | --- |
| Avatar Display Name | `<MyAvatar>` |
| Unity Project Path | `<E:/UnityProjects/MyAvatarProject>` |
| Unity Version (`ProjectVersion.txt`) | `<2022.3.22f1>` |
| Avatar Root Object | `<AvatarRootName>` |
| Current Active Work Scene | `<Assets/VRCWork/MyAvatar/Scenes/MyAvatar_v05_Wardrobe.unity>` |
| Last Known-Good Rollback Scene | `<Assets/VRCWork/MyAvatar/Scenes/MyAvatar_v04_Baseline.unity>` |
| Base Vendor Prefab (Read-Only) | `<Assets/VendorAvatar/Prefabs/Avatar_Full.prefab>` |
| Key Package Versions | VRChat SDK `<3.x>`, Modular Avatar `<1.x>`, NDMF `<1.x>`, AAO `<1.x>`, Shader `<lilToon / Poiyomi>` |
| Synced Parameter Budget (Baked) | `<120 / 256 bits>` |
| Blueprint Upload Target | Omit full `avtr_...` ID here; note only whether main and variant scenes are detached. |

### Copy-Paste Session Kickoff Prompt

> Please read `<path/to/this-handoff.md>` first. This session's goal is: **[describe task]**. Pick the matching skill (`vrchat-project-audit-and-repair`, `vrchat-avatar-modding`, or `vrchat-clothing-rebuild`), connect via Unity MCP, verify the active project and scene first, isolate edits in a new versioned scene under `Assets/VRCWork/`, and report all four deliverables at the end.

---

## 2. Skill Routing Quick Reference

| Request Type | Skill |
| --- | --- |
| Read-only inspection, diff two versions, explain warnings, trace GUID/FX breaks | `vrchat-project-audit-and-repair` |
| Install outfits/hair/props, menus & FX toggles, UV texture edits, lighting/fit, optimization, SDK build | `vrchat-avatar-modding` |
| Reconstruct torso-fitted garment mesh in Blender for modified body shape | `vrchat-clothing-rebuild` |

---

## 3. Wardrobe, Hair, And Props Matrix

| System | Parameter Name | Type | Values / Default | Notes & Linked Rules |
| --- | --- | --- | --- | --- |
| Outfit Switch | `ClothingSet` | `Int` (synced) | `0` Base, `1` Casual, `2` Formal (default `0`) | Hides base underlayers when covered; restores on `0` |
| Shared Hat | `SharedHat` | `Bool` (synced) | `false` | Hides ears only when `SharedHat && ClothingSet != 2` |
| Handheld Prop | `HandProp` | `Int` (synced) | `0` Off, `1` Prop A, `2` Prop B (unsaved) | Mutually exclusive on right hand |
| Hairstyles | `HairStyle` | `Int` (synced) | `0` Default, `1` Alternate | AFK curves follow body visibility cleanly |

---

## 4. User Preferences & Non-Negotiable Constraints

- Keep original avatar proportions and height unless explicitly asked to rescale.
- Keep Scene View in `Persp` mode; run pose/animation tests only on temporary clones (never pollute the work scene's rest skeleton).
- Preserve vendor source assets untouched; clone any modified controller, clip, menu, material, or mesh into the current work version folder.
- Only run SDK Build / Upload when explicitly requested; handle login and 2FA manually in Unity's SDK panel.

---

## 5. Version History & Rollback Index

| Version | Scene / Work Folder | Summary of Changes | Verification Level |
| --- | --- | --- | --- |
| `v01` | `Scenes/MyAvatar_v01_Base.unity` | Clean work scene cloned from full vendor prefab | Unity-resolved + NDMF clone |
| `v02` | `Scenes/MyAvatar_v02_Hair.unity` | Transplanted alternate hair + AFK visibility fix | NDMF + Gesture Manager |
| `v03` | `Scenes/MyAvatar_v03_Wardrobe.unity` | Added outfits 1–2 with `ClothingSet` & menu | NDMF + Windows local SDK Build |

---

## 6. Last Session Four-Item Delivery Log

1. **Version & file locations**: `<new work scene path, work folder, rollback baseline>`
2. **Exact changes made**: `<objects, menus, parameters, materials, meshes, scripts>`
3. **Verification level achieved**:
   - Static YAML / GUID checks: `<pass / skipped>`
   - Unity-resolved checks (compile errors, missing refs, reload persistence): `<pass / details>`
   - NDMF / Gesture Manager / local SDK Build: `<pass / details>`
4. **Pending in-game / user checks**: `<VRChat Contacts, PhysBone grabs, remote sync, world lighting, manual upload>`
