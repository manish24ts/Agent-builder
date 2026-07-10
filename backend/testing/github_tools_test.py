from backend.tools.github_tools import github_tool


TEST_REPO = "https://github.com/fastapi/fastapi"


def run_test(title: str, payload: dict):
    print("\n" + "=" * 100)
    print(f"TEST: {title}")
    print("=" * 100)

    try:
        result = github_tool.invoke(payload)

        if isinstance(result, dict):
            print(f"Success: {result.get('success')}")

            if result.get("success"):
                print(f"Operation: {result.get('operation')}")
                print("\nData:")
                print(result.get("data"))
            else:
                print("\nError:")
                print(result.get("error"))

        else:
            print(result)

    except Exception as e:
        print(f"Exception: {e}")


def main():

    # ==========================================================================
    # Repository Summary
    # ==========================================================================

    run_test(
        "Repository Summary",
        {
            "operation": "repository_summary",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Analyze Repository
    # ==========================================================================

    run_test(
        "Analyze Repository",
        {
            "operation": "analyze_repo",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Architecture
    # ==========================================================================

    run_test(
        "Architecture",
        {
            "operation": "architecture",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Dependencies
    # ==========================================================================

    run_test(
        "Dependencies",
        {
            "operation": "dependencies",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Statistics
    # ==========================================================================

    run_test(
        "Statistics",
        {
            "operation": "statistics",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # API Routes
    # ==========================================================================

    run_test(
        "API Routes",
        {
            "operation": "api_routes",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Installation
    # ==========================================================================

    run_test(
        "Installation Guide",
        {
            "operation": "installation",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Security Scan
    # ==========================================================================

    run_test(
        "Security Scan",
        {
            "operation": "security_scan",
            "repository_url": TEST_REPO,
        },
    )

    # ==========================================================================
    # Search Code
    # ==========================================================================

    run_test(
        "Search 'fastapi'",
        {
            "operation": "search_code",
            "repository_url": TEST_REPO,
            "query": "fastapi",
        },
    )

    run_test(
        "Search 'middleware'",
        {
            "operation": "search_code",
            "repository_url": TEST_REPO,
            "query": "middleware",
        },
    )

    run_test(
        "Search 'dependency'",
        {
            "operation": "search_code",
            "repository_url": TEST_REPO,
            "query": "dependency",
        },
    )

    # ==========================================================================
    # Explain File
    # ==========================================================================

    run_test(
        "Explain README",
        {
            "operation": "explain_file",
            "repository_url": TEST_REPO,
            "file_path": "README.md",
        },
    )

    run_test(
        "Explain pyproject.toml",
        {
            "operation": "explain_file",
            "repository_url": TEST_REPO,
            "file_path": "pyproject.toml",
        },
    )

    # ==========================================================================
    # Validation Tests
    # ==========================================================================

    run_test(
        "Missing Repository URL",
        {
            "operation": "statistics",
        },
    )

    run_test(
        "Invalid GitHub URL",
        {
            "operation": "statistics",
            "repository_url": "https://google.com",
        },
    )

    run_test(
        "Missing Query",
        {
            "operation": "search_code",
            "repository_url": TEST_REPO,
        },
    )

    run_test(
        "Missing File Path",
        {
            "operation": "explain_file",
            "repository_url": TEST_REPO,
        },
    )

    run_test(
        "Invalid File",
        {
            "operation": "explain_file",
            "repository_url": TEST_REPO,
            "file_path": "this_file_does_not_exist.py",
        },
    )

    run_test(
        "Repository Does Not Exist",
        {
            "operation": "statistics",
            "repository_url": "https://github.com/openai/this_repo_does_not_exist",
        },
    )


if __name__ == "__main__":
    main()