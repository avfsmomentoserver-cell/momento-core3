# GPU Intelligence Module for Momento Core V5

## Overview

The GPU Intelligence module provides GPU-accelerated AI processing capabilities for the Momento Core platform, implementing V5 specifications for CUDA-based parallel processing, TensorRT optimization, and high-throughput inference.

## Features

### 1. CUDA Device Management
- Automatic GPU detection and initialization
- Support for NVIDIA A100, H100, V100, and RTX 4090
- Multi-GPU support with device context management
- Memory monitoring and synchronization

### 2. Memory Pooling
- Efficient memory allocation with pooling strategies
- Automatic defragmentation and garbage collection
- Memory pressure monitoring
- Configurable pool sizes and block management

### 3. TensorRT Optimization
- Model optimization for low-latency inference
- FP16/INT8 quantization support
- Layer fusion and kernel auto-tuning
- Dynamic batching for variable workloads
- PyTorch fallback when TensorRT unavailable

### 4. Batch Processing
- Dynamic batching with configurable timeouts
- Specialized AnalysisBatchProcessor for ML workloads
- Async processing with queue management
- Performance metrics and statistics

### 5. Feature Extraction
- GPU-accelerated statistical features (mean, std, percentiles)
- Pattern detection (ladders, streaks, spikes)
- Signal processing (momentum, volatility, trend)
- Batch feature extraction for high throughput

## Installation

### Prerequisites
- NVIDIA GPU with CUDA 12.2+ support
- CUDA Toolkit 12.2+
- Python 3.11+

### Install Dependencies

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install TensorRT (from NVIDIA wheels)
# Visit: https://developer.nvidia.com/tensorrt
pip install tensorrt

# Install CuPy for GPU NumPy operations
pip install cupy-cuda12x

# Install other dependencies
pip install numpy scipy
```

### Optional: torch2trt for PyTorch to TensorRT conversion
```bash
pip install torch2trt
```

## Usage

### Initialization

The GPU intelligence subsystem is automatically initialized when the FastAPI application starts. It gracefully falls back to CPU-only mode if GPU is unavailable.

```python
from gpu_intelligence.integration import (
    initialize_gpu_intelligence,
    is_gpu_available,
    get_gpu_status,
)

# Initialize (called automatically in app.py)
success = initialize_gpu_intelligence()

# Check availability
if is_gpu_available():
    status = get_gpu_status()
    print(f"GPU available: {status['device_count']} devices")
```

### Integration with Analysis Module

The analysis module automatically uses GPU acceleration when available:

```python
from momento.analysis import analyze, robust_percentiles

# Percentile calculation uses GPU for large datasets
percentiles = robust_percentiles(multipliers)

# Full analysis includes GPU-accelerated features
result = analyze(rounds, settings)
# result['gpu_features'] contains GPU-extracted features
```

### Direct Feature Extraction

```python
from gpu_intelligence.integration import get_feature_extractor

extractor = get_feature_extractor()
result = extractor.extract_features(multipliers)

# Access features
print(result.features['mean'])
print(result.features['percentiles'])
print(result.features['momentum'])
```

### Pattern Detection

```python
from gpu_intelligence.integration import get_feature_extractor

extractor = get_feature_extractor()
patterns = extractor.detect_patterns_gpu(multipliers)

# Access detected patterns
print(patterns['ladder']['detected'])
print(patterns['streak']['max_streak'])
print(patterns['spike']['count'])
```

### Batch Processing

```python
from gpu_intelligence.integration import get_batch_processor

processor = get_batch_processor()
await processor.start()

# Submit items for batch processing
result = await processor.submit(data, metadata={'source': 'test'})

# Get statistics
stats = processor.get_stats()
print(f"Throughput: {stats['throughput_ips']} items/sec")

await processor.stop()
```

## API Endpoints

The module provides REST API endpoints for monitoring and control:

### GET /api/v1/gpu/status
Get GPU intelligence status and metrics.

### GET /api/v1/gpu/devices
Get detailed information about available GPU devices.

### GET /api/v1/gpu/memory
Get memory usage summary for a device.

### GET /api/v1/gpu/pool/stats
Get memory pool statistics.

### POST /api/v1/gpu/pool/clear
Clear the memory pool.

### GET /api/v1/gpu/batch/stats
Get batch processing statistics.

### POST /api/v1/gpu/batch/reset
Reset batch processing statistics.

### POST /api/v1/gpu/cache/clear
Clear GPU cache to free memory.

### POST /api/v1/gpu/synchronize
Synchronize CUDA operations.

### GET /api/v1/gpu/features/extract
Extract features from data using GPU acceleration.

### GET /api/v1/gpu/health
Health check endpoint.

## Configuration

GPU intelligence can be configured via the `GPUConfig` class:

```python
from gpu_intelligence.config import GPUConfig, PrecisionMode

config = GPUConfig(
    cuda=CUDAConfig(
        enable_mixed_precision=True,
        enable_tensor_cores=True,
        memory_fraction=0.9,
    ),
    tensorrt=TensorRTConfig(
        precision=PrecisionMode.FP16,
        enable_layer_fusion=True,
        target_latency_ms=1.0,
    ),
    batch=BatchConfig(
        enabled=True,
        dynamic_batching=True,
        max_batch_size=128,
    ),
)
```

## Performance Targets (V5 Specifications)

- **Latency**: <1ms inference
- **Throughput**: 1000+ inferences/second
- **Memory**: <2GB per model
- **Accuracy**: <1% degradation with quantization

## Hardware Support

### Supported GPUs
- NVIDIA A100 (80GB HBM2e)
- NVIDIA H100 (80GB HBM3)
- NVIDIA V100 (32GB HBM2)
- NVIDIA RTX 4090 (24GB GDDR6X) - for development

### Unsupported
- Consumer GPUs older than RTX 30-series
- GPUs without tensor cores (reduced performance)

## Troubleshooting

### GPU Not Detected
```bash
# Check CUDA installation
nvidia-smi

# Check PyTorch CUDA availability
python -c "import torch; print(torch.cuda.is_available())"
```

### Out of Memory Errors
- Reduce batch size in configuration
- Clear memory pool via API: POST /api/v1/gpu/pool/clear
- Reduce memory_fraction in CUDAConfig

### TensorRT Import Errors
- Ensure TensorRT is installed for your CUDA version
- Check Python path includes TensorRT libraries
- Verify CUDA Toolkit version matches TensorRT requirements

## Architecture

```
gpu_intelligence/
├── __init__.py              # Module exports
├── config.py                # Configuration classes
├── device_manager.py        # CUDA device management
├── memory_pool.py           # Memory pooling
├── tensorrt_engine.py       # TensorRT inference
├── batch_processor.py      # Batch processing
├── feature_extractor.py     # Feature extraction
├── integration.py           # Integration layer
└── README.md               # This file
```

## Performance Optimization Tips

1. **Use Mixed Precision**: Enable FP16 for 2-4x speedup with minimal accuracy loss
2. **Batch Appropriately**: Use dynamic batching to balance latency and throughput
3. **Pool Memory**: Pre-allocate memory blocks for your typical workload sizes
4. **Synchronize Sparingly**: Only synchronize when necessary to avoid stalls
5. **Monitor Memory**: Use the API endpoints to track memory usage and pressure

## License

Part of Momento Core V5 - See project license for details.
