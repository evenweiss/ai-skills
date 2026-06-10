#!/usr/bin/env bash
# identity-detect — comprehensive project type detection
# Covers: JS/TS, Python, Go, Java, Kotlin, PHP, Ruby, Rust, C#, Swift, Dart, Elixir,
#         Deno, Bun, mobile, data science, DevOps, static sites, monorepos.
# Outputs markdown identity block. Zero AI inference.

ROOT="${1:-.}"
cd "$ROOT" 2>/dev/null || { echo "identity: cannot access $ROOT"; exit 1; }

# ── Helpers ──────────────────────────────────────────────────────
has()    { test -e "$1"; }
has_any() { for f in "$@"; do test -e "$f" && return 0; done; return 1; }
glob()   { compgen -G "$1" 2>/dev/null | head -1 | grep -q .; }

# ── File presence ────────────────────────────────────────────────

# JavaScript / TypeScript ecosystem
h_pkg=false;      has package.json && h_pkg=true
h_ts=false;       has tsconfig.json && h_ts=true
h_node_modules=false; has node_modules && h_node_modules=true
h_eslint=false;   has_any .eslintrc.js .eslintrc.cjs .eslintrc.mjs eslint.config.js eslint.config.mjs && h_eslint=true
h_prettier=false; has_any .prettierrc .prettierrc.js .prettierrc.json prettier.config.js && h_prettier=true
h_vitest=false;   $h_pkg && grep -q '"vitest"' package.json 2>/dev/null && h_vitest=true
h_jest=false;     $h_pkg && grep -q '"jest"' package.json 2>/dev/null && h_jest=true

# Frontend meta-frameworks & libraries
h_vue=false;      has_any src/App.vue app.vue && h_vue=true
h_react=false;    has_any src/App.tsx src/App.jsx && h_react=true
h_next=false;     has_any next.config.js next.config.ts next.config.mjs src/app/layout.tsx src/pages/_app.tsx && h_next=true
h_nuxt=false;     has_any nuxt.config.ts nuxt.config.js && h_nuxt=true
h_svelte=false;   has_any src/routes/+page.svelte svelte.config.js && h_svelte=true
h_angular=false;  has angular.json && h_angular=true
h_astro=false;    has astro.config.mjs && h_astro=true
h_remix=false;    has_any remix.config.js remix.config.ts && h_remix=true
h_solid=false;    $h_pkg && grep -q '"solid-js"' package.json 2>/dev/null && h_solid=true
h_vite=false;     has_any vite.config.js vite.config.ts vite.config.mts && h_vite=true
h_webpack=false;  has_any webpack.config.js webpack.config.ts webpack.config.mjs && h_webpack=true
h_tailwind=false; has_any tailwind.config.js tailwind.config.ts tailwind.config.mjs && h_tailwind=true

# Backend JS/TS frameworks (detected from deps if h_pkg)
h_express=false; h_fastify=false; h_nestjs=false; h_koa=false; h_hono=false
if $h_pkg && command -v node &>/dev/null; then
  _dep_chk() { node -e "try{const d=require('./package.json');const k=Object.keys({...d.dependencies,...d.devDependencies});if(k.includes('$1'))process.stdout.write('1')}catch(e){}" 2>/dev/null; }
  [ -n "$(_dep_chk express)" ]       && h_express=true
  [ -n "$(_dep_chk fastify)" ]       && h_fastify=true
  [ -n "$(_dep_chk '@nestjs/core')" ] && h_nestjs=true
  [ -n "$(_dep_chk koa)" ]           && h_koa=true
  [ -n "$(_dep_chk hono)" ]          && h_hono=true
fi

# Electron / Tauri
h_electron=false; has_any electron-builder.yml electron-builder.json electron-builder.config.js && h_electron=true
h_tauri=false;    has_any src-tauri/tauri.conf.json src-tauri/Cargo.toml && h_tauri=true

# Bun / Deno
h_bun=false;  has_any bun.lockb bun.lock && h_bun=true
h_deno=false; has_any deno.json deno.jsonc deno.lock && h_deno=true

