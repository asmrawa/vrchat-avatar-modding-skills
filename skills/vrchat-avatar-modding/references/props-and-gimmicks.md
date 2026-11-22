# Handheld Props, Interactive Gimmicks, And Effects

Use this reference when importing handheld props, constraints, Contacts, pose/tracking systems, or multi-part interactive gimmicks.

## Import And Locate Drivers

- Inspect vendor documentation, asset lists, dependencies, supported avatar versions, and GUID collisions before importing. Verify whether existing SDK, Modular Avatar, NDMF, and shader packages already satisfy requirements.
- A single prefab may bundle sub-props, menus, parameters, and FX controllers. Instantiate it according to vendor instructions once, then check for duplicate menu entries and valid installer targets. Wire into existing prop/toy submenus when appropriate and preserve vendor gestures, cooldowns, summon animations, Contacts, audio, and PhysBones.
- When dedicated `Hold`, `Grip`, `Target`, or `ModularAvatarBoneProxy` nodes exist, find the true runtime driver first. Never move a parent node that a constraint or proxy snaps back every frame; inspect resolved hand/finger bones, proxy attachment mode, constraint sources, offsets, and scale inheritance before editing.

## Fit Props To Real Poses

1. Use an actual grip gesture or reproducible test pose to verify left/right hand, palm vs. back-of-hand orientation, finger gaps, and contact points. For directional props, confirm front/back or tip/base via mesh geometry, UVs, or VFX anchor points—2D screen directions in a screenshot do not map directly to 3D axes.
2. Compute grip points and orientations from resolved bone world transforms, then convert into the attached bone's local space. Scale proportions relative to the current avatar's hand size. Distinguish "increase by X%" from "set to X% of original" and calculate from the recorded baseline.
3. After scaling a prop, verify that smoke emitters, glow tips, audio sources, Contacts, and colliders follow properly. When resizing a single item inside a multi-prop package, separate the visible mesh and its local VFX from shared triggers so unrelated triggers are not scaled accidentally.
4. Check alignment from at least two clear angles (e.g., top-down, side, and back-of-hand). If a screenshot pose differs from the active test pose, align the pose first before judging misalignment. Test secondary motions to confirm binding, without over-promising zero clipping across every possible VR gesture.

## Switches, Triggers, And Multi-System Coexistence

- Use [toggle-implementation.md](toggle-implementation.md) for menu/FX wiring. Only make props mutually exclusive when requested (for example, two props occupying the same hand); keep independent props usable simultaneously unless told otherwise.
- Audit Contact/collider real-world radius (accounting for parent and proxy scale), attached bone, left/right hand, collision tags, receiver parameter, local vs. remote permissions, and default hidden state.
- Test menu summon/stow, gesture/Contact triggers, and re-summoning after release. Separate Animator transition/Parameter Driver checks from real VRChat hand-Contact and remote-player verification.

## Multi-Avatar Packages & Parallel Pose/Tracking Systems

- For multi-avatar packages, verify the user's package variant, supported avatar list, and vendor installer first. Prefer standard Unity import and verify landed paths, GUIDs, and compilation status. If a non-interactive import returns without registering assets, inspect whether partial files exist; when importing file-by-file, verify paths stay inside `Assets/`, dependencies and original `.meta` files remain intact, and no GUID collisions occur before letting `AssetDatabase` register them.
- When two pose or tracking systems coexist (e.g., a posing system alongside full-body or gesture tracking), audit both systems' Animator layers, bone/tracking weights, parameter names/types, and exit/reset states. Verify `A -> B`, `B -> A`, clean exit back to standing, remote visibility, and combined synced parameter cost (`<= 256` bits). Consider keeping a full-suite scene and a coexisting-suite scene as separate work scenes when budgets are tight.

## Shared Body-Part Interactions (Ears/Tails) With Wardrobe Switches

- Vendor installers may modify ear/tail PhysBone grab, pose, or stretch settings. Record every original PhysBone component, root bone, parameter, and endpoint before installation, and inspect readable installer scripts to confirm exact target paths and restore logic. Customize vendor behaviour in a cloned work controller.
- Audit merged FX curves carefully: ear/tail visibility may simultaneously be driven by root-bone scale, `Renderer.enabled`, parent `m_IsActive`, or outfit replacements. Gate interactive gimmicks by the **effective** wardrobe/accessory visibility using explicit Animator conditions so mutually exclusive states each hold ownership of the same properties.
- Test default-off, disabling mid-interaction, restoration/regeneration, outfit switches, and quiet startup (frame 0 and several frames after spawn). Check overlapping `Any State` transitions for ping-pong loops.
- Separate owner-only controls from remote-visible state: to stay within the 256-bit parameter budget, owner enable toggles or reset buttons may stay local (`networkSynced = false`) while syncing only the resulting visible states—**only after verifying** that remote players' visuals and audio do not depend on those local parameters.
- NDMF clones can validate parameter-driven left/right independence, outfit interactions, and remote-view branches offline; Contacts, PhysBone grabs, real networking, and timing still require VRChat in-game testing.
