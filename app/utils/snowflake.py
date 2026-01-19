"""Snowflake ID generator utility."""

import time
from threading import Lock


class SnowflakeGenerator:
    """53-bit Snowflake ID generator (JavaScript safe).

    53-bit ID structure (fits in JS Number.MAX_SAFE_INTEGER):
    - 41 bits: timestamp (milliseconds since epoch, ~69 years)
    - 4 bits: machine id (0-15)
    - 8 bits: sequence number (0-255 per millisecond)

    Max value: 2^53 - 1 = 9007199254740991 (JS safe)
    """

    # 位数配置
    TIMESTAMP_BITS = 41
    MACHINE_BITS = 4
    SEQUENCE_BITS = 8

    # 最大值
    MAX_MACHINE_ID = (1 << MACHINE_BITS) - 1  # 15
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1    # 255

    # 位移
    MACHINE_SHIFT = SEQUENCE_BITS              # 8
    TIMESTAMP_SHIFT = SEQUENCE_BITS + MACHINE_BITS  # 12

    def __init__(self, machine_id: int = 1, epoch: int = 1704067200000):
        """Initialize snowflake generator.

        machine_id: int, 机器ID (0-15), 默认1
        epoch: int, 起始时间戳(毫秒), 默认2024-01-01 00:00:00 UTC
        """
        if machine_id < 0 or machine_id > self.MAX_MACHINE_ID:
            raise ValueError(f"machine_id must be between 0 and {self.MAX_MACHINE_ID}")

        self.machine_id = machine_id
        self.epoch = epoch
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = Lock()

    def _current_millis(self) -> int:
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        timestamp = self._current_millis()
        while timestamp <= last_timestamp:
            timestamp = self._current_millis()
        return timestamp

    def generate(self) -> int:
        """Generate a unique snowflake ID (53-bit, JS safe)."""
        with self._lock:
            timestamp = self._current_millis()

            if timestamp < self.last_timestamp:
                raise RuntimeError(f"Clock moved backwards. Refusing to generate id for {self.last_timestamp - timestamp} milliseconds")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            return ((timestamp - self.epoch) << self.TIMESTAMP_SHIFT) | (self.machine_id << self.MACHINE_SHIFT) | self.sequence


# Global snowflake generator instance
_snowflake: SnowflakeGenerator | None = None


def init_snowflake(machine_id: int | None = None) -> None:
    """Initialize global snowflake generator.

    Args:
        machine_id: 机器ID (0-15)。若为 None，则使用进程 PID % 16 自动分配，
                    确保多 worker 环境下不冲突
    """
    global _snowflake
    if machine_id is None:
        import os
        machine_id = os.getpid() % 16
        print(f"[Snowflake] Auto-assigned machine_id={machine_id} for PID={os.getpid()}")
    _snowflake = SnowflakeGenerator(machine_id=machine_id)


def generate_id() -> int:
    """Generate a unique snowflake ID (53-bit, JS safe)."""
    if _snowflake is None:
        raise RuntimeError("Snowflake not initialized. Call init_snowflake() first.")
    return _snowflake.generate()