# Python
h_py_req=false;    has requirements.txt && h_py_req=true
h_pyproj=false;    has pyproject.toml && h_pyproj=true
h_setup=false;     has setup.py && h_setup=true
h_pipfile=false;   has Pipfile && h_pipfile=true
h_poetry=false;    $h_pyproj && grep -q '\[tool\.poetry\]' pyproject.toml 2>/dev/null && h_poetry=true
h_django=false;    has manage.py && h_django=true
h_flask=false;     $h_py_req && grep -qi flask requirements.txt 2>/dev/null && h_flask=true
h_fastapi_py=false; $h_py_req && grep -qi fastapi requirements.txt 2>/dev/null && h_fastapi_py=true
h_notebook=false;  { glob "*.ipynb" || glob "notebooks/*.ipynb"; } && h_notebook=true
h_torch=false;     $h_py_req && grep -qE 'torch|tensorflow|pytorch' requirements.txt 2>/dev/null && h_torch=true

# Go
h_go=false;       has go.mod && h_go=true
h_go_sum=false;   has go.sum && h_go_sum=true
h_gin=false;      $h_go && grep -q 'github.com/gin-gonic/gin' go.mod 2>/dev/null && h_gin=true
h_echo=false;     $h_go && grep -q 'github.com/labstack/echo' go.mod 2>/dev/null && h_echo=true
h_fiber=false;    $h_go && grep -q 'github.com/gofiber/fiber' go.mod 2>/dev/null && h_fiber=true

# Java
h_maven=false;   has pom.xml && h_maven=true
h_gradle=false;  has_any build.gradle build.gradle.kts settings.gradle settings.gradle.kts && h_gradle=true
h_spring=false;  $h_maven && grep -q 'spring-boot' pom.xml 2>/dev/null && h_spring=true
h_micronaut=false; $h_gradle && grep -qi micronaut build.gradle* settings.gradle* 2>/dev/null && h_micronaut=true

# Kotlin
h_kotlin=false;  has_any build.gradle.kts settings.gradle.kts && h_kotlin=true

# PHP
h_composer=false; has composer.json && h_composer=true
h_laravel=false;  has artisan && h_laravel=true
h_symfony=false;  has_any bin/console symfony.lock && h_symfony=true

# Ruby
h_gemfile=false;  has Gemfile && h_gemfile=true
h_rails=false;    has_any config/routes.rb app/controllers && h_rails=true

# Rust
h_cargo=false;    has Cargo.toml && h_cargo=true
h_actix=false;    $h_cargo && grep -qi actix Cargo.toml 2>/dev/null && h_actix=true
h_axum=false;     $h_cargo && grep -qi axum Cargo.toml 2>/dev/null && h_axum=true
h_rocket=false;   $h_cargo && grep -qi rocket Cargo.toml 2>/dev/null && h_rocket=true

# C# / .NET
h_dotnet=false;   has_any "*.csproj" "*.sln" "*.fsproj" && h_dotnet=true
h_unity=false;    has_any Assets ProjectSettings && h_unity=true

# Swift / iOS
h_swift=false;    has_any Package.swift "*.xcodeproj" "*.xcworkspace" && h_swift=true

# Dart / Flutter
h_flutter=false;  has pubspec.yaml && grep -q flutter pubspec.yaml 2>/dev/null && h_flutter=true
h_dart=false;     has pubspec.yaml && ! $h_flutter && h_dart=true

# Elixir
h_elixir=false;   has mix.exs && h_elixir=true
h_phoenix=false;  $h_elixir && grep -q phoenix mix.exs 2>/dev/null && h_phoenix=true

# Mobile
h_android=false;  has app/src/main/AndroidManifest.xml && h_android=true
h_ios=false;      has_any "*.xcodeproj" "*.xcworkspace" && h_ios=true
h_react_native=false; $h_pkg && grep -q '"react-native"' package.json 2>/dev/null && h_react_native=true
h_expo=false;     $h_pkg && grep -q '"expo"' package.json 2>/dev/null && h_expo=true

# Static sites / docs
h_hugo=false;     has_any config.toml config.yaml hugo.toml hugo.yaml content/ && h_hugo=true
h_jekyll=false;   has_any _config.yml _posts index.md && h_jekyll=true
h_gatsby=false;   $h_pkg && grep -q '"gatsby"' package.json 2>/dev/null && h_gatsby=true
h_vitepress=false; $h_pkg && grep -q '"vitepress"' package.json 2>/dev/null && h_vitepress=true
h_docusaurus=false; $h_pkg && grep -q '"@docusaurus' package.json 2>/dev/null && h_docusaurus=true

