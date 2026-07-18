#!/usr/bin/env python3
"""pdf-split — split a PDF into per-section files using its bookmark outline.

Reads the PDF's table of contents (bookmarks) and writes one PDF per section.
Bookmarks above the split level become folders; bookmarks at the split level
become files named after the section title.

Usage:
    python pdf_split.py input.pdf output_dir/
    python pdf_split.py input.pdf output_dir/ --depth 1
    python pdf_split.py input.pdf output_dir/ --dry-run
"""
import argparse
import os
import re
import shutil
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("error: PyMuPDF is required. Install it with:  pip install pymupdf")


def sanitize(name: str) -> str:
    """Make a bookmark title safe to use as a file/folder name."""
    name = name.replace("/", "-").replace("\\", "-").replace(":", " -")
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "", name)  # drop chars illegal on common filesystems
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    return name[:150] or "untitled"


def build_plan(toc, n_pages, depth, overlap):
    """Turn a table of contents into a list of (folder_parts, filename, start, end).

    - Bookmarks at level < depth that contain deeper bookmarks become folders.
    - Bookmarks at the split level (or shallower leaves) become files.
    - Deeper bookmarks are folded into the file that contains their pages.

    Each file spans [start, next file's start]. With --overlap (default) the shared
    boundary page is kept on the earlier file so content flowing across a page break
    is never clipped; --no-overlap makes an exact, non-overlapping page partition.
    """
    files = []          # (folder_parts, title, start_page)
    stack = []          # open folder ancestors: (level, title, page)
    pending_start = None  # start page carried from freshly opened folders to their first file

    for idx, (level, title, page) in enumerate(toc):
        if level > depth:
            continue  # folded into the enclosing section file

        while stack and stack[-1][0] >= level:
            stack.pop()

        has_deeper = idx + 1 < len(toc) and toc[idx + 1][0] > level
        if level < depth and has_deeper:
            # folder: remember the shallowest open page so intro pages land in the first file
            if pending_start is None:
                pending_start = page
            stack.append((level, title, page))
        else:
            start = pending_start if pending_start is not None else page
            pending_start = None
            folder_parts = [sanitize(t) for (_, t, _) in stack]
            files.append((folder_parts, sanitize(title), start))

    if not files:
        return []

    # Capture any cover pages that precede the first bookmark.
    fp, name, _ = files[0]
    files[0] = (fp, name, 1)

    plan = []
    for i, (folder_parts, name, start) in enumerate(files):
        nxt = files[i + 1][2] if i + 1 < len(files) else n_pages + 1
        end = nxt if overlap else nxt - 1
        end = min(max(end, start), n_pages)
        plan.append((folder_parts, name, start, end))
    return plan


def main():
    ap = argparse.ArgumentParser(
        description="Split a PDF into per-section files using its bookmark outline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("pdf", help="input PDF file")
    ap.add_argument("outdir", help="output directory")
    ap.add_argument("--depth", type=int, default=2,
                    help="outline level that becomes individual files; shallower levels become folders")
    ap.add_argument("--no-overlap", dest="overlap", action="store_false",
                    help="exact page partition (no shared boundary pages); may clip content that flows across a page break")
    ap.add_argument("--dry-run", action="store_true", help="print the plan without writing files")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        sys.exit(f"error: no such file: {args.pdf}")

    doc = fitz.open(args.pdf)
    toc = doc.get_toc(simple=True)  # [level, title, page(1-based)]
    if not toc:
        sys.exit("error: this PDF has no bookmark outline to split on")

    plan = build_plan(toc, doc.page_count, args.depth, args.overlap)
    if not plan:
        sys.exit("error: nothing to split at this depth")

    if not args.dry_run and os.path.exists(args.outdir):
        shutil.rmtree(args.outdir)

    prev_dir = object()
    for folder_parts, name, start, end in plan:
        rel_dir = os.path.join(*folder_parts) if folder_parts else ""
        if rel_dir != prev_dir:
            print(f"\n{rel_dir or '.'}/")
            prev_dir = rel_dir
        span = f"p{start}" if start == end else f"p{start}-{end}"
        print(f"    {name}.pdf   [{span}]")
        if not args.dry_run:
            dest_dir = os.path.join(args.outdir, rel_dir)
            os.makedirs(dest_dir, exist_ok=True)
            sub = fitz.open()
            sub.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
            sub.save(os.path.join(dest_dir, f"{name}.pdf"))
            sub.close()

    folders = len({tuple(fp) for fp, _, _, _ in plan})
    verb = "would write" if args.dry_run else "wrote"
    print(f"\n{verb} {len(plan)} files across {folders} folder(s) -> {args.outdir}")


if __name__ == "__main__":
    main()
