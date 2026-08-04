from dataclasses import dataclass, field
from time import time


@dataclass
class RuntimeState:
    started_at: float = field(default_factory=time)
    bot_id: int | None = None
    bot_name: str = ""
    web_started: bool = False
    force_sub_enabled: bool = False

    @property
    def uptime_seconds(self):
        return int(time() - self.started_at)

state = RuntimeState()
