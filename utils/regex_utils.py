import functools
import re

from ..core.constants import SEPARATOR_ITEMS


def add_named_capture_group(func):
    """
    関数の戻り値を名前付きキャプチャグループで囲むデコレーター
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        group = self.id
        return f"(?P<{group}>{func(self, *args, **kwargs)})"

    return wrapper


def add_separator_by_order(func):
    """
    要素の順序に基づいてセパレーターを追加するデコレーター
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        sep = f"(?:{re.escape(self.separator)})?"
        order = self.order
        result = func(self, *args, **kwargs)
        if result:
            if order != 0:
                return f"{sep}{result}"
            else:
                seps = "|".join(re.escape(item[0]) for item in SEPARATOR_ITEMS)
                return f"{result}(?:{seps})?"
        else:
            return result

    return wrapper
