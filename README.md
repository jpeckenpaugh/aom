# Age of Mycology — web demo

Playable browser build of *Age of Mycology*, served from GitHub Pages:

**https://jpeckenpaugh.github.io/aom/**

## About this repo

This repository holds the game's **runtime build inputs** — the game package
(`AoM/`: Python source plus the compiled runtime assets under `AoM/assets/`) and
the pinned pygbag build configuration. It contains no raw/authoring assets,
Blender/GLB source, render tooling, or tests; those live in the private
`aom-internal` repository.

## How the demo is built

The [`pages.yml`](.github/workflows/pages.yml) GitHub Action builds the bundle
**server-side** with the pinned toolchain (`pygbag==0.9.3`, Python 3.12) and
deploys the generated `web/` output to GitHub Pages via
`actions/upload-pages-artifact` + `actions/deploy-pages`.

The large `aom.tar.gz` bundle is produced in CI and deployed as a Pages artifact;
it is **never committed to git**. See ADR-002 for the decision record.

## Local build

```bash
python -m pip install pygbag==0.9.3 -r requirements.txt
cd AoM
python -m pygbag --build --template default-browserfs.tmpl \
  --PYBUILD 3.12 --width 1280 --height 720 .
# output: AoM/build/web/
```
