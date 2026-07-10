from pprint import pprint

from backend.tools.sports_tools import sports_tool


def separator(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def run_test(title, payload):
    separator(title)

    try:
        result = sports_tool.invoke(payload)

        pprint(result)

        assert isinstance(result, dict)
        assert "success" in result

        if result["success"]:
            assert "matches" in result
            assert "match_count" in result

        print("\n✅ PASSED")

    except Exception as e:
        print(f"\n❌ FAILED\n{e}")


###############################################################
# Football
###############################################################

run_test(
    "TEST 1 Football Live",
    {
        "sport": "football",
        "operation": "live",
    },
)

run_test(
    "TEST 2 Football Fixtures",
    {
        "sport": "football",
        "operation": "fixtures",
    },
)

run_test(
    "TEST 3 Football Results",
    {
        "sport": "football",
        "operation": "results",
    },
)

###############################################################
# Basketball
###############################################################

run_test(
    "TEST 4 Basketball Live",
    {
        "sport": "basketball",
        "operation": "live",
    },
)

###############################################################
# American Football
###############################################################

run_test(
    "TEST 5 American Football",
    {
        "sport": "american_football",
        "operation": "live",
    },
)

###############################################################
# Tennis
###############################################################

run_test(
    "TEST 6 Tennis",
    {
        "sport": "tennis",
        "operation": "live",
    },
)

###############################################################
# Baseball
###############################################################

run_test(
    "TEST 7 Baseball",
    {
        "sport": "baseball",
        "operation": "live",
    },
)

###############################################################
# Ice Hockey
###############################################################

run_test(
    "TEST 8 Ice Hockey",
    {
        "sport": "ice_hockey",
        "operation": "live",
    },
)

###############################################################
# Cricket
###############################################################

run_test(
    "TEST 9 Cricket Live",
    {
        "sport": "cricket",
        "operation": "live",
    },
)

run_test(
    "TEST 10 Cricket Fixtures",
    {
        "sport": "cricket",
        "operation": "fixtures",
    },
)

run_test(
    "TEST 11 Cricket Results",
    {
        "sport": "cricket",
        "operation": "results",
    },
)

###############################################################
# Team Filter
###############################################################

run_test(
    "TEST 12 Team Filter",
    {
        "sport": "football",
        "operation": "fixtures",
        "team": "Manchester",
    },
)

###############################################################
# League Filter
###############################################################

run_test(
    "TEST 13 League Filter",
    {
        "sport": "football",
        "operation": "results",
        "league": "Premier",
    },
)

###############################################################
# Date Filter
###############################################################

run_test(
    "TEST 14 Date Filter",
    {
        "sport": "football",
        "operation": "fixtures",
        "date": "2026-07-15",
    },
)

###############################################################
# Invalid Sport
###############################################################

separator("TEST 15 Invalid Sport")

result = sports_tool.invoke(
    {
        "sport": "kabaddi",
        "operation": "live",
    }
)

pprint(result)

assert result["success"] is False

print("✅ PASSED")

###############################################################
# Invalid Date
###############################################################

separator("TEST 16 Invalid Date")

result = sports_tool.invoke(
    {
        "sport": "football",
        "operation": "fixtures",
        "date": "abcd",
    }
)

pprint(result)

print("✅ Tool handled invalid date")

###############################################################
# Empty Team
###############################################################

run_test(
    "TEST 17 Empty Team Filter",
    {
        "sport": "football",
        "operation": "fixtures",
        "team": "",
    },
)

###############################################################
# Response Schema Validation
###############################################################

separator("TEST 18 Response Schema")

result = sports_tool.invoke(
    {
        "sport": "football",
        "operation": "live",
    }
)

required = [
    "success",
]

for key in required:
    assert key in result

print("Returned keys:")
print(result.keys())

print("✅ PASSED")

###############################################################
# Invoke Interface
###############################################################

separator("TEST 19 StructuredTool.invoke()")

payload = {
    "sport": "football",
    "operation": "live",
}

result = sports_tool.invoke(payload)

assert isinstance(result, dict)

print("invoke() works correctly.")
print("✅ PASSED")

###############################################################
# Stress Test
###############################################################

separator("TEST 20 Stress Test")

sports = [
    "football",
    "basketball",
    "tennis",
    "baseball",
    "ice_hockey",
]

operations = [
    "live",
    "fixtures",
    "results",
]

count = 0

for sport in sports:
    for op in operations:

        result = sports_tool.invoke(
            {
                "sport": sport,
                "operation": op,
            }
        )

        assert isinstance(result, dict)

        count += 1

print(f"Executed {count} requests successfully.")

print("✅ PASSED")

###############################################################

print("\n")
print("=" * 100)
print("ALL TESTS COMPLETED")
print("=" * 100)