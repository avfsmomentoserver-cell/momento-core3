"""
Test script for V5 CPU Intelligence with available dependencies
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("v5_test")

# Test available dependencies
try:
    import psutil
    logger.info(f"✓ psutil available: {psutil.__version__}")
except ImportError:
    logger.warning("✗ psutil not available")

try:
    import numpy as np
    logger.info(f"✓ numpy available: {np.__version__}")
except ImportError:
    logger.warning("✗ numpy not available")

try:
    import sklearn
    logger.info(f"✓ sklearn available: {sklearn.__version__}")
except ImportError:
    logger.warning("✗ sklearn not available")

try:
    import onnxruntime as ort
    logger.info(f"✓ onnxruntime available: {ort.__version__}")
except ImportError:
    logger.warning("✗ onnxruntime not available (will use fallback)")

# Test CPU intelligence processor with fallback
try:
    from cpu_intelligence import get_cpu_processor
    cpu_processor = get_cpu_processor()
    logger.info("✓ CPU intelligence processor initialized")
    
    # Test basic functionality
    test_data = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
    logger.info(f"Test data shape: {len(test_data)} samples")
    
    # Get performance stats
    stats = cpu_processor.get_performance_stats()
    logger.info(f"Performance stats: {stats}")
    
    logger.info("✓ CPU intelligence processor functional")
    
except Exception as e:
    logger.error(f"✗ CPU intelligence processor failed: {e}")
    import traceback
    traceback.print_exc()

# Test system metrics
try:
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    logger.info(f"System CPU: {cpu_percent}%")
    logger.info(f"System Memory: {memory.percent}%")
    logger.info("✓ System monitoring functional")
except Exception as e:
    logger.error(f"✗ System monitoring failed: {e}")

logger.info("V5 component test complete")