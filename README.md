# pdf-split

Split a PDF into per-section files using its **bookmark outline** (table of contents).

Bookmarks above the split level become folders; bookmarks at the split level become
individual PDFs named after the section title. Deeper bookmarks are folded into the
section that contains them.

```
input.pdf                     output_dir/
├─ 1 Introduction             ├─ 1 Introduction/
│  ├─ 1.1 Scope         ──►    │  ├─ 1.1 Scope.pdf
│  └─ 1.2 Purpose              │  └─ 1.2 Purpose.pdf
└─ 2 References                └─ 2 References.pdf
```

## Install

```bash
pip install pymupdf
```

## Usage

```bash
python pdf_split.py input.pdf output_dir/
```

Options:

| Option         | Default | Description                                                              |
| -------------- | ------- | ------------------------------------------------------------------------ |
| `--depth N`    | `2`     | Outline level that becomes files; shallower levels become folders.       |
| `--no-overlap` | off     | Exact page partition — no page appears in two files.                     |
| `--dry-run`    | off     | Print the plan without writing anything.                                 |

Examples:

```bash
# one folder per chapter, one PDF per section (default)
python pdf_split.py spec.pdf out/

# one PDF per top-level chapter, no folders
python pdf_split.py spec.pdf out/ --depth 1

# preview first
python pdf_split.py spec.pdf out/ --dry-run
```

## How page ranges are chosen

Each section runs from its start page to the **start page of the next section**.

By default the shared boundary page is kept on the *earlier* section (overlap), so
content that flows across a page break is never clipped — e.g. a section whose text
continues onto the page where the next section begins keeps that page. Use
`--no-overlap` for an exact partition where every page appears in exactly one file
(at the cost of possibly clipping cross-page content). Sections that share a single
page each get their own file containing that page.

Pages before the first bookmark (cover, legal, table of contents) are included in the
first file.

## Tests

```bash
python tests/test_split.py     # or: pytest
```

Covers the page-range logic, including the regression that a chapter's last
section stops at the next chapter instead of running to the end of the document.

## Requirements

- Python 3.7+
- [PyMuPDF](https://pymupdf.readthedocs.io/) (`pip install pymupdf`)

The PDF must contain a bookmark outline; the tool exits with an error if it has none.

## License

MIT