# DevOps / Infra
h_docker=false;   has_any Dockerfile docker-compose.yml docker-compose.yaml && h_docker=true
h_k8s=false;      has_any k8s/ charts/ helm/Chart.yaml && h_k8s=true
h_terraform=false; glob "*.tf" && h_terraform=true
h_ansible=false;  has_any ansible.cfg playbook.yml playbook.yaml && h_ansible=true
h_ci=false;       has_any .github/workflows .gitlab-ci.yml Jenkinsfile && h_ci=true

# Monorepo tools
h_turbo=false;    has turbo.json && h_turbo=true
h_nx=false;       has nx.json && h_nx=true
h_lerna=false;    has lerna.json && h_lerna=true
h_pnpm_ws=false;  has pnpm-workspace.yaml && h_pnpm_ws=true

# Database / ORM
h_prisma=false;   has_any schema.prisma prisma/schema.prisma && h_prisma=true
h_drizzle=false;  $h_pkg && grep -q '"drizzle-orm"' package.json 2>/dev/null && h_drizzle=true

# GraphQL
h_graphql=false;  { glob "*.graphql" || has schema.graphql || has_any .graphqlconfig .graphqlrc; } && h_graphql=true

# ── Category scoring ─────────────────────────────────────────────

# Frontend signals
fw_score=0
$h_vue      && { fw_score=$((fw_score+3)); fw_signal="Vue"; }
$h_react    && { fw_score=$((fw_score+3)); fw_signal="React"; }
$h_next     && { fw_score=$((fw_score+4)); fw_signal="Next.js"; }
$h_nuxt     && { fw_score=$((fw_score+4)); fw_signal="Nuxt"; }
$h_svelte   && { fw_score=$((fw_score+3)); fw_signal="Svelte"; }
$h_angular  && { fw_score=$((fw_score+4)); fw_signal="Angular"; }
$h_astro    && { fw_score=$((fw_score+3)); fw_signal="Astro"; }
$h_remix    && { fw_score=$((fw_score+3)); fw_signal="Remix"; }
$h_solid    && { fw_score=$((fw_score+2)); fw_signal="SolidJS"; }
$h_vite     && fw_score=$((fw_score+1))
$h_webpack  && fw_score=$((fw_score+1))
$h_tailwind && fw_score=$((fw_score+1))
$h_pkg      && { has_any src/ components/ pages/ && fw_score=$((fw_score+2)); }

# Backend signals
be_score=0
$h_go       && { be_score=$((be_score+4)); be_signal="Go"; }
$h_maven    && { be_score=$((be_score+3)); be_signal="Java (Maven)"; }
$h_gradle   && { be_score=$((be_score+3)); [ -z "$be_signal" ] && be_signal="Java (Gradle)"; }
$h_pyproj   && { be_score=$((be_score+3)); be_signal="Python"; }
$h_py_req   && { [ $be_score -lt 2 ] && be_score=$((be_score+2)); [ -z "$be_signal" ] && be_signal="Python"; }
$h_cargo    && { be_score=$((be_score+4)); be_signal="Rust"; }
$h_gemfile  && { be_score=$((be_score+2)); be_signal="Ruby"; }
$h_rails    && { be_score=$((be_score+4)); be_signal="Rails"; }
$h_composer && { be_score=$((be_score+3)); be_signal="PHP"; }
$h_laravel  && { be_score=$((be_score+4)); be_signal="Laravel"; }
$h_symfony  && { be_score=$((be_score+3)); be_signal="Symfony"; }
$h_elixir   && { be_score=$((be_score+3)); be_signal="Elixir"; }
$h_dotnet   && { be_score=$((be_score+3)); be_signal=".NET"; }
$h_express  && { be_score=$((be_score+2)); [ -z "$be_signal" ] && be_signal="Express"; }
$h_fastify  && { be_score=$((be_score+2)); [ -z "$be_signal" ] && be_signal="Fastify"; }
$h_nestjs   && { be_score=$((be_score+3)); be_signal="NestJS"; }
$h_koa      && { be_score=$((be_score+2)); [ -z "$be_signal" ] && be_signal="Koa"; }
$h_hono     && { be_score=$((be_score+2)); [ -z "$be_signal" ] && be_signal="Hono"; }

# Mobile signals
mo_score=0
$h_android       && { mo_score=$((mo_score+4)); mo_signal="Android"; }
$h_ios           && { mo_score=$((mo_score+4)); mo_signal="iOS"; }
$h_flutter       && { mo_score=$((mo_score+4)); mo_signal="Flutter"; }
$h_react_native  && { mo_score=$((mo_score+3)); mo_signal="React Native"; }
$h_expo          && { mo_score=$((mo_score+3)); mo_signal="Expo"; }

