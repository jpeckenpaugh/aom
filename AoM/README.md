# AoM Package

This is the playable Age of Mycology package. Run commands from the repository root through `scripts/`:

```bash
../scripts/run-native.sh
../scripts/run-pygbag-docker.sh
../scripts/test-native.sh
```

Runtime assets live in `assets/`. Source models, renders, and concept art live in `../source_assets/` so they are not shipped in the browser bundle.

See `../docs/` for architecture, game design, asset pipeline, and browser/Pygbag notes.
