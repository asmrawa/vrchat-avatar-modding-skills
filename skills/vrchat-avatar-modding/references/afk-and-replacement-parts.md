# AFK And Replacement Hair/Parts

Use this reference when a transplanted hair or replacement part disappears, floats, or fails to restore during AFK or other actions. Diagnose the actual driver before touching skin weights or adding override layers.

## Find The Actual Driver Before Rebinding

1. Inspect the part and every ancestor: `activeSelf`, `activeInHierarchy`, `Renderer.enabled`, scale-to-zero curves, material visibility, bounds, and dedicated PhysBone/helper activation.
2. Trace **every** relevant controller: descriptor FX and Action layers, Modular Avatar merge animators, legacy compatibility helpers, blend trees, and animation clips. A helper with a reassuring name often holds an obsolete unconditional `AFK -> hide` curve.
3. Audit skinning independently: enumerate only bone slots with nonzero vertex weights (`GetAllBoneWeights()`), resolve them to the current head/attachment hierarchy, and check bind poses. A `rootBone` named `Hips` does not mean visible hair vertices are weighted to `Hips`.
4. Separate ordinary AFK from prop-dependent, transition-effect, or surrogate/LOD avatar branches:
   - If a branch intentionally hides the real body, forcing real hair visible produces floating hair.
   - If a branch displays a separate surrogate head, that head requires its own fitted/bound hair; hiding the real hair is not a surrogate-hair fix.

If weighted bones already follow the intended head and only an active-state curve hides the part, repair the curve rather than rebinding skin weights.

## Patch With Explicit Visibility Semantics

- Record enter, loop, exit, and finish/reset states, transition conditions, timing, reverse playback, and Write Defaults.
- Copy the owning controller and affected clips into the current work version folder. Preserve all other layers, transitions, behaviours, animation events, timing, and unrelated curves.
- In ordinary visible-body stages, keep replacement hair and its dedicated physics helper explicitly enabled.
- In stages where the real body disappears (or reappears with a delay), mirror the actual body's `m_IsActive` curve onto the replacement part and its physics root. Use an explicit per-stage fallback only after verifying that stage's intended visibility.
- When supporting multiple hairstyles alongside AFK, keep **hairstyle selection** and **AFK/effect-stage hiding** on cleanly separated hierarchy levels or under single-owner logic so switching hairstyles during or before AFK stays consistent.
- Remove or retarget proven conflicting helpers only in the work scene. Preserve intentionally inactive sub-pieces (such as an optional side ponytail); never bulk-enable every descendant to cure a bald head.

Reusable helpers in [scripts/VrcAvatarIntegration.cs](../scripts/VrcAvatarIntegration.cs):

```csharp
// Use discovered project and hierarchy paths, never hardcoded avatar names.
var fixedClip = VrcAvatarIntegration.CloneVisibilityClip(
    sourceClip, bodyPath, new[] { replacementRootPath, physicsRootPath },
    newClipPath, missingReferenceDefault: null);
var fixedController = VrcAvatarIntegration.CloneControllerWithClips(
    sourceController, replacements, newControllerPath);
```

Passing `null` rejects a missing reference curve; pass `true` or `false` only after proving the stage's intended fallback. The controller copier handles nested state machines and affected blend trees without mutating source assets. For `AnimatorOverrideController`, resolve overrides explicitly rather than casting and losing them.

## Validate Entry, Loop, Exit, And Binding

- Inspect the **NDMF/MA-built** controller and hierarchy, not just pre-build merge components.
- Confirm the obsolete hiding helper/curve no longer drives the replacement.
- Sample every affected stage around visibility transitions to assert hair and physics match intended body visibility, ordinary AFK stays haired, and exit restores normal appearance.
- Trigger the actual AFK parameter chain for each discovered branch—direct `Animator.Play` sampling alone does not prove transitions fire. Record which states were actually reached.
- Verify weighted bones follow head motion and remain valid after build. Disclose that offline FX evaluation does not fully simulate VRChat Action-layer runtime, IK, networking, or PhysBone dynamics.