# Data science
ds_score=0
$h_notebook && ds_score=$((ds_score+3))
$h_torch    && ds_score=$((ds_score+3))

# DevOps
do_score=0
$h_docker    && do_score=$((do_score+2))
$h_k8s       && do_score=$((do_score+3))
$h_terraform && do_score=$((do_score+3))
$h_ansible   && do_score=$((do_score+2))

# Static site
ss_score=0
$h_hugo       && ss_score=$((ss_score+4))
$h_jekyll     && ss_score=$((ss_score+3))
$h_gatsby     && ss_score=$((ss_score+3))
$h_vitepress  && ss_score=$((ss_score+2))
$h_docusaurus && ss_score=$((ss_score+2))

# ── Monorepo scanning ────────────────────────────────────────────
# If nothing found at root, check 1-level subdirectories
if [ $fw_score -eq 0 ] && [ $be_score -eq 0 ] && [ $mo_score -eq 0 ] && [ $ds_score -eq 0 ] && [ $do_score -eq 0 ] && [ $ss_score -eq 0 ]; then
  has_subs=false
  for sub in */; do
    sub="${sub%/}"
    [ "$sub" = "node_modules" ] && continue
    [ "$sub" = ".git" ] && continue
    [ -d "$sub" ] || continue
    sub_found=0
    # Quick check for project files in subdirectory
    has "$sub/package.json"   && sub_found=1
    has "$sub/go.mod"         && sub_found=1
    has "$sub/pom.xml"        && sub_found=1
    has "$sub/Cargo.toml"     && sub_found=1
    has "$sub/pyproject.toml" && sub_found=1
    has "$sub/composer.json"  && sub_found=1
    has "$sub/Gemfile"        && sub_found=1
    has "$sub/mix.exs"        && sub_found=1
    has "$sub/pubspec.yaml"   && sub_found=1
    if [ $sub_found -gt 0 ]; then
      echo "  (monorepo sub-project: $sub)"
      # Recurse into first found sub-project
      if [ "${ROOT}" = "." ]; then
        exec bash "$0" "./$sub"
      else
        exec bash "$0" "$ROOT/$sub"
      fi
      exit 0
    fi
  done
fi

# ── Decision ─────────────────────────────────────────────────────

type_label="未知"; identity="通用高级软件工程师"; cat="unknown"

if [ $fw_score -ge 2 ] && [ $be_score -ge 2 ]; then
  cat="fullstack"; type_label="全栈"; identity="高级全栈开发工程师"
elif [ $fw_score -ge 2 ]; then
  cat="frontend"; type_label="前端"; identity="高级前端开发工程师"
elif [ $be_score -ge 2 ]; then
  cat="backend"; type_label="后端"; identity="高级后端开发工程师"
elif [ $mo_score -ge 2 ]; then
  cat="mobile"; type_label="移动端"; identity="高级移动端开发工程师"
elif [ $ds_score -ge 2 ]; then
  cat="datascience"; type_label="数据科学"; identity="高级数据科学工程师"
elif [ $do_score -ge 3 ] && [ $fw_score -eq 0 ] && [ $be_score -eq 0 ]; then
  cat="devops"; type_label="DevOps"; identity="高级 DevOps 工程师"
elif [ $ss_score -ge 3 ]; then
  cat="static"; type_label="静态站点"; identity="前端开发工程师"
elif $h_k8s || $h_terraform; then
  cat="infra"; type_label="基础设施"; identity="高级 DevOps 工程师"
elif $h_ci; then
  cat="pipeline"; type_label="CI/CD"; identity="DevOps 工程师"
fi

# ── Framework name ────────────────────────────────────────────────

framework=""
if [ "$cat" = "fullstack" ]; then
  [ -n "$fw_signal" ] && framework="$fw_signal"
  [ -n "$be_signal" ] && framework="${framework:+$framework + }$be_signal"
elif [ "$cat" = "frontend" ]; then
  framework="$fw_signal"
  [ -z "$framework" ] && $h_pkg && framework="Node.js"
elif [ "$cat" = "backend" ]; then
  framework="$be_signal"
elif [ "$cat" = "mobile" ]; then
  framework="$mo_signal"
