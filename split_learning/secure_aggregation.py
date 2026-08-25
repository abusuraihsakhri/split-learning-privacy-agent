"""
Secure Aggregation for Cut-Layer Activations using Shamir's Secret Sharing.
Protects smashed data at the cut layer during split learning.
Domain: Privacy-Preserving Federated Healthcare & FHE
Standard: HIPAA Safe Harbor / Google SecAgg Standards
"""
import hashlib
import logging
import secrets
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ActivationShare:
    """A Shamir secret share of a cut-layer activation vector."""
    client_id: str
    share_index: int
    share_values: np.ndarray  # shares of the activation vector
    commitment: List[int]     # Feldman commitment for verification
    timestamp: float = field(default_factory=time.time)


@dataclass
class SecureAggConfig:
    """Configuration for secure aggregation of activations."""
    prime: int = 2**61 - 1
    threshold_fraction: float = 0.5
    padding_enabled: bool = True
    share_refresh_enabled: bool = True


class ShamirSecretSharing:
    """Shamir's Secret Sharing over GF(p) for activation vectors."""

    def __init__(self, prime: int = 2**61 - 1):
        self.prime = prime

    def split_vector(
        self, values: np.ndarray, num_shares: int, threshold: int
    ) -> List[np.ndarray]:
        """Split a vector of values into n shares with threshold t."""
        flat = values.flatten().astype(np.int64)
        all_shares = []
        for _ in range(num_shares):
            all_shares.append(np.zeros(len(flat), dtype=np.int64))

        for idx in range(len(flat)):
            secret = int(flat[idx]) % self.prime
            coefficients = [secret]
            for _ in range(threshold - 1):
                coefficients.append(secrets.randbelow(self.prime))
            for share_idx in range(num_shares):
                x = share_idx + 1
                value = 0
                for power, coeff in enumerate(coefficients):
                    value = (value + coeff * pow(x, power, self.prime)) % self.prime
                all_shares[share_idx][idx] = value

        return [s.reshape(values.shape) for s in all_shares]

    def reconstruct_vector(
        self, shares: List[Tuple[int, np.ndarray]]
    ) -> np.ndarray:
        """Reconstruct vector from shares using Lagrange interpolation."""
        if not shares:
            raise ValueError("No shares provided")
        shape = shares[0][1].shape
        flat_shares = [(idx, s.flatten().astype(np.int64)) for idx, s in shares]
        n = len(flat_shares[0][1])
        result = np.zeros(n, dtype=np.int64)

        for i, (xi, yi) in enumerate(flat_shares):
            numerator = 1
            denominator = 1
            for j, (xj, _) in enumerate(flat_shares):
                if i != j:
                    numerator = (numerator * (-xj)) % self.prime
                    denominator = (denominator * (xi - xj)) % self.prime
            lagrange = (numerator * pow(int(denominator), -1, self.prime)) % self.prime
            result = (result + yi * lagrange) % self.prime

        return result.reshape(shape)


class SecureActivationAggregator:
    """Secure aggregation for cut-layer activations in split learning."""

    def __init__(self, config: Optional[SecureAggConfig] = None):
        self.config = config or SecureAggConfig()
        self.sss = ShamirSecretSharing(self.prime)
        self.client_shares: Dict[str, List[ActivationShare]] = {}
        self.max_activation_dim: int = 0

    @property
    def prime(self) -> int:
        return self.config.prime

    def register_client(self, client_id: str, activation_dim: int):
        """Register a client with its activation dimensionality."""
        self.max_activation_dim = max(self.max_activation_dim, activation_dim)
        logger.info(
            f"Client {client_id} registered with dim={activation_dim}, "
            f"max_dim={self.max_activation_dim}"
        )

    def pad_activations(self, activations: np.ndarray) -> np.ndarray:
        """Pad activations to maximum dimension for uniform sharing."""
        if not self.config.padding_enabled:
            return activations
        current_dim = activations.shape[-1]
        if current_dim < self.max_activation_dim:
            pad_width = [(0, 0)] * (len(activations.shape) - 1) + [
                (0, self.max_activation_dim - current_dim)
            ]
            return np.pad(activations, pad_width, mode="constant", constant_values=0)
        return activations

    def generate_shares(
        self,
        client_id: str,
        activations: np.ndarray,
        num_participants: int,
    ) -> List[ActivationShare]:
        """Generate Shamir shares of a client's smashed data."""
        threshold = max(2, int(num_participants * self.config.threshold_fraction) + 1)
        padded = self.pad_activations(activations)
        share_arrays = self.sss.split_vector(padded, num_participants, threshold)

        shares = []
        for i, share_arr in enumerate(share_arrays):
            share = ActivationShare(
                client_id=client_id,
                share_index=i + 1,
                share_values=share_arr,
                commitment=[],  # simplified
            )
            shares.append(share)

        if client_id not in self.client_shares:
            self.client_shares[client_id] = []
        self.client_shares[client_id] = shares
        return shares

    def aggregate_shares(
        self,
        all_shares: List[List[ActivationShare]],
        num_participants: int,
    ) -> np.ndarray:
        """Aggregate shares from all clients to reconstruct summed activations."""
        threshold = max(2, int(num_participants * self.config.threshold_fraction) + 1)
        aggregated = None
        for client_shares in all_shares:
            selected = client_shares[:threshold]
            share_tuples = [(s.share_index, s.share_values) for s in selected]
            reconstructed = self.sss.reconstruct_vector(share_tuples)
            if aggregated is None:
                aggregated = reconstructed.astype(np.float64)
            else:
                aggregated += reconstructed.astype(np.float64)
        if aggregated is not None:
            aggregated /= len(all_shares)
        return aggregated

    def refresh_shares(self, client_id: str, activations: np.ndarray, num_participants: int) -> List[ActivationShare]:
        """Refresh shares after each forward/backward pass."""
        return self.generate_shares(client_id, activations, num_participants)
