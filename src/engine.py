"""DF-CAPE-CORAL-PHASE-MONITOR Engine [CRUX-MK]

Monatliche Cape-Coral-Phase-Trigger-Detection per KLAUSEL-PATENT-WEGZUGS-CLAUSE
24M-Pre-Closing-Plan.

Architektur (4 Pillars):
- PatentAggregatAuditor: prueft Aggregat-Bewertung vs §6 AStG-Wertgrenze
- DBAUpdateDetector: detektiert DBA-USA-DE-Update (Schritt-Aenderung)
- IRS482ComplianceTracker: Transfer-Pricing-Drift-Detector
- ReMigrationTriggerMonitor: 24M-Plan Phase-Wechsel-Trigger

Bei Phase-Trigger: Pflicht-Phronesis-Alert an Martin via Inbox-Note + Decision-Card-Draft.
KEIN Auto-Aktion (K_0-Sperr-Liste P6 Item-3 Cape-Coral-Pacing).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ENGINE_PROCESS_NAME = "df_cape_coral_phase_monitor.engine"
DEFAULT_STATE_DIR = Path.home() / ".df-cape-coral-phase-monitor"
DEFAULT_STOP_FLAG = Path("/tmp/df-cape-coral-phase-monitor.stop")
DEFAULT_HEALTH_FILE = Path("/tmp/df-cape-coral-phase-monitor-health.json")

PILLARS = ("patent_aggregat_audit", "dba_update_detector", "irs_482_compliance", "re_migration_trigger")

# §6 AStG-Wertgrenze (vereinfacht; in Production aus aktueller Gesetzes-Quelle)
ASTG_VALUE_THRESHOLD_EUR = 500_000


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PillarSignal:
    pillar: str
    detected_at: str
    severity: str  # info|warn|critical
    summary: str
    diff: dict = field(default_factory=dict)


@dataclass
class PhaseTriggerAlert:
    triggered_at: str
    pillars_triggered: list[str]
    severity: str
    martin_phronesis_required: bool = True
    sperr_liste_item: int = 3  # P6 Item-3 Cape-Coral-Pacing
    summary: str = ""


@dataclass
class MonitorResult:
    started_at: str
    finished_at: str = ""
    pillars_checked: int = 0
    pillars_with_signal: int = 0
    phase_triggers: int = 0
    mode: str = "full"
    signals: list[PillarSignal] = field(default_factory=list)
    alerts: list[PhaseTriggerAlert] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class PreActionVerifier:
    """Pre-Action-Domain-Check (K13).

    Cape-Coral ist K_0-Domain. Pflicht-Phronesis fuer JEDEN Auto-Aktion-Pfad.
    """

    def __init__(self, source_root: Path, env_tag: str = "production") -> None:
        self.source_root = source_root
        self.env_tag = env_tag

    def verify(self) -> dict:
        return {
            "env_tag": self.env_tag,
            "mount_check": self.source_root.exists(),
            "blast_radius": "state-only (kein Auto-Aktion)",
            "reversibility_class": "state-only",
            "k0_sperr_liste_item": 3,
            "ok": self.source_root.exists() and self.env_tag in {"production", "staging", "dev"},
        }


class PatentAggregatAuditor:
    """Pillar 1: Patent-Aggregat-Bewertungs-Audit (drift vs §6 AStG)."""

    def __init__(self, threshold_eur: float = ASTG_VALUE_THRESHOLD_EUR) -> None:
        self.threshold_eur = threshold_eur

    def audit(self, current_aggregat_eur: float, prev_aggregat_eur: float) -> PillarSignal | None:
        diff = current_aggregat_eur - prev_aggregat_eur
        diff_ratio = diff / prev_aggregat_eur if prev_aggregat_eur > 0 else 0
        # Trigger 1: Aggregat ueberschreitet Schwelle
        if current_aggregat_eur > self.threshold_eur and prev_aggregat_eur <= self.threshold_eur:
            return PillarSignal(
                pillar="patent_aggregat_audit",
                detected_at=iso_now(),
                severity="critical",
                summary=(
                    f"Aggregat ueberschreitet §6 AStG-Schwelle "
                    f"({prev_aggregat_eur:,.0f} -> {current_aggregat_eur:,.0f} EUR)"
                ),
                diff={"prev": prev_aggregat_eur, "current": current_aggregat_eur,
                      "threshold": self.threshold_eur},
            )
        # Trigger 2: Drift > 20%
        if abs(diff_ratio) > 0.20:
            return PillarSignal(
                pillar="patent_aggregat_audit",
                detected_at=iso_now(),
                severity="warn",
                summary=f"Aggregat-Drift {diff_ratio*100:+.1f}%",
                diff={"prev": prev_aggregat_eur, "current": current_aggregat_eur,
                      "diff_ratio": diff_ratio},
            )
        return None


class DBAUpdateDetector:
    """Pillar 2: DBA-USA-DE-Update-Detector."""

    def detect(self, current_dba_version: str, prev_dba_version: str) -> PillarSignal | None:
        if not current_dba_version:
            return None
        if current_dba_version == prev_dba_version:
            return None
        # Initial-Snapshot ist info, nicht critical (sonst Pflicht-Alert beim 1. Run)
        severity = "info" if prev_dba_version == "" else "critical"
        return PillarSignal(
            pillar="dba_update_detector",
            detected_at=iso_now(),
            severity=severity,
            summary=f"DBA-USA-DE Update: {prev_dba_version or '(initial)'} -> {current_dba_version}",
            diff={"prev": prev_dba_version, "current": current_dba_version},
        )


class IRS482ComplianceTracker:
    """Pillar 3: Transfer-Pricing-Drift-Detector (IRS §482)."""

    DRIFT_RATIO_WARN = 0.10
    DRIFT_RATIO_CRITICAL = 0.25

    def track(self, current_arms_length_factor: float,
              expected_factor: float = 1.0) -> PillarSignal | None:
        if expected_factor <= 0:
            return None
        drift = abs(current_arms_length_factor - expected_factor) / expected_factor
        if drift > self.DRIFT_RATIO_CRITICAL:
            sev = "critical"
        elif drift > self.DRIFT_RATIO_WARN:
            sev = "warn"
        else:
            return None
        return PillarSignal(
            pillar="irs_482_compliance",
            detected_at=iso_now(),
            severity=sev,
            summary=f"IRS §482 Arms-Length-Drift {drift*100:.1f}%",
            diff={"current": current_arms_length_factor, "expected": expected_factor,
                  "drift": drift},
        )


class ReMigrationTriggerMonitor:
    """Pillar 4: 24M-Pre-Closing-Plan Phase-Wechsel-Trigger."""

    PHASES = (
        ("M-24", "Pre-Audit-Phase"),
        ("M-18", "Defensive-Publication-Cascade"),
        ("M-12", "Aggregat-Final-Bewertung"),
        ("M-06", "DBA-Optimierung"),
        ("M-03", "Pre-Closing-Final"),
        ("M-00", "Closing-Live"),
    )

    def monitor(self, months_to_closing: int) -> PillarSignal | None:
        for phase_marker, phase_name in self.PHASES:
            target = -int(phase_marker[2:])  # M-24 -> -24
            if months_to_closing == target:
                return PillarSignal(
                    pillar="re_migration_trigger",
                    detected_at=iso_now(),
                    severity="critical",
                    summary=f"Phase-Trigger {phase_marker}: {phase_name}",
                    diff={"phase": phase_marker, "name": phase_name,
                          "months_to_closing": months_to_closing},
                )
        return None


class PhronesisAlertWriter:
    """Schreibt Pflicht-Phronesis-Alert an Martin bei Phase-Trigger."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def write(self, alert: PhaseTriggerAlert, signals: list[PillarSignal]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        date = alert.triggered_at[:10]
        path = self.output_dir / f"PHASE-TRIGGER-{date}.md"
        body = (
            f"# Cape-Coral Phase-Trigger Alert [CRUX-MK]\n\n"
            f"**Triggered:** {alert.triggered_at}\n"
            f"**Severity:** {alert.severity}\n"
            f"K_0-Sperr-Liste P6 Item: {alert.sperr_liste_item} (Cape-Coral-Pacing)\n"
            f"Phronesis Pflicht: {alert.martin_phronesis_required}\n\n"
            f"## Triggered Pillars\n"
            + "\n".join(f"- {p}" for p in alert.pillars_triggered)
            + "\n\n## Signals\n"
            + "\n".join(
                f"- [{s.severity}] {s.pillar}: {s.summary}" for s in signals
            )
            + "\n\n## Pflicht-Phronesis-Action\n"
            "Architekt darf NICHT autonom handeln. Martin entscheidet Phase-Aktion.\n"
        )
        path.write_text(body)
        return path


