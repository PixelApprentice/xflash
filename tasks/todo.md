# Tasks: Cross-Platform Hosting & Distribution Pipeline (`npx`, PyPI, Standalone Offline Binaries)

## Phase 1: Foundation & Packaging Separation

### Task 1: Create reproducible Python wheel/source distribution packaging script without dev fixtures
**Description:** Build a clean packaging pipeline that produces lightweight, pure distribution packages (wheel and sdist) containing only production runtime code (`xflash` package + static web assets) and stripping out test files, development mocks, and scratch data.

**Acceptance criteria:**
- [ ] Packaging script or config excludes `tests/`, `research/`, `aegis_data/`, and development artifacts.
- [ ] Resulting wheel contains all required static web dashboard assets (`xflash/web/static/*`) and TUI components.
- [ ] Output wheel size is under 1MB.

**Verification:**
- [ ] Tests pass: `python3 -m unittest discover -s tests -v`
- [ ] Build succeeds: `python3 -m pip install build && python3 -m build --wheel --sdist`
- [ ] Manual check: Inspect wheel contents using `unzip -l dist/*.whl` to confirm absence of tests/fixtures.

**Dependencies:** None

**Files likely touched:**
- `pyproject.toml`
- `tools/package_release.py`

**Estimated scope:** Small (1-2 files)

---

### Task 2: Implement CLI and TUI process contract test for stdio passthrough, terminal raw mode, and exit codes
**Description:** Implement unit and integration tests verifying that `xflash` behaves as a well-behaved child process: preserving exit codes, forwarding signals (SIGINT/SIGTERM), supporting non-interactive output piping, and validating stdin/stdout behavior when spawned by external process wrappers.

**Acceptance criteria:**
- [ ] Test verifies that non-zero exit codes (e.g. invalid arguments or failure states) are correctly propagated to calling processes.
- [ ] Test verifies `--plain` and non-TTY execution paths without throwing broken pipe or terminal mode errors.
- [ ] Test validates TUI `--once rules` and `--once help` rendering through subprocess execution.

**Verification:**
- [ ] Tests pass: `python3 -m unittest tests/test_process_contract.py -v`
- [ ] Build succeeds: `python3 run.py tui --once help` returns exit code 0

**Dependencies:** None

**Files likely touched:**
- `tests/test_process_contract.py`
- `src/xflash/cli.py`

**Estimated scope:** Small (1-2 files)

---

## Checkpoint: Foundation & Packaging
- [ ] All unit and process contract tests pass (`python3 -m unittest discover -s tests -v`).
- [ ] Python wheel builds cleanly without packaging extraneous test data.
- [ ] CLI exit codes and stdio streams operate reliably in subprocess environments.

---

## Phase 2: npm Package Bridge & Cross-Platform Node Runner

### Task 3: Develop standard-library Node.js launcher (`bin/xflash.js`) with multi-platform Python discovery
**Description:** Implement the standalone, zero-dependency Node.js executable script (`bin/xflash.js`) that serves as the entry point for `npx @pixelapprentice/xflash` and globally installed `xflash`. It automatically detects Python 3.10+ across Windows (`py -3`, `python3`, `python`, AppData paths) and Unix/macOS (`python3`, `python`), configures `PYTHONPATH` to the bundled `python/` directory, spawns the process with inherited stdio, and handles terminal mode/signals cleanly.

**Acceptance criteria:**
- [ ] `bin/xflash.js` is written in pure vanilla Node.js (uses only `child_process`, `fs`, `path`, `os`).
- [ ] Probes and discovers Python 3.10+ across Windows, Linux, and macOS without crashing.
- [ ] Forwards all command-line arguments (e.g. `xflash tui`, `xflash scan --format json`) seamlessly.
- [ ] Preserves `stdio: 'inherit'` so that ANSI colors and interactive TUI keystrokes work natively.
- [ ] Emits an actionable, clear error message with download links if Python 3.10+ is absent.

**Verification:**
- [ ] Tests pass: `node bin/xflash.js --help`
- [ ] Manual check: `node bin/xflash.js tui --once help` renders the help screen with colors intact.

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `distribution/npm/bin/xflash.js`

