# pyright: reportInvalidTypeForm=false
import random
from typing import Set

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import Context

from .addon import prefs
from .core.constants import ELEMENT_TYPE_ITEMS, POSITION_ENUM_ITEMS
from .core.pattern_system import PatternFacade
from .core.rename_service import OperationScope, RenameOperationType, RenameService
from .core.rename_target import TargetCollector
from .utils.logging import get_logger

log = get_logger(__name__)


class MODRENAMER_OT_Rename(bpy.types.Operator):
    """
    一括リネーム操作を実行する
    """

    bl_idname = "modrenamer.rename"
    bl_label = "Rename"
    bl_options = {"REGISTER", "UNDO"}

    # TODO: インデックス指定にしたい
    target_element: bpy.props.StringProperty(
        name="Target Element",
        description="リネーム対象の要素",
        default="",
    )  # type: ignore

    operation_type: bpy.props.EnumProperty(
        name="Operation Type",
        description="リネーム操作の種類",
        items=[
            ("ADD_REPLACE", "Add Replace", "Add Replace"),
            ("REMOVE", "Remove", "Remove"),
        ],
        default="ADD_REPLACE",
    )  # type: ignore

    index: bpy.props.IntProperty(
        name="Index",
        description="Preset Index or Counter Index",
        default=0,
    )  # type: ignore

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(
            TargetCollector(
                context, OperationScope.from_context(context)
            ).get_selected_items()
        )

    def execute(self, context: Context) -> Set[str]:
        pr = prefs(context)

        target_element = pr.get_active_pattern().get_element_by_id(self.target_element)
        if not target_element:
            self.report({"ERROR"}, "リネーム対象が見つかりません")
            return {"CANCELLED"}

        if target_element.element_type == "numeric_counter":
            target_value = self.index
        else:
            target_item = target_element.get_item_by_idx(self.index)
            if not target_item:
                self.report({"ERROR"}, "リネーム対象が見つかりません")
                return {"CANCELLED"}
            target_value = target_item.name

        if self.operation_type == "ADD_REPLACE":
            update_dict = {target_element.id: target_value}
        else:
            update_dict = {target_element.id: None}

        rs = RenameService(context, OperationScope.from_context(context))
        if not rs.r_ctx:
            self.report({"ERROR"}, "リネーム対象が見つかりません")
            return {"CANCELLED"}

        rs.generate_rename_plan(update_dict)
        rs.apply_rename_plan()

        # 全てのエリアを再描画
        for area in context.screen.areas:
            area.tag_redraw()
        return {"FINISHED"}


