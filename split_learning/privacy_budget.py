"""
Differential Privacy Budget Exhaustion Monitoring for Split Learning.
Tracks cumulative privacy expenditure across split learning epochs.
Domain: Privacy-Preserving Federated Healthcare & FHE
Standard: HIPAA Safe Harbor / Google SecAgg Standards
"""
import logging
import math
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CompositionMethod(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    RDP = "rdp"


@dataclass
class PrivacyEvent:
    """Record of a privacy-relevant event."""
    epoch: int
    layer_name: str
    epsilon_consumed: float
    delta: float
    noise_scale: float
    clipping_norm: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class BudgetConfig:
    """Configuration for privacy budget tracking."""
    total_epsilon: float = 10.0
    total_delta: float = 1e-5
    composition_method: CompositionMethod = CompositionMethod.ADVANCED
    alert_threshold: float = 0.8  # alert at 80% budget consumption
    auto_halt_enabled: bool = True


class PrivacyBudgetTracker:
    """Track cumulative privacy expenditure across split learning epochs."""

    def __init__(self, config: Optional[BudgetConfig] = None):
        self.config = config or BudgetConfig()
        self.cumulative_epsilon: float = 0.0
        self.cumulative_delta: float = 0.0
        self.events: List[PrivacyEvent] = []
        self.epoch_count: int = 0
        self.alerts: List[Dict[str, Any]] = []
        self.per_layer_leakage: Dict[str, float] = {}

    def consume_budget(
        self,
        epoch: int,
        layer_name: str,
        noise_scale: float,
        clipping_norm: float,
        num_samples: int,
    ) -> Dict[str, Any]:
        """Record privacy consumption for a training step."""
        if self.config.composition_method == CompositionMethod.BASIC:
            step_epsilon = clipping_norm / noise_scale
        elif self.config.composition_method == CompositionMethod.ADVANCED:
            step_epsilon = clipping_norm / noise_scale
            step_epsilon *= math.sqrt(2 * math.log(1.0 / self.config.total_delta))
        else:
            step_epsilon = clipping_norm / noise_scale

        event = PrivacyEvent(
            epoch=epoch,
            layer_name=layer_name,
            epsilon_consumed=step_epsilon,
            delta=self.config.total_delta,
            noise_scale=noise_scale,
            clipping_norm=clipping_norm,
        )
        self.events.append(event)

        if self.config.composition_method == CompositionMethod.BASIC:
            self.cumulative_epsilon += step_epsilon
        else:
            k = len(self.events)
            self.cumulative_epsilon = math.sqrt(2 * k * math.log(1.0 / self.config.total_delta)) * step_epsilon

        self.cumulative_delta += self.config.total_delta
        self.epoch_count = max(self.epoch_count, epoch)

        if layer_name not in self.per_layer_leakage:
            self.per_layer_leakage[layer_name] = 0.0
        self.per_layer_leakage[layer_name] += step_epsilon

        result = {
            "cumulative_epsilon": self.cumulative_epsilon,
            "remaining_epsilon": max(0, self.config.total_epsilon - self.cumulative_epsilon),
            "budget_fraction_used": self.cumulative_epsilon / self.config.total_epsilon,
            "epochs_completed": self.epoch_count,
            "per_layer_leakage": dict(self.per_layer_leakage),
        }

        fraction_used = self.cumulative_epsilon / self.config.total_epsilon
        if fraction_used >= self.config.alert_threshold:
            alert = {
                "type": "budget_warning",
                "message": f"Privacy budget {fraction_used:.1%} consumed",
                "cumulative_epsilon": self.cumulative_epsilon,
                "total_epsilon": self.config.total_epsilon,
                "timestamp": time.time(),
            }
            self.alerts.append(alert)
            logger.warning(f"Privacy budget alert: {alert['message']}")

        if self.config.auto_halt_enabled and self.cumulative_epsilon >= self.config.total_epsilon:
            result["halt_training"] = True
            logger.error("Privacy budget exhausted! Training should be halted.")
        else:
            result["halt_training"] = False

        return result

    def get_status(self) -> Dict[str, Any]:
        """Get current privacy budget status."""
        return {
            "cumulative_epsilon": self.cumulative_epsilon,
            "cumulative_delta": self.cumulative_delta,
            "remaining_epsilon": max(0, self.config.total_epsilon - self.cumulative_epsilon),
            "total_epsilon": self.config.total_epsilon,
            "total_delta": self.config.total_delta,
            "budget_fraction_used": self.cumulative_epsilon / self.config.total_epsilon,
            "epochs_completed": self.epoch_count,
            "total_events": len(self.events),
            "per_layer_leakage": dict(self.per_layer_leakage),
            "alerts": list(self.alerts),
            "composition_method": self.config.composition_method.value,
        }

    def get_layer_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Get per-layer privacy leakage breakdown."""
        breakdown = {}
        for layer, epsilon in self.per_layer_leakage.items():
            breakdown[layer] = {
                "cumulative_epsilon": epsilon,
                "fraction_of_total": epsilon / max(self.cumulative_epsilon, 1e-10),
            }
        return breakdown

    def forecast_exhaustion(self, current_rate: float) -> Dict[str, Any]:
        """Forecast when budget will be exhausted at current consumption rate."""
        remaining = max(0, self.config.total_epsilon - self.cumulative_epsilon)
        if current_rate <= 0:
            return {"remaining_epochs": float("inf"), "exhaustion_date": "never"}
        remaining_epochs = remaining / current_rate
        return {
            "remaining_epochs": remaining_epochs,
            "current_rate_per_epoch": current_rate,
            "remaining_budget": remaining,
        }
