#!/usr/bin/env bash
# Actualiza las skills vendorizadas en .claude/skills/ desde sus repos upstream.
# Conserva la memoria aprendida (.claude/skills/video-director/director.yaml);
# los defaults nuevos de upstream quedan al lado como director.starter.yaml.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SK="$ROOT/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Descargando upstream..."
git clone --depth 1 -q https://github.com/rsmed31/video-director-skill "$TMP/vd"
git clone --depth 1 -q --filter=blob:none --sparse https://github.com/heygen-com/hyperframes "$TMP/hf"
git -C "$TMP/hf" sparse-checkout set skills

# video-director (MIT): reemplaza todo menos la memoria
MEM="$SK/video-director/director.yaml"
[ -f "$MEM" ] && cp "$MEM" "$TMP/director.yaml.keep"
rm -rf "$SK/video-director"
cp -r "$TMP/vd/skills/video-director" "$SK/"
cp "$TMP/vd/LICENSE" "$SK/video-director/LICENSE"
if [ -f "$TMP/director.yaml.keep" ]; then
  mv "$SK/video-director/director.yaml" "$SK/video-director/director.starter.yaml"
  cp "$TMP/director.yaml.keep" "$MEM"
fi

# HyperFrames core (Apache-2.0)
for s in hyperframes hyperframes-cli hyperframes-registry media-use; do
  rm -rf "${SK:?}/$s"
  cp -r "$TMP/hf/skills/$s" "$SK/"
  cp "$TMP/hf/LICENSE" "$SK/$s/LICENSE"
done

find "$SK" -name __pycache__ -prune -exec rm -rf {} +

echo "Listo. Versiones instaladas:"
git -C "$TMP/vd" log -1 --format='  video-director  %h  %cs'
git -C "$TMP/hf" log -1 --format='  hyperframes     %h  %cs'
echo "Actualiza la tabla de versiones en README.md, revisa 'git diff' y haz commit."
echo "Si hay director.starter.yaml, compáralo con director.yaml por si trae defaults nuevos."
