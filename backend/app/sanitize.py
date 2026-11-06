"""Sanitising public form input before it is stored or shown.

The site renders every string through Jinja autoescape or the admin panel's
``esc()``, so HTML is already neutralised at the point it reaches a page. This
module is the second layer: it strips markup and control characters at the
boundary, normalises whitespace, and enforces the column limits. Storing plain
text means a message copied out of the database, a log, or an export is safe too
— the guarantee does not depend on every future renderer remembering to escape.

The functions are intentionally conservative rather than clever. No HTML parser
is involved and no entities are decoded: a literal ``&lt;script&gt;`` is harmless
once escaped, while decoding it would turn it back into a tag for the stripper
to worry about.
"""

import re

# C0 controls except tab (09) and newline (0A), plus DEL. Carriage returns are
# normalised to newlines before this runs, so a stray CR never reaches a column.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Anything that looks like a tag. This is not an HTML parser; it is a cheap
# second line of defence behind output escaping, and it also keeps angle
# brackets out of the admin inbox where a browser might re-interpret them.
_TAGS = re.compile(r"<[^>]*>")

# Runs of spaces/tabs inside a message become one space. Newlines are kept.
_INLINE_SPACE = re.compile(r"[ \t\f\v]+")
# More than one blank line is noise in a short contact message.
_BLANK_LINES = re.compile(r"\n{3,}")
# A single-line field cannot contain a line break at all.
_ANY_SPACE = re.compile(r"\s+")


def clean_text(value: str | None, *, max_length: int, multiline: bool = False) -> str:
    """Return ``value`` as plain text, bounded to ``max_length`` characters.

    ``multiline`` keeps paragraph breaks for the message body; without it every
    run of whitespace (including newlines) collapses to one space, which is what
    a name, contact detail or subject line wants.
    """
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = _TAGS.sub("", text)

    if multiline:
        text = _INLINE_SPACE.sub(" ", text)
        text = _BLANK_LINES.sub("\n\n", text)
        text = "\n".join(line.strip() for line in text.split("\n")).strip()
    else:
        text = _ANY_SPACE.sub(" ", text).strip()

    return text[:max_length].rstrip()
