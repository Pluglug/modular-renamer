# import re
# import functools
# import datetime
# import random
# from abc import ABC, abstractmethod

# from .utils.logging import get_logger

# log = get_logger(__name__)

# # Debug helper, can be replaced with proper logging later
# def debug_log(message, enabled=False):
#     if enabled:
#         print(f"[ModularRenamer] {message}")


# # Constants for default debug settings
# DEBUG_RENAME = False


# def add_named_capture_group(func):
#     """
#     関数の戻り値を名前付きキャプチャグループで囲むデコレーター
#     """

#     @functools.wraps(func)
#     def wrapper(self, *args, **kwargs):
#         group = self.id
#         return f"(?P<{group}>{func(self, *args, **kwargs)})"

#     return wrapper


# def add_separator_by_order(func):
#     """
#     要素の順序に基づいてセパレーターを追加するデコレーター
#     """

#     @functools.wraps(func)
#     def wrapper(self, *args, **kwargs):
#         sep = f"(?:{re.escape(self.separator)})?"
#         order = self.order
#         result = func(self, *args, **kwargs)
#         if result:
#             if order == 0:  # 最初の要素
#                 return f"{result}{sep}"
#             else:  # 順序が1以上の要素
#                 return f"{sep}{result}"
#         else:
#             return result

#     return wrapper


# class NamingElementProcessor(ABC):
#     """Base class for all naming element processors"""

#     def __init__(self, element_data):
#         """
#         Initialize the processor with element data from preferences

#         Args:
#             element_data: Data structure containing element properties
#         """
#         self.id = element_data.id
#         self.enabled = element_data.enabled
#         self.separator = element_data.separator
#         self.element_type = element_data.element_type
#         self.order = element_data.order
#         self.cache_invalidated = True
#         self.compiled_pattern = None
#         self._value = None

#     @property
#     def value(self):
#         """Get the current value of this element"""
#         return self._value

#     @value.setter
#     def value(self, new_value):
#         """Set the value of this element"""
#         if new_value is not None:
#             try:
#                 self._value = str(new_value)
#             except ValueError:
#                 print(f"Value '{new_value}' cannot be converted to string.")
#         else:
#             self._value = None

#     def standby(self):
#         """Reset the element to its initial state"""
#         self._value = None

#     def update_cache(self):
#         """Update any cached data (like compiled regex)"""
#         if self.cache_invalidated:
#             self.compiled_pattern = re.compile(self.build_pattern())
#             debug_log(
#                 f"Updated cache for {self.id}: {self.compiled_pattern}", DEBUG_RENAME
#             )
#             self.cache_invalidated = False

#     def search(self, target_string):
#         """
#         Search for this element in the target string

#         Args:
#             target_string: String to search in

#         Returns:
#             bool: True if element was found, False otherwise
#         """
#         if self.cache_invalidated:
#             self.update_cache()
#         match = self.compiled_pattern.search(target_string)
#         return self.capture(match)

#     def capture(self, match):
#         """
#         Extract value from a regex match

#         Args:
#             match: Regex match object

#         Returns:
#             bool: True if value was captured, False otherwise
#         """
#         if match:
#             self.value = match.group(self.id)
#             return True
#         return False

#     def update(self, new_string):
#         """
#         Update this element by searching in a new string

#         Args:
#             new_string: New string to search in
#         """
#         self.search(new_string)

#     def render(self):
#         """
#         Render this element as a tuple of (separator, value)

#         Returns:
#             tuple or None: (separator, value) if element has a value, None otherwise
#         """
#         if self.enabled and self.value:
#             return self.separator, self.value
#         return None

#     @abstractmethod
#     def build_pattern(self):
#         """Build the regex pattern for this element"""
#         pass

#     @abstractmethod
#     def generate_random_value(self):
#         """Generate a random value for this element (for testing)"""
#         pass

#     def test_random_output(self):
#         """
#         Generate a random test output for this element

#         Returns:
#             tuple: (separator, random_value)
#         """
#         self.value = self.generate_random_value()
#         return self.separator, self.value


# class TextElementProcessor(NamingElementProcessor):
#     """Processor for text elements with predefined options"""

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         self.items = [item.name for item in element_data.items]

#     @add_separator_by_order
#     @add_named_capture_group
#     def build_pattern(self):
#         """Build pattern that matches any of the predefined items with separator"""
#         if not self.items:
#             return ""

#         escaped_items = [re.escape(item) for item in self.items]
#         return "|".join(escaped_items)

#     def generate_random_value(self):
#         """Generate a random value from the available items"""
#         if self.items:
#             return random.choice(self.items)
#         return ""


