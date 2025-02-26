import bpy
from bpy.props import (
    StringProperty, BoolProperty, IntProperty, 
    EnumProperty, CollectionProperty, PointerProperty
)
import json

# Constants for default separator options
SEPARATOR_ITEMS = [
    ('_', "Underscore", "_"),
    ('.', "Dot", "."),
    ('-', "Dash", "-"),
    (' ', "Space", " "),
]

# Constants for element types
ELEMENT_TYPE_ITEMS = [
    ('text', "Text", "Normal text with predefined options"),
    ('free_text', "Free Text", "Any text input"),
    ('position', "Position", "Positional indicators (L/R, Top/Bot, etc)"),
    ('counter', "Counter", "Numerical counter with formatting options"),
    ('date', "Date", "Date in various formats"),
    ('regex', "RegEx", "Custom regular expression pattern")
]


class NamingElementItem(bpy.types.PropertyGroup):
    """Single item within a naming element's options"""
    name: StringProperty(
        name="Name",
        description="Name of this item",
        default=""
    )


class NamingElement(bpy.types.PropertyGroup):
    """Definition of a naming element"""
    id: StringProperty(
        name="ID",
        description="Unique identifier for this element",
        default=""
    )
    
    display_name: StringProperty(
        name="Display Name",
        description="User-friendly name for this element",
        default=""
    )
    
    element_type: EnumProperty(
        name="Type",
        description="Type of this naming element",
        items=ELEMENT_TYPE_ITEMS,
        default='text'
    )
    
    enabled: BoolProperty(
        name="Enabled",
        description="Whether this element is active",
        default=True
    )
    
    order: IntProperty(
        name="Order",
        description="Position in the naming sequence",
        default=0,
        min=0
    )
    
    separator: EnumProperty(
        name="Separator",
        description="Character used to separate this element from the next",
        items=SEPARATOR_ITEMS,
        default='_'
    )
    
    # For text elements - predefined options
    items: CollectionProperty(
        type=NamingElementItem,
        name="Items",
        description="Predefined text options for this element"
    )
    
    # For counter elements
    padding: IntProperty(
        name="Padding",
        description="Number of digits for counter (zero-padded)",
        default=2,
        min=1,
        max=10
    )
    
    # For regex elements
    pattern: StringProperty(
        name="Pattern",
        description="Regular expression pattern for matching",
        default="(.*)"
    )
    
    # For date elements
    date_format: StringProperty(
        name="Format",
        description="Date format string (strftime)",
        default="%Y%m%d"
    )
    
    # For free text
    default_text: StringProperty(
        name="Default Text",
        description="Default text to use",
        default=""
    )


