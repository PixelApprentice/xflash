# Implementation Plan: Cross-Platform Hosting & Distribution Pipeline (`npx`, PyPI, Standalone Offline Binaries)

## Overview

This plan defines the end-to-end execution for hosting and distributing **Xflash** so that any user in the future can execute or install it instantly via `npx @pixelapprentice/xflash` (or globally via `npm i -g @pixelapprentice/xflash`), accessing commands like `xflash` and `xflash tui` directly from their terminal at any time.

Crucially, **Xflash is strictly offline-first**: it performs zero telemetry, zero analytics, zero external network queries during hardware diagnosis, and has zero third-party runtime dependencies (stdlib-only). The distribution architecture decouples the core diagnostic engine from the packaging and hosting channels (npm, PyPI, GitHub Releases, and USB kits), ensuring the offline integrity of the diagnostic tool remains inviolate.

---

## Architecture Decisions

### 1. Dual-Tier Distribution Architecture (Separation of Concerns)
To fulfill the requirement to *"host offline version of this application separately separate from this one"*:
- **Core Engine Repository (`Xflesh` / `xflash-core`)**: Maintains the pure diagnostic algorithms, hardware collectors, test fixtures, TUI, and local web dashboard. Contains zero npm or node dependencies.
- **Distribution Channel Layer**:
  - **npm Registry Channel (`@pixelapprentice/xflash`)**: A thin, cross-platform Node.js wrapper package published to npmjs.org. It bundles the pure-Python `xflash` distribution directly within the package (`python/` payload), so runtime execution is 100% offline with zero additional network fetches.
  - **PyPI Channel (`xflash`)**: Python native distribution (`pip install xflash`, `uvx xflash`, `pipx run xflash`).
  - **Standalone Binary Releases (GitHub Releases)**: Standalone single-file executables (`xflash-linux-x86_64`, `xflash-windows-x86_64.exe`) compiled via PyInstaller, plus zero-install portable USB zip packages for air-gapped field inspections.

### 2. Node.js Launcher Bridge (`bin/xflash.js`)
- Standard-library-only Node script (no `node_modules` dependencies) supporting Node >= 16.
- Detects the best available Python 3.10+ interpreter on the host machine:
  - Windows: probes `py -3`, `python3`, `python`, and known registry/AppData paths.
  - Linux / macOS: probes `python3`, `python`.
- Forwards terminal stdio (`stdio: 'inherit'`) and preserves raw terminal modes, ANSI truecolor, and interactive keyboard input (`msvcrt` on Windows, `termios` on Unix) so that `xflash tui` feels native.
- Transmits exit codes and handles `SIGINT`/`SIGTERM` gracefully.
- If no compatible Python 3 is found, displays an actionable, friendly diagnostic pointing the user to Python installation or the zero-python standalone binary.

### 3. Packaging & Offline Integrity
- All web assets (CSS/JS) and diagnostic rules are bundled inside the package at build time.
- The npm package bundles the Python source tree inside `python/` directory. Running `npx @pixelapprentice/xflash` executes locally from the npm cache or global install without contacting any network service.
- Package naming: npm requires lowercase package names; hence `@pixelapprentice/xflash`.

---

## Task List

### Phase 1: Foundation & Packaging Separation
- [ ] Task 1: Create reproducible Python wheel/source distribution packaging script without dev fixtures
- [ ] Task 2: Implement CLI and TUI process contract test for stdio passthrough, terminal raw mode, and exit codes

### Checkpoint: Foundation & Packaging
- [ ] Core package builds clean wheel (< 1MB) containing all assets and zero test fixtures
- [ ] Process contract tests pass with 100% exit code and signal propagation

### Phase 2: npm Package Bridge & Cross-Platform Node Runner
- [ ] Task 3: Develop standard-library Node.js launcher (`bin/xflash.js`) with multi-platform Python discovery
- [ ] Task 4: Configure `package.json` and package metadata for `@pixelapprentice/xflash`
- [ ] Task 5: Implement automated test suite for npm wrapper runner (Windows & Linux mock tests, npx dry-run)

### Checkpoint: npm Runner Verification
- [ ] `npm pack` produces clean tarball under 600KB
- [ ] `npx . tui --once help` and `npx . scan --format json` execute successfully through the Node bridge
- [ ] Missing Python 3 gracefully caught with informative message

### Phase 3: Standalone Offline Hosting & CI/CD Release Automation
- [ ] Task 6: Implement GitHub Actions automated PyInstaller release workflow for Linux ELF and Windows EXE binaries
- [ ] Task 7: Implement automated GitHub Actions publishing workflow for `@pixelapprentice/xflash` to npm registry
- [ ] Task 8: Implement portable offline USB bundle builder script and zip packaging

### Checkpoint: Release Pipeline
- [ ] GitHub Actions release workflow successfully generates signed/checksummed binaries
- [ ] Dry-run npm publish passes npm audit and packing verification
- [ ] Portable USB bundle unpacks and runs offline on Windows and Linux

### Phase 4: Documentation, Verification, & User Guides
- [ ] Task 9: Author comprehensive distribution and hosting guide (`docs/distribution.md`)
- [ ] Task 10: Update project `README.md` and user-facing installation instructions with `npx` and global CLI usage

### Checkpoint: Complete
- [ ] All acceptance criteria met across all 10 tasks
- [ ] End-to-end user workflows (`npx @pixelapprentice/xflash`, `npm i -g`, `xflash tui`) verified and documented

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Host machine has Node.js installed but lacks Python 3.10+ | Medium | `bin/xflash.js` detects Python version on launch; if missing, displays clear instructions and provides direct links to the standalone single-binary release. |
| Terminal raw mode or special keys broken when spawned from Node child_process | High | Use `child_process.spawn(..., { stdio: 'inherit' })`. Write a dedicated process test verifying interactive terminal escape codes and Windows console handling. |
| npm registry case sensitivity (`@PixelApprentice` vs `@pixelapprentice`) | Low | npm requires strictly lowercase package scope/names. Configure `"name": "@pixelapprentice/xflash"` in `package.json`. |
| Unintended network dependencies creeping into release artifacts | High | Strict offline audit rule: all release bundles are verified with network disabled; `xflash` runtime tests enforce zero-socket policy. |
| Large binary file size if bundling full Python runtime inside npm package | Medium | Keep npm package ultra-lightweight (~500KB) by bundling the pure-Python source and utilizing host Python, while providing PyInstaller single-file binaries separately on GitHub Releases for zero-Python systems. |

---

## Open Questions

1. **Repository Structure**: Would you prefer the npm package source (`package.json`, `bin/xflash.js`) to live in a dedicated `distribution/npm/` folder within this repository, or in a completely separate Git repository (e.g. `PixelApprentice/xflash-npm`)?
2. **Zero-Python npm Fallback**: Should the npm package rely on host Python 3 (lightweight, ~500KB download), or should it optionally download/include a standalone binary for users who don't have Python installed?
3. **Global npm command name**: On global install (`npm install -g @pixelapprentice/xflash`), the binary alias will be `xflash`. Should we also alias `xflash-tui` for direct shortcut access?
