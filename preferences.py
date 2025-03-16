# pyright: reportInvalidTypeForm=false
import json

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from .addon import ADDON_ID
from .core.constants import ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS, SEPARATOR_ITEMS
from .utils.logging import AddonLoggerPreferencesMixin, get_logger

log = get_logger(__name__)


class NamingElementItem(bpy.types.PropertyGroup):
    """Single item within a naming element's options"""

    name: StringProperty(name="Name", description="Name of this item", default="")


class NamingElement(bpy.types.PropertyGroup):
    """Definition of a naming element"""

    id: StringProperty(
        name="ID", description="Unique identifier for this element", default=""
    )

    display_name: StringProperty(
        name="Display Name",
        description="User-friendly name for this element",
        default="",
    )

    element_type: EnumProperty(
        name="Type",
        description="Type of this naming element",
        items=ELEMENT_TYPE_ITEMS,
        default="text",
    )

    enabled: BoolProperty(
        name="Enabled", description="Whether this element is active", default=True
    )

    order: IntProperty(
        name="Order", description="Position in the naming sequence", default=0, min=0
    )

    # For all elements - separator selection
    separator: EnumProperty(
        name="Separator",
        description="Character used to separate this element from the next",
        items=SEPARATOR_ITEMS,
        default="_",
    )

    # For text elements - predefined options
    items: CollectionProperty(
        type=NamingElementItem,
        name="Items",
        description="Predefined text options for this element",
    )

    # For text elements - active item index
    active_item_index: IntProperty(name="Active Item Index", default=0)

    # For counter elements
    padding: IntProperty(
        name="Padding",
        description="Number of digits for counter (zero-padded)",
        default=2,
        min=1,
        max=10,
    )

    # For regex elements
    pattern: StringProperty(
        name="Pattern",
        description="Regular expression pattern for matching",
        default="(.*)",
    )

    # For date elements
    date_format: StringProperty(
        name="Format", description="Date format string (strftime)", default="%Y%m%d"
    )

    # For free text
    default_text: StringProperty(
        name="Default Text", description="Default text to use", default=""
    )

    # For position elements
    xaxis_type: EnumProperty(
        name="X Axis Type",
        description="Type of X-axis position indicator",
        items=[(item[0], item[1], item[2]) for item in POSITION_ENUM_ITEMS["XAXIS"]],
        default="L|R",
    )

    xaxis_enabled: BoolProperty(
        name="X Axis Enabled",
        description="Whether X-axis position is enabled",
        default=True,
    )

    yaxis_enabled: BoolProperty(
        name="Y Axis Enabled",
        description="Whether Y-axis position is enabled",
        default=False,
    )

    zaxis_enabled: BoolProperty(
        name="Z Axis Enabled",
        description="Whether Z-axis position is enabled",
        default=False,
    )


class NamingPattern(bpy.types.PropertyGroup):
    """A complete naming pattern for a specific object type"""

    id: StringProperty(
        name="ID", description="Unique identifier for this pattern", default=""
    )

    name: StringProperty(
        name="Name", description="User-friendly name for this pattern", default=""
    )

    object_type: StringProperty(
        name="Object Type",
        description="Type of object this pattern applies to",
        default="",
    )

    elements: CollectionProperty(
        type=NamingElement,
        name="Elements",
        description="Elements that make up this naming pattern",
    )

    active_element_index: IntProperty(name="Active Element Index", default=0)

    edit_mode: BoolProperty(
        name="Edit Mode",
        description="Whether the pattern is in edit mode",
        default=False,
    )

    # Add or remove an element
    def add_element(self, id, element_type, display_name):
        elem = self.elements.add()
        elem.id = id
        elem.element_type = element_type
        elem.display_name = display_name
        elem.order = len(self.elements) - 1
        return elem

    def remove_element(self, index):
        if 0 <= index < len(self.elements):
            removed_order = self.elements[index].order
            self.elements.remove(index)

            # 削除されたエレメントよりも高い順序値を持つエレメントの順序を調整
            for elem in self.elements:
                if elem.order > removed_order:
                    elem.order -= 1

    def move_element_up(self, index):
        """エレメントを上に移動（順序を前に）"""
        if 0 < index < len(self.elements):
            # 現在のエレメントと1つ前のエレメントの順序値を取得
            current_elem = self.elements[index]
            prev_elem = self.elements[index - 1]

            # 順序値を交換
            temp_order = current_elem.order
            current_elem.order = prev_elem.order
            prev_elem.order = temp_order

            # UIリストの表示順序に反映するために、コレクション内の要素も交換
            self.elements.move(index, index - 1)
            self.active_element_index = index - 1

    def move_element_down(self, index):
        """エレメントを下に移動（順序を後ろに）"""
        if 0 <= index < len(self.elements) - 1:
            # 現在のエレメントと1つ後のエレメントの順序値を取得
            current_elem = self.elements[index]
            next_elem = self.elements[index + 1]

            # 順序値を交換
            temp_order = current_elem.order
            current_elem.order = next_elem.order
            next_elem.order = temp_order

            # UIリストの表示順序に反映するために、コレクション内の要素も交換
            self.elements.move(index, index + 1)
            self.active_element_index = index + 1