class NamingPattern(bpy.types.PropertyGroup):
    """A complete naming pattern for a specific object type"""
    id: StringProperty(
        name="ID",
        description="Unique identifier for this pattern",
        default=""
    )
    
    name: StringProperty(
        name="Name",
        description="User-friendly name for this pattern",
        default=""
    )
    
    object_type: StringProperty(
        name="Object Type",
        description="Type of object this pattern applies to",
        default=""
    )
    
    elements: CollectionProperty(
        type=NamingElement,
        name="Elements",
        description="Elements that make up this naming pattern"
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
            self.elements.remove(index)
            # Reorder remaining elements
            for i, elem in enumerate(self.elements):
                elem.order = i


class ModularRenamerPreferences(bpy.types.AddonPreferences):
    """Addon preferences for ModularRenamer"""
    bl_idname = "modular-renamer"
    
    # Collection of all naming patterns
    patterns: CollectionProperty(
        type=NamingPattern,
        name="Naming Patterns",
        description="All available naming patterns"
    )
    
    # Currently selected pattern
    active_pattern_index: IntProperty(
        name="Active Pattern",
        default=0
    )
    
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
                "elements": []
            }
            
            for element in pattern.elements:
                element_data = {
                    "id": element.id,
                    "display_name": element.display_name,
                    "type": element.element_type,
                    "enabled": element.enabled,
                    "order": element.order,
                    "separator": element.separator,
                }
                
                # Add type-specific properties
                if element.element_type == 'text':
                    element_data["items"] = [item.name for item in element.items]
                elif element.element_type == 'counter':
                    element_data["padding"] = element.padding
                elif element.element_type == 'regex':
                    element_data["pattern"] = element.pattern
                elif element.element_type == 'date':
                    element_data["date_format"] = element.date_format
                elif element.element_type == 'free_text':
                    element_data["default_text"] = element.default_text
                
                pattern_data["elements"].append(element_data)
            
            data.append(pattern_data)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        
        return True
    
    # Import patterns from JSON
    def import_patterns(self, filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Clear existing patterns
            self.patterns.clear()
            
            for pattern_data in data:
                pattern = self.add_pattern(
                    pattern_data["id"],
                    pattern_data["name"],
                    pattern_data["object_type"]
                )
                
                for element_data in pattern_data["elements"]:
                    element = pattern.add_element(
                        element_data["id"],
                        element_data["type"],
                        element_data["display_name"]
                    )
                    
                    element.enabled = element_data.get("enabled", True)
                    element.order = element_data.get("order", 0)
                    element.separator = element_data.get("separator", "_")
                    
                    # Set type-specific properties
                    if element.element_type == 'text' and "items" in element_data:
                        for item_name in element_data["items"]:
                            item = element.items.add()
                            item.name = item_name
                    
                    if element.element_type == 'counter' and "padding" in element_data:
                        element.padding = element_data["padding"]
                    
                    if element.element_type == 'regex' and "pattern" in element_data:
                        element.pattern = element_data["pattern"]
                    
                    if element.element_type == 'date' and "date_format" in element_data:
                        element.date_format = element_data["date_format"]
                    
                    if element.element_type == 'free_text' and "default_text" in element_data:
                        element.default_text = element_data["default_text"]
            
            return True
        
        except Exception as e:
            print(f"Error importing patterns: {e}")
            return False
    
    def create_default_patterns(self):
        # Clear existing patterns
        self.patterns.clear()
        
        # Create a default pattern for pose bones
        bone_pattern = self.add_pattern("pose_bone_default", "Default Bone Pattern", "POSE_BONE")
        
        # Add prefix element
        prefix = bone_pattern.add_element("prefix", "text", "Prefix")
        for name in ["CTRL", "DEF", "MCH", "ORG", "DRV", "TRG", "PROP"]:
            item = prefix.items.add()
            item.name = name
        
        # Add middle element
        middle = bone_pattern.add_element("middle", "text", "Middle")
        for name in ["Bone", "Root", "Spine", "Chest", "Torso", "Hips", "Tail", "Neck", 
                    "Head", "Shoulder", "Arm", "Elbow", "ForeArm", "Hand", "InHand", 
                    "Finger", "UpLeg", "Leg", "Shin", "Foot", "Knee", "Toe"]:
            item = middle.items.add()
            item.name = name
        
        # Add finger element
        finger = bone_pattern.add_element("finger", "text", "Finger")
        for name in ["Finger", "Thumb", "Index", "Middle", "Ring", "Pinky"]:
            item = finger.items.add()
            item.name = name
        
        # Add suffix element
        suffix = bone_pattern.add_element("suffix", "text", "Suffix")
        for name in ["Base", "Tweak", "Pole", "IK", "FK", "Roll", "Rot", "Loc", "Scale", "INT"]:
            item = suffix.items.add()
            item.name = name
        
        # Add counter element
        counter = bone_pattern.add_element("counter", "counter", "Counter")
        counter.padding = 2
        counter.separator = "-"
        
        # Add position element
        position = bone_pattern.add_element("position", "position", "Position")
        position.separator = "."
        for name in ["L", "R", "Top", "Bot", "Fr", "Bk"]:
            item = position.items.add()
            item.name = name
        
        return True


# Registration
classes = [
    NamingElementItem,
    NamingElement,
    NamingPattern,
    ModularRenamerPreferences
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


# Utility function to get preferences
def get_preferences():
    return bpy.context.preferences.addons["modular-renamer"].preferences
