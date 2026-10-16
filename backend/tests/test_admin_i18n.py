"""Tests for the bilingual admin panel strings.

Two tables that drift apart is a bug that shows up as raw English on the Spanish
panel — or, worse, as `lookup()` handing the page a key name it then renders as
literal text. Both directions are cheap to check, so both are checked.
"""

import re
import pathlib

import pytest

from app.admin_i18n import DEFAULT_LANG, STRINGS, SUPPORTED, strings_for

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / "app" / "templates"


@pytest.mark.parametrize("lang", SUPPORTED)
def test_every_language_has_every_key(lang):
    reference = set(STRINGS[DEFAULT_LANG])
    assert set(STRINGS[lang]) == reference, f"{lang} is missing or has extra keys"


@pytest.mark.parametrize("lang", SUPPORTED)
def test_every_placeholder_is_the_same_in_every_language(lang):
    """A placeholder that exists in one table and not another renders raw."""
    for key, value in STRINGS[DEFAULT_LANG].items():
        expected = set(re.findall(r"\{(\w+)\}", value))
        assert set(re.findall(r"\{(\w+)\}", STRINGS[lang][key])) == expected, key


@pytest.mark.parametrize("lang", SUPPORTED)
def test_strings_cover_every_language(lang):
    """Merging the language over English must never drop a key, and must never
    let the English copy win where the language has its own wording."""
    table = strings_for(lang)
    reference = STRINGS[DEFAULT_LANG]
    assert set(table) == set(reference)
    for key, fallback in reference.items():
        assert table[key] == STRINGS[lang].get(key, fallback), key


def test_unknown_language_gets_the_default_table():
    assert strings_for("zz") == STRINGS[DEFAULT_LANG]


def test_templates_only_reference_keys_that_exist():
    """`lookup()` returns the key itself when it is missing, so a typo renders
    as `menu_heading` on the page instead of failing loudly."""
    unknown = set()
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        keys = set(re.findall(r'data-i18n(?:-args)?="([a-z_]+)"', text))
        keys |= set(re.findall(r"AdminI18n\.t\('([a-z_]+)'\)", text))
        unknown |= {key for key in keys if key not in STRINGS[DEFAULT_LANG]}
    assert unknown == set()


def test_the_menu_page_covers_the_menu_and_schedule_strings():
    """The menu page needs its own labels in both languages, not just English."""
    menu_page = (TEMPLATES / "admin" / "menu.html").read_text(encoding="utf-8")
    for key in ("menu_heading", "menu_intro", "add_category", "item_price",
                "item_ingredients_en", "add_promo", "delete_category"):
        assert key in menu_page, key
        for lang in SUPPORTED:
            assert key in STRINGS[lang], f"{key} missing from {lang}"


@pytest.mark.parametrize("page", ["admin/menu.html", "admin/schedule.html"])
def test_admin_pages_escape_quotes(page):
    """`esc()` output goes into `value="..."` as well as into the page.

    The obvious implementation — set `textContent`, read `innerHTML` — escapes
    `<` and `&` but leaves `"` intact, so an admin-entered name containing a
    quote breaks out of the attribute. Both pages build their forms this way.
    """
    text = (TEMPLATES / page).read_text(encoding="utf-8")

    table = re.search(r"var HTML_ESCAPES = \{(.*?)\};", text, re.DOTALL)
    assert table, f"{page} has no escape table for esc()"
    entities = set(re.findall(r"'(&[a-z]+;|&#\d+;)'", table.group(1)))
    assert entities == {"&amp;", "&lt;", "&gt;", "&quot;", "&#39;"}, (
        f"{page} esc() does not cover all five HTML metacharacters"
    )
    assert re.search(r"\.replace\(/\[&<>\"'\]/g", text), (
        f"{page} esc() does not run every character through the table"
    )
    assert "div.textContent" not in text, (
        f"{page} esc() is textContent-based, which leaves quotes unescaped in attributes"
    )