class ModularRenamerPreferences(
    AddonLoggerPreferencesMixin,
    bpy.types.AddonPreferences,
):
    """Addon preferences for ModularRenamer"""

    bl_idname = ADDON_ID

    # Collection of all naming patterns
    patterns: CollectionProperty(
        type=NamingPattern,
        name="Naming Patterns",
        description="All available naming patterns",
    )

    # Currently selected pattern
    active_pattern_index: IntProperty(name="Active Pattern", default=0)

    def add_pattern(self, id, name, object_type):
        pattern = self.patterns.add()
        pattern.id = id
        pattern.name = name
        pattern.object_type = object_type
        return pattern

    def remove_pattern(self, index):
        if 0 <= index < len(self.patterns):
            self.patterns.remove(index)

    # Export patterns to JSON
    def export_patterns(self, filepath):
        data = []
        for pattern in self.patterns:
            pattern_data = {
                "id": pattern.id,
                "name": pattern.name,
                "object_type": pattern.object_type,
                "elements": [],
            }

            for element in pattern.elements:
                element_config = {
                    "id": element.id,
                    "display_name": element.display_name,
                    "type": element.element_type,
                    "enabled": element.enabled,
                    "order": element.order,
                    "separator": element.separator,
                }

                # Add type-specific properties
                if element.element_type == "text":
                    element_config["items"] = [item.name for item in element.items]
                elif element.element_type == "counter":
                    element_config["padding"] = element.padding
                elif element.element_type == "regex":
                    element_config["pattern"] = element.pattern
                elif element.element_type == "date":
                    element_config["date_format"] = element.date_format
                elif element.element_type == "free_text":
                    element_config["default_text"] = element.default_text
                elif element.element_type == "position":
                    element_config["position_type"] = element.position_type

                pattern_data["elements"].append(element_config)

            data.append(pattern_data)

        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)

        return True

    # Import patterns from JSON
    def import_patterns(self, filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Clear existing patterns
            self.patterns.clear()

            for pattern_data in data:
                pattern = self.add_pattern(
                    pattern_data["id"],
                    pattern_data["name"],
                    pattern_data["object_type"],
                )

                for element_config in pattern_data["elements"]:
                    element = pattern.add_element(
                        element_config["id"],
                        element_config["type"],
                        element_config["display_name"],
                    )

                    element.enabled = element_config.get("enabled", True)
                    element.order = element_config.get("order", 0)
                    element.separator = element_config.get("separator", "_")

                    # Set type-specific properties
                    if element.element_type == "text" and "items" in element_config:
                        for item_name in element_config["items"]:
                            item = element.items.add()
                            item.name = item_name

                    if element.element_type == "counter" and "padding" in element_config:
                        element.padding = element_config["padding"]

                    if element.element_type == "regex" and "pattern" in element_config:
                        element.pattern = element_config["pattern"]

                    if element.element_type == "date" and "date_format" in element_config:
                        element.date_format = element_config["date_format"]

                    if (
                        element.element_type == "free_text"
                        and "default_text" in element_config
                    ):
                        element.default_text = element_config["default_text"]

                    if (
                        element.element_type == "position"
                        and "position_type" in element_config
                    ):
                        element.position_type = element_config["position_type"]

            return True

        except Exception as e:
            print(f"Error importing patterns: {e}")
            return False

    def create_default_patterns(self):
        # Clear existing patterns
        self.patterns.clear()

        # Create a default pattern for pose bones
        bone_pattern = self.add_pattern(
            "pose_bone_default", "Default Bone Pattern", "POSE_BONE"
        )

        # Add prefix element
        prefix = bone_pattern.add_element("prefix", "text", "Prefix")
        for name in ["CTRL", "DEF", "MCH", "ORG", "DRV", "TRG", "PROP"]:
            item = prefix.items.add()
            item.name = name

        # Add middle element
        middle = bone_pattern.add_element("middle", "text", "Middle")
        for name in [
            "Bone",
            "Root",
            "Spine",
            "Chest",
            "Torso",
            "Hips",
            "Tail",
            "Neck",
            "Head",
            "Shoulder",
            "Arm",
            "Elbow",
            "ForeArm",
            "Hand",
            "InHand",
            "Finger",
            "UpLeg",
            "Leg",
            "Shin",
            "Foot",
            "Knee",
            "Toe",
        ]:
            item = middle.items.add()
            item.name = name

        # Add finger element
        finger = bone_pattern.add_element("finger", "text", "Finger")
        for name in ["Finger", "Thumb", "Index", "Middle", "Ring", "Pinky"]:
            item = finger.items.add()
            item.name = name

        # Add suffix element
        suffix = bone_pattern.add_element("suffix", "text", "Suffix")
        for name in [
            "Base",
            "Tweak",
            "Pole",
            "IK",
            "FK",
            "Roll",
            "Rot",
            "Loc",
            "Scale",
            "INT",
        ]:
            item = suffix.items.add()
            item.name = name

        # Add counter element
        counter = bone_pattern.add_element("counter", "counter", "Counter")
        counter.padding = 2
        counter.separator = "-"

        # Add position element
        position = bone_pattern.add_element("position", "position", "Position")
        position.separator = "."
        # X軸の設定
        position.xaxis_type = "L|R"
        position.xaxis_enabled = True
        # Y軸の設定（デフォルトで無効だが、設定可能にする）
        position.yaxis_enabled = False
        # Z軸の設定（デフォルトで無効だが、設定可能にする）
        position.zaxis_enabled = False

        return True

    def draw(self, context):
        layout = self.layout
        self.draw_logger_preferences(layout)


# Registration
# classes = [NamingElementItem, NamingElement, NamingPattern, ModularRenamerPreferences]


# def register():
#     for cls in classes:
#         bpy.utils.register_class(cls)


# def unregister():
#     for cls in reversed(classes):
#         bpy.utils.unregister_class(cls)


# # Utility function to get preferences
# def get_preferences():
#     return bpy.context.preferences.addons["modular-renamer"].preferences
