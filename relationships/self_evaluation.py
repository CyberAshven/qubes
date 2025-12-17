"""
Self-Evaluation System for Qubes

Enables qubes to evaluate their own performance, behavior, and growth.
Complements the relationship system by providing introspective metrics.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
import json

from utils.logging import get_logger

logger = get_logger(__name__)


class SelfEvaluation:
    """
    Self-evaluation metrics for a qube

    Tracks introspective metrics about the qube's own performance,
    behavior patterns, and areas for growth.
    """

    # Self-Evaluation Metrics (10 core metrics, 0-100 scale)
    METRICS = [
        "self_awareness",      # Understanding own capabilities and limitations
        "confidence",          # Belief in abilities (without arrogance)
        "consistency",         # Behavioral stability and predictability
        "growth_rate",         # Speed of learning and adaptation
        "goal_alignment",      # Acting according to stated values
        "critical_thinking",   # Quality of reasoning and analysis
        "adaptability",        # Flexibility in approach
        "emotional_intelligence",  # Response management in difficult situations
        "humility",            # Recognizing and admitting mistakes
        "curiosity"            # Drive to explore and learn
    ]

    def __init__(self, qube_id: str, data_dir: Path):
        """
        Initialize self-evaluation tracker

        Args:
            qube_id: Qube's unique identifier
            data_dir: Path to qube's data directory
        """
        self.qube_id = qube_id
        self.data_dir = Path(data_dir)
        self.relationships_dir = self.data_dir / "relationships"
        self.self_eval_file = self.relationships_dir / "self_evaluation.json"
        # Use new unified snapshots directory structure
        self.snapshots_dir = self.data_dir / "snapshots" / "self_evaluations"

        # Ensure directories exist
        self.relationships_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metrics
        self.metrics: Dict[str, float] = {metric: 50.0 for metric in self.METRICS}
        self.evaluation_count = 0
        self.first_evaluation: Optional[int] = None
        self.last_evaluation: Optional[int] = None
        self.last_evaluation_summary: Optional[str] = None
        self.last_evaluation_reasoning: Optional[str] = None
        self.strengths: list[str] = []
        self.areas_for_improvement: list[str] = []

        # Load existing data if available
        self._load()

    def _load(self):
        """Load self-evaluation data from disk"""
        if self.self_eval_file.exists():
            try:
                with open(self.self_eval_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Load metrics
                self.metrics = data.get("metrics", {metric: 50.0 for metric in self.METRICS})
                self.evaluation_count = data.get("evaluation_count", 0)
                self.first_evaluation = data.get("first_evaluation")
                self.last_evaluation = data.get("last_evaluation")
                self.last_evaluation_summary = data.get("last_evaluation_summary")
                self.last_evaluation_reasoning = data.get("last_evaluation_reasoning")
                self.strengths = data.get("strengths", [])
                self.areas_for_improvement = data.get("areas_for_improvement", [])

                logger.debug(f"[SELF_EVAL] Loaded for {self.qube_id}: {self.evaluation_count} evaluations")
            except Exception as e:
                logger.error(f"[SELF_EVAL] Failed to load: {e}")

    def _save(self):
        """Save self-evaluation data to disk"""
        try:
            data = {
                "qube_id": self.qube_id,
                "metrics": self.metrics,
                "evaluation_count": self.evaluation_count,
                "first_evaluation": self.first_evaluation,
                "last_evaluation": self.last_evaluation,
                "last_evaluation_summary": self.last_evaluation_summary,
                "last_evaluation_reasoning": self.last_evaluation_reasoning,
                "strengths": self.strengths,
                "areas_for_improvement": self.areas_for_improvement
            }

            with open(self.self_eval_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"[SELF_EVAL] Saved for {self.qube_id}")
        except Exception as e:
            logger.error(f"[SELF_EVAL] Failed to save: {e}")

    def update_from_ai_evaluation(self, evaluation_data: Dict[str, Any], block_number: int):
        """
        Update metrics from AI evaluation

        Args:
            evaluation_data: Dict containing AI evaluation results
            block_number: Block number where evaluation occurred
        """
        current_time = int(datetime.now(timezone.utc).timestamp())

        # Update metrics
        if "metrics" in evaluation_data:
            for metric, value in evaluation_data["metrics"].items():
                if metric in self.metrics:
                    # Ensure value is in 0-100 range
                    self.metrics[metric] = max(0.0, min(100.0, float(value)))

        # Update evaluation metadata
        self.evaluation_count += 1
        if self.first_evaluation is None:
            self.first_evaluation = current_time
        self.last_evaluation = current_time

        # Store evaluation summary and reasoning
        self.last_evaluation_summary = evaluation_data.get("evaluation_summary", "")
        self.last_evaluation_reasoning = evaluation_data.get("reasoning", "")
        self.strengths = evaluation_data.get("strengths", [])
        self.areas_for_improvement = evaluation_data.get("areas_for_improvement", [])

        # Save to disk
        self._save()

        # Create snapshot
        self._create_snapshot(block_number, evaluation_data)

        logger.info(
            f"[SELF_EVAL] Updated for {self.qube_id}",
            extra={
                "evaluation_count": self.evaluation_count,
                "avg_score": sum(self.metrics.values()) / len(self.metrics)
            }
        )

    def _create_snapshot(self, block_number: int, evaluation_data: Dict[str, Any]):
        """
        Create snapshot for timeline visualization

        Args:
            block_number: Block number where evaluation occurred
            evaluation_data: Full evaluation data
        """
        try:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            snapshot_file = self.snapshots_dir / f"evaluation_snapshot_{block_number}_{timestamp}.json"

            snapshot = {
                "block_number": block_number,
                "timestamp": timestamp,
                "metrics": self.metrics.copy(),
                "evaluation_summary": evaluation_data.get("evaluation_summary", ""),
                "reasoning": evaluation_data.get("reasoning", ""),
                "strengths": evaluation_data.get("strengths", []),
                "areas_for_improvement": evaluation_data.get("areas_for_improvement", [])
            }

            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2)

            logger.debug(f"[SELF_EVAL] Created snapshot at block {block_number}")
        except Exception as e:
            logger.error(f"[SELF_EVAL] Failed to create snapshot: {e}")

    def get_metrics(self) -> Dict[str, float]:
        """Get current metric values"""
        return self.metrics.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get evaluation summary for display"""
        return {
            "qube_id": self.qube_id,
            "metrics": self.metrics.copy(),
            "evaluation_count": self.evaluation_count,
            "first_evaluation": self.first_evaluation,
            "last_evaluation": self.last_evaluation,
            "last_evaluation_summary": self.last_evaluation_summary,
            "last_evaluation_reasoning": self.last_evaluation_reasoning,
            "strengths": self.strengths.copy() if self.strengths else [],
            "areas_for_improvement": self.areas_for_improvement.copy() if self.areas_for_improvement else [],
            "overall_score": sum(self.metrics.values()) / len(self.metrics) if self.metrics else 50.0
        }

    def get_timeline(self) -> list[Dict[str, Any]]:
        """
        Get self-evaluation timeline from snapshots

        Returns:
            List of snapshot data points sorted by timestamp
        """
        timeline = []

        try:
            # Read all snapshot files
            for snapshot_file in sorted(self.snapshots_dir.glob("*.json")):
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    snapshot = json.load(f)
                    timeline.append(snapshot)

            # Sort by timestamp
            timeline.sort(key=lambda x: x.get("timestamp", 0))

            logger.debug(f"[SELF_EVAL] Loaded {len(timeline)} timeline points")
        except Exception as e:
            logger.error(f"[SELF_EVAL] Failed to load timeline: {e}")

        return timeline
