"""
Prometheus Metrics for Qubes

Tracks:
- Memory chain operations (blocks created, anchored, searched)
- AI API calls (latency, costs, tokens, failures by provider)
- P2P network activity (peers, messages, bandwidth)
- Storage operations (reads, writes, cache hits)
- System health (errors, warnings, circuit breaker states)
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Dict
import time


# =============================================================================
# REGISTRY
# =============================================================================

# Use custom registry to avoid conflicts
registry = CollectorRegistry()


# =============================================================================
# MEMORY CHAIN METRICS
# =============================================================================

memory_blocks_created = Counter(
    "qubes_memory_blocks_created_total",
    "Total number of memory blocks created",
    ["qube_id", "block_type"],
    registry=registry,
)

memory_blocks_anchored = Counter(
    "qubes_memory_blocks_anchored_total",
    "Total number of session blocks anchored to permanent chain",
    ["qube_id"],
    registry=registry,
)

memory_search_duration = Histogram(
    "qubes_memory_search_duration_seconds",
    "Memory search latency in seconds",
    ["qube_id", "search_type"],  # search_type: semantic, metadata, full_text, temporal
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

memory_search_results = Histogram(
    "qubes_memory_search_results",
    "Number of results returned by memory search",
    ["qube_id", "search_type"],
    buckets=[0, 1, 5, 10, 20, 50, 100, 200, 500],
    registry=registry,
)

memory_chain_length = Gauge(
    "qubes_memory_chain_length",
    "Current length of memory chain",
    ["qube_id"],
    registry=registry,
)


# =============================================================================
# AI API METRICS
# =============================================================================

ai_api_calls = Counter(
    "qubes_ai_api_calls_total",
    "Total number of AI API calls",
    ["provider", "model", "status"],  # status: success, error, timeout, rate_limit
    registry=registry,
)

ai_api_latency = Histogram(
    "qubes_ai_api_latency_seconds",
    "AI API call latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry,
)

ai_api_tokens = Counter(
    "qubes_ai_api_tokens_total",
    "Total number of tokens processed",
    ["provider", "model", "token_type"],  # token_type: input, output
    registry=registry,
)

ai_api_cost = Counter(
    "qubes_ai_api_cost_usd",
    "Total AI API cost in USD",
    ["provider", "model"],
    registry=registry,
)

ai_circuit_breaker_state = Gauge(
    "qubes_ai_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["provider"],
    registry=registry,
)

ai_provider_failures = Counter(
    "qubes_ai_provider_failures_total",
    "Total number of AI provider failures",
    ["provider", "error_type"],  # error_type: timeout, rate_limit, api_error, invalid_response
    registry=registry,
)


# =============================================================================
# P2P NETWORK METRICS
# =============================================================================

p2p_peers_connected = Gauge(
    "qubes_p2p_peers_connected",
    "Number of currently connected peers",
    ["qube_id"],
    registry=registry,
)

p2p_messages_sent = Counter(
    "qubes_p2p_messages_sent_total",
    "Total number of P2P messages sent",
    ["qube_id", "message_type"],
    registry=registry,
)

p2p_messages_received = Counter(
    "qubes_p2p_messages_received_total",
    "Total number of P2P messages received",
    ["qube_id", "message_type"],
    registry=registry,
)

p2p_message_latency = Histogram(
    "qubes_p2p_message_latency_seconds",
    "P2P message round-trip latency in seconds",
    ["qube_id"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

p2p_bandwidth_bytes = Counter(
    "qubes_p2p_bandwidth_bytes_total",
    "Total P2P bandwidth in bytes",
    ["qube_id", "direction"],  # direction: sent, received
    registry=registry,
)

p2p_handshake_failures = Counter(
    "qubes_p2p_handshake_failures_total",
    "Total number of P2P handshake failures",
    ["qube_id", "reason"],
    registry=registry,
)


# =============================================================================
# BLOCKCHAIN METRICS
# =============================================================================

blockchain_nft_mints = Counter(
    "qubes_blockchain_nft_mints_total",
    "Total number of NFT mints",
    ["status"],  # status: success, failed
    registry=registry,
)

blockchain_nft_verifications = Counter(
    "qubes_blockchain_nft_verifications_total",
    "Total number of NFT ownership verifications",
    ["result"],  # result: verified, failed, not_found
    registry=registry,
)

blockchain_transaction_latency = Histogram(
    "qubes_blockchain_transaction_latency_seconds",
    "Blockchain transaction confirmation latency in seconds",
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
    registry=registry,
)

blockchain_transaction_cost = Summary(
    "qubes_blockchain_transaction_cost_bch",
    "Blockchain transaction cost in BCH",
    registry=registry,
)


# =============================================================================
# STORAGE METRICS
# =============================================================================

storage_operations = Counter(
    "qubes_storage_operations_total",
    "Total number of storage operations",
    ["operation", "status"],  # operation: read, write, delete; status: success, error
    registry=registry,
)

storage_operation_latency = Histogram(
    "qubes_storage_operation_latency_seconds",
    "Storage operation latency in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

storage_cache_hits = Counter(
    "qubes_storage_cache_hits_total",
    "Total number of storage cache hits",
    ["cache_type"],  # cache_type: lmdb, faiss
    registry=registry,
)

storage_cache_misses = Counter(
    "qubes_storage_cache_misses_total",
    "Total number of storage cache misses",
    ["cache_type"],
    registry=registry,
)

storage_disk_usage_bytes = Gauge(
    "qubes_storage_disk_usage_bytes",
    "Current disk usage in bytes",
    ["qube_id", "storage_tier"],  # storage_tier: hot, warm, cold
    registry=registry,
)


# =============================================================================
# SYSTEM HEALTH METRICS
# =============================================================================

system_errors = Counter(
    "qubes_system_errors_total",
    "Total number of system errors",
    ["error_code", "severity"],
    registry=registry,
)

system_warnings = Counter(
    "qubes_system_warnings_total",
    "Total number of system warnings",
    ["warning_type"],
    registry=registry,
)

active_qubes = Gauge(
    "qubes_active_qubes",
    "Number of currently active Qubes",
    registry=registry,
)

system_uptime_seconds = Gauge(
    "qubes_system_uptime_seconds",
    "System uptime in seconds",
    registry=registry,
)


# =============================================================================
# METRIC RECORDING HELPERS
# =============================================================================

class MetricsRecorder:
    """Helper class for recording metrics with timing context"""

    @staticmethod
    def record_memory_block_created(qube_id: str, block_type: str):
        """Record creation of a memory block"""
        memory_blocks_created.labels(qube_id=qube_id, block_type=block_type).inc()
        memory_chain_length.labels(qube_id=qube_id).inc()

    @staticmethod
    def record_memory_blocks_anchored(qube_id: str):
        """Record session blocks being anchored"""
        memory_blocks_anchored.labels(qube_id=qube_id).inc()

    @staticmethod
    def record_memory_search(qube_id: str, search_type: str, duration: float, result_count: int):
        """Record memory search metrics"""
        memory_search_duration.labels(qube_id=qube_id, search_type=search_type).observe(duration)
        memory_search_results.labels(qube_id=qube_id, search_type=search_type).observe(result_count)

    @staticmethod
    def record_ai_api_call(
        provider: str,
        model: str,
        status: str,
        latency: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ):
        """Record AI API call metrics"""
        ai_api_calls.labels(provider=provider, model=model, status=status).inc()

        if latency > 0:
            ai_api_latency.labels(provider=provider, model=model).observe(latency)

        if input_tokens > 0:
            ai_api_tokens.labels(provider=provider, model=model, token_type="input").inc(input_tokens)
        if output_tokens > 0:
            ai_api_tokens.labels(provider=provider, model=model, token_type="output").inc(output_tokens)
        if cost_usd > 0:
            ai_api_cost.labels(provider=provider, model=model).inc(cost_usd)

    @staticmethod
    def record_ai_cost(cost_usd: float, provider: str, model: str):
        """Record AI cost"""
        ai_api_cost.labels(provider=provider, model=model).inc(cost_usd)

    @staticmethod
    def record_tool_execution(tool_name: str, status: str):
        """Record tool execution"""
        # For now, use ai_api_calls metric with tool prefix
        ai_api_calls.labels(provider="tool", model=tool_name, status=status).inc()

    @staticmethod
    def record_p2p_message(qube_id: str, message_type: str, direction: str, bytes_count: int):
        """Record P2P message metrics"""
        if direction == "sent":
            p2p_messages_sent.labels(qube_id=qube_id, message_type=message_type).inc()
        else:
            p2p_messages_received.labels(qube_id=qube_id, message_type=message_type).inc()

        p2p_bandwidth_bytes.labels(qube_id=qube_id, direction=direction).inc(bytes_count)

    @staticmethod
    def record_p2p_event(event_type: str, qube_id: str):
        """
        Record general P2P event

        Args:
            event_type: Event type (message_sent, handshake_success, discovery, etc.)
            qube_id: Qube ID associated with the event
        """
        # Map events to appropriate metrics
        if event_type in ["message_sent", "message_encrypted"]:
            p2p_messages_sent.labels(qube_id=qube_id, message_type="general").inc()
        elif event_type in ["message_received", "message_decrypted"]:
            p2p_messages_received.labels(qube_id=qube_id, message_type="general").inc()
        elif event_type in ["handshake_failed", "handshake_rejected"]:
            p2p_handshake_failures.labels(qube_id=qube_id, reason=event_type).inc()
        # For other events, we just silently accept them (they're logged but not metriced)

    @staticmethod
    def record_error(error_code: str, severity: str):
        """Record system error"""
        system_errors.labels(error_code=error_code, severity=severity).inc()

    @staticmethod
    def time_operation(metric_histogram, **labels):
        """
        Context manager for timing operations

        Example:
            with MetricsRecorder.time_operation(ai_api_latency, provider="openai", model="gpt-4"):
                response = await openai_client.chat.completions.create(...)
        """
        return _TimingContext(metric_histogram, labels)


class _TimingContext:
    """Context manager for timing metrics"""

    def __init__(self, histogram, labels):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.histogram.labels(**self.labels).observe(duration)


# =============================================================================
# METRICS EXPORT
# =============================================================================

def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format

    Returns:
        Metrics in Prometheus exposition format
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """Get content type for Prometheus metrics"""
    return CONTENT_TYPE_LATEST


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Record some example metrics
    MetricsRecorder.record_memory_block_created("A3F2C1B8", "INTERACTION")
    MetricsRecorder.record_memory_search("A3F2C1B8", "semantic", 0.15, 10)
    MetricsRecorder.record_ai_api_call(
        provider="openai",
        model="gpt-4",
        status="success",
        latency=1.23,
        input_tokens=150,
        output_tokens=80,
        cost_usd=0.0042,
    )

    # Print metrics
    print(get_metrics().decode("utf-8"))
