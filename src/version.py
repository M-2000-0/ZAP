"""
Zap language version.

GRAMMAR_VERSION is a string that AI models and tooling can match against.
Breaking changes to the grammar require a major version bump and a note in
CHANGELOG.md. Additive changes (new keywords, new builtin) require a minor
bump and a note in CHANGELOG.md. Bug fixes are patch bumps.

The version is also exposed as `zap version` on the CLI and via the
`--grammar=0.2` flag for tools that need to verify they are targeting the
same grammar the file was written for.
"""

# Bump in lockstep with pyproject.toml. Format: MAJOR.MINOR.PATCH.
VERSION = "0.2.0"

# The grammar version this interpreter understands. If a .zap file declares
# a different grammar version, the parser emits a Z001 diagnostic.
GRAMMAR_VERSION = "0.2"

# Keywords that exist in the 0.2 grammar. Anything not in this set will not
# be tokenized as a keyword. The set is small on purpose: an AI should be able
# to hold the entire grammar in its context window.
GRAMMAR_0_2_KEYWORDS = frozenset({
    "fn", "let", "if", "el", "for", "in", "while", "ret",
    "true", "false", "none", "and", "or", "not",
    "import", "from", "class", "async", "await", "match", "intend",
    "service", "database", "api", "page", "schema", "model", "expose",
    "requires", "ensures", "invariant", "expect", "permission",
    "concurrent", "channel", "guarantees", "version", "check",
})


def is_keyword(name: str) -> bool:
    """True if `name` is reserved in the current grammar."""
    return name in GRAMMAR_0_2_KEYWORDS


def parse_grammar_pragma(source: str) -> str | None:
    """
    Look for a top-of-file pragma `# grammar: 0.2` and return the version
    string, or None if absent. Stops scanning at the first non-comment,
    non-blank line. This is how .zap files declare which grammar they target.
    """
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            break
        # Strip leading "#" and any spaces.
        body = stripped.lstrip("#").strip()
        # Accept "grammar: 0.2", "grammar = 0.2", with optional whitespace
        # between "grammar" and the separator.
        for sep in (":", "="):
            for prefix in (f"grammar{sep}", f"grammar {sep}"):
                if body.startswith(prefix):
                    rest = body[len(prefix):].strip()
                    if rest:
                        return rest.split()[0]
        # Bare "grammar 0.2" with whitespace separator. The next token must
        # not be a separator (those are handled by the loop above).
        if body.startswith("grammar "):
            rest = body[len("grammar"):].strip()
            if rest and rest[0] not in (":", "="):
                return rest.split()[0]
    return None
