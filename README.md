# DF-CAPE-CORAL-PHASE-MONITOR [CRUX-MK]

**Status:** PRE-PRODUCTION-CONDITIONAL
**Schedule:** Monatlich 1. 09:00
**Trigger:** Welle-5-DF-BOOST-2

## Scope
4-Pillar-Cape-Coral-Phase-Trigger-Detection per KLAUSEL-PATENT-WEGZUGS-CLAUSE
24M-Pre-Closing-Plan. Bei Phase-Trigger: Pflicht-Phronesis-Alert
(K_0-Sperr-Liste P6 Item-3).

## 4 Pillars
1. **PatentAggregatAuditor:** §6 AStG-Wertgrenze (500k EUR) + Drift > 20%
2. **DBAUpdateDetector:** DBA-USA-DE-Update (Schritt-Aenderung)
3. **IRS482ComplianceTracker:** Transfer-Pricing-Drift (warn 10% / critical 25%)
4. **ReMigrationTriggerMonitor:** 24M-Plan Phase-Marker (M-24, M-18, M-12, M-06, M-03, M-00)

## Pflicht-Phronesis (K_0-Sperr-Liste P6 Item-3)
- Cape-Coral-Pacing ist binaerer K_0-Decision-Trigger
- Architekt darf NICHT autonom Phase-Aktion auslosen
- DF schreibt nur State + Pflicht-Phronesis-Alert an Martin
- Martin entscheidet konkrete Aktion

## Pipeline
1. PreActionVerifier (env_tag + mount + sperr-item=3)
2. K16 Concurrent-Spawn-Check
3. 4 Pillars sequenziell
4. PhronesisAlertWriter bei kritischen Signalen
5. StateTracker (idempotent)
6. Health + JSONL

## Activation (Phronesis-Pflicht!)
```
launchctl bootstrap gui/$UID com.kemmer.df-cape-coral-phase-monitor.plist
```
NICHT autonom aktivieren. P-DF-G.

## CRUX-Bindung
- K_0: DIREKT GESCHUETZT (Wegzugssteuer §6 AStG; Cape-Coral-Pacing K_0-Sperr-Item-3)
- Q_0: Familien-Pacing-Stabilitaet
- W_0: Steueranwalts-Bandbreite optimiert
