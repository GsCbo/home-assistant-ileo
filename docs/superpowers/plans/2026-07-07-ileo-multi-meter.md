# ILEO Multi-Meter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app internally multi-meter capable while preserving the current single-meter behavior until the ILEO portal can be inspected again.

**Architecture:** Add stable `IleoMeter` and meter-aware `IleoReading` models in the ILEO client. Update statistics and runtime code to operate per meter, with `default` as a compatibility meter when ILEO exposes only one CSV. Persist sync markers under a `meters` map and migrate legacy root-level state in memory.

**Tech Stack:** Python 3, aiohttp via Alpine `py3-aiohttp`, Home Assistant Core REST API, pytest-style tests, JSON state in `/data/last_sync.json`.

---

### Task 1: Add Meter-Aware Client Model

**Files:**
- Modify: `ileo/app/ileo_client.py`
- Modify: `tests/test_ileo_client.py`

- [ ] **Step 1: Add the expected model test**

Add this test to `tests/test_ileo_client.py`:

```python
def test_parse_readings_csv_assigns_default_meter_id() -> None:
    csv_text = "date;consommation (litres);index\n02/03/2025;180;120180\n"

    readings = parse_readings_csv(csv_text)

    assert readings[0].meter_id == "default"
```

- [ ] **Step 2: Update the model**

In `ileo/app/ileo_client.py`, add:

```python
DEFAULT_METER_ID = "default"

@dataclass(frozen=True, slots=True)
class IleoMeter:
    meter_id: str
    name: str
```

Change `IleoReading` to:

```python
@dataclass(frozen=True, slots=True)
class IleoReading:
    date: date
    litres: float
    index_litres: int
    meter_id: str = DEFAULT_METER_ID
```

- [ ] **Step 3: Run verification**

Run:

```bash
python -m py_compile ileo/app/ileo_client.py tests/test_ileo_client.py
```

Expected: exit code 0.

- [ ] **Step 4: Commit**

```bash
git add ileo/app/ileo_client.py tests/test_ileo_client.py
git commit -m "Add meter-aware ILEO reading model"
```

### Task 2: Generate Entity And Statistics Per Meter

**Files:**
- Modify: `ileo/app/statistics.py`
- Modify: `tests/test_statistics.py`

- [ ] **Step 1: Add statistics tests**

Add tests proving:

```python
def test_meter_entity_id_keeps_single_meter_compatibility() -> None:
    assert meter_entity_id("default") == "sensor.ileo_water_index"


def test_meter_entity_id_slugs_explicit_meter_id() -> None:
    assert meter_entity_id("Contrat 12 Rue de Lille") == "sensor.ileo_water_index_contrat_12_rue_de_lille"
```

Add a multi-meter payload test:

```python
def test_import_statistics_payload_uses_meter_specific_statistic_id() -> None:
    readings = [IleoReading(date(2025, 3, 2), 180.0, 120180, meter_id="contract-123")]

    payload = import_statistics_payload(readings, "contract-123", "Maison")

    assert payload["metadata"]["statistic_id"] == "sensor.ileo_water_index_contract_123"
    assert payload["metadata"]["name"] == "ILEO eau - Maison"
```

- [ ] **Step 2: Implement statistics helpers**

Add:

```python
def meter_entity_id(meter_id: str) -> str:
    if meter_id == DEFAULT_METER_ID:
        return "sensor.ileo_water_index"
    return f"sensor.ileo_water_index_{_slugify(meter_id)}"


def meter_name(meter_label: str | None) -> str:
    if meter_label:
        return f"ILEO eau - {meter_label}"
    return "ILEO water index"
```

Update `latest_state` and `import_statistics_payload` to accept `meter_id` and `meter_label`.

- [ ] **Step 3: Run verification**

Run:

```bash
python -m py_compile ileo/app/statistics.py tests/test_statistics.py
```

Expected: exit code 0.

- [ ] **Step 4: Commit**

```bash
git add ileo/app/statistics.py tests/test_statistics.py
git commit -m "Add meter-specific Home Assistant statistics"
```

### Task 3: Persist Per-Meter Sync State

**Files:**
- Modify: `ileo/app/main.py`
- Modify: `tests/test_runtime.py`

- [ ] **Step 1: Add state migration tests**

Add tests proving:

```python
def test_meter_sync_state_reads_legacy_root_marker(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    write_last_sync(state_path, {"last_imported_date": "2025-03-02", "latest_index_litres": 120180})

    assert read_meter_sync_state(state_path, "default") == {
        "last_imported_date": "2025-03-02",
        "latest_index_litres": 120180,
    }


def test_write_meter_sync_state_preserves_installation_id(tmp_path: Path) -> None:
    state_path = tmp_path / "last_sync.json"
    write_last_sync(state_path, {"installation_id": "stable"})

    write_meter_sync_state(state_path, "contract-123", {"last_imported_date": "2025-03-03"})

    assert read_last_sync(state_path)["installation_id"] == "stable"
    assert read_last_sync(state_path)["meters"]["contract-123"]["last_imported_date"] == "2025-03-03"
```

