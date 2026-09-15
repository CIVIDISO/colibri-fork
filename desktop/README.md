# colibrì desktop

Tauri v2 shell for the shared React interface in `../web`.

This directory intentionally contains no second frontend. During development,
Tauri starts the Vite server from `web/`; release builds package `web/dist`.

## Development

The shared web UI landed in PR #23 and is already part of `main`. From the
repository root, install its dependencies and start the desktop shell:

```sh
cd web
npm ci
cd ../desktop
cargo install tauri-cli --version "^2.0.0" --locked
cargo tauri dev
```

The application connects to an OpenAI-compatible server configured in the UI.
Bundling the inference engine or managing its process is intentionally deferred:
the model is hundreds of gigabytes and must remain an external, user-selected
resource rather than an opaque application sidecar.

## Start on Windows

From a source checkout, run `start-colibri.cmd`. It starts Ollama, the Colibri
deep-model dashboard, the project workbench, and the native desktop shell. Set
`COLIBRI_MODEL` and `COLIBRI_PROJECT` before launching when the model or target
project lives somewhere else.

To make startup automatic, run once from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-colibri-startup.ps1
```

The startup shortcut is opt-in and can be removed with `-Remove`.

This first desktop increment only packages the existing UI in a native window.
It does not change the web application, start the inference engine, download
models, or add native filesystem and process permissions.

## Validation

```sh
cargo fmt --manifest-path src-tauri/Cargo.toml --check
cargo check --manifest-path src-tauri/Cargo.toml
```
