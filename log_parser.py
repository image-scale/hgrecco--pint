import re


def parse_log(log: str) -> dict[str, str]:
    """Parse test runner output into per-test results.

    Args:
        log: Full stdout+stderr output of `bash run_test.sh 2>&1`.

    Returns:
        Dict mapping test_id to status.
        - test_id: pytest native format (e.g. "pint/testsuite/foo.py::TestClass::test_func[param]")
        - status: one of "PASSED", "FAILED", "SKIPPED", "ERROR"
    """
    results = {}

    # Strip ANSI escape codes
    log = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', log)

    # Match pytest verbose output lines ending with [ XX%]:
    # test_id STATUS (optional reason) [ XX%]
    # test_id can contain spaces inside bracket params like test_foo[param with spaces]
    pattern = re.compile(
        r'^(pint/testsuite/.*?)\s+(PASSED|FAILED|SKIPPED|XFAIL|ERROR)'
        r'(?:[ \t][^\n]*)?\[\s*\d+%\]',
        re.MULTILINE,
    )

    for m in pattern.finditer(log):
        test_id = m.group(1).strip()
        status = m.group(2)
        # Map XFAIL to SKIPPED (expected failures are not run normally)
        if status == 'XFAIL':
            status = 'SKIPPED'
        results.setdefault(test_id, status)

    # Handle collection errors: "ERROR pint/testsuite/foo.py - ImportError: ..."
    error_pattern = re.compile(r'^ERROR (pint/testsuite/\S+\.py)', re.MULTILINE)
    for m in error_pattern.finditer(log):
        results.setdefault(m.group(1), 'ERROR')

    return results

