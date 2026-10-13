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
    """Track pure-DP composition bounds for a Laplace-mechanism model.

    This is not a proof of privacy for an arbitrary split-learning or DP-SGD
    training workflow. RDP mode uses the conservative basic bound.
    """

    def __init__(self, config: Optional[BudgetConfig] = None):
        self.config = config or BudgetConfig()
        if (not math.isfinite(self.config.total_epsilon) or self.config.total_epsilon <= 0
                or not 0 < self.config.total_delta < 1
                or not 0 < self.config.alert_threshold <= 1):
            raise ValueError("Invalid privacy budget configuration")
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
        if (not isinstance(epoch, int) or epoch < 0 or not layer_name.strip()
                or not isinstance(num_samples, int) or num_samples < 1):
            raise ValueError("Invalid epoch, layer name, or sample count")
        if (not math.isfinite(noise_scale) or noise_scale <= 0
                or not math.isfinite(clipping_norm) or clipping_norm < 0):
            raise ValueError("Noise scale must be positive and clipping norm nonnegative")
        if self.config.auto_halt_enabled and self.cumulative_epsilon >= self.config.total_epsilon:
            raise RuntimeError("Privacy budget already exhausted")
        # This assumes a pure-DP mechanism with sensitivity=clipping_norm and
        # Laplace noise scale=noise_scale; it is not an RDP/DP-SGD accountant.
        step_epsilon = clipping_norm / noise_scale

        event = PrivacyEvent(
            epoch=epoch,
            layer_name=layer_name,
            epsilon_consumed=step_epsilon,
            delta=0.0,
            noise_scale=noise_scale,
            clipping_norm=clipping_norm,
        )
        self.events.append(event)

        epsilons = [e.epsilon_consumed for e in self.events]
        basic_bound = sum(epsilons)
        if self.config.composition_method == CompositionMethod.ADVANCED:
            # Advanced composition for heterogeneous pure-DP mechanisms.
            # Min with basic composition never provides a weaker bound.
            if max(epsilons) < 50:
                advanced_bound = (
                    math.sqrt(2 * math.log(1 / self.config.total_delta) * sum(e * e for e in epsilons))
                    + sum(e * math.expm1(e) for e in epsilons)
                )
                self.cumulative_epsilon = min(basic_bound, advanced_bound)
            else:
                self.cumulative_epsilon = basic_bound
            self.cumulative_delta = self.config.total_delta
        else:
            # RDP selected without Renyi orders: use the conservative pure-DP
            # composition bound, rather than reporting a fictitious RDP value.
            self.cumulative_epsilon = basic_bound
            self.cumulative_delta = 0.0
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
                "fraction_of_total": epsilon / max(sum(self.per_layer_leakage.values()), 1e-10),
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
