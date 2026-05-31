import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.models.alert import AnomalyType, Severity


@dataclass
class PulseScanAlert:
    camera_id: str
    camera_label: str
    survey_id: str
    species: str
    anomaly_type: AnomalyType
    severity: Severity
    detected_at: datetime
    last_confirmed_sighting: Optional[datetime]
    baseline_avg_visits: float
    current_visits: float
    z_score: float
    recommended_action: str


class PulseScan:
    """
    Layer 3: Temporal behaviour intelligence.

    Processes species detection sequences to build activity baselines,
    then fires conservation alerts the moment a pattern breaks.
    No model weights required — pure statistical analysis with pandas + scipy.
    """

    MIN_DETECTIONS_FOR_BASELINE = 5
    ABSENCE_LOOKBACK_DAYS = 7
    ABSENCE_CONSECUTIVE_DAYS = 3
    GROUP_COLLAPSE_WINDOW_DAYS = 5
    NEW_SPECIES_CONSECUTIVE_DAYS = 3

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def group_into_windows(
        self,
        detections: pd.DataFrame,
        window_hours: int = 2,
    ) -> pd.DataFrame:
        """
        Group detections into time windows per camera per species.

        Input DataFrame columns required: camera_id, species, captured_at (datetime), count_estimate (int)
        Output columns: camera_id, species, window_start, window_end, visit_count, avg_group_size

        Window start is floored to the nearest window_hours boundary.
        Example: 01:37 with window_hours=2 → window_start=00:00, window_end=02:00
        """
        if detections.empty:
            return pd.DataFrame(columns=[
                "camera_id", "species", "window_start", "window_end",
                "visit_count", "avg_group_size",
            ])

        df = detections.copy()
        df["captured_at"] = pd.to_datetime(df["captured_at"])

        freq = f"{window_hours}h"
        df["window_start"] = df["captured_at"].dt.floor(freq)
        df["window_end"] = df["window_start"] + pd.Timedelta(hours=window_hours)

        grouped = (
            df.groupby(["camera_id", "species", "window_start", "window_end"])
            .agg(
                visit_count=("captured_at", "count"),
                avg_group_size=("count_estimate", "mean"),
            )
            .reset_index()
        )
        grouped["avg_group_size"] = grouped["avg_group_size"].round(2)
        return grouped

    def build_baseline(
        self,
        windows: pd.DataFrame,
        camera_id: str,
        species: str,
        lookback_days: int = 30,
    ) -> dict[int, dict[str, float]]:
        """
        Build a rolling baseline for one camera+species pair.

        Returns a dict keyed by hour_block (0–11, each representing a 2-hour slot):
          { hour_block: { "avg": float, "std": float, "sample_count": int } }

        Returns empty dict if fewer than MIN_DETECTIONS_FOR_BASELINE windows exist.
        """
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=lookback_days)
        subset = windows[
            (windows["camera_id"] == camera_id)
            & (windows["species"] == species)
            & (windows["window_start"] >= cutoff)
        ].copy()

        if len(subset) < self.MIN_DETECTIONS_FOR_BASELINE:
            return {}

        subset["hour_block"] = (subset["window_start"].dt.hour // 2).astype(int)

        baseline: dict[int, dict[str, float]] = {}
        for hour_block, group in subset.groupby("hour_block"):
            counts = group["visit_count"].values
            baseline[int(hour_block)] = {
                "avg": round(float(np.mean(counts)), 3),
                "std": round(float(np.std(counts)), 3),
                "sample_count": len(counts),
            }
        return baseline

    def _peak_hour_block(self, baseline: dict) -> Optional[int]:
        """Return the hour_block with the highest average visits."""
        if not baseline:
            return None
        return max(baseline, key=lambda hb: baseline[hb]["avg"])

    def detect_anomalies(
        self,
        windows: pd.DataFrame,
        all_baselines: dict[tuple[str, str], dict],
        camera_labels: dict[str, str],
        survey_id: str,
        zscore_threshold: float = 2.5,
    ) -> list[PulseScanAlert]:
        """
        Compare current activity windows against baselines.
        Returns a list of PulseScanAlert for every detected anomaly.

        Detects five anomaly types:
        1. SUDDEN_ABSENCE      — species active last 7d, zero visits last 3d
        2. FREQUENCY_SPIKE     — visit count z-score > threshold
        3. ACTIVITY_TIME_SHIFT — peak activity hour shifted by 4+ hours
        4. GROUP_SIZE_COLLAPSE — avg group size dropped >50% over last 5 days
        5. NEW_SPECIES_APPEARANCE — species with zero history appears 3+ consecutive days
        """
        alerts: list[PulseScanAlert] = []
        now = pd.Timestamp.utcnow().tz_localize(None)

        for (camera_id, species), baseline in all_baselines.items():
            camera_label = camera_labels.get(camera_id, camera_id)
            cam_species = windows[
                (windows["camera_id"] == camera_id) & (windows["species"] == species)
            ]

            # --- 1. SUDDEN_ABSENCE ---
            prior_7d = cam_species[
                cam_species["window_start"] >= (now - pd.Timedelta(days=7))
            ]
            last_3d = cam_species[
                cam_species["window_start"] >= (now - pd.Timedelta(days=3))
            ]
            if len(prior_7d) >= self.MIN_DETECTIONS_FOR_BASELINE and len(last_3d) == 0:
                last_seen = cam_species["window_start"].max()
                alerts.append(PulseScanAlert(
                    camera_id=camera_id,
                    camera_label=camera_label,
                    survey_id=survey_id,
                    species=species,
                    anomaly_type=AnomalyType.SUDDEN_ABSENCE,
                    severity=Severity.HIGH,
                    detected_at=now.to_pydatetime(),
                    last_confirmed_sighting=last_seen.to_pydatetime() if pd.notna(last_seen) else None,
                    baseline_avg_visits=round(float(prior_7d["visit_count"].mean()), 2),
                    current_visits=0.0,
                    z_score=0.0,
                    recommended_action=(
                        f"Deploy field team to {camera_label} within 48 hours. "
                        f"Confirm {species} presence. Check patrol routes for snares."
                    ),
                ))

            # --- 2. FREQUENCY_SPIKE ---
            if baseline:
                recent = cam_species[
                    cam_species["window_start"] >= (now - pd.Timedelta(hours=48))
                ]
                for _, row in recent.iterrows():
                    hb = int(row["window_start"].hour // 2)
                    if hb not in baseline:
                        continue
                    b = baseline[hb]
                    if b["std"] < 0.01:
                        continue
                    z = (row["visit_count"] - b["avg"]) / b["std"]
                    if z > zscore_threshold:
                        severity = Severity.HIGH if z >= 4.0 else Severity.MEDIUM
                        alerts.append(PulseScanAlert(
                            camera_id=camera_id,
                            camera_label=camera_label,
                            survey_id=survey_id,
                            species=species,
                            anomaly_type=AnomalyType.FREQUENCY_SPIKE,
                            severity=severity,
                            detected_at=now.to_pydatetime(),
                            last_confirmed_sighting=row["window_start"].to_pydatetime(),
                            baseline_avg_visits=round(b["avg"], 2),
                            current_visits=round(float(row["visit_count"]), 2),
                            z_score=round(z, 2),
                            recommended_action=(
                                f"Unusual activity spike for {species} at {camera_label}. "
                                f"Possible prey concentration or human disturbance. "
                                f"Increase monitoring frequency."
                            ),
                        ))

            # --- 3. ACTIVITY_TIME_SHIFT ---
            if baseline and len(cam_species) >= self.MIN_DETECTIONS_FOR_BASELINE:
                baseline_peak = self._peak_hour_block(baseline)
                recent_cam = cam_species[
                    cam_species["window_start"] >= (now - pd.Timedelta(days=7))
                ].copy()
                if not recent_cam.empty:
                    recent_cam["hour_block"] = (recent_cam["window_start"].dt.hour // 2).astype(int)
                    recent_peak = (
                        recent_cam.groupby("hour_block")["visit_count"]
                        .sum()
                        .idxmax()
                    )
                    if baseline_peak is not None and abs(recent_peak - baseline_peak) >= 2:
                        alerts.append(PulseScanAlert(
                            camera_id=camera_id,
                            camera_label=camera_label,
                            survey_id=survey_id,
                            species=species,
                            anomaly_type=AnomalyType.ACTIVITY_TIME_SHIFT,
                            severity=Severity.MEDIUM,
                            detected_at=now.to_pydatetime(),
                            last_confirmed_sighting=recent_cam["window_start"].max().to_pydatetime(),
                            baseline_avg_visits=round(baseline[baseline_peak]["avg"], 2),
                            current_visits=round(float(recent_cam["visit_count"].mean()), 2),
                            z_score=0.0,
                            recommended_action=(
                                f"Behavioural shift detected for {species} at {camera_label}. "
                                f"Activity peak moved {abs(recent_peak - baseline_peak) * 2}h from baseline. "
                                f"Possible human disturbance forcing adaptation."
                            ),
                        ))

            # --- 4. GROUP_SIZE_COLLAPSE ---
            if len(cam_species) >= self.MIN_DETECTIONS_FOR_BASELINE:
                historical = cam_species[
                    cam_species["window_start"] < (now - pd.Timedelta(days=self.GROUP_COLLAPSE_WINDOW_DAYS))
                ]
                recent_gs = cam_species[
                    cam_species["window_start"] >= (now - pd.Timedelta(days=self.GROUP_COLLAPSE_WINDOW_DAYS))
                ]
                if len(historical) >= self.MIN_DETECTIONS_FOR_BASELINE and not recent_gs.empty:
                    hist_avg = float(historical["avg_group_size"].mean())
                    curr_avg = float(recent_gs["avg_group_size"].mean())
                    if hist_avg > 0 and (hist_avg - curr_avg) / hist_avg > 0.50:
                        alerts.append(PulseScanAlert(
                            camera_id=camera_id,
                            camera_label=camera_label,
                            survey_id=survey_id,
                            species=species,
                            anomaly_type=AnomalyType.GROUP_SIZE_COLLAPSE,
                            severity=Severity.MEDIUM,
                            detected_at=now.to_pydatetime(),
                            last_confirmed_sighting=recent_gs["window_start"].max().to_pydatetime(),
                            baseline_avg_visits=round(hist_avg, 2),
                            current_visits=round(curr_avg, 2),
                            z_score=0.0,
                            recommended_action=(
                                f"Group size dropped {round((hist_avg - curr_avg) / hist_avg * 100)}% "
                                f"for {species} at {camera_label}. "
                                f"Possible family separation or predation event."
                            ),
                        ))

        # --- 5. NEW_SPECIES_APPEARANCE ---
        # Triggered independently — no baseline needed (species never seen before)
        all_camera_ids = windows["camera_id"].unique()
        for camera_id in all_camera_ids:
            camera_label = camera_labels.get(camera_id, camera_id)
            cam_windows = windows[windows["camera_id"] == camera_id]
            known_species = {s for (cid, s) in all_baselines if cid == camera_id}
            all_seen = set(cam_windows["species"].unique())
            new_species = all_seen - known_species
            for species in new_species:
                species_windows = cam_windows[
                    (cam_windows["species"] == species)
                    & (cam_windows["window_start"] >= (now - pd.Timedelta(days=self.NEW_SPECIES_CONSECUTIVE_DAYS)))
                ]
                if len(species_windows) >= self.NEW_SPECIES_CONSECUTIVE_DAYS:
                    alerts.append(PulseScanAlert(
                        camera_id=camera_id,
                        camera_label=camera_label,
                        survey_id=survey_id,
                        species=species,
                        anomaly_type=AnomalyType.NEW_SPECIES_APPEARANCE,
                        severity=Severity.LOW,
                        detected_at=now.to_pydatetime(),
                        last_confirmed_sighting=species_windows["window_start"].max().to_pydatetime(),
                        baseline_avg_visits=0.0,
                        current_visits=round(float(species_windows["visit_count"].mean()), 2),
                        z_score=0.0,
                        recommended_action=(
                            f"New species detected at {camera_label}: {species}. "
                            f"Possible range expansion or new habitat corridor. "
                            f"Document for population survey."
                        ),
                    ))

        self.logger.info(
            f"PulseScan complete: {len(alerts)} alerts generated "
            f"({sum(1 for a in alerts if a.severity == Severity.HIGH)} HIGH, "
            f"{sum(1 for a in alerts if a.severity == Severity.MEDIUM)} MEDIUM, "
            f"{sum(1 for a in alerts if a.severity == Severity.LOW)} LOW)"
        )
        return alerts


if __name__ == "__main__":
    import sys
    from datetime import timedelta

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    now = datetime.utcnow()

    # Bengal Tiger at Camera-7: 22 visits spread over 30 days.
    # Last visit is 4 days + 1 hour ago — 4-day clean absence.
    # 10 of the visits fall within the last 7 days (days -4 to -7), triggering SUDDEN_ABSENCE.
    tiger_times = [now - timedelta(days=d, hours=h) for d, h in [
        (30, 2),  (28, 8),  (26, 14), (24, 6),  (22, 10),
        (20, 4),  (18, 16), (16, 8),  (14, 2),  (12, 12),
        (10, 6),  (8, 18),
        # last 10 visits in the 7-day window (before 3-day cutoff)
        (7, 3),  (7, 9),
        (6, 15), (6, 7),
        (5, 11), (5, 3),
        (4, 19), (4, 13), (4, 7), (4, 1),   # last visit: 4d 1h ago
    ]]

    # One-horned Rhino at Camera-3: brand-new species — 6 detections over last 3 days.
    # No baseline exists → triggers NEW_SPECIES_APPEARANCE.
    rhino_times = [now - timedelta(days=d, hours=h) for d, h in [
        (2, 6), (2, 14),
        (1, 8), (1, 18),
        (0, 10), (0, 20),
    ]]

    detections = pd.DataFrame([
        *[{"camera_id": "cam-7", "species": "Bengal Tiger",
           "captured_at": t, "count_estimate": 1} for t in tiger_times],
        *[{"camera_id": "cam-3", "species": "One-horned Rhino",
           "captured_at": t, "count_estimate": 3} for t in rhino_times],
    ])

    ps = PulseScan()

    windows = ps.group_into_windows(detections)
    print(f"\nGrouped into {len(windows)} activity windows across {windows['camera_id'].nunique()} cameras.\n")

    # Build baseline only for Bengal Tiger — Rhino is a new species with no history
    tiger_baseline = ps.build_baseline(windows, "cam-7", "Bengal Tiger")
    all_baselines: dict[tuple[str, str], dict] = {}
    if tiger_baseline:
        all_baselines[("cam-7", "Bengal Tiger")] = tiger_baseline

    camera_labels = {
        "cam-7": "Camera-7 (Chitwan South)",
        "cam-3": "Camera-3 (Bardia West)",
    }

    alerts = ps.detect_anomalies(
        windows,
        all_baselines,
        camera_labels,
        survey_id="survey-2026-nepal",
    )

    if not alerts:
        print("No anomalies detected.")
        sys.exit(0)

    print(f"\n{'═' * 56}")
    print(f"  FAUNA.AI PULSE SCAN — {len(alerts)} ALERT(S) DETECTED")
    print(f"{'═' * 56}")

    for i, alert in enumerate(alerts, 1):
        severity_tag = f"[{alert.severity.value}]"
        print(f"\n  Alert #{i}  {severity_tag}")
        print(f"  {'─' * 50}")
        print(f"  Species        : {alert.species}")
        print(f"  Camera         : {alert.camera_label}")
        print(f"  Anomaly        : {alert.anomaly_type.value}")
        print(f"  Severity       : {alert.severity.value}")
        if alert.last_confirmed_sighting:
            print(f"  Last seen      : {alert.last_confirmed_sighting.strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"  Baseline visits: {alert.baseline_avg_visits}")
        print(f"  Current visits : {alert.current_visits}")
        if alert.z_score:
            print(f"  Z-score        : {alert.z_score}")
        print(f"  Action         : {alert.recommended_action}")

    print(f"\n{'═' * 56}\n")
