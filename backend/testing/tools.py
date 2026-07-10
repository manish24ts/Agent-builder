from pprint import pprint

from backend.tools.tools import (
    TOOL_REGISTRY,
    list_available_tools,
    get_tools_by_names,
    get_all_tools,
)

print("=" * 80)
print("TEST 1 : List every registered tool")
print("=" * 80)

tools = list_available_tools()

print(f"\nRegistered tools : {len(tools)}\n")

for tool in tools:
    pprint(tool)

print()


###########################################################################

print("=" * 80)
print("TEST 2 : List only custom tools")
print("=" * 80)

custom = list_available_tools(category="custom")

for tool in custom:
    pprint(tool)

print()


###########################################################################

print("=" * 80)
print("TEST 3 : List only builtin tools")
print("=" * 80)

builtin = list_available_tools(category="builtin")

for tool in builtin:
    pprint(tool)

print()


###########################################################################

print("=" * 80)
print("TEST 4 : Load one tool")
print("=" * 80)

loaded = get_tools_by_names(["math_tool"])

print(loaded)

assert len(loaded) == 1
print("PASS\n")


###########################################################################

print("=" * 80)
print("TEST 5 : Load multiple tools")
print("=" * 80)

loaded = get_tools_by_names([
    "math_tool",
    "github_tool",
    "stock_tool",
    "chart_tool"
])

print(f"Loaded {len(loaded)} tools")

for t in loaded:
    print(t.name)

print()


###########################################################################

print("=" * 80)
print("TEST 6 : Invalid tool names")
print("=" * 80)

loaded = get_tools_by_names([
    "math_tool",
    "not_real",
    "another_fake",
])

print("Loaded")

for t in loaded:
    print(t.name)

print("Should only load math_tool\n")


###########################################################################

print("=" * 80)
print("TEST 7 : Load ALL tools")
print("=" * 80)

all_tools = get_all_tools()

print(f"Loaded {len(all_tools)} tools")

for t in all_tools:
    print("-", t.name)

print()


###########################################################################

print("=" * 80)
print("TEST 8 : Load ALL custom tools")
print("=" * 80)

all_custom = get_all_tools(category="custom")

print(f"Loaded {len(all_custom)} custom tools")

for t in all_custom:
    print("-", t.name)

print()


###########################################################################

print("=" * 80)
print("TEST 9 : Lazy loading")
print("=" * 80)

entry = TOOL_REGISTRY["math_tool"]

print("Before loading")

print(entry._instance)

tool = entry.get()

print("After loading")

print(entry._instance)

assert entry._instance is not None

print("PASS\n")


###########################################################################

print("=" * 80)
print("TEST 10 : Cached instance")
print("=" * 80)

entry = TOOL_REGISTRY["math_tool"]

tool1 = entry.get()

tool2 = entry.get()

print(id(tool1))
print(id(tool2))

assert tool1 is tool2

print("PASS\n")


###########################################################################

print("=" * 80)
print("TEST 11 : Registry metadata")
print("=" * 80)

for name, entry in TOOL_REGISTRY.items():

    print()

    print("Name:", entry.name)

    print("Category:", entry.category)

    print("Description:", entry.description)

    print("Requires Key:", entry.requires_key)

    print("Available:", entry.available)

print()


###########################################################################

print("=" * 80)
print("TEST 12 : Invoke math tool")
print("=" * 80)

math = get_tools_by_names(["math_tool"])[0]

try:

    result = math.invoke({"expression": "25*4+10"})

    print(result)

except Exception as e:

    print("Invocation failed")

    print(e)

print()


###########################################################################

print("=" * 80)
print("TEST 13 : Availability check")
print("=" * 80)

for name, entry in TOOL_REGISTRY.items():

    print(name, "->", entry.available)

print()


###########################################################################

print("=" * 80)
print("TEST 14 : Duplicate names")
print("=" * 80)

tools = get_tools_by_names([
    "math_tool",
    "math_tool",
    "math_tool"
])

print(len(tools))

for t in tools:
    print(id(t))

print("Same object should appear three times.\n")


###########################################################################

print("=" * 80)
print("TEST 15 : Unknown category")
print("=" * 80)

unknown = list_available_tools(category="xyz")

print(unknown)

assert unknown == []

print("PASS")


###########################################################################

print("=" * 80)
print("ALL TESTS COMPLETED")
print("=" * 80)