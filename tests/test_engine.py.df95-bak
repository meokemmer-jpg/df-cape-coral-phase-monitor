
# K16-Trinity-AGGRESSIVE 2026-05-17
def k16_lock(name):
    import fcntl, os
    fd = os.open(f'/tmp/df-aggr-{name}.lock', os.O_CREAT|os.O_WRONLY)
    fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
    return fd

# K13-Trinity-AGGRESSIVE 2026-05-17
def k13_anchor(h):
    from datetime import datetime, timezone
    return {'t': 'rfc3161-mock', 'ts': datetime.now(timezone.utc).isoformat(), 'h': h}

# K12-Trinity-AGGRESSIVE 2026-05-17
def k12_provenance(p, k=b'df-aggr'):
    import hashlib, hmac
    return {'h': hashlib.sha256(p).hexdigest(), 'm': hmac.new(k,p,hashlib.sha256).hexdigest()}
"""DF-CAPE-CORAL-PHASE-MONITOR Engine Tests [CRUX-MK]

12 Pflicht-Tests:
- iso_now Format
- PreActionVerifier (env_tag + mount + sperr_liste_item)
- PatentAggregatAuditor (threshold-trigger + drift-trigger + no-signal)
- DBAUpdateDetector (initial + change-detection + no-change)
- IRS482ComplianceTracker (warn + critical + no-signal)
- ReMigrationTriggerMonitor (Phase-Match + No-Phase)
- PhronesisAlertWriter (Decision-Card-Draft + K_0-Sperr-Item)
- StateTracker (persist + update_pillar)
- Engine.run (Aggregat-Trigger + Phase-Trigger + No-Trigger)
- K16 concurrent-spawn
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.engine import (
    ASTG_VALUE_THRESHOLD_EUR,
    CapeCoralPhaseMonitorEngine,
    DBAUpdateDetector,
    IRS482ComplianceTracker,
    PILLARS,
    PatentAggregatAuditor,
    PhaseTriggerAlert,
    PhronesisAlertWriter,
    PillarSignal,
    PreActionVerifier,
    ReMigrationTriggerMonitor,
    StateTracker,
    iso_now,
    k16_concurrent_spawn_check,
)


def test_iso_now_format() -> None:
    s = iso_now()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", s)


def test_pre_action_verifier_ok(tmp_path: Path) -> None:
    pa = PreActionVerifier(tmp_path, env_tag="dev").verify()
    assert pa["ok"] is True
    assert pa["k0_sperr_liste_item"] == 3


def test_pre_action_verifier_missing_mount(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    pa = PreActionVerifier(missing).verify()
    assert pa["ok"] is False


def test_aggregat_auditor_threshold_trigger() -> None:
    a = PatentAggregatAuditor()
    sig = a.audit(current_aggregat_eur=600_000, prev_aggregat_eur=400_000)
    assert sig is not None
    assert sig.severity == "critical"
    assert "AStG" in sig.summary


def test_aggregat_auditor_drift_trigger() -> None:
    a = PatentAggregatAuditor()
    sig = a.audit(current_aggregat_eur=300_000, prev_aggregat_eur=200_000)  # +50%
    assert sig is not None
    assert sig.severity == "warn"


def test_aggregat_auditor_no_signal() -> None:
    a = PatentAggregatAuditor()
    sig = a.audit(current_aggregat_eur=100_000, prev_aggregat_eur=105_000)  # ~5%
    assert sig is None


def test_dba_detector_change() -> None:
    d = DBAUpdateDetector()
    sig = d.detect(current_dba_version="v2026", prev_dba_version="v2024")
    assert sig is not None
    assert sig.severity == "critical"


def test_dba_detector_no_change() -> None:
    d = DBAUpdateDetector()
    sig = d.detect(current_dba_version="v2024", prev_dba_version="v2024")
    assert sig is None


def test_irs_tracker_warn() -> None:
    t = IRS482ComplianceTracker()
    sig = t.track(current_arms_length_factor=1.15, expected_factor=1.0)
    assert sig is not None
    assert sig.severity == "warn"


def test_irs_tracker_critical() -> None:
    t = IRS482ComplianceTracker()
    sig = t.track(current_arms_length_factor=1.30, expected_factor=1.0)
    assert sig is not None
    assert sig.severity == "critical"


def test_irs_tracker_no_signal() -> None:
    t = IRS482ComplianceTracker()
    sig = t.track(current_arms_length_factor=1.05, expected_factor=1.0)
    assert sig is None


def test_remigration_monitor_phase_match() -> None:
    m = ReMigrationTriggerMonitor()
    sig = m.monitor(months_to_closing=-24)
    assert sig is not None
    assert "M-24" in sig.summary


def test_remigration_monitor_no_phase() -> None:
    m = ReMigrationTriggerMonitor()
    sig = m.monitor(months_to_closing=-19)
    assert sig is None


def test_phronesis_alert_writer(tmp_path: Path) -> None:
    writer = PhronesisAlertWriter(tmp_path)
    alert = PhaseTriggerAlert(
        triggered_at="2026-05-09T10:00:00Z",
        pillars_triggered=["patent_aggregat_audit"],
        severity="critical",
        summary="test",
    )
    sig = PillarSignal(pillar="patent_aggregat_audit", detected_at="x",
                       severity="critical", summary="test-summary")
    path = writer.write(alert, [sig])
    assert path.exists()
    text = path.read_text()
    assert "K_0-Sperr-Liste P6 Item: 3" in text
    assert "Phronesis Pflicht: True" in text


def test_state_tracker_update_pillar(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    tracker = StateTracker(state_file)
    state = tracker.load()
    state = tracker.update_pillar(state, "patent_aggregat_audit", {"aggregat_eur": 500_000})
    tracker.save(state)
    state2 = tracker.load()
    assert state2["patent_aggregat_audit"]["aggregat_eur"] == 500_000


def test_engine_run_no_triggers(tmp_path: Path) -> None:
    eng = CapeCoralPhaseMonitorEngine(
        source_root=tmp_path,
        output_dir=tmp_path / "out",
        state_file=tmp_path / ".state" / "state.json",
        env_tag="dev",
    )
    result = eng.run(
        current_aggregat_eur=100_000,
        current_dba_version="v2024",
        current_arms_length_factor=1.0,
        months_to_closing=-19,
    )
    assert result.pillars_checked == len(PILLARS)
    assert result.phase_triggers == 0


def test_engine_run_aggregat_trigger(tmp_path: Path) -> None:
    eng = CapeCoralPhaseMonitorEngine(
        source_root=tmp_path,
        output_dir=tmp_path / "out",
        state_file=tmp_path / ".state" / "state.json",
        env_tag="dev",
    )
    result = eng.run(
        current_aggregat_eur=600_000,  # ueber Schwelle
        current_dba_version="v2024",
        current_arms_length_factor=1.0,
        months_to_closing=-19,
    )
    assert result.phase_triggers >= 1
    # Pflicht-Phronesis-Alert geschrieben
    assert len(result.alerts) >= 1
    assert result.alerts[0].sperr_liste_item == 3


def test_engine_run_phase_trigger(tmp_path: Path) -> None:
    eng = CapeCoralPhaseMonitorEngine(
        source_root=tmp_path,
        output_dir=tmp_path / "out",
        state_file=tmp_path / ".state" / "state.json",
        env_tag="dev",
    )
    result = eng.run(
        current_aggregat_eur=100_000,
        current_dba_version="v2024",
        current_arms_length_factor=1.0,
        months_to_closing=-12,  # Phase M-12
    )
    assert result.phase_triggers >= 1


def test_k16_concurrent_spawn_check() -> None:
    assert k16_concurrent_spawn_check() == 0
