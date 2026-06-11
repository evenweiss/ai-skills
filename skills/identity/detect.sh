#!/usr/bin/env bash
# identity-detect — lightweight project fingerprint collector
# Outputs JSON. Zero decision logic — just file presence + deps facts.

ROOT="${1:-.}"
cd "$ROOT" 2>/dev/null || { echo '{"error":"cannot access dir"}'; exit 1; }

# ── Helpers ────────────────────────────────────────────────────────
json_arr() {
  local first=1
  printf '['
  for item in "$@"; do
    [ $first -eq 0 ] && printf ', '
    # escape " and \
    local escaped="${item//\\/\\\\}"
    escaped="${escaped//\"/\\\"}"
    printf '"%s"' "$escaped"
    first=0
  done
  printf ']'
}

# ── Key signal files ───────────────────────────────────────────────
SIGNALS=(
  package.json tsconfig.json
  vite.config.js vite.config.ts vite.config.mts
  vue.config.js vue.config.ts
  next.config.js next.config.ts next.config.mjs
  nuxt.config.ts nuxt.config.js
  webpack.config.js webpack.config.ts
  tailwind.config.js tailwind.config.ts
  postcss.config.js postcss.config.cjs
  "src/App.vue" "src/App.tsx" "src/App.jsx"
  "src/app/layout.tsx" "src/pages/_app.tsx"
  angular.json astro.config.mjs astro.config.js
  remix.config.js remix.config.ts
  svelte.config.js
  src/ components/ pages/ app/
  go.mod pom.xml build.gradle build.gradle.kts settings.gradle
  Cargo.toml
  requirements.txt pyproject.toml Pipfile manage.py setup.py
  composer.json artisan
  Gemfile config/routes.rb
  mix.exs
  pubspec.yaml
  "app/src/main/AndroidManifest.xml"
  Dockerfile docker-compose.yml docker-compose.yaml
  turbo.json nx.json lerna.json pnpm-workspace.yaml
  hugo.toml hugo.yaml config.toml config.yaml
  schema.prisma prisma/schema.prisma
  deno.json deno.jsonc
  bun.lockb bun.lock
  electron-builder.yml electron-builder.json
  "src-tauri/tauri.conf.json"
  "*.php"
)

found=()
shopt -s nullglob
for pat in "${SIGNALS[@]}"; do
  for f in $pat; do
    if [ -e "$f" ]; then
      found+=("$f")
      break
    fi
  done
done
shopt -u nullglob

# ── Deps from package.json ─────────────────────────────────────────
deps="[]"
if [ -f package.json ] && command -v node &>/dev/null; then
  deps=$(node -e 'try{const p=require("./package.json");console.log(JSON.stringify(Object.keys({...p.dependencies,...p.devDependencies})))}catch(e){console.log("[]")}' 2>/dev/null)
fi

# ── Sub-project hints (monorepo) ───────────────────────────────────
subs=()
probes=(package.json go.mod pom.xml Cargo.toml pyproject.toml composer.json Gemfile mix.exs pubspec.yaml)
# level 1
for d in */; do
  d="${d%/}"
  [[ "$d" == node_modules || "$d" == .git ]] && continue
  [ -d "$d" ] || continue
  for p in "${probes[@]}"; do
    if [ -e "$d/$p" ]; then subs+=("$d"); break; fi
  done
done
# level 2 (only if L1 empty)
if [ ${#subs[@]} -eq 0 ]; then
  for d in */*/; do
    d="${d%/}"
    [[ "$d" == node_modules/* || "$d" == .git/* ]] && continue
    [ -d "$d" ] || continue
    for p in "${probes[@]}"; do
      if [ -e "$d/$p" ]; then subs+=("$d"); break; fi
    done
  done
fi

# Notebooks?
for nb in *.ipynb notebooks/*.ipynb; do
  [ -e "$nb" ] && { found+=("notebooks/*.ipynb"); break; }
done

# ── Output ─────────────────────────────────────────────────────────
printf '{"files":'
json_arr "${found[@]}"
printf ',"deps":%s' "$deps"
printf ',"subs":'
json_arr "${subs[@]}"
printf '}\n'
