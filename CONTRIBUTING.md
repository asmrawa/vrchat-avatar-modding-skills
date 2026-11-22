# Contributing

Contributions that improve reliability, cross-client compatibility, or VRChat SDK / Modular Avatar / NDMF accuracy are welcome.

## Authoring Standards

1. **Agent-agnostic wording**: Keep skills and scripts compatible with Codex, Antigravity, Cursor, and any client supporting the Agent Skills format. Do not hardcode client-specific names or paths.
2. **English inside `skills/`**: Keep `SKILL.md`, `references/*.md`, and `agents/openai.yaml` in concise, unambiguous English to maximize token efficiency and cross-locale reach. Keep top-level README translations (`README.md`, `README_CN.md`, `README_JA.md`) synchronized.
3. **Zero private or copyrighted avatar assets**: Never commit commercial/private avatar names, personal local paths, VRChat `avtr_...` Blueprint IDs, credentials, presigned upload URLs, Unity logs, or vendor `.unitypackage` / `.fbx` / `.png` assets.
4. **Keep `SKILL.md` lean**: Put detailed procedures, edge cases, and code skeletons in `references/` and link them from the routing table in `SKILL.md`.
5. **Respect third-party licenses**: Do not remove upstream `LICENSE` files or attribution notices under `unity-mcp/`, `blender-mcp/`, or `skills/vrchat-avatar-modding/`.

## Before Opening A Pull Request

Run the automated validation suite and unit tests:

```bash
python scripts/validate_toolkit.py
python -m unittest discover -s tests -v
```

Ensure all checks exit with code `0` and confirm `git status` contains no temporary files or unrequested changes.