**Estimated scope:** Medium (1-2 files)

---

### Task 4: Configure `package.json` and package metadata for `@pixelapprentice/xflash`
**Description:** Create the complete npm packaging manifest and metadata for `@pixelapprentice/xflash`, specifying binary entry points (`"bin": { "xflash": "./bin/xflash.js" }`), license, repository links, engines (`node >= 16`), and file inclusion rules (`bin/`, `python/`, `README.md`, `LICENSE`).

**Acceptance criteria:**
- [ ] Package name is strictly valid for npm registry (`@pixelapprentice/xflash`).
- [ ] `"bin"` correctly maps `xflash` to `./bin/xflash.js`.
- [ ] `"files"` whitelist strictly bundles `bin/`, `python/`, `README.md`, `LICENSE`, excluding any build leftovers.
- [ ] `npm pack --dry-run` confirms clean, compact package structure.

**Verification:**
- [ ] Build succeeds: `cd distribution/npm && npm pack --dry-run`
- [ ] Manual check: Inspect tarball manifest to verify that all necessary Python modules are included.

**Dependencies:** Task 3

**Files likely touched:**
- `distribution/npm/package.json`
- `distribution/npm/README.md`
- `distribution/npm/.npmignore`

**Estimated scope:** Small (2-3 files)

---

### Task 5: Implement automated test suite for npm wrapper runner (Windows & Linux mock tests, npx dry-run)
**Description:** Write an automated test suite that executes `bin/xflash.js` via Node.js to verify argument pass-through, version detection, subcommands (`tui`, `scan`, `serve`, `analyze`), exit code transmission, and missing Python error reporting.

**Acceptance criteria:**
- [ ] Tests run `node bin/xflash.js` across multiple subcommands and verify matching exit codes and stdout.
- [ ] Test simulates missing Python environment (via PATH override) and asserts that the user receives an informative, actionable message.
- [ ] Test validates that global executable symlinks (`npm link` simulation) execute as expected.

**Verification:**
- [ ] Tests pass: `npm test` inside `distribution/npm` or `node tests/test_npm_runner.js`
- [ ] Manual check: `npx . --help` executed from local npm package directory.

**Dependencies:** Task 3, Task 4

**Files likely touched:**
- `distribution/npm/test/runner.test.js`

**Estimated scope:** Small (1-2 files)

---

## Checkpoint: npm Runner Verification
- [ ] Node runner executes Python `xflash` cleanly on Linux and Windows.
- [ ] `npm pack` creates a self-contained tarball under 600KB containing pure-Python core.
- [ ] Full automated test suite passes for the Node bridge.

---

## Phase 3: Standalone Offline Hosting & CI/CD Release Automation

### Task 6: Implement GitHub Actions automated PyInstaller release workflow for Linux ELF and Windows EXE binaries
**Description:** Configure a multi-platform GitHub Actions release workflow that builds standalone, zero-dependency single-file executables for Linux (`xflash-linux-x86_64`) and Windows (`xflash-windows-x86_64.exe`) using PyInstaller, generates SHA256 checksums, and attaches them to GitHub Releases.

**Acceptance criteria:**
- [ ] Workflow matrix builds binaries on `ubuntu-latest` and `windows-latest`.
- [ ] Windows binary embeds version metadata and console execution flags.
- [ ] Generates `SHA256SUMS.txt` for all release assets.
- [ ] Executables run without requiring Python or Node to be installed on target systems.

**Verification:**
- [ ] Build succeeds: Test run on GitHub Actions or local `python3 tools/build_standalone.py --all`
- [ ] Manual check: `dist/xflash --version` executes properly from standalone binary.

**Dependencies:** Task 1

**Files likely touched:**
- `.github/workflows/release-binaries.yml`
- `tools/build_standalone.py`

**Estimated scope:** Medium (2-3 files)

---

### Task 7: Implement automated GitHub Actions publishing workflow for `@pixelapprentice/xflash` to npm registry
**Description:** Create a GitHub Actions workflow that stages the verified Python source tree into `distribution/npm/python/`, verifies the package via `npm pack`, and publishes `@pixelapprentice/xflash` to npmjs.org on release tags with provenance.