class MODRENAMER_OT_PatternPreview(bpy.types.Operator):
    """Test the current naming pattern with random values"""

    bl_idname = "modrenamer.pattern_preview"
    bl_label = "Pattern Preview"

    count: IntProperty(
        name="Count",
        description="Number of test names to generate",
        default=5,
        min=1,
        max=20,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        pr = prefs(context)
        return bool(pr.get_active_pattern())

    def execute(self, context):
        pf = PatternFacade(context)
        pattern = pf.get_active_pattern()
        if not pattern:
            self.report({"ERROR"}, "No active naming pattern selected")
            return {"CANCELLED"}

        test_names = pattern.gen_test_names(self.count)

        # Display test names in a popup
        def draw(self, _context):
            layout = self.layout
            for name in test_names:
                layout.label(text=name)

        context.window_manager.popup_menu(draw, title="Test Names", icon="INFO")

        return {"FINISHED"}


class MODRENAMER_UL_ElementsList(bpy.types.UIList):
    """要素を表示するためのカスタム UI リスト"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        # data は NamingPattern、item は NamingElement
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # 要素の有効/無効トグル
            row = layout.row(align=True)
            row.prop(item, "enabled", text="", emboss=False)

            # 要素の名前
            if item.display_name:
                text = item.display_name
            else:
                text = f"Element {index}"

            row.label(text=text)

            # タイプ表示
            row.label(text=f"({item.element_type})")

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


# カスタム UI リストクラス - Text Items 用
class MODRENAMER_UL_TextItemsList(bpy.types.UIList):
    """テキスト項目を表示するためのカスタム UI リスト"""

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        # data は NamingElement、item は NamingElementItem
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.label(text=item.name)

        elif self.layout_type in {"GRID"}:
            layout.alignment = "CENTER"
            layout.label(text="", icon_value=icon)


class MODRENAMER_PT_MainPanel(bpy.types.Panel):
    """Main panel for the ModularRenamer addon"""

    bl_label = "Modular Renamer"
    bl_idname = "MODRENAMER_PT_MainPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        pr = prefs()

        row = layout.row()
        row.operator("wm.save_userpref", text="Save User Prefs")
        row.label(text="Pattern:")

        if pr.patterns:
            row = layout.row()
            row.template_list(
                "UI_UL_list",
                "pattern_list",
                pr,
                "patterns",
                pr,
                "active_pattern_index",
            )

            col = row.column(align=True)
            col.operator("modrenamer.add_pattern", icon="ADD", text="")
            col.operator("modrenamer.remove_pattern", icon="REMOVE", text="")
            col.separator()
            col.operator(
                "modrenamer.pattern_preview", icon="OUTLINER_OB_LIGHT", text=""
            )

            # Show active pattern details
            if pr.active_pattern_index < len(pr.patterns):
                pattern = pr.patterns[pr.active_pattern_index]

                # Object type
                row = layout.row()

                # Edit mode toggle
                row = layout.row()
                if pr.edit_mode:
                    row.alert = True
                    row.operator(
                        "modrenamer.toggle_edit_mode",
                        text="Exit Edit Mode",
                        icon="SCREEN_BACK",
                    )
                else:
                    row.operator(
                        "modrenamer.toggle_edit_mode",
                        text="Enter Edit Mode",
                        icon="SETTINGS",
                    )

                # Elements section
                layout.separator()

                if pr.edit_mode:
                    # In edit mode, show element list with edit controls
                    self.draw_edit_mode(layout, pattern)
                else:
                    # Normal mode, show elements for renaming
                    layout.label(text="Elements:")
                    self.draw_pattern_elements(layout, pattern)

                    # Actions
                    # layout.separator()
                    # row = layout.row(align=True)
                    # row.operator("modrenamer.bulk_rename", icon="SORTSIZE")
        else:
            layout.operator(
                "modrenamer.create_default_patterns", text="Create Default Patterns"
            )

    def draw_edit_mode(self, layout, pattern):
        """Draw the edit mode UI for element management"""
        box = layout.box()
        row = box.row()
        row.label(text="Elements:", icon="OUTLINER_DATA_GP_LAYER")

        # Add element button
        row.operator("modrenamer.add_element", text="", icon="ADD")

        # Element list - カスタムUIリストを使用
        row = box.row()
        row.template_list(
            "MODRENAMER_UL_ElementsList",
            "element_list",
            pattern,
            "elements",
            pattern,
            "active_element_index",
        )

        # Element controls
        col = row.column(align=True)
        col.operator("modrenamer.move_element_up", text="", icon="TRIA_UP")
        col.operator("modrenamer.move_element_down", text="", icon="TRIA_DOWN")
        col.separator()
        col.operator("modrenamer.remove_element", text="", icon="REMOVE")

        # Selected element details
        if pattern.active_element_index < len(pattern.elements):
            element = pattern.elements[pattern.active_element_index]

            # Element properties
            ele_box = box.box()
            row = ele_box.row()
            row.prop(element, "display_name", text="Name")
            row.prop(element, "enabled", text="")

            # Element type (read-only in edit mode)
            row = ele_box.row()
            row.label(text=f"Type: {element.element_type}")

            # Separator (disabled for first element)
            row = ele_box.row()
            row.enabled = element.order > 0
            row.prop(element, "separator", text="Separator")

            # Element-specific properties
            self.draw_element_properties(ele_box, element, pattern.active_element_index)
        else:

            ele_box = layout.box()
            row = ele_box.row()
            row.label(text="No element selected.")

    def draw_element_properties(self, layout, element, element_index):
        """Draw the properties specific to each element type in edit mode"""
        layout.separator()

        if element.element_type == "text":
            self.draw_text_element_properties(layout, element, element_index)
        elif element.element_type == "position":
            self.draw_position_element_properties(layout, element)
        elif element.element_type == "numeric_counter":
            self.draw_counter_element_properties(layout, element)
        # elif element.element_type == "blender_counter":
        #     self.draw_counter_element_properties(layout, element)
        # elif element.element_type == "free_text":
        #     self.draw_free_text_element_properties(layout, element)
        # elif element.element_type == "date":
        #     self.draw_date_element_properties(layout, element)
        # elif element.element_type == "regex":
        #     self.draw_regex_element_properties(layout, element)

    def draw_text_element_properties(self, layout, element, element_index):
        """Draw properties for text elements in edit mode"""
        row = layout.row()
        row.label(text="Text Items:")

        # Add item button
        row.operator("modrenamer.add_text_item", text="", icon="ADD").element_index = (
            element_index
        )

        # Text items list - カスタムUIリストを使用
        row = layout.row()
        row.template_list(
            "MODRENAMER_UL_TextItemsList",
            "text_item_list",
            element,
            "items",
            element,
            "active_item_index",
        )

        # Item controls
        col = row.column(align=True)
        col.operator(
            "modrenamer.move_text_item_up", text="", icon="TRIA_UP"
        ).element_index = element_index
        col.operator(
            "modrenamer.move_text_item_down", text="", icon="TRIA_DOWN"
        ).element_index = element_index
        col.separator()
        col.operator(
            "modrenamer.remove_text_item", text="", icon="REMOVE"
        ).element_index = element_index

        # Edit selected item
        if element.active_item_index < len(element.items):
            item = element.items[element.active_item_index]
            row = layout.row()
            row.prop(item, "name", text="Item")

    def draw_position_element_properties(self, layout, element):
        """Draw properties for position elements in edit mode"""
        # X軸の設定
        box = layout.box()
        row = box.row()
        row.prop(element, "xaxis_enabled", text="X Axis")

        if element.xaxis_enabled:
            row = box.row()
            row.label(text="X Axis Type:")
            row = box.row()
            row.prop(element, "xaxis_type", text="")

        # Y軸の設定
        box = layout.box()
        row = box.row()
        row.prop(element, "yaxis_enabled", text="Y Axis (Top/Bot)")

        # Z軸の設定
        box = layout.box()
        row = box.row()
        row.prop(element, "zaxis_enabled", text="Z Axis (Fr/Bk)")

    def draw_counter_element_properties(self, layout, element):
        """Draw properties for counter elements in edit mode"""
        row = layout.row()
        row.prop(element, "padding", text="Padding")

    # def draw_free_text_element_properties(self, layout, element):
    #     """Draw properties for free text elements in edit mode"""
    #     row = layout.row()
    #     row.prop(element, "default_text", text="Default Text")

    # def draw_date_element_properties(self, layout, element):
    #     """Draw properties for date elements in edit mode"""
    #     row = layout.row()
    #     row.prop(element, "date_format", text="Format")

    # def draw_regex_element_properties(self, layout, element):
    #     """Draw properties for regex elements in edit mode"""
    #     row = layout.row()
    #     row.prop(element, "pattern", text="Pattern")

    def draw_pattern_elements(self, layout, pattern):
        """Draw the elements of a pattern for renaming (non-edit mode)"""
        for element in sorted(pattern.elements, key=lambda e: e.order):
            if not element.enabled:
                continue

            box = layout.box()
            row = box.row()
            row.label(text=element.display_name)

            if element.element_type == "text":
                self.draw_text_element(box, element)
            elif element.element_type == "position":
                self.draw_position_element(box, element)
            elif element.element_type == "numeric_counter":
                self.draw_counter_element(box, element)
            # elif element.element_type == "blender_counter":
            #     self.draw_counter_element(box, element)
            # elif element.element_type == "free_text":
            #     self.draw_free_text_element(box, element)
            # elif element.element_type == "date":
            #     self.draw_date_element(box, element)
            # elif element.element_type == "regex":
            #     self.draw_regex_element(box, element)

    def draw_text_element(self, layout, element):
        """Draw UI for a text element in normal mode"""
        flow = layout.column_flow(columns=3)
        for idx, item in enumerate(element.items):
            op = flow.operator("modrenamer.rename", text=item.name)
            op.operation_type = RenameOperationType.ADD_REPLACE
            op.target_element = element.id
            op.index = idx

        row = layout.row(align=True)
        op = row.operator("modrenamer.rename", text="Remove", icon="X")
        op.operation_type = RenameOperationType.REMOVE
        op.target_element = element.id

    def draw_position_element(self, layout, element):
        """Draw UI for a position element in normal mode"""
        # すべての有効な軸の値を表示

        # X軸の値
        if element.xaxis_enabled and element.xaxis_type:
            pos_parts = element.xaxis_type.split("|")
            if len(pos_parts) == 2:
                left, right = pos_parts
                row = layout.row(align=True)

                # Left position
                op = row.operator("modrenamer.rename", text=left)
                op.operation_type = RenameOperationType.ADD_REPLACE
                op.target_element = element.id
                op.index = 0

                # Right position
                op = row.operator("modrenamer.rename", text=right)
                op.operation_type = RenameOperationType.ADD_REPLACE
                op.target_element = element.id
                op.index = 1

        # Y軸の値
        if element.yaxis_enabled:
            pos_parts = POSITION_ENUM_ITEMS["YAXIS"][0][0].split("|")
            if len(pos_parts) == 2:
                top, bot = pos_parts
                row = layout.row(align=True)

                # Top position
                op = row.operator("modrenamer.rename", text=top)
                op.operation_type = RenameOperationType.ADD_REPLACE
                op.target_element = element.id
                op.index = 0

                # Bottom position
                op = row.operator("modrenamer.rename", text=bot)
                op.operation_type = RenameOperationType.ADD_REPLACE
                op.target_element = element.id
                op.index = 1

        # Z軸の値
        if element.zaxis_enabled:
            pos_parts = POSITION_ENUM_ITEMS["ZAXIS"][0][0].split("|")
            if len(pos_parts) == 2:
                front, back = pos_parts
                row = layout.row(align=True)

                # Front position
                op = row.operator("modrenamer.rename", text=front)
                op.operation_type = RenameOperationType.ADD_REPLACE
                op.target_element = element.id
                op.index = 0

                # Back position
                op = row.operator("modrenamer.rename", text=back)
                op.operation_type = RenameOperationType.ADD_REPLACE
                op.target_element = element.id
                op.index = 1

    def draw_counter_element(self, layout, element):
        """Draw UI for a counter element in normal mode"""
        flow = layout.column_flow(columns=5)
        for i in range(1, 11):
            op = flow.operator("modrenamer.rename", text=f"{i:0{element.padding}d}")
            op.operation_type = RenameOperationType.ADD_REPLACE
            op.target_element = element.id
            op.index = i

        row = layout.row(align=True)
        op = row.operator("modrenamer.rename", text="Remove", icon="X")
        op.operation_type = RenameOperationType.REMOVE
        op.target_element = element.id
        op.index = 0

    # def draw_free_text_element(self, layout, element):
    #     """Draw UI for a free text element in normal mode"""
    #     row = layout.row(align=True)
    #     row.prop(element, "default_text", text="")
    #     op = row.operator("modrenamer.add_remove_element", text="", icon="CHECKMARK")
    #     op.operation = "add"
    #     op.element_id = element.id
    #     op.value = element.default_text

    #     row = layout.row(align=True)
    #     op = row.operator("modrenamer.add_remove_element", text="Remove", icon="X")
    #     op.operation = "delete"
    #     op.element_id = element.id

    # def draw_date_element(self, layout, element):
    #     """Draw UI for a date element in normal mode"""
    #     row = layout.row()
    #     row.prop(element, "date_format", text="Format")
    #     op = row.operator("modrenamer.add_remove_element", text="", icon="CHECKMARK")
    #     op.operation = "add"
    #     op.element_id = element.id
    #     op.value = "date"  # Will be formatted when applied

    #     row = layout.row(align=True)
    #     op = row.operator("modrenamer.add_remove_element", text="Remove", icon="X")
    #     op.operation = "delete"
    #     op.element_id = element.id

    # def draw_regex_element(self, layout, element):
    #     """Draw UI for a regex element in normal mode"""
    #     row = layout.row()
    #     row.prop(element, "pattern", text="Pattern")

    #     row = layout.row(align=True)
    #     op = row.operator("modrenamer.add_remove_element", text="Add", icon="CHECKMARK")
    #     op.operation = "add"
    #     op.element_id = element.id
    #     op.value = element.pattern

    #     row = layout.row(align=True)
    #     op = row.operator("modrenamer.add_remove_element", text="Remove", icon="X")
    #     op.operation = "delete"
    #     op.element_id = element.id


class MODRENAMER_OT_AddPattern(bpy.types.Operator):
    """Add a new naming pattern"""

    bl_idname = "modrenamer.add_pattern"
    bl_label = "Add Pattern"

    pattern_name: StringProperty(name="Pattern Name", default="New Pattern")

    # pattern_type: EnumProperty(
    #     name="Object Type", items=RENAMABLE_OBJECT_TYPES, default="POSE_BONE"
    # )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "pattern_name")
        # layout.prop(self, "pattern_type")

    def execute(self, context):
        pr = prefs()
        pattern_id = f"pattern_{len(pr.patterns) + 1}"

        pattern = pr.add_pattern(pattern_id, self.pattern_name)
        pr.active_pattern_index = len(pr.patterns) - 1

        return {"FINISHED"}


class MODRENAMER_OT_RemovePattern(bpy.types.Operator):
    """Remove the selected naming pattern"""

    bl_idname = "modrenamer.remove_pattern"
    bl_label = "Remove Pattern"

    def execute(self, context):
        pr = prefs()

        if not pr.patterns:
            return {"CANCELLED"}

        pr.remove_pattern(pr.active_pattern_index)

        if pr.active_pattern_index >= len(pr.patterns):
            pr.active_pattern_index = max(0, len(pr.patterns) - 1)

        return {"FINISHED"}


# New operators for Edit Mode functionality


class MODRENAMER_OT_ToggleEditMode(bpy.types.Operator):
    """Toggle edit mode for the current pattern"""

    bl_idname = "modrenamer.toggle_edit_mode"
    bl_label = "Toggle Edit Mode"

    def execute(self, context):
        pr = prefs()
        pr.edit_mode = not pr.edit_mode
        return {"FINISHED"}


class MODRENAMER_OT_AddElement(bpy.types.Operator):
    """Add a new naming element to the pattern"""

    bl_idname = "modrenamer.add_element"
    bl_label = "Add Element"

    element_type: EnumProperty(
        name="Element Type", items=ELEMENT_TYPE_ITEMS, default="text"
    )

    display_name: StringProperty(name="Display Name", default="New Element")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "element_type")
        layout.prop(self, "display_name")

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            self.report({"ERROR"}, "No active naming pattern selected")
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        # Generate a unique ID
        element_id = f"{self.element_type}_{len(pattern.elements) + 1}"

        # Add the new element
        element = pattern.add_element(element_id, self.element_type, self.display_name)

        # Set active element to the new one
        pattern.active_element_index = len(pattern.elements) - 1

        return {"FINISHED"}


class MODRENAMER_OT_RemoveElement(bpy.types.Operator):
    """Remove the selected naming element from the pattern"""

    bl_idname = "modrenamer.remove_element"
    bl_label = "Remove Element"

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            self.report({"ERROR"}, "No active naming pattern selected")
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if pattern.active_element_index >= len(pattern.elements):
            self.report({"ERROR"}, "No active element selected")
            return {"CANCELLED"}

        # Remove the element
        pattern.remove_element(pattern.active_element_index)

        # Adjust active index if needed
        if pattern.active_element_index >= len(pattern.elements):
            pattern.active_element_index = max(0, len(pattern.elements) - 1)

        return {"FINISHED"}


class MODRENAMER_OT_MoveElementUp(bpy.types.Operator):
    """Move the selected element up in the order"""

    bl_idname = "modrenamer.move_element_up"
    bl_label = "Move Element Up"

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if pattern.active_element_index <= 0 or pattern.active_element_index >= len(
            pattern.elements
        ):
            return {"CANCELLED"}

        pattern.move_element_up(pattern.active_element_index)

        return {"FINISHED"}


class MODRENAMER_OT_MoveElementDown(bpy.types.Operator):
    """Move the selected element down in the order"""

    bl_idname = "modrenamer.move_element_down"
    bl_label = "Move Element Down"

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if (
            pattern.active_element_index < 0
            or pattern.active_element_index >= len(pattern.elements) - 1
        ):
            return {"CANCELLED"}

        pattern.move_element_down(pattern.active_element_index)

        return {"FINISHED"}


# Text Item management operators


class MODRENAMER_OT_AddTextItem(bpy.types.Operator):
    """Add a new text item to the element"""

    bl_idname = "modrenamer.add_text_item"
    bl_label = "Add Text Item"

    element_index: IntProperty(name="Element Index", default=0)

    item_name: StringProperty(name="Item Name", default="New Item")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "item_name")

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if self.element_index >= len(pattern.elements):
            return {"CANCELLED"}

        element = pattern.elements[self.element_index]

        # Add the new item
        item = element.items.add()
        item.name = self.item_name

        # Set active item to the new one
        element.active_item_index = len(element.items) - 1

        return {"FINISHED"}


class MODRENAMER_OT_RemoveTextItem(bpy.types.Operator):
    """Remove the selected text item from the element"""

    bl_idname = "modrenamer.remove_text_item"
    bl_label = "Remove Text Item"

    element_index: IntProperty(name="Element Index", default=0)

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if self.element_index >= len(pattern.elements):
            return {"CANCELLED"}

        element = pattern.elements[self.element_index]

        if element.active_item_index >= len(element.items):
            return {"CANCELLED"}

        # Remove the item
        element.items.remove(element.active_item_index)

        # Adjust active index if needed
        if element.active_item_index >= len(element.items):
            element.active_item_index = max(0, len(element.items) - 1)

        return {"FINISHED"}


class MODRENAMER_OT_MoveTextItemUp(bpy.types.Operator):
    """Move the selected text item up in the list"""

    bl_idname = "modrenamer.move_text_item_up"
    bl_label = "Move Item Up"

    element_index: IntProperty(name="Element Index", default=0)

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if self.element_index >= len(pattern.elements):
            return {"CANCELLED"}

        element = pattern.elements[self.element_index]

        if element.active_item_index <= 0 or element.active_item_index >= len(
            element.items
        ):
            return {"CANCELLED"}

        # Move the item up
        element.items.move(element.active_item_index, element.active_item_index - 1)
        element.active_item_index -= 1

        return {"FINISHED"}


class MODRENAMER_OT_MoveTextItemDown(bpy.types.Operator):
    """Move the selected text item down in the list"""

    bl_idname = "modrenamer.move_text_item_down"
    bl_label = "Move Item Down"

    element_index: IntProperty(name="Element Index", default=0)

    def execute(self, context):
        pr = prefs()
        active_idx = pr.active_pattern_index

        if active_idx >= len(pr.patterns):
            return {"CANCELLED"}

        pattern = pr.patterns[active_idx]

        if self.element_index >= len(pattern.elements):
            return {"CANCELLED"}

        element = pattern.elements[self.element_index]

        if (
            element.active_item_index < 0
            or element.active_item_index >= len(element.items) - 1
        ):
            return {"CANCELLED"}

        # Move the item down
        element.items.move(element.active_item_index, element.active_item_index + 1)
        element.active_item_index += 1

        return {"FINISHED"}


class MODRENAMER_OT_CreateDefaultPatterns(bpy.types.Operator):
    """Create default naming patterns"""

    bl_idname = "modrenamer.create_default_patterns"
    bl_label = "Create Default Patterns"

    def execute(self, context):
        pr = prefs()
        pr.create_default_patterns()
        self.report({"INFO"}, "Default patterns created")
        return {"FINISHED"}
