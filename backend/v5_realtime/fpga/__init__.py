"""
V5 FPGA Acceleration Layer

Hardware-accelerated parsing and processing using Xilinx/AMD Alveo UL3524.
Target latencies: FIX parsing 14ns, orderbook updates 4ns, feature extraction 50ns.
"""

from .parser_interface import (
    FPGAParserInterface,
    FPGADeviceType,
    FPGASpecs,
    ParserMetrics,
    ParseError,
)
from .fix_parser import FIXParserFPGA, FIXMessage, FIXMessageType
from .feature_extractor import FeatureExtractorFPGA, FeatureResult, WindowStats

__all__ = [
    "FPGAParserInterface",
    "FPGADeviceType",
    "FPGASpecs",
    "ParserMetrics",
    "ParseError",
    "FIXParserFPGA",
    "FIXMessage",
    "FIXMessageType",
    "FeatureExtractorFPGA",
    "FeatureResult",
    "WindowStats",
]
