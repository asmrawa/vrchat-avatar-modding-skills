# Toggle, FX, And Linked-State Implementation

Use this reference when building clothing/prop toggles from scratch, completing missing vendor switches, wiring mutual-exclusion or override rules, or fixing broken defaults and restoration. For multi-outfit architecture and shared-accessory rebinding, see [wardrobe-and-shared-accessories.md](wardrobe-and-shared-accessories.md).

## Write A State Table Before Editing Animators

1. Confirm the target menu entry, display label, objects shown in each state, default value, `saved` state, and `networkSynced` state. Separate **user preference** from **effective visibility**—for example, a user's "Wear Hat" preference can stay on while a hooded outfit temporarily hides the hat, restoring it automatically when leaving that outfit.
2. Inspect `VRCAvatarDescriptor` menus, parameters, and FX layers plus descendant `ModularAvatarMenuInstaller`, `ModularAvatarMenuItem`, `ModularAvatarParameters`, `ModularAvatarMergeAnimator`, or project generators. Prefer wiring into vendor-provided controls when they already work. Record exact target paths, component types, properties, and both `activeSelf` and `activeInHierarchy`.
3. Use `AnimationUtility.GetCurveBindings` and `GetObjectReferenceCurveBindings` to find every actual writer across nested state machines, BlendTrees, and Override Controllers, accounting for Modular Avatar path rewriting. Visibility may be driven by `GameObject.m_IsActive`, `Renderer.m_Enabled`, weighted bone scale, or `MA Shape Changer`. Check ancestor nodes and competing layers; Unity Hierarchy eye icons or reordering Animator layers do not prove runtime linkage.

| Requirement | Typical Pattern | Regression Focus |
| --- | --- | --- |
| Independent on/off | `Bool`, two explicit states, Menu Toggle | Off, on, off again; initial join and reload defaults |
| N-of-1 outfit switch | `Int`, unique value per outfit, explicit default & invalid-value fallback | Direct switch between any pair; base clothes, accessories, and heel/floor offsets restore |
| Coexisting props | Separate `Bool`s or vendor inputs | Both active simultaneously still stow cleanly; avoid unintended exclusion |
| Same-hand exclusive props | Single `Int` with explicit empty-hand value (`0`) when exclusivity is requested | `A -> B`, `B -> A`, return to empty hand without mid-transition overlap |
| Accessory / body linkage | Effective state derived from conditions | Restoration once override clears while preserving user preference |
| Momentary gesture / Contact / button | Preserve vendor trigger, latch, cooldown, and release states | Input reset, re-trigger, left/right hand, remote player visibility |

Example linkage: `HatVisible = UserHatPref && OutfitAllowsHat`, `OriginalEarVisible = !HatVisible`. If a hat only covers one ear, drive only that ear bone. Always write back measured rest/baseline values from the current avatar rather than assuming every bone scale equals `1`. If an outfit's own tail can be toggled off independently, hide the base tail only when the outfit tail is **effectively active**.

## Authoring Or Wiring Controls

1. **Choose binding granularity**: Toggle dedicated visible children via `m_IsActive`. If disabling a root would deactivate Modular Avatar installers, Contacts, constraint sources, or shared bones, keep the functional root active and toggle only its visible children or renderers. For single ears or sub-parts on a shared renderer, use dedicated weighted bones or explicit mesh/BlendShape rules. Record initial and restored values.
2. **Isolate work assets**: Create or clone menus, parameters, controllers, and modified `.anim` clips inside the current work version folder. After copying a controller, audit sub-state machines, BlendTrees, and external clip references—editing an uncloned `.anim` still mutates older versions. Moving menu items or translating labels normally keeps parameter names untouched; if renaming a parameter, migrate menus, parameter assets, Animator conditions, Parameter Drivers, and Contacts together.
3. **Configure parameters & menus**: Keep `Bool`/`Int`/`Float` type, default, `saved`, and `networkSynced` consistent. Check for existing same-name parameters before adding duplicates. Keep menu pages at or under 8 controls (checking the **post-merge** menu tree) and verify total synced bit cost via `CalcTotalCost()` on the baked descriptor (`<= 256` bits).
4. **Configure FX layers**: Follow the project's existing controller conventions or append a small `ModularAvatarMergeAnimator` targeting FX. Verify whether binding paths are relative to the avatar root or the installer's relative root.
   - Independent `Bool`: `Off` and `On` states with two zero-duration, no-exit-time transitions (avoid self-transitions for instant switches; preserve timing for animated equip/stow props).
   - Every state should explicitly drive the same controlled property set, including restored values.
   - Follow the project's Write Defaults convention—do not flip WD across unrelated vendor states for a single toggle.
   - For `Int` selectors, define every valid value plus startup, invalid-value, and return-to-default handling.
5. **Unify defaults & ownership**: Align scene/prefab state, FX default state, `VRCExpressionParameters`, `ModularAvatarParameters`, and baked output. Test both clean initial load and previously `saved` parameter values. Prefer one layer or generator owning each property rather than stacking competing layers.
6. **Shared-clip & expression-edit check**: When editing an expression clip (such as removing sweat BlendShapes from a wink), verify whether both hand gestures and direct expression menu entries reference the same clip, and confirm BlendShape names after optimizer (AAO) remapping in the built avatar.

Minimal C# snippet for a two-keyframe constant visibility clip (`bindingRoot` = avatar root or MA relative root):

```csharp
var path = AnimationUtility.CalculateTransformPath(visibleChild, bindingRoot);
var binding = EditorCurveBinding.FloatCurve(path, typeof(GameObject), "m_IsActive");
AnimationUtility.SetEditorCurve(clip, binding, AnimationCurve.Constant(0f, 1f / 60f, isOn ? 1f : 0f));
```

## Verification & Troubleshooting

- Trace the **baked/merged** avatar from the final menu entry through remapped parameters, FX states, and target objects (accounting for inactive parents, merged renderers, and optimizer-rewritten paths). Seeing a matching clip in source assets is not proof.
- Test: `default -> on -> off -> on`, switching outfits and returning, preference retention across switches, rapid exclusive switching, and relevant gesture/AFK combinations. Record expected vs. actual in a compact state table.
- **Menu exists but does nothing**: Check parameter name/type/value, installer target, and animated hierarchy path.
- **Turns on but cannot turn off**: Check reverse transitions, saved parameter defaults, default state values, and competing layers.
- **Fails to restore after switching**: Check whether the exit state writes baseline values back, whether a parent remains inactive, or whether another toggle still overrides it.
- Separate offline simulation / Parameter Driver inspection from VRChat in-game verification in the final report.