class StateTracker:
    """Persistiert pillar-state (idempotent)."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file

    def load(self) -> dict:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def save(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2))

    def update_pillar(self, state: dict, pillar: str, value: dict) -> dict:
        state[pillar] = {**value, "updated_at": iso_now()}
        return state


def k16_concurrent_spawn_check() -> int:
    my_pid = os.getpid()
    try:
        result = subprocess.run(
            ["pgrep", "-f", ENGINE_PROCESS_NAME],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return 0
    pids = [int(p) for p in result.stdout.strip().split("\n") if p and int(p) != my_pid]
    return 1 if pids else 0


class CapeCoralPhaseMonitorEngine:
    """Master-Engine. Koordiniert 4 Pillars + Pflicht-Phronesis-Alert."""

    def __init__(
        self,
        source_root: Path,
        output_dir: Path,
        state_file: Path,
        env_tag: str = "production",
    ) -> None:
        self.source_root = source_root
        self.output_dir = output_dir
        self.state_file = state_file
        self.env_tag = env_tag
        self.tracker = StateTracker(state_file)
        self.verifier = PreActionVerifier(source_root, env_tag)
        self.alert_writer = PhronesisAlertWriter(output_dir)
        self.aggregat_auditor = PatentAggregatAuditor()
        self.dba_detector = DBAUpdateDetector()
        self.irs_tracker = IRS482ComplianceTracker()
        self.remigration_monitor = ReMigrationTriggerMonitor()

    def run(
        self,
        current_aggregat_eur: float = 0.0,
        current_dba_version: str = "",
        current_arms_length_factor: float = 1.0,
        months_to_closing: int = 0,
        mode: str = "full",
    ) -> MonitorResult:
        result = MonitorResult(started_at=iso_now(), mode=mode)
        if DEFAULT_STOP_FLAG.exists():
            result.errors.append("STOP.flag-detected")
            result.finished_at = iso_now()
            return result
        if k16_concurrent_spawn_check():
            result.errors.append("K16-concurrent-spawn-detected")
            result.finished_at = iso_now()
            return result
        pa = self.verifier.verify()
        if not pa["ok"]:
            result.errors.append(f"pre-action-fail: {pa}")
            result.finished_at = iso_now()
            return result
        state = self.tracker.load()

        # Pillar 1
        prev_aggregat = state.get("patent_aggregat_audit", {}).get("aggregat_eur", 0.0)
        sig1 = self.aggregat_auditor.audit(current_aggregat_eur, prev_aggregat)
        if sig1 is not None:
            result.signals.append(sig1)
            result.pillars_with_signal += 1
        state = self.tracker.update_pillar(state, "patent_aggregat_audit",
                                          {"aggregat_eur": current_aggregat_eur})
        result.pillars_checked += 1

        # Pillar 2
        prev_dba = state.get("dba_update_detector", {}).get("dba_version", "")
        sig2 = self.dba_detector.detect(current_dba_version, prev_dba)
        if sig2 is not None:
            result.signals.append(sig2)
            result.pillars_with_signal += 1
        state = self.tracker.update_pillar(state, "dba_update_detector",
                                          {"dba_version": current_dba_version})
        result.pillars_checked += 1

        # Pillar 3
        sig3 = self.irs_tracker.track(current_arms_length_factor)
        if sig3 is not None:
            result.signals.append(sig3)
            result.pillars_with_signal += 1
        state = self.tracker.update_pillar(state, "irs_482_compliance",
                                          {"arms_length_factor": current_arms_length_factor})
        result.pillars_checked += 1

        # Pillar 4
        sig4 = self.remigration_monitor.monitor(months_to_closing)
        if sig4 is not None:
            result.signals.append(sig4)
            result.pillars_with_signal += 1
        state = self.tracker.update_pillar(state, "re_migration_trigger",
                                          {"months_to_closing": months_to_closing})
        result.pillars_checked += 1

        self.tracker.save(state)

        # Phase-Trigger-Aggregation
        critical_signals = [s for s in result.signals if s.severity == "critical"]
        if critical_signals:
            alert = PhaseTriggerAlert(
                triggered_at=iso_now(),
                pillars_triggered=[s.pillar for s in critical_signals],
                severity="critical",
                summary=f"{len(critical_signals)} kritische Pillar-Signale",
            )
            self.alert_writer.write(alert, result.signals)
            result.alerts.append(alert)
            result.phase_triggers = len(critical_signals)

        result.finished_at = iso_now()
        self._write_health(result)
        return result

    def _write_health(self, result: MonitorResult) -> None:
        DEFAULT_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_HEALTH_FILE.write_text(json.dumps({
            "df": "DF-CAPE-CORAL-PHASE-MONITOR",
            "ts": iso_now(),
            "score": 1.0 if not result.errors else 0.5,
            "pillars_with_signal": result.pillars_with_signal,
            "phase_triggers": result.phase_triggers,
        }, indent=2))


def main() -> int:
    source_root = Path(os.environ.get("DF_CC_SOURCE", str(Path.home() / "branch-hub" / "cape-coral")))
    output = Path(os.environ.get("DF_CC_OUT", str(Path.home() / "df-cape-coral-out")))
    state_file = DEFAULT_STATE_DIR / "state.json"
    eng = CapeCoralPhaseMonitorEngine(source_root, output, state_file,
                                       env_tag=os.environ.get("DF_CC_ENV", "production"))
    # Parameter aus ENV (in Production aus aktueller Steuer-Bewertungs-Pipeline)
    aggregat = float(os.environ.get("DF_CC_AGGREGAT_EUR", "0"))
    dba = os.environ.get("DF_CC_DBA_VERSION", "")
    arms_length = float(os.environ.get("DF_CC_ARMS_LENGTH", "1.0"))
    months = int(os.environ.get("DF_CC_MONTHS_TO_CLOSING", "0"))
    result = eng.run(aggregat, dba, arms_length, months)
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
