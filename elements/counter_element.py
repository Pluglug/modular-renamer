import random
from typing import Tuple

from ..core.element import BaseCounter, ElementData
from ..utils import logging, regex_utils

log = logging.get_logger(__name__)


# class CounterElement(BaseElement):
#     """
#     固定桁数のカウンター要素
#     """

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         # 'custom' or 'blender'
#         self.counter_type = element_data.get("counter_type")
#         if self.counter_type == "blender":

#             self._order = 1000
#             self._enabled = False
#             self._separator = "."
#             self.digits = 3
#         else:
#             self.digits = element_data.get("digits", 2)

#         self.forward = None
#         self.backward = None

#     def standby(self) -> None:
#         super().standby()
#         self.forward = None
#         self.backward = None

#     def parse(self, name: str) -> bool:
#         if self._pattern is None:
#             log.debug(f"Cache isn not initialized for {self.id}. Initializing cache...")
#             self.initialize_cache()
#         match = self._pattern.match(name)
#         if match:
#             self._value = match.group(self.id)
#             self.forward = match.string[: match.start(self.id)]
#             self.backward = match.string[match.end(self.id) :]
#             return True
#         return False

#     @add_separator_by_order
#     @add_named_capture_group
#     def _build_pattern(self) -> str:
#         if self.counter_type == "blender":
#             return "\\.\\d{3}$"
#         return f"\\d{{{self.digits}}}"

#     def increment(self) -> None:
#         """
#         カウンター値をインクリメントし、桁数に合わせた文字列にフォーマットする
#         """
#         if self._value is None:
#             num = 1
#         else:
#             num = int(self._value) + 1
#         self._value = f"{num:0{self.digits}d}"

#     def gen_proposed_name(self, i: int) -> str:
#         return f"{self.forward}{i:0{self.digits}d}{self.backward}"

#     def generate_random_value(self) -> Tuple[str, str]:
#         random_value = f"{random.randint(0, 10**self.digits):0{self.digits}d}"
#         return self.separator, random_value


class NumericCounter(BaseCounter):
    """Simple numeric counter with configurable digits"""

    def __init__(self, element_data):
        super().__init__(element_data)
        self.digits = element_data.get("digits", 2)

    @regex_utils.add_separator_by_order
    @regex_utils.add_named_capture_group
    def _build_pattern(self) -> str:
        """Build regex pattern for numeric counter"""
        return f"\\d{{{self.digits}}}"

    def format_value(self, value: int) -> str:
        """Format integer value as zero-padded string"""
        return f"{value:0{self.digits}d}"

    def gen_proposed_name(self, value: int) -> str:
        """Generate proposed name with given counter value"""
        return f"{self.forward}{self.format_value(value)}{self.backward}"

    def generate_random_value(self) -> Tuple[str, str]:
        """Generate random value for numeric counter"""
        random_value = f"{random.randint(0, 10**self.digits):0{self.digits}d}"
        return self.separator, random_value


class BlenderCounter(BaseCounter):
    """Blender's native counter (.001 format)"""

    element_type = "blender_counter"

    def __init__(self, element_data):
        super().__init__(element_data)
        # 強制的にBlender形式に設定
        self._order = 1000  # 絶対に最後にマッチするようにする
        self._enabled = False
        self._separator = "."
        self.digits = 3

    @regex_utils.add_named_capture_group
    def _build_pattern(self) -> str:
        """Build regex pattern for Blender counter"""
        return f"\\{self._separator}\\d{{{self.digits}}}$"  # ".1000"以降は考慮しない

    def _parse_value(self, value_str: str) -> int:
        """Parse Blender counter value (.001 -> 1)"""
        # セパレータードット除去して数値化
        return int(value_str[1:])

    def format_value(self, value: int) -> str:
        """Format integer as Blender counter (.001)"""
        return f"{self._separator}{value:0{self.digits}d}"

    def gen_proposed_name(self, value: int) -> str:
        """Generate proposed name with Blender counter"""
        return f"{self.forward}{self.format_value(value)}"

    def generate_random_value(self) -> Tuple[str, str]:
        """Generate random value for Blender counter"""
        random_value = f"{random.randint(0, 10**self.digits):0{self.digits}d}"
        return self.separator, random_value


blender_counter_element_data = ElementData(
    type="blender_counter",
    id="blender_counter",
    order=1000,
    enabled=False,
    separator=".",
    digits=3,
)


class AlphabeticCounter(BaseCounter):
    """Alphabetic counter (A, B, C... AA, AB...)"""

    def __init__(self, element_data):
        super().__init__(element_data)
        self.uppercase = element_data.get("uppercase", True)

    @regex_utils.add_separator_by_order
    @regex_utils.add_named_capture_group
    def _build_pattern(self) -> str:
        """Build regex for alphabetic counter"""
        pattern = r"[A-Z]+" if self.uppercase else r"[a-z]+"
        return f"{pattern}"

    def _parse_value(self, value_str: str) -> int:
        """Convert alphabetic value to integer (A->1, B->2...)"""
        result = 0
        for char in value_str:
            base_char = "A" if self.uppercase else "a"
            result = result * 26 + (ord(char) - ord(base_char) + 1)
        return result

    def format_value(self, value: int) -> str:
        """Convert integer to alphabetic sequence (1->A, 27->AA...)"""
        if value <= 0:
            return ""

        result = ""
        base_char = ord("A") if self.uppercase else ord("a")

        while value > 0:
            value, remainder = divmod(value - 1, 26)
            result = chr(base_char + remainder) + result

        return result

    def gen_proposed_name(self, value: int) -> str:
        """Generate proposed name with alphabetic counter"""
        return f"{self.forward}{self.format_value(value)}{self.backward}"

    def generate_random_value(self) -> Tuple[str, str]:
        """Generate random value for alphabetic counter"""
        random_value = random.randint(1, 26)
        return self.separator, self.format_value(random_value)
