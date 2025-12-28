"""通用序列号生成器"""

import random
from datetime import datetime
from enum import Enum
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SeqKey(str, Enum):
    """预定义序列标识"""
    USER_ID = "user_id"
    ORDER_NO = "order_no"


# 序列初始化配置: {current_value, step_min, step_max, prefix, description}
SEQ_INIT_CONFIG = {
    SeqKey.USER_ID: (random.randint(1_000_000, 1_001_000), 1, 20, None, "用户ID"),
    SeqKey.ORDER_NO: (1, 1, 1, "ORD", "充值订单号"),
}


async def generate_sequence_id(
    db: AsyncSession, seq_key: str | SeqKey, *,
    with_prefix: bool = False, with_datetime: bool = False, datetime_format: str = "%y%m%d%H%M",
) -> int | str:
    """生成序列号

    Examples:
        user_id = await generate_sequence_id(db, SeqKey.USER_ID)  # 5234567
        order_no = await generate_sequence_id(db, SeqKey.ORDER_NO, with_prefix=True, with_datetime=True)  # ORD2312231530000001
    """
    key = seq_key.value if isinstance(seq_key, SeqKey) else seq_key

    result = await db.execute(
        text("SELECT current_value, step_min, step_max, prefix FROM id_sequences WHERE seq_key = :key FOR UPDATE"),
        {"key": key}
    )
    row = result.fetchone()
    if row is None:
        raise ValueError(f"Sequence '{key}' not found")

    current_value, step_min, step_max, prefix = row
    step = step_min if step_min == step_max else random.randint(
        step_min, step_max)
    new_value = current_value + step

    await db.execute(
        text("UPDATE id_sequences SET current_value = :new_value, update_time = NOW() WHERE seq_key = :key"),
        {"new_value": new_value, "key": key}
    )

    if not with_prefix and not with_datetime:
        return new_value

    parts = []
    if with_prefix and prefix:
        parts.append(prefix)
    if with_datetime:
        parts.append(datetime.now().strftime(datetime_format))
    parts.append(str(new_value).zfill(6))
    return "".join(parts)


async def init_sequence(
    db: AsyncSession, seq_key: str | SeqKey, *,
    current_value: int = 1000000, step_min: int = 1, step_max: int = 1,
    prefix: str | None = None, description: str | None = None,
) -> None:
    """初始化序列（如果不存在）"""
    key = seq_key.value if isinstance(seq_key, SeqKey) else seq_key

    result = await db.execute(text("SELECT 1 FROM id_sequences WHERE seq_key = :key"), {"key": key})
    if result.fetchone():
        return

    config = SEQ_INIT_CONFIG.get(key)
    if config:
        current_value, step_min, step_max, prefix, description = config

    await db.execute(
        text("""INSERT INTO id_sequences (seq_key, current_value, step_min, step_max, prefix, description, create_time, update_time)
                VALUES (:key, :cv, :smin, :smax, :prefix, :desc, NOW(), NOW())"""),
        {"key": key, "cv": current_value, "smin": step_min,
            "smax": step_max, "prefix": prefix, "desc": description}
    )
    await db.commit()


async def init_all_sequences(db: AsyncSession) -> None:
    """初始化所有预定义序列"""
    for seq_key in SEQ_INIT_CONFIG:
        await init_sequence(db, seq_key)
