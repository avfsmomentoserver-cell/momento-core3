"""
V5 Realtime Ingestion System

Phase 2 Implementation: FPGA-accelerated, sub-millisecond data ingestion
with DPDK kernel-bypass networking and lock-free data structures.

Target Performance:
- <1ms data ingestion latency
- 100K+ events/second throughput
- Zero packet loss
- FPGA parsing: 14ns target
- DPDK packet processing: <2μs
"""

__version__ = "5.0.0"
__author__ = "V5 Realtime Ingestion Team"
