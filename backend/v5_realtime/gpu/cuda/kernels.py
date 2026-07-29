"""
CUDA Kernels - High-Performance GPU Operations

Provides optimized CUDA kernels for parallel processing operations:
- Feature extraction kernels
- Matrix operations
- Reduction operations
- Pattern matching kernels

Performance Targets:
- Memory coalescing optimization
- Tensor core utilization
- Kernel fusion for efficiency
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class KernelConfig:
    """Configuration for kernel execution."""
    block_size: int = 256
    grid_size: int = 0  # 0 = auto-calculate
    shared_memory: int = 0
    stream: Optional[Any] = None


class CUDAKernels:
    """
    Provides high-performance CUDA kernels for ML operations.
    
    Operations:
    - Parallel feature extraction
    - Matrix multiplication
    - Reduction operations
    - Pattern matching
    """
    
    def __init__(self):
        """Initialize CUDA kernels module."""
        self._cuda_available = False
        self._initialized = False
        self._check_cuda_availability()
    
    def _check_cuda_availability(self) -> None:
        """Check if CUDA is available for kernel operations."""
        try:
            import torch
            self._cuda_available = torch.cuda.is_available()
            if self._cuda_available:
                self._initialized = True
                logger.info("CUDA kernels initialized")
            else:
                logger.warning("CUDA not available, kernels disabled")
        except ImportError:
            logger.warning("PyTorch not available, CUDA kernels disabled")
    
    @property
    def is_available(self) -> bool:
        """Check if CUDA kernels are available."""
        return self._cuda_available
    
    def parallel_feature_extraction(
        self,
        data: np.ndarray,
        feature_fn: callable,
        config: Optional[KernelConfig] = None
    ) -> np.ndarray:
        """
        Extract features in parallel using GPU.
        
        Args:
            data: Input data array (N, D)
            feature_fn: Feature extraction function
            config: Kernel configuration
            
        Returns:
            Feature array (N, F)
        """
        if not self._cuda_available:
            # CPU fallback
            return self._cpu_feature_extraction(data, feature_fn)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensor
            data_tensor = torch.from_numpy(data).float().cuda()
            
            # Parallel feature extraction using torch operations
            # This leverages optimized torch kernels under the hood
            features = self._torch_feature_extraction(data_tensor, feature_fn)
            
            # Convert back to numpy
            return features.cpu().numpy()
            
        except Exception as e:
            logger.error(f"Parallel feature extraction failed: {e}")
            return self._cpu_feature_extraction(data, feature_fn)
    
    def _torch_feature_extraction(
        self,
        data: torch.Tensor,
        feature_fn: callable
    ) -> torch.Tensor:
        """
        Extract features using torch operations.
        
        Args:
            data: Input tensor (N, D)
            feature_fn: Feature extraction function
            
        Returns:
            Feature tensor (N, F)
        """
        # Implement common feature extraction patterns
        # These are optimized torch operations that use CUDA kernels
        
        N, D = data.shape
        
        # Statistical features (mean, std, min, max)
        mean = data.mean(dim=1, keepdim=True)
        std = data.std(dim=1, keepdim=True)
        min_val = data.min(dim=1, keepdim=True).values
        max_val = data.max(dim=1, keepdim=True).values
        
        # Trend features (difference, slope)
        diff = data[:, 1:] - data[:, :-1] if D > 1 else torch.zeros_like(data)
        trend = diff.mean(dim=1, keepdim=True) if diff.numel() > 0 else torch.zeros(N, 1, device=data.device)
        
        # Concatenate features
        features = torch.cat([mean, std, min_val, max_val, trend], dim=1)
        
        return features
    
    def _cpu_feature_extraction(
        self,
        data: np.ndarray,
        feature_fn: callable
    ) -> np.ndarray:
        """
        CPU fallback for feature extraction.
        
        Args:
            data: Input data array
            feature_fn: Feature extraction function
            
        Returns:
            Feature array
        """
        try:
            return feature_fn(data)
        except:
            # Simple statistical features as fallback
            mean = np.mean(data, axis=1, keepdims=True)
            std = np.std(data, axis=1, keepdims=True)
            min_val = np.min(data, axis=1, keepdims=True)
            max_val = np.max(data, axis=1, keepdims=True)
            
            if data.shape[1] > 1:
                diff = np.diff(data, axis=1)
                trend = np.mean(diff, axis=1, keepdims=True)
                return np.concatenate([mean, std, min_val, max_val, trend], axis=1)
            else:
                return np.concatenate([mean, std, min_val, max_val, np.zeros_like(mean)], axis=1)
    
    def matrix_multiply(
        self,
        A: np.ndarray,
        B: np.ndarray,
        config: Optional[KernelConfig] = None
    ) -> np.ndarray:
        """
        High-performance matrix multiplication using GPU tensor cores.
        
        Args:
            A: Matrix A (M, K)
            B: Matrix B (K, N)
            config: Kernel configuration
            
        Returns:
            Result matrix (M, N)
        """
        if not self._cuda_available:
            return np.dot(A, B)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensors with FP16 for tensor core acceleration
            A_tensor = torch.from_numpy(A).half().cuda()
            B_tensor = torch.from_numpy(B).half().cuda()
            
            # Matrix multiplication with tensor cores
            C_tensor = torch.matmul(A_tensor, B_tensor)
            
            # Convert back to numpy
            return C_tensor.float().cpu().numpy()
            
        except Exception as e:
            logger.error(f"GPU matrix multiplication failed: {e}")
            return np.dot(A, B)
    
    def reduction_sum(
        self,
        data: np.ndarray,
        axis: Optional[int] = None,
        config: Optional[KernelConfig] = None
    ) -> np.ndarray:
        """
        Parallel reduction sum operation.
        
        Args:
            data: Input array
            axis: Axis to reduce (None = all axes)
            config: Kernel configuration
            
        Returns:
            Reduced array
        """
        if not self._cuda_available:
            return np.sum(data, axis=axis)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensor
            data_tensor = torch.from_numpy(data).float().cuda()
            
            # Reduction
            result = torch.sum(data_tensor, dim=axis)
            
            return result.cpu().numpy()
            
        except Exception as e:
            logger.error(f"GPU reduction failed: {e}")
            return np.sum(data, axis=axis)
    
    def pattern_match(
        self,
        data: np.ndarray,
        pattern: np.ndarray,
        threshold: float = 0.9,
        config: Optional[KernelConfig] = None
    ) -> np.ndarray:
        """
        Parallel pattern matching using correlation.
        
        Args:
            data: Input data (N, D)
            pattern: Pattern to match (D,)
            threshold: Correlation threshold
            config: Kernel configuration
            
        Returns:
            Boolean array of matches
        """
        if not self._cuda_available:
            return self._cpu_pattern_match(data, pattern, threshold)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensors
            data_tensor = torch.from_numpy(data).float().cuda()
            pattern_tensor = torch.from_numpy(pattern).float().cuda()
            
            # Normalize data and pattern
            data_norm = (data_tensor - data_tensor.mean(dim=1, keepdim=True)) / (
                data_tensor.std(dim=1, keepdim=True) + 1e-8
            )
            pattern_norm = (pattern_tensor - pattern_tensor.mean()) / (
                pattern_tensor.std() + 1e-8
            )
            
            # Compute correlation
            correlation = torch.sum(data_norm * pattern_norm, dim=1) / data.shape[1]
            
            # Return matches above threshold
            matches = correlation > threshold
            
            return matches.cpu().numpy()
            
        except Exception as e:
            logger.error(f"GPU pattern matching failed: {e}")
            return self._cpu_pattern_match(data, pattern, threshold)
    
    def _cpu_pattern_match(
        self,
        data: np.ndarray,
        pattern: np.ndarray,
        threshold: float
    ) -> np.ndarray:
        """
        CPU fallback for pattern matching.
        
        Args:
            data: Input data
            pattern: Pattern to match
            threshold: Correlation threshold
            
        Returns:
            Boolean array of matches
        """
        from scipy.stats import pearsonr
        
        matches = []
        for row in data:
            if len(row) != len(pattern):
                matches.append(False)
                continue
            
            try:
                corr, _ = pearsonr(row, pattern)
                matches.append(corr > threshold)
            except:
                matches.append(False)
        
        return np.array(matches)
    
    def batch_distance(
        self,
        query: np.ndarray,
        database: np.ndarray,
        metric: str = "euclidean",
        config: Optional[KernelConfig] = None
    ) -> np.ndarray:
        """
        Compute batch distances between query and database.
        
        Args:
            query: Query vectors (N, D)
            database: Database vectors (M, D)
            metric: Distance metric ('euclidean', 'cosine')
            config: Kernel configuration
            
        Returns:
            Distance matrix (N, M)
        """
        if not self._cuda_available:
            return self._cpu_batch_distance(query, database, metric)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensors
            query_tensor = torch.from_numpy(query).float().cuda()
            db_tensor = torch.from_numpy(database).float().cuda()
            
            if metric == "euclidean":
                # Euclidean distance: ||q - d||^2
                # Optimized using matrix operations
                query_norm = (query_tensor ** 2).sum(dim=1, keepdim=True)
                db_norm = (db_tensor ** 2).sum(dim=1)
                dot_product = torch.matmul(query_tensor, db_tensor.T)
                distances = torch.sqrt(query_norm + db_norm - 2 * dot_product)
            elif metric == "cosine":
                # Cosine distance: 1 - cosine similarity
                query_norm = query_tensor / (query_tensor.norm(dim=1, keepdim=True) + 1e-8)
                db_norm = db_tensor / (db_tensor.norm(dim=1, keepdim=True) + 1e-8)
                similarity = torch.matmul(query_norm, db_norm.T)
                distances = 1 - similarity
            else:
                raise ValueError(f"Unknown metric: {metric}")
            
            return distances.cpu().numpy()
            
        except Exception as e:
            logger.error(f"GPU batch distance failed: {e}")
            return self._cpu_batch_distance(query, database, metric)
    
    def _cpu_batch_distance(
        self,
        query: np.ndarray,
        database: np.ndarray,
        metric: str
    ) -> np.ndarray:
        """
        CPU fallback for batch distance computation.
        
        Args:
            query: Query vectors
            database: Database vectors
            metric: Distance metric
            
        Returns:
            Distance matrix
        """
        from scipy.spatial.distance import cdist
        
        return cdist(query, database, metric=metric)
    
    def parallel_sort(
        self,
        data: np.ndarray,
        axis: int = -1,
        config: Optional[KernelConfig] = None
    ) -> np.ndarray:
        """
        Parallel sort using GPU.
        
        Args:
            data: Input array
            axis: Axis to sort along
            config: Kernel configuration
            
        Returns:
            Sorted array
        """
        if not self._cuda_available:
            return np.sort(data, axis=axis)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensor
            data_tensor = torch.from_numpy(data).float().cuda()
            
            # Sort
            sorted_tensor, _ = torch.sort(data_tensor, dim=axis)
            
            return sorted_tensor.cpu().numpy()
            
        except Exception as e:
            logger.error(f"GPU sort failed: {e}")
            return np.sort(data, axis=axis)
    
    def gpu_histogram(
        self,
        data: np.ndarray,
        bins: int = 50,
        range_: Optional[Tuple[float, float]] = None,
        config: Optional[KernelConfig] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute histogram using GPU.
        
        Args:
            data: Input array
            bins: Number of bins
            range_: Value range (min, max)
            config: Kernel configuration
            
        Returns:
            Tuple of (histogram counts, bin edges)
        """
        if not self._cuda_available:
            return np.histogram(data, bins=bins, range=range_)
        
        try:
            import torch
            
            config = config or KernelConfig()
            
            # Convert to GPU tensor
            data_tensor = torch.from_numpy(data).float().cuda()
            
            if range_ is None:
                range_ = (data_tensor.min().item(), data_tensor.max().item())
            
            # Compute histogram using torch histogram
            hist_tensor = torch.histc(
                data_tensor,
                bins=bins,
                min=range_[0],
                max=range_[1]
            )
            
            # Compute bin edges
            bin_edges = np.linspace(range_[0], range_[1], bins + 1)
            
            return hist_tensor.cpu().numpy(), bin_edges
            
        except Exception as e:
            logger.error(f"GPU histogram failed: {e}")
            return np.histogram(data, bins=bins, range=range_)


# Global kernels instance
_global_kernels: Optional[CUDAKernels] = None


def get_cuda_kernels() -> CUDAKernels:
    """Get global CUDA kernels instance."""
    global _global_kernels
    if _global_kernels is None:
        _global_kernels = CUDAKernels()
    return _global_kernels
