# # pyright: reportInvalidTypeForm=false
# import json
# from typing import List, Optional

# import bpy
# from bpy.props import (
#     BoolProperty,
#     CollectionProperty,
#     EnumProperty,
#     FloatProperty,
#     IntProperty,
#     PointerProperty,
#     StringProperty,
# )

# from ..core.constants import ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS, SEPARATOR_ITEMS
# # from ..utils.logging import get_logger

# # log = get_logger(__name__)


# class ModifiedPropMixin:
#     def _update_modified(self):
#         """自分と親のmodifiedフラグをTrueに"""
#         if hasattr(self, "modified"):
#             self.modified = True
#         parent = getattr(self, "id_data", None)
#         if parent and hasattr(parent, "_update_modified"):
#             parent._update_modified()


# def modified_updater():
#     return lambda self, context: self._update_modified()


# class NamingElementItemProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
#     """Single item within a naming element's options"""

#     name: StringProperty(
#         name="Name",
#         description="Name of this item",
#         default="",
#         update=modified_updater(),
#     )


# class NamingElementProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
#     """Definition of a naming element"""

#     id: StringProperty(
#         name="ID", description="Unique identifier for this element", default=""
#     )

#     display_name: StringProperty(
#         name="Display Name",
#         description="User-friendly name for this element",
#         default="",
#         update=modified_updater(),
#     )

#     element_type: EnumProperty(
#         name="Type",
#         description="Type of this naming element",
#         items=ELEMENT_TYPE_ITEMS,
#         default="text",
#         update=modified_updater(),
#     )

#     enabled: BoolProperty(
#         name="Enabled",
#         description="Whether this element is active",
#         default=True,
#         update=modified_updater(),
#     )

#     order: IntProperty(
#         name="Order",
#         description="Position in the naming sequence",
#         default=0,
#         min=0,
#         update=modified_updater(),
#     )

#     # For all elements - separator selection
#     separator: EnumProperty(
#         name="Separator",
#         description="Character used to separate this element from the next",
#         items=SEPARATOR_ITEMS,
#         default="_",
#         update=modified_updater(),
#     )

#     # For text elements - predefined options
#     items: CollectionProperty(
#         type=NamingElementItemProperty,
#         name="Items",
#         description="Predefined text options for this element",
#     )

#     # For text elements - active item index
#     active_item_index: IntProperty(
#         name="Active Item Index", default=0, update=modified_updater()
#     )

#     def get_item_by_idx(self, idx: int) -> Optional[NamingElementItemProperty]:
#         if not self.items:
#             return None
#         return self.items[idx]

#     # For counter elements
#     padding: IntProperty(
#         name="Padding",
#         description="Number of digits for counter (zero-padded)",
#         default=2,
#         min=1,
#         max=10,
#         update=modified_updater(),
#     )

#     # # For regex elements
#     # pattern: StringProperty(
#     #     name="Pattern",
#     #     description="Regular expression pattern for matching",
#     #     default="(.*)",
#     #     update=modified_updater(),
#     # )

#     # # For date elements
#     # date_format: StringProperty(
#     #     name="Format",
#     #     description="Date format string (strftime)",
#     #     default="%Y%m%d",
#     #     update=modified_updater(),
#     # )

#     # # For free text
#     # default_text: StringProperty(
#     #     name="Default Text",
#     #     description="Default text to use",
#     #     default="",
#     #     update=modified_updater(),
#     # )

#     # For position elements
#     xaxis_type: EnumProperty(
#         name="X Axis Type",
#         description="Type of X-axis position indicator",
#         items=[(item[0], item[1], item[2]) for item in POSITION_ENUM_ITEMS["XAXIS"]],
#         default="L|R",
#         update=modified_updater(),
#     )

#     xaxis_enabled: BoolProperty(
#         name="X Axis Enabled",
#         description="Whether X-axis position is enabled",
#         default=True,
#         update=modified_updater(),
#     )

#     yaxis_enabled: BoolProperty(
#         name="Y Axis Enabled",
#         description="Whether Y-axis position is enabled",
#         default=False,
#         update=modified_updater(),
#     )

#     zaxis_enabled: BoolProperty(
#         name="Z Axis Enabled",
#         description="Whether Z-axis position is enabled",
#         default=False,
#         update=modified_updater(),
#     )


# class NamingPatternProperty(bpy.types.PropertyGroup, ModifiedPropMixin):
#     """A complete naming pattern for a specific object type"""

#     id: StringProperty(
#         name="ID", description="Unique identifier for this pattern", default=""
#     )

#     name: StringProperty(
#         name="Name",
#         description="User-friendly name for this pattern",
#         default="",
#         update=modified_updater(),
#     )

#     elements: CollectionProperty(
#         type=NamingElementProperty,
#         name="Elements",
#         description="Elements that make up this naming pattern",
#     )

#     modified: BoolProperty(
#         name="Modified",
#         description="Whether the pattern has been modified",
#         default=True,
#     )

#     active_element_index: IntProperty(name="Active Element Index", default=0)

#     def get_element_by_id(self, id: str) -> Optional[NamingElementProperty]:
#         if not self.elements:
#             return None
#         for elem in self.elements:
#             if elem.id == id:
#                 return elem
#         return None

#     # Add or remove an element
#     def add_element(self, id, element_type, display_name):
#         self.modified = True
#         elem = self.elements.add()
#         elem.id = id
#         elem.element_type = element_type
#         elem.display_name = display_name
#         elem.order = len(self.elements) - 1
#         return elem

#     def remove_element(self, index):
#         self.modified = True
#         if 0 <= index < len(self.elements):
#             removed_order = self.elements[index].order
#             self.elements.remove(index)

#             # 削除されたエレメントよりも高い順序値を持つエレメントの順序を調整
#             for elem in self.elements:
#                 if elem.order > removed_order:
#                     elem.order -= 1

#     def move_element_up(self, index):
#         """エレメントを上に移動（順序を前に）"""
#         self.modified = True
#         if 0 < index < len(self.elements):
#             # 現在のエレメントと1つ前のエレメントの順序値を取得
#             current_elem = self.elements[index]
#             prev_elem = self.elements[index - 1]

#             # 順序値を交換
#             temp_order = current_elem.order
#             current_elem.order = prev_elem.order
#             prev_elem.order = temp_order

#             # UIリストの表示順序に反映するために、コレクション内の要素も交換
#             self.elements.move(index, index - 1)
#             self.active_element_index = index - 1

#     def move_element_down(self, index):
#         """エレメントを下に移動（順序を後ろに）"""
#         self.modified = True
#         if 0 <= index < len(self.elements) - 1:
#             # 現在のエレメントと1つ後のエレメントの順序値を取得
#             current_elem = self.elements[index]
#             next_elem = self.elements[index + 1]

#             # 順序値を交換
#             temp_order = current_elem.order
#             current_elem.order = next_elem.order
#             next_elem.order = temp_order

#             # UIリストの表示順序に反映するために、コレクション内の要素も交換
#             self.elements.move(index, index + 1)
#             self.active_element_index = index + 1