# class FreeTextElementProcessor(NamingElementProcessor):
#     """Processor for free text input elements"""

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         self.default_text = element_data.default_text

#     @add_separator_by_order
#     @add_named_capture_group
#     def build_pattern(self):
#         """Build pattern that captures any text with separator"""
#         return f".*{re.escape(self.default_text)}.*"  # Capture the configured text

#     def generate_random_value(self):
#         """Generate a random text value"""
#         if self.default_text:
#             return self.default_text

#         # Generate a random word-like string
#         letters = "abcdefghijklmnopqrstuvwxyz"
#         length = random.randint(3, 8)
#         return "".join(random.choice(letters) for _ in range(length))


# class PositionElementProcessor(NamingElementProcessor):
#     """Processor for position indicator elements (L/R, Top/Bot, Fr/Bk, etc)"""

#     def __init__(self, element_data):
#         super().__init__(element_data)

#         # X軸の値を取得
#         self.xaxis_type = element_data.xaxis_type
#         self.xaxis_enabled = element_data.xaxis_enabled
#         self.xaxis_values = (
#             self.xaxis_type.split("|") if self.xaxis_type and self.xaxis_enabled else []
#         )

#         # Y軸の値を取得
#         self.yaxis_enabled = element_data.yaxis_enabled
#         self.yaxis_values = (
#             POSITION_ENUM_ITEMS["YAXIS"][0][0].split("|") if self.yaxis_enabled else []
#         )

#         # Z軸の値を取得
#         self.zaxis_enabled = element_data.zaxis_enabled
#         self.zaxis_values = (
#             POSITION_ENUM_ITEMS["ZAXIS"][0][0].split("|") if self.zaxis_enabled else []
#         )

#         # すべての可能な位置値を組み合わせる
#         self.position_values = []
#         if self.xaxis_enabled and self.xaxis_values:
#             self.position_values.extend(self.xaxis_values)
#         if self.yaxis_enabled and self.yaxis_values:
#             self.position_values.extend(self.yaxis_values)
#         if self.zaxis_enabled and self.zaxis_values:
#             self.position_values.extend(self.zaxis_values)

#     def build_pattern(self):
#         """Build pattern for position indicators with appropriate separator based on order"""
#         if not self.position_values:
#             return f"(?P<{self.id}>)"

#         # 位置値をエスケープして正規表現パターンを構築
#         escaped_positions = [re.escape(pos) for pos in self.position_values]
#         positions_pattern = "|".join(escaped_positions)

#         # 順序に基づいてセパレーターを適用
#         sep = re.escape(self.separator)

#         if self.order == 0:  # 最初の要素
#             return f"(?P<{self.id}>{positions_pattern}){sep}?"
#         else:  # 順序が1以上の要素
#             return f"{sep}?(?P<{self.id}>{positions_pattern})"

#     def generate_random_value(self):
#         """Generate a random position value"""
#         if self.position_values:
#             return random.choice(self.position_values)
#         return "L"  # デフォルト値


# class CounterElementProcessor(NamingElementProcessor):
#     """Processor for counter elements"""

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         self.padding = element_data.padding
#         self.counter_type = element_data.counter_type  # 'custom' or 'blender'

#     # @add_separator_by_order
#     # @add_named_capture_group
#     def build_pattern(self):
#         """Build pattern for counters with padding and separator"""
#         sep = re.escape(self.separator)

#         if self.counter_type == "blender":
#             return f"(?P<{self.id}>{sep}\\d{{{self.padding}}})$"
#         else:  # 'custom'
#             if self.order == 0:  # 最初の要素
#                 return f"(?P<{self.id}>\\d{{{self.padding}}}){sep}?"
#             else:  # 他の要素
#                 return f"{sep}?(?P<{self.id}>\\d{{{self.padding}}})"

#     def generate_random_value(self):
#         """Generate a random counter value"""
#         max_value = 10**self.padding - 1
#         return f"{random.randint(1, max_value):0{self.padding}d}"

#     def format_value(self, number):
#         """Format a number according to padding"""
#         return f"{int(number):0{self.padding}d}"


# class DateElementProcessor(NamingElementProcessor):
#     """Processor for date elements"""

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         self.date_format = element_data.date_format

#     @add_separator_by_order
#     @add_named_capture_group
#     def build_pattern(self):
#         """Build a pattern that can match dates in various formats with separator"""
#         # これは簡略化されたパターン。実際のアプリケーションに合わせて調整が必要かもしれません
#         return "\\d{4}\\d{2}\\d{2}"

#     def generate_random_value(self):
#         """Generate a current date value"""
#         return datetime.datetime.now().strftime(self.date_format)