elif [ "$cat" = "static" ]; then
  $h_hugo       && framework="Hugo"
  $h_jekyll     && framework="Jekyll"
  $h_gatsby     && framework="Gatsby"
  $h_vitepress  && framework="VitePress"
  $h_docusaurus && framework="Docusaurus"
fi
[ -z "$framework" ] && framework="无"

# ── Language ──────────────────────────────────────────────────────

lang=""
$h_ts      && lang="${lang:+$lang, }TypeScript"
$h_go      && lang="${lang:+$lang, }Go"
$h_maven   && lang="${lang:+$lang, }Java"
[ -z "$lang" ] && $h_gradle && $h_kotlin && lang="Kotlin"
[ -z "$lang" ] && $h_gradle && ! $h_kotlin && lang="Java"
$h_pyproj  && lang="${lang:+$lang, }Python"
[ -z "$lang" ] && $h_py_req && lang="Python"
$h_cargo   && lang="${lang:+$lang, }Rust"
$h_gemfile && lang="${lang:+$lang, }Ruby"
$h_composer && lang="${lang:+$lang, }PHP"
$h_dotnet  && lang="${lang:+$lang, }C#"
$h_swift   && lang="${lang:+$lang, }Swift"
$h_flutter && lang="${lang:+$lang, }Dart"
$h_dart    && lang="${lang:+$lang, }Dart"
$h_elixir  && lang="${lang:+$lang, }Elixir"
$h_deno    && lang="${lang:+$lang, }TypeScript"
$h_bun     && [ -z "$lang" ] && $h_pkg && lang="JavaScript"
[ -z "$lang" ] && $h_pkg && lang="JavaScript"
[ -z "$lang" ] && lang="未知"

# ── Toolchain extras ──────────────────────────────────────────────

extras=""
$h_vite        && extras="$extras, Vite"
$h_webpack     && extras="$extras, Webpack"
$h_tailwind    && extras="$extras, Tailwind"
$h_poetry      && extras="$extras, Poetry"
$h_turbo       && extras="$extras, Turborepo"
$h_nx          && extras="$extras, Nx"
$h_prisma      && extras="$extras, Prisma"
$h_drizzle     && extras="$extras, Drizzle"
$h_graphql     && extras="$extras, GraphQL"
$h_docker      && extras="$extras, Docker"
$h_vitest      && extras="$extras, Vitest"
$h_jest        && extras="$extras, Jest"
$h_spring      && extras="$extras, Spring Boot"
$h_gin         && extras="$extras, Gin"
$h_echo        && extras="$extras, Echo"
$h_fiber       && extras="$extras, Fiber"
$h_actix       && extras="$extras, Actix"
$h_axum        && extras="$extras, Axum"
$h_phoenix     && extras="$extras, Phoenix"
$h_electron    && extras="$extras, Electron"
$h_tauri       && extras="$extras, Tauri"
extras="${extras#, }"

# ── Clues list ────────────────────────────────────────────────────

clues=""
$h_pkg        && clues="$clues, package.json"
$h_ts         && clues="$clues, tsconfig.json"
has src/      && clues="$clues, src/"
$h_go         && clues="$clues, go.mod"
$h_maven      && clues="$clues, pom.xml"
$h_gradle     && clues="$clues, build.gradle"
$h_pyproj     && clues="$clues, pyproject.toml"
$h_py_req     && clues="$clues, requirements.txt"
$h_cargo      && clues="$clues, Cargo.toml"
$h_composer   && clues="$clues, composer.json"
$h_gemfile    && clues="$clues, Gemfile"
$h_rails      && clues="$clues, config/routes.rb"
$h_elixir     && clues="$clues, mix.exs"
$h_dotnet     && clues="$clues, .csproj/.sln"
$h_swift      && clues="$clues, .xcodeproj"
$h_flutter    && clues="$clues, pubspec.yaml"
$h_android    && clues="$clues, AndroidManifest.xml"
$h_docker     && clues="$clues, Dockerfile"
$h_notebook   && clues="$clues, notebooks/"
$h_hugo       && clues="$clues, config.toml"
clues="${clues#, }"

# ── Output ────────────────────────────────────────────────────────

cat <<EOF
## 项目类型识别
- **类型**：$type_label
- **框架**：$framework
- **语言**：$lang
- **身份**：$identity
EOF

[ -n "$extras" ] && echo "- **工具链**：$extras"
echo "- **判断依据**：${clues:-无}"
