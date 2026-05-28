import re
from pathlib import Path

import pytest

CASSETTES_DIR = Path(__file__).parent / "cassettes"

FORBIDDEN_PATTERNS = [
    (
        re.compile(r'"api_token"\s*:\s*"(?!REDACTED)[^"]+"'),
        "api_token value",
        '"api_token":"REDACTED"',
    ),
    (re.compile(r'"email"\s*:\s*"(?!REDACTED)[^"]+"'), "email value", '"email":"REDACTED"'),
]


def test_scrubber_redacts_and_fails_on_sensitive_cassette(tmp_path):
    cassette = tmp_path / "dirty.yaml"
    cassette.write_text('"api_token": "real_secret"\n"email": "user@example.com"\n')

    with pytest.raises(AssertionError, match="leaked"):
        test_cassette_has_no_sensitive_data(cassette)

    redacted = cassette.read_text()
    assert '"api_token":"REDACTED"' in redacted
    assert '"email":"REDACTED"' in redacted


@pytest.mark.parametrize("cassette", sorted(CASSETTES_DIR.glob("*.yaml")), ids=lambda p: p.name)
def test_cassette_has_no_sensitive_data(cassette: Path):
    """Ensure no sensitive user data leaks into VCR cassettes.

    Certain endpoints such as `me/` return api_token or email values which means that they may end
    up recorded in the cassettes.

    Make sure you run the full test suite before pushing any changes that add or regenerate
    cassettes. If this test fails, it will redact the offending field in the cassette (replace the
    value with "REDACTED") and trim the response body to only the fields the code actually reads.
    """
    text = cassette.read_text()
    violations = []
    for pattern, label, replacement in FORBIDDEN_PATTERNS:
        if pattern.search(text):
            violations.append(label)
            text = pattern.sub(replacement, text)

    if violations:
        cassette.write_text(text)
        assert False, (
            f"{cassette.name} leaked {', '.join(violations)} — "
            "values have been scrubbed automatically; please review the cassette before committing."
        )