# class RegexElementProcessor(NamingElementProcessor):
#     """Processor for custom regex elements"""

#     def __init__(self, element_data):
#         super().__init__(element_data)
#         self.pattern = element_data.pattern

#     @add_separator_by_order
#     @add_named_capture_group
#     def build_pattern(self):
#         """Use the custom pattern directly with separator"""
#         return self.pattern

#     def generate_random_value(self):
#         """Generate a placeholder for regex values"""
#         return f"regex_{random.randint(1, 100)}"


# class NamingProcessor:
#     """Main class for processing naming patterns"""

#     def __init__(self, pattern_data):
#         """
#         Initialize with a naming pattern

#         Args:
#             pattern_data: A NamingPattern from preferences
#         """
#         self.pattern_id = pattern_data.id
#         self.pattern_name = pattern_data.name
#         self.object_type = pattern_data.object_type

#         # Create processors for each element
#         self.processors = []
#         for element in sorted(pattern_data.elements, key=lambda e: e.order):
#             processor = self._create_processor(element)
#             if processor:
#                 self.processors.append(processor)

#     def _create_processor(self, element):
#         """Create the appropriate processor for an element"""
#         element_type = element.element_type

#         if element_type == "text":
#             return TextElementProcessor(element)
#         elif element_type == "free_text":
#             return FreeTextElementProcessor(element)
#         elif element_type == "position":
#             return PositionElementProcessor(element)
#         elif element_type == "counter":
#             return CounterElementProcessor(element)
#         elif element_type == "date":
#             return DateElementProcessor(element)
#         elif element_type == "regex":
#             return RegexElementProcessor(element)

#         print(f"Unknown element type: {element_type}")
#         return None

#     def get_processor(self, element_id):
#         """Get a processor by its ID"""
#         for processor in self.processors:
#             if processor.id == element_id:
#                 return processor
#         return None

#     def standby(self):
#         """Reset all processors"""
#         for processor in self.processors:
#             processor.standby()

#     def analyze_name(self, name):
#         """
#         Extract elements from an existing name

#         Args:
#             name: Name to analyze

#         Returns:
#             dict: Mapping of element IDs to their values
#         """
#         for processor in self.processors:
#             processor.standby()
#             processor.search(name)

#         return {
#             processor.id: processor.value
#             for processor in self.processors
#             if processor.value
#         }

#     def generate_name(self, element_values=None):
#         """
#         Generate a name based on provided element values

#         Args:
#             element_values: Dictionary mapping element IDs to values

#         Returns:
#             str: Generated name
#         """
#         if element_values:
#             for element_id, value in element_values.items():
#                 processor = self.get_processor(element_id)
#                 if processor:
#                     processor.value = value

#         # Build the name from enabled processors with values
#         parts = []
#         for processor in self.processors:
#             rendered = processor.render()
#             if rendered:
#                 separator, value = rendered
#                 if parts:  # Add separator before next part
#                     parts.append(separator)
#                 parts.append(value)

#         return "".join(parts)

#     def update_elements(self, new_values):
#         """
#         Update multiple elements at once

#         Args:
#             new_values: Dictionary mapping element IDs to new values

#         Returns:
#             str: Updated name
#         """
#         if not new_values:
#             return self.generate_name()

#         for element_id, value in new_values.items():
#             processor = self.get_processor(element_id)
#             if processor:
#                 processor.value = value

#         return self.generate_name()

#     def generate_test_names(self, count=5):
#         """
#         Generate random test names

#         Args:
#             count: Number of test names to generate

#         Returns:
#             list: Generated test names
#         """
#         test_names = []
#         for _ in range(count):
#             # Reset all processors
#             self.standby()

#             # Randomly enable some processors
#             for processor in self.processors:
#                 if random.choice([True, False]):
#                     processor.value = processor.generate_random_value()

#             test_names.append(self.generate_name())

#         return test_names


# class NamespaceManager:
#     """Manages name uniqueness within object namespaces"""

#     def __init__(self):
#         self.namespaces = {}

#     def get_namespace(self, obj_id, obj_type):
#         """
#         Get a namespace for an object

#         Args:
#             obj_id: Object ID (usually from id_data)
#             obj_type: Type of object

#         Returns:
#             set: Set of names in this namespace
#         """
#         key = (obj_id, obj_type)
#         if key not in self.namespaces:
#             self.namespaces[key] = set()
#         return self.namespaces[key]

#     def register_namespace(self, obj_id, obj_type, names):
#         """
#         Register a namespace with initial names

#         Args:
#             obj_id: Object ID
#             obj_type: Type of object
#             names: Initial set of names
#         """
#         namespace = self.get_namespace(obj_id, obj_type)
#         namespace.update(names)

