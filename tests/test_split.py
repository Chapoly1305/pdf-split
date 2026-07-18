"""Tests for pdf_split.build_plan (no real PDF needed — it operates on a TOC).

Regression focus: the last section of a chapter must stop at the next chapter,
never run to the end of the document.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdf_split import build_plan  # noqa: E402

# (level, title, page) — Ch.1 has a trailing section (1.2) followed by Ch.2,
# and 2.2 is the last section in the whole document.
TOC = [
    (1, "Front Matter", 1),
    (1, "Chapter 1. General", 3),
    (2, "1.1. Alpha", 3),
    (2, "1.2. Beta", 10),          # last section of chapter 1
    (1, "Chapter 2. Stuff", 20),
    (2, "2.1. Gamma", 20),
    (2, "2.2. Delta", 25),         # last section of the document
    (3, "2.2.1. deeper", 26),      # folded into 2.2
]
N_PAGES = 30


def _byname(plan):
    return {name: (parts, start, end) for parts, name, start, end in plan}


def test_last_section_stops_at_next_chapter():
    """The regression: 1.2 (last in Ch.1) must end at Ch.2's start, not at N_PAGES."""
    files = _byname(build_plan(TOC, N_PAGES, depth=2, overlap=True))
    _, start, end = files["1.2. Beta"]
    assert start == 10
    assert end == 20, f"1.2 should end at chapter 2's start (20), got {end}"
    assert end != N_PAGES


def test_no_file_extends_past_the_next_file():
    """General invariant: every file ends at or before the next file's start page."""
    plan = build_plan(TOC, N_PAGES, depth=2, overlap=True)
    for (_, _, _, end), (_, _, nxt_start, _) in zip(plan, plan[1:]):
        assert end <= nxt_start


def test_overlap_shares_exactly_the_boundary_page():
    files = _byname(build_plan(TOC, N_PAGES, depth=2, overlap=True))
    # overlap: a section ends on the next section's start page
    assert files["1.1. Alpha"][2] == files["1.2. Beta"][1] == 10
    assert files["2.1. Gamma"][2] == files["2.2. Delta"][1] == 25


def test_no_overlap_is_an_exact_partition():
    plan = build_plan(TOC, N_PAGES, depth=2, overlap=False)
    files = _byname(plan)
    assert files["1.2. Beta"][2] == 19          # 20 - 1, no shared page
    # pages are covered without overlap
    for (_, _, _, end), (_, _, nxt_start, _) in zip(plan, plan[1:]):
        assert end < nxt_start


def test_last_section_reaches_end_of_document():
    files = _byname(build_plan(TOC, N_PAGES, depth=2, overlap=True))
    assert files["2.2. Delta"][2] == N_PAGES


def test_first_file_absorbs_cover_pages():
    plan = build_plan(TOC, N_PAGES, depth=2, overlap=True)
    assert plan[0][2] == 1  # start page of the very first file is 1


def test_structure_folders_and_folded_deeper_bookmarks():
    files = _byname(build_plan(TOC, N_PAGES, depth=2, overlap=True))
    assert files["1.1. Alpha"][0] == ["Chapter 1. General"]
    assert files["2.1. Gamma"][0] == ["Chapter 2. Stuff"]
    assert files["Front Matter"][0] == []          # subsection-less top level -> root
    assert "2.2.1. deeper" not in files            # level-3 folded into 2.2


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