**Acceptance criteria:**
- [ ] Workflow securely consumes `NPM_TOKEN` secret.
- [ ] Automatically synchronizes version from `pyproject.toml` to `package.json`.
- [ ] Verifies offline package integrity before publishing.
- [ ] Supports automated or manual dispatch release triggers.

**Verification:**
- [ ] Build succeeds: Dry run GitHub Actions workflow or local release packaging script.
- [ ] Manual check: `npm pack` produces tarball with valid checksum and correct metadata.

**Dependencies:** Task 4, Task 5

**Files likely touched:**
- `.github/workflows/publish-npm.yml`
- `tools/sync_npm_package.py`

**Estimated scope:** Medium (2-3 files)

---

### Task 8: Implement portable offline USB bundle builder script and zip packaging
**Description:** Automate the generation of the standalone "Offline Shop Inspection Kit" USB bundle (`xflash-usb-portable.zip`), containing the ready-to-run Windows launcher (`start-xflash.bat`), Linux launcher (`start-xflash.sh`), `autorun.inf`, standalone executables, and zero-trace portable configuration (`.portable`).

**Acceptance criteria:**
- [ ] Packaging script bundles launcher scripts, documentation, and standalone executables into a clean zip archive.
- [ ] Extracted archive runs immediately when copied to any USB thumb drive without internet access.
- [ ] Includes `docs/offline-shop-inspection-guide.md` and offline README.

**Verification:**
- [ ] Build succeeds: `python3 tools/prepare_offline_usb.py --bundle-zip`
- [ ] Manual check: Extract zip to temporary location and test launch.

**Dependencies:** Task 6

**Files likely touched:**
- `tools/prepare_offline_usb.py`

**Estimated scope:** Small (1-2 files)

---

## Checkpoint: Release Pipeline
- [ ] GitHub Actions workflows defined and validated with syntax linting.
- [ ] Standalone binaries and USB bundles compile deterministically with SHA256 checksums.
- [ ] Automated npm packaging script syncs versions and packages without errors.

---

## Phase 4: Documentation, Verification, & User Guides

### Task 9: Author comprehensive distribution and hosting guide (`docs/distribution.md`)
**Description:** Document the complete distribution architecture, hosting locations, release procedures, token configuration, local development testing with `npm link` / `npx`, and troubleshooting guide for offline environments.

**Acceptance criteria:**
- [ ] Explains how `npx @pixelapprentice/xflash` works under the hood.
- [ ] Details step-by-step instructions for publishing releases to npm, PyPI, and GitHub Releases.
- [ ] Outlines security and offline integrity guarantees (zero telemetry, zero phone-homes).

**Verification:**
- [ ] Manual check: Review document for technical clarity, completeness, and adherence to project rules.

**Dependencies:** Task 7, Task 8

**Files likely touched:**
- `docs/distribution.md`

**Estimated scope:** Small (1 file)

---

### Task 10: Update main `README.md` and user-facing installation instructions with `npx` and global CLI usage
**Description:** Update the primary `README.md` with modern, intuitive quickstart commands showcasing instant execution via `npx @pixelapprentice/xflash`, global installation via `npm i -g @pixelapprentice/xflash`, Python native execution (`pipx run xflash` / `uvx xflash`), and USB portable download links.

**Acceptance criteria:**
- [ ] Quickstart section prominently features `npx @pixelapprentice/xflash` and `npx @pixelapprentice/xflash tui`.
- [ ] Documents global `xflash` command usage after `npm i -g @pixelapprentice/xflash`.
- [ ] Maintains clear guidance on offline-first operation and privacy guarantees.

**Verification:**
- [ ] Manual check: Read formatted markdown and verify all links and commands.

**Dependencies:** Task 9

**Files likely touched:**
- `README.md`

**Estimated scope:** Small (1 file)

---

## Checkpoint: Complete
- [ ] All 10 tasks completed with passing acceptance criteria and verification steps.
- [ ] `npx @pixelapprentice/xflash` and `npm i -g @pixelapprentice/xflash` ready for production deployment.
- [ ] Standalone offline binaries, USB bundle, and documentation fully prepared.
