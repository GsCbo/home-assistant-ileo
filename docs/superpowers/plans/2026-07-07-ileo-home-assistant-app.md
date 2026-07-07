# ILEO Home Assistant App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the repository from a HACS custom integration to a Home Assistant Supervisor App repository that syncs ILEO water readings into Home Assistant Energy statistics.

**Architecture:** Replace `custom_components/ileo` with an add-on folder `ileo/` containing app metadata, Docker runtime files, and a Python worker. The Python worker reads `/data/options.json`, reuses the hardened ILEO CSV parsing/login behavior, writes Home Assistant state/statistics through the Supervisor-proxied Core API, and loops on the configured interval.

**Tech Stack:** Home Assistant Supervisor Apps, Python 3, `aiohttp`, Docker, YAML app metadata, pytest unit tests.

---

## File Structure

- Create `repository.yaml`: top-level Home Assistant app repository metadata.
- Create `ileo/config.yaml`: Supervisor app metadata and configuration schema.
- Create `ileo/Dockerfile`: Python app image based on Home Assistant base image.
- Create `ileo/run.sh`: container entrypoint.
- Create `ileo/requirements.txt`: app runtime Python dependencies.
- Create `ileo/README.md`: app-specific installation and configuration docs.
- Create `ileo/app/ileo_client.py`: ILEO HTTP client and CSV parser, ported from the current integration.
- Create `ileo/app/config.py`: `/data/options.json` parser and validation.
- Create `ileo/app/ha_api.py`: Home Assistant Core API client through Supervisor.
- Create `ileo/app/statistics.py`: water statistic payload generation and import orchestration.
- Create `ileo/app/main.py`: runtime loop and mode handling.
- Modify `README.md`: repository-level app installation docs.
- Delete `custom_components/ileo/**`, `hacs.json`, and integration-only tests.
- Keep focused tests for parser/config/statistics generation under `tests/`.

## Tasks

### Task 1: Add App Repository Skeleton

**Files:**
- Create: `repository.yaml`
- Create: `ileo/config.yaml`
- Create: `ileo/Dockerfile`
- Create: `ileo/run.sh`
- Create: `ileo/requirements.txt`
- Create: `ileo/README.md`
- Modify: `README.md`

- [ ] Create `repository.yaml` with repository name and URL.
- [ ] Create `ileo/config.yaml` with app name, version, slug `ileo`, arch list, `startup: application`, `boot: auto`, `homeassistant_api: true`, options and schema for `username`, `password`, `start_date`, `sync_interval_hours`, and `mode`.
- [ ] Create `ileo/Dockerfile` using `ghcr.io/home-assistant/base:latest`, installing Python and app requirements, copying `run.sh` and `app/`.
- [ ] Create `ileo/run.sh` that runs `python3 -m app.main`.
- [ ] Create app and root README docs for Apps > Store > Repositories installation.
- [ ] Run YAML/JSON/text validation where available.
- [ ] Commit: `Add ILEO Home Assistant app skeleton`.

### Task 2: Port ILEO Client And Configuration

**Files:**
- Create: `ileo/app/__init__.py`
- Create: `ileo/app/ileo_client.py`
- Create: `ileo/app/config.py`
- Create/modify: `tests/test_ileo_client.py`
- Create: `tests/test_app_config.py`
- Delete/replace: `tests/test_api.py`

- [ ] Port `IleoReading`, parser, login form validation, hidden input handling, and CSV export client from `custom_components/ileo/api.py` into `ileo/app/ileo_client.py`.
- [ ] Implement `AppConfig` in `config.py` with strict `YYYY-MM-DD`, positive interval, and `mode in {"sync", "reset"}`.
- [ ] Update parser/client tests to import `ileo.app.ileo_client` directly.
- [ ] Add config validation tests.
- [ ] Run Python compilation.
- [ ] Commit: `Port ILEO client to app runtime`.

### Task 3: Add Home Assistant API And Statistics Writer

**Files:**
- Create: `ileo/app/ha_api.py`
- Create: `ileo/app/statistics.py`
- Create: `tests/test_statistics.py`

- [ ] Implement `HomeAssistantClient` using `SUPERVISOR_TOKEN` and `http://supervisor/core/api`.
- [ ] Add methods for posting states and importing statistics.
- [ ] Implement water index state payload with `device_class: water`, `state_class: total_increasing`, unit `L`.
- [ ] Implement statistic payload generation from readings with stable timestamps and duplicate filtering hooks.
- [ ] Add tests for state attributes and statistic payload shape.
- [ ] Run Python compilation.
- [ ] Commit: `Add Home Assistant statistics writer`.

### Task 4: Add Runtime Loop

**Files:**
- Create: `ileo/app/main.py`
- Create: `tests/test_runtime.py`

- [ ] Implement startup config loading from `/data/options.json`.
- [ ] Implement `sync_once`: fetch readings, publish current water index state, import statistics, persist latest imported reading metadata in `/data/last_sync.json`.
- [ ] Implement `mode: reset` as a non-destructive log-only action for v1.
- [ ] Implement loop sleep based on `sync_interval_hours`.
- [ ] Add tests for no-new-reading behavior and sync orchestration with fake clients.
- [ ] Run Python compilation.
- [ ] Commit: `Add ILEO app runtime loop`.

### Task 5: Remove Custom Integration Packaging

**Files:**
- Delete: `custom_components/ileo/**`
- Delete: `hacs.json`
- Delete/adjust: `tests/test_config_flow.py`, `tests/test_coordinator.py`, `tests/test_sensor.py`, `tests/conftest.py`
- Modify: `requirements-dev.txt`

- [ ] Remove the HACS custom integration files.
- [ ] Remove Home Assistant custom component tests that no longer apply.
- [ ] Keep only app runtime tests.
- [ ] Adjust dev requirements to pytest plus app test dependencies.
- [ ] Run repository file search for HACS/custom integration references.
- [ ] Commit: `Remove HACS integration packaging`.

### Task 6: Verify And Publish

**Files:**
- No planned source edits unless verification finds issues.

- [ ] Compile all Python files with the bundled Python runtime.
- [ ] Validate YAML files with an available parser or conservative syntax inspection.
- [ ] Run tests if dependencies are available.
- [ ] Check `git status -sb`.
- [ ] Push `main` to GitHub.
- [ ] Commit any verification fixes before push.

## Self-Review

Spec coverage:

- App repository shape: Tasks 1 and 5.
- Python runtime choice: Tasks 2 through 4.
- App configuration: Tasks 1 and 2.
- Supervisor/Home Assistant communication: Task 3.
- Energy statistics: Task 3.
- Runtime loop and persistence: Task 4.
- Migration from HACS integration: Task 5.
- Verification and push: Task 6.

Deferred:

- TypeScript/.NET rewrite.
- Cost calculations.
- Multi-meter support.
- Ingress UI.
- Safe destructive statistics reset; v1 only logs reset intent and exits without deleting data.
