#!/usr/bin/env bash
set -euo pipefail

# Install VRChat Avatar Modding Skills on macOS / Linux.
# Usage: ./install.sh [codex|antigravity|cursor|all] [--force] [--install-unity-deps] [--install-blender-addon]

CLIENT="${1:-codex}"
FORCE=0
INSTALL_UNITY_DEPS=0
INSTALL_BLENDER_ADDON=0

shift || true
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --install-unity-deps) INSTALL_UNITY_DEPS=1 ;;
    --install-blender-addon) INSTALL_BLENDER_ADDON=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$ROOT/skills"

install_to() {
  local name="$1"
  local dest_root="$2"
  mkdir -p "$dest_root"
  echo ""
  echo "[$name] Installing skills to: $dest_root"
  for skill_dir in "$SKILLS_SRC"/*/; do
    skill_name="$(basename "$skill_dir")"
    dest="$dest_root/$skill_name"
    if [ -e "$dest" ]; then
      if [ "$FORCE" -ne 1 ]; then
        echo "  Skipped '$skill_name' (already exists). Re-run with --force to replace."
        continue
      fi
      backup="${dest}.bak_$(date +%Y%m%d_%H%M%S)"
      mv "$dest" "$backup"
      echo "  Backed up previous version to: $backup"
    fi
    cp -R "${skill_dir%/}" "$dest"
    echo "  Installed: $skill_name"
  done
}

case "$CLIENT" in
  codex)       install_to "codex"       "$HOME/.codex/skills" ;;
  antigravity) install_to "antigravity" "$HOME/.gemini/config/skills" ;;
  cursor)      install_to "cursor"      "$HOME/.cursor/skills" ;;
  all)
    install_to "codex"       "$HOME/.codex/skills"
    install_to "antigravity" "$HOME/.gemini/config/skills"
    install_to "cursor"      "$HOME/.cursor/skills"
    ;;
  *)
    echo "Usage: $0 [codex|antigravity|cursor|all] [--force] [--install-unity-deps] [--install-blender-addon]" >&2
    exit 1
    ;;
esac

if [ "$INSTALL_UNITY_DEPS" -eq 1 ]; then
  echo ""
  echo "[Unity MCP] Installing locked Node.js dependencies..."
  (cd "$ROOT/unity-mcp/unity-mcp-server" && npm ci --omit=dev --ignore-scripts)
fi

if [ "$INSTALL_BLENDER_ADDON" -eq 1 ]; then
  echo ""
  echo "[Blender MCP] Installing Blender add-on from bundled wheel..."
  uvx --from "$ROOT/blender-mcp/mcp_for_blender-2.3.1-py3-none-any.whl" mcp-for-blender install-addon
fi

echo ""
echo "Done! Restart your AI client or open a new session to load the skills."
