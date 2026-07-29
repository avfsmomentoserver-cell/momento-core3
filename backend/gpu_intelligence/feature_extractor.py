"""GPU-accelerated feature extraction pipeline.

Implements high-performance feature extraction using GPU acceleration for
pattern detection, statistical analysis, and signal processing.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .config import GPUConfig
from .device_manager import DeviceManager
from .memory_pool import GPUMemoryPool

logger = logging.getLogger(__name__)


@dataclass
class FeatureExtractionResult:
    """Result from feature extraction."""
    features: Dict[str, Any]
    extraction_time_ms: float
    batch_size: int
    device_id: int
    used_gpu: bool


class GPUFeatureExtractor:
    """GPU-accelerated feature extraction for ML workloads.

    Provides optimized implementations of common feature extraction operations:
    - Statistical features (mean, std, percentiles)
    - Pattern detection (ladders, streaks, regimes)
    - Signal processing (moving averages, derivatives)
    - Distance metrics for pattern matching
    """

    def __init__(
        self,
        device_manager: DeviceManager,
        memory_pool: GPUMemoryPool,
        config: Optional[GPUConfig] = None,
    ):
        """Initialize feature extractor.

        Args:
            device_manager: Device manager instance
            memory_pool: Memory pool instance
            config: GPU configuration
        """
        self.device_manager = device_manager
        self.memory_pool = memory_pool
        self.config = config or GPUConfig()

        # Feature extraction cache
        self._feature_cache: Dict[str, Any] = {}

        # Try to import GPU libraries
        self._torch = None
        self._cupy = None
        self._initialize_gpu_libraries()

    def _initialize_gpu_libraries(self) -> None:
        """Initialize GPU libraries for feature extraction."""
        try:
            import torch

            self._torch = torch
            logger.info("PyTorch available for GPU feature extraction")
        except ImportError:
            logger.warning("PyTorch not available, using CPU fallback")

        try:
            import cupy as cp

            self._cupy = cp
            logger.info("CuPy available for GPU feature extraction")
        except ImportError:
            logger.debug("CuPy not available")

    def extract_features(
        self,
        data: Sequence[float],
        feature_names: Optional[List[str]] = None,
    ) -> FeatureExtractionResult:
        """Extract features from data.

        Args:
            data: Input data sequence (e.g., multipliers)
            feature_names: List of features to extract (None = all)

        Returns:
            FeatureExtractionResult with extracted features
        """
        import time

        start_time = time.time()
        device_id = self.device_manager.get_current_device() or 0
        used_gpu = False

        if not data:
            return FeatureExtractionResult(
                features={},
                extraction_time_ms=0.0,
                batch_size=0,
                device_id=device_id,
                used_gpu=False,
            )

        # Default feature set
        if feature_names is None:
            feature_names = [
                "mean",
                "std",
                "median",
                "min",
                "max",
                "range",
                "percentiles",
                "skewness",
                "kurtosis",
                "momentum",
                "volatility",
                "trend",
            ]

        features = {}

        # Try GPU extraction if available
        if self._torch and self.device_manager.is_available:
            try:
                features, used_gpu = self._extract_with_torch(data, feature_names)
            except Exception as e:
                logger.warning(f"GPU extraction failed, falling back to CPU: {e}")
                features = self._extract_with_numpy(data, feature_names)
        else:
            features = self._extract_with_numpy(data, feature_names)

        extraction_time_ms = (time.time() - start_time) * 1000

        return FeatureExtractionResult(
            features=features,
            extraction_time_ms=extraction_time_ms,
            batch_size=len(data),
            device_id=device_id,
            used_gpu=used_gpu,
        )

    def _extract_with_torch(
        self, data: Sequence[float], feature_names: List[str]
    ) -> Tuple[Dict[str, Any], bool]:
        """Extract features using PyTorch on GPU.

        Args:
            data: Input data
            feature_names: Features to extract

        Returns:
            Tuple of (features dict, used_gpu flag)
        """
        import torch

        device_id = self.device_manager.get_current_device() or 0
        device = f"cuda:{device_id}"

        # Convert to tensor
        tensor = torch.tensor(data, dtype=torch.float32, device=device)

        features = {}

        # Statistical features
        if "mean" in feature_names:
            features["mean"] = torch.mean(tensor).cpu().item()

        if "std" in feature_names:
            features["std"] = torch.std(tensor).cpu().item()

        if "median" in feature_names:
            features["median"] = torch.median(tensor).cpu().item()

        if "min" in feature_names:
            features["min"] = torch.min(tensor).cpu().item()

        if "max" in feature_names:
            features["max"] = torch.max(tensor).cpu().item()

        if "range" in feature_names:
            features["range"] = (torch.max(tensor) - torch.min(tensor)).cpu().item()

        # Percentiles
        if "percentiles" in feature_names:
            sorted_tensor, _ = torch.sort(tensor)
            n = len(sorted_tensor)
            features["percentiles"] = {
                "p05": sorted_tensor[int(n * 0.05)].cpu().item(),
                "p10": sorted_tensor[int(n * 0.10)].cpu().item(),
                "p25": sorted_tensor[int(n * 0.25)].cpu().item(),
                "p50": sorted_tensor[int(n * 0.50)].cpu().item(),
                "p75": sorted_tensor[int(n * 0.75)].cpu().item(),
                "p90": sorted_tensor[int(n * 0.90)].cpu().item(),
                "p95": sorted_tensor[int(n * 0.95)].cpu().item(),
            }

        # Higher-order moments
        if "skewness" in feature_names:
            mean = torch.mean(tensor)
            std = torch.std(tensor)
            if std > 0:
                skew = torch.mean(((tensor - mean) / std) ** 3)
                features["skewness"] = skew.cpu().item()
            else:
                features["skewness"] = 0.0

        if "kurtosis" in feature_names:
            mean = torch.mean(tensor)
            std = torch.std(tensor)
            if std > 0:
                kurt = torch.mean(((tensor - mean) / std) ** 4) - 3
                features["kurtosis"] = kurt.cpu().item()
            else:
                features["kurtosis"] = 0.0

        # Momentum and trend
        if "momentum" in feature_names:
            if len(tensor) > 1:
                momentum = (tensor[-1] - tensor[0]) / tensor[0] if tensor[0] > 0 else 0
                features["momentum"] = momentum.cpu().item()
            else:
                features["momentum"] = 0.0

        if "volatility" in feature_names:
            if len(tensor) > 1:
                log_returns = torch.log(tensor[1:] / tensor[:-1] + 1e-8)
                features["volatility"] = torch.std(log_returns).cpu().item()
            else:
                features["volatility"] = 0.0

        if "trend" in feature_names:
            if len(tensor) > 1:
                # Linear regression slope
                x = torch.arange(len(tensor), dtype=torch.float32, device=device)
                x_mean = torch.mean(x)
                y_mean = torch.mean(tensor)
                numerator = torch.sum((x - x_mean) * (tensor - y_mean))
                denominator = torch.sum((x - x_mean) ** 2)
                slope = (
                    (numerator / denominator).cpu().item() if denominator > 0 else 0.0
                )
                features["trend"] = slope
            else:
                features["trend"] = 0.0

        return features, True

    def _extract_with_numpy(
        self, data: Sequence[float], feature_names: List[str]
    ) -> Dict[str, Any]:
        """Extract features using NumPy on CPU.

        Args:
            data: Input data
            feature_names: Features to extract

        Returns:
            Features dictionary
        """
        arr = np.array(data, dtype=np.float32)
        features = {}

        # Statistical features
        if "mean" in feature_names:
            features["mean"] = float(np.mean(arr))

        if "std" in feature_names:
            features["std"] = float(np.std(arr))

        if "median" in feature_names:
            features["median"] = float(np.median(arr))

        if "min" in feature_names:
            features["min"] = float(np.min(arr))

        if "max" in feature_names:
            features["max"] = float(np.max(arr))

        if "range" in feature_names:
            features["range"] = float(np.max(arr) - np.min(arr))

        # Percentiles
        if "percentiles" in feature_names:
            features["percentiles"] = {
                "p05": float(np.percentile(arr, 5)),
                "p10": float(np.percentile(arr, 10)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75)),
                "p90": float(np.percentile(arr, 90)),
                "p95": float(np.percentile(arr, 95)),
            }

        # Higher-order moments
        if "skewness" in feature_names:
            from scipy import stats

            features["skewness"] = float(stats.skew(arr))

        if "kurtosis" in feature_names:
            from scipy import stats

            features["kurtosis"] = float(stats.kurtosis(arr))

        # Momentum and trend
        if "momentum" in feature_names:
            if len(arr) > 1 and arr[0] > 0:
                features["momentum"] = float((arr[-1] - arr[0]) / arr[0])
            else:
                features["momentum"] = 0.0

        if "volatility" in feature_names:
            if len(arr) > 1:
                log_returns = np.log(arr[1:] / arr[:-1] + 1e-8)
                features["volatility"] = float(np.std(log_returns))
            else:
                features["volatility"] = 0.0

        if "trend" in feature_names:
            if len(arr) > 1:
                x = np.arange(len(arr))
                slope = np.polyfit(x, arr, 1)[0]
                features["trend"] = float(slope)
            else:
                features["trend"] = 0.0

        return features

    def extract_batch_features(
        self,
        data_batch: Sequence[Sequence[float]],
        feature_names: Optional[List[str]] = None,
    ) -> List[FeatureExtractionResult]:
        """Extract features from a batch of data.

        Args:
            data_batch: Batch of input sequences
            feature_names: Features to extract

        Returns:
            List of FeatureExtractionResult
        """
        results = []
        for data in data_batch:
            result = self.extract_features(data, feature_names)
            results.append(result)
        return results

    def detect_patterns_gpu(
        self,
        data: Sequence[float],
        pattern_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Detect patterns in data using GPU acceleration.

        Args:
            data: Input data sequence
            pattern_types: Patterns to detect (ladders, streaks, etc.)

        Returns:
            Dictionary with detected patterns
        """
        if pattern_types is None:
            pattern_types = ["ladder", "streak", "regime", "spike"]

        patterns = {}

        # Try GPU pattern detection
        if self._torch and self.device_manager.is_available:
            patterns = self._detect_patterns_torch(data, pattern_types)
        else:
            patterns = self._detect_patterns_numpy(data, pattern_types)

        return patterns

    def _detect_patterns_torch(
        self, data: Sequence[float], pattern_types: List[str]
    ) -> Dict[str, Any]:
        """Detect patterns using PyTorch on GPU.

        Args:
            data: Input data
            pattern_types: Patterns to detect

        Returns:
            Dictionary with detected patterns
        """
        import torch

        device_id = self.device_manager.get_current_device() or 0
        device = f"cuda:{device_id}"
        tensor = torch.tensor(data, dtype=torch.float32, device=device)

        patterns = {}

        # Ladder detection (ascending sequence)
        if "ladder" in pattern_types:
            diffs = torch.diff(tensor)
            # Count consecutive positive differences
            ladder_length = 0
            for diff in diffs:
                if diff > 0:
                    ladder_length += 1
                else:
                    break
            patterns["ladder"] = {
                "detected": ladder_length >= 3,
                "length": ladder_length,
                "strength": ladder_length / len(data) if len(data) > 0 else 0,
            }

        # Streak detection
        if "streak" in pattern_types:
            mean = torch.mean(tensor)
            below_mean = tensor < mean
            # Find longest consecutive sequence
            streak = 0
            max_streak = 0
            for value in below_mean:
                if value:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            patterns["streak"] = {
                "current_streak": streak,
                "max_streak": max_streak,
                "threshold": mean.cpu().item(),
            }

        # Spike detection
        if "spike" in pattern_types:
            std = torch.std(tensor)
            mean = torch.mean(tensor)
            z_scores = torch.abs((tensor - mean) / (std + 1e-8))
            spike_threshold = 2.0  # 2 standard deviations
            spikes = torch.sum(z_scores > spike_threshold).cpu().item()
            patterns["spike"] = {
                "count": int(spikes),
                "threshold": spike_threshold,
                "fraction": spikes / len(data) if len(data) > 0 else 0,
            }

        return patterns

    def _detect_patterns_numpy(
        self, data: Sequence[float], pattern_types: List[str]
    ) -> Dict[str, Any]:
        """Detect patterns using NumPy on CPU.

        Args:
            data: Input data
            pattern_types: Patterns to detect

        Returns:
            Dictionary with detected patterns
        """
        arr = np.array(data, dtype=np.float32)
        patterns = {}

        # Ladder detection
        if "ladder" in pattern_types:
            diffs = np.diff(arr)
            ladder_length = 0
            for diff in diffs:
                if diff > 0:
                    ladder_length += 1
                else:
                    break
            patterns["ladder"] = {
                "detected": ladder_length >= 3,
                "length": ladder_length,
                "strength": ladder_length / len(arr) if len(arr) > 0 else 0,
            }

        # Streak detection
        if "streak" in pattern_types:
            mean = np.mean(arr)
            below_mean = arr < mean
            streak = 0
            max_streak = 0
            for value in below_mean:
                if value:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 0
            patterns["streak"] = {
                "current_streak": streak,
                "max_streak": max_streak,
                "threshold": float(mean),
            }

        # Spike detection
        if "spike" in pattern_types:
            std = np.std(arr)
            mean = np.mean(arr)
            z_scores = np.abs((arr - mean) / (std + 1e-8))
            spikes = np.sum(z_scores > 2.0)
            patterns["spike"] = {
                "count": int(spikes),
                "threshold": 2.0,
                "fraction": spikes / len(arr) if len(arr) > 0 else 0,
            }

        return patterns

    def compute_distance_matrix(
        self,
        sequences: Sequence[Sequence[float]],
        metric: str = "euclidean",
    ) -> np.ndarray:
        """Compute pairwise distance matrix for sequences.

        Args:
            sequences: List of sequences
            metric: Distance metric (euclidean, cosine, dtw)

        Returns:
            Distance matrix as numpy array
        """
        from scipy.spatial.distance import pdist, squareform

        # Pad sequences to same length
        max_len = max(len(seq) for seq in sequences)
        padded = []
        for seq in sequences:
            if len(seq) < max_len:
                padded_seq = list(seq) + [0.0] * (max_len - len(seq))
            else:
                padded_seq = list(seq)
            padded.append(padded_seq)

        # Compute distances
        dist_matrix = squareform(pdist(padded, metric=metric))
        return dist_matrix

    def __repr__(self) -> str:
        return (
            f"GPUFeatureExtractor("
            f"gpu_available={self.device_manager.is_available}, "
            f"torch_available={self._torch is not None}, "
            f"cupy_available={self._cupy is not None})"
        )
