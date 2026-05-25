"""Ticker — Tick 时间感知 (数据平面)

从旧 agent-arch/ticker.py 迁移
功能: 每个LLM调用注入 TICK 时间戳
"""

import time
import datetime
from typing import Optional
from dataclasses import dataclass

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

PERIODS = [
    (5, 9, "early morning"),
    (9, 12, "morning"),
    (12, 14, "noon"),
    (14, 18, "afternoon"),
    (18, 21, "evening"),
    (21, 24, "late night"),
    (0, 5, "midnight"),
]


def get_period(hour: int) -> str:
    for start, end, name in PERIODS:
        if start <= hour < end:
            return name
    return "midnight"


def format_timestamp(dt: datetime.datetime = None) -> str:
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
    offset = dt.strftime("%z")
    offset_str = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
    return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}{offset_str}"


def describe_existence(birth_time: float) -> str:
    ms = (time.time() - birth_time) * 1000
    minutes = int(ms / 60000)
    hours = int(ms / 3600000)
    days = int(ms / 86400000)
    if minutes < 3:
        return "刚刚苏醒"
    if minutes < 15:
        return f"已经醒来 {minutes} 分钟了"
    if minutes < 60:
        return f"已经存在了约 {minutes} 分钟"
    if hours < 24:
        return f"已经存在了约 {hours} 小时"
    if days < 7:
        return f"已经存在了 {days} 天"
    return f"已经存在了 {days} 天（{days // 7} 周）"


@dataclass
class TickContext:
    tick_id: int = 0
    timestamp: str = ""
    weekday: str = ""
    period: str = ""
    since_birth: str = ""

    def format(self) -> str:
        if not self.timestamp:
            return ""
        return f"TICK {self.timestamp} | {self.weekday} {self.period} | {self.since_birth}"


_tick_count = 0
_birth_time: float = time.time()


def get_tick() -> TickContext:
    global _tick_count
    _tick_count += 1
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    return TickContext(
        tick_id=_tick_count,
        timestamp=format_timestamp(now),
        weekday=WEEKDAYS[now.weekday()],
        period=get_period(now.hour),
        since_birth=describe_existence(_birth_time),
    )


def get_tick_string() -> str:
    return get_tick().format()


def reset_birth():
    global _birth_time
    _birth_time = time.time()