- [ ] **Step 2: Implement state helpers**

Add in `ileo/app/main.py`:

```python
def read_meter_sync_state(path: Path, meter_id: str) -> dict[str, Any]:
    state = read_last_sync(path)
    meters = state.get("meters")
    if isinstance(meters, dict) and isinstance(meters.get(meter_id), dict):
        return meters[meter_id]
    if meter_id == DEFAULT_METER_ID:
        legacy = {
            key: state[key]
            for key in ("last_imported_date", "latest_index_litres")
            if key in state
        }
        return legacy
    return {}


def write_meter_sync_state(path: Path, meter_id: str, meter_state: dict[str, Any]) -> None:
    state = read_last_sync(path)
    meters = state.get("meters") if isinstance(state.get("meters"), dict) else {}
    meters = {**meters, meter_id: meter_state}
    write_last_sync(path, {**state, "meters": meters})
```

- [ ] **Step 3: Run verification**

Run:

```bash
python -m py_compile ileo/app/main.py tests/test_runtime.py
```

Expected: exit code 0.

- [ ] **Step 4: Commit**

```bash
git add ileo/app/main.py tests/test_runtime.py
git commit -m "Persist ILEO sync state per meter"
```

### Task 4: Sync Each Meter Separately

**Files:**
- Modify: `ileo/app/main.py`
- Modify: `tests/test_runtime.py`

- [ ] **Step 1: Add runtime test for multi-meter readings**

Add a fake client returning readings for two meters:

```python
readings = [
    IleoReading(date(2025, 3, 2), 180.0, 120180, meter_id="house"),
    IleoReading(date(2025, 3, 2), 90.0, 88090, meter_id="garage"),
]
```

Assert that `sync_once` calls `async_set_state` twice and imports two separate statistics payloads.

- [ ] **Step 2: Implement grouping**

In `sync_once`, group readings by `meter_id`, then for each group:

```python
for meter_id, meter_readings in grouped.items():
    entity_id = meter_entity_id(meter_id)
    state, attributes = latest_state(meter_readings, meter_id=meter_id, meter_label=None)
    await ha_client.async_set_state(entity_id, state, attributes)
    meter_state = read_meter_sync_state(state_path, meter_id)
    new_readings = filter_after_last_sync(meter_readings, meter_state.get("last_imported_date"))
    if new_readings:
        await ha_client.async_import_statistics(import_statistics_payload(new_readings, meter_id, None))
    write_meter_sync_state(...)
```

- [ ] **Step 3: Run verification**

Run:

```bash
python -m py_compile ileo/app/main.py tests/test_runtime.py
```

Expected: exit code 0.

- [ ] **Step 4: Commit**

```bash
git add ileo/app/main.py tests/test_runtime.py
git commit -m "Sync ILEO readings per meter"
```

### Task 5: Document Current Multi-Meter Behavior

**Files:**
- Modify: `README.md`
- Modify: `ileo/README.md`

- [ ] **Step 1: Update documentation**

Add a section explaining:

- the app is internally ready for multiple meters;
- until ILEO is available, discovery is still using the default single-meter export;
- when multi-meter discovery is confirmed, all detected meters will be imported by default;
- entities can be renamed in Home Assistant without changing the technical meter id.

- [ ] **Step 2: Run scan**

Run:

```bash
rg -n "multi|compteur|meter|default" README.md ileo/README.md
```

Expected: README sections mention multi-meter behavior.

- [ ] **Step 3: Commit**

```bash
git add README.md ileo/README.md
git commit -m "Document ILEO multi-meter behavior"
```

### Task 6: Final Verification And Push

**Files:**
- Verify repository state.

- [ ] **Step 1: Compile all Python**

Run:

```bash
python -m py_compile ileo/app/__init__.py ileo/app/config.py ileo/app/ha_api.py ileo/app/ileo_client.py ileo/app/main.py ileo/app/statistics.py tests/test_app_config.py tests/test_ileo_client.py tests/test_runtime.py tests/test_statistics.py
```

Expected: exit code 0.

- [ ] **Step 2: Attempt pytest**

Run:

```bash
python -m pytest tests -q
```

Expected in the current local environment may be `No module named pytest`; report that limitation if it remains true.

- [ ] **Step 3: Push**

```bash
git status --short
git push origin main
```

Expected: clean working tree after push.

