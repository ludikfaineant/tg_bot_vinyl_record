from aiogram_ui import FilterableStr
from enum import Enum


class DefaultCallbacks(FilterableStr, Enum):
    home = "home"
    cancel = "cancel"
    record = "record_vinyl"
    without_time = "without_timecodes"
    with_time = "with_timecodes"