#     def check_duplicate(self, obj_id, obj_type, name):
#         """
#         Check if a name exists in a namespace

#         Args:
#             obj_id: Object ID
#             obj_type: Type of object
#             name: Name to check

#         Returns:
#             bool: True if name already exists
#         """
#         namespace = self.get_namespace(obj_id, obj_type)
#         return name in namespace

#     def update_name(self, obj_id, obj_type, old_name, new_name):
#         """
#         Update a name in a namespace

#         Args:
#             obj_id: Object ID
#             obj_type: Type of object
#             old_name: Old name to remove
#             new_name: New name to add
#         """
#         namespace = self.get_namespace(obj_id, obj_type)
#         if old_name in namespace:
#             namespace.remove(old_name)
#         namespace.add(new_name)

#     def find_unique_counter(
#         self, obj_id, obj_type, processor, name_template, max_counter=999
#     ):
#         """
#         Find a unique counter value

#         Args:
#             obj_id: Object ID
#             obj_type: Type of object
#             processor: CounterElementProcessor
#             name_template: Function to generate a name from counter
#             max_counter: Maximum counter value to try

#         Returns:
#             int or None: Unique counter value or None if not found
#         """
#         namespace = self.get_namespace(obj_id, obj_type)

#         for i in range(1, max_counter + 1):
#             formatted = processor.format_value(i)
#             potential_name = name_template(formatted)
#             if potential_name not in namespace:
#                 return i

#         return None


# class RenameableObject:
#     """Base class for objects that can be renamed"""

#     def __init__(self, obj, obj_type, namespace_manager, processor):
#         """
#         Initialize a renameable object

#         Args:
#             obj: The Blender object
#             obj_type: Type of object
#             namespace_manager: NamespaceManager instance
#             processor: NamingProcessor instance
#         """
#         self.obj = obj
#         self.obj_type = obj_type
#         self.namespace_manager = namespace_manager
#         self.processor = processor
#         self.current_name = self.get_current_name()
#         self.new_name = ""
#         self.updated = False

#     def get_current_name(self):
#         """Get the current name of the object"""
#         return self.obj.name

#     def analyze_current_name(self):
#         """Analyze the current name and extract elements"""
#         self.processor.standby()
#         return self.processor.analyze_name(self.current_name)

#     def update_elements(self, new_values):
#         """
#         Update naming elements

#         Args:
#             new_values: Dictionary of element IDs and new values

#         Returns:
#             self: For method chaining
#         """
#         self.new_name = self.processor.update_elements(new_values)
#         self.updated = True
#         return self

#     def check_name_conflict(self):
#         """
#         Check if the new name conflicts with existing names

#         Returns:
#             bool: True if there's a conflict
#         """
#         if not self.new_name or self.new_name == self.current_name:
#             return False

#         return self.namespace_manager.check_duplicate(
#             self.get_namespace_id(), self.obj_type, self.new_name
#         )

#     def resolve_name_conflict(self):
#         """
#         Resolve name conflicts by adding a counter

#         Returns:
#             bool: True if conflict was resolved
#         """
#         if not self.check_name_conflict():
#             return True

#         counter_processor = self.processor.get_processor("counter")
#         if not counter_processor:
#             return False

#         # Function to generate a name with a given counter value
#         def name_template(counter_value):
#             return self.processor.update_elements({"counter": counter_value})

#         unique_counter = self.namespace_manager.find_unique_counter(
#             self.get_namespace_id(), self.obj_type, counter_processor, name_template
#         )

#         if unique_counter:
#             self.new_name = self.processor.update_elements({"counter": unique_counter})
#             return True

#         return False

#     def apply_new_name(self):
#         """
#         Apply the new name to the object

#         Returns:
#             tuple: (old_name, new_name) if successful, None otherwise
#         """
#         if not self.new_name or self.new_name == self.current_name:
#             return None

#         old_name = self.current_name
#         self.obj.name = self.new_name

#         # Update the namespace
#         self.namespace_manager.update_name(
#             self.get_namespace_id(), self.obj_type, old_name, self.new_name
#         )

#         self.current_name = self.new_name
#         self.updated = False

#         return (old_name, self.new_name)

#     @abstractmethod
#     def get_namespace_id(self):
#         """Get the ID for the namespace this object belongs to"""
#         pass


# class PoseBoneObject(RenameableObject):
#     """Specialized renameable object for pose bones"""

#     def get_namespace_id(self):
#         """Get the armature as the namespace ID"""
#         return self.obj.id_data

#     def get_current_name(self):
#         """Get the bone name"""
#         return self.obj.name
