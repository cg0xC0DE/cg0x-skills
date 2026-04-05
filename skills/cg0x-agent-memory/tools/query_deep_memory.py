"""
query_deep_memory.py — Deep Memory Search Tool
Part of cg0x-agent-memory skill: https://github.com/cg0x/cg0x-skills

Searches archived memory entries in memory/archive/ for matching keywords.
Only call this when the user explicitly asks you to recall something that
is not in MEMORY.md. Do NOT call proactively.

Usage:
    python query_deep_memory.py <keyword> [<keyword2> ...]

    # Search for entries containing ALL keywords (AND logic)
    python query_deep_memory.py 旅行 上海
    python query_deep_memory.py project deadline

    # Search from a specific workspace directory
    python query_deep_memory.py --workspace /path/to/workspace keyword

Options:
    --workspace DIR   Workspace directory containing memory/archive/
                      (default: directory where this script lives)
    --max-results N   Maximum results to return (default: 20)
    --month YYYY-MM   Search only a specific month's archive

Examples:
    python query_deep_memory.py 项目
    python query_deep_memory.py 2026-01 用户
    python query_deep_memory.py --max-results 5 deadline
"""

import argparse
import sys
from pathlib import Path


def search_archive(
    archive_dir: Path,
    keywords: list[str],
    max_results: int = 20,
    month: str = None,
) -> list[dict]:
    """
    Search archived memory entries for entries containing ALL keywords.

    Args:
        archive_dir:  Path to memory/archive/ directory
        keywords:     List of keywords (AND logic — all must match)
        max_results:  Maximum number of results to return
        month:        Optional YYYY-MM filter (e.g. '2026-01')

    Returns:
        List of dicts: [{month, line, line_number}]
    """
    if not archive_dir.exists():
        return []

    archive_files = sorted(archive_dir.glob("*.md"), reverse=True)

    if month:
        archive_files = [f for f in archive_files if f.stem == month]

    matches = []
    for archive_file in archive_files:
        try:
            content = archive_file.read_text(encoding="utf-8")
        except Exception:
            continue

        for i, line in enumerate(content.split("\n"), 1):
            if not line.startswith("- "):
                continue
            line_lower = line.lower()
            if all(kw.lower() in line_lower for kw in keywords):
                matches.append({
                    "month": archive_file.stem,
                    "line": line,
                    "line_number": i,
                })
                if len(matches) >= max_results:
                    return matches

    return matches


def format_results(matches: list[dict], keywords: list[str]) -> str:
    """Format search results for display."""
    if not matches:
        return f"No archived memories found matching: {', '.join(keywords)}"

    lines = [f"Found {len(matches)} archived memory entries matching: {', '.join(keywords)}\n"]
    current_month = None
    for m in matches:
        if m["month"] != current_month:
            current_month = m["month"]
            lines.append(f"\n[{current_month}]")
        lines.append(f"  {m['line']}")

    return "\n".join(lines)


def _parse_args():
    p = argparse.ArgumentParser(
        description="Search archived memory entries in memory/archive/"
    )
    p.add_argument("keywords", nargs="+",
                   help="Keywords to search for (AND logic — all must match)")
    p.add_argument("--workspace", default=None,
                   help="Workspace directory containing memory/archive/ "
                        "(default: directory where this script lives)")
    p.add_argument("--max-results", type=int, default=20,
                   help="Maximum results to return (default: 20)")
    p.add_argument("--month",
                   help="Search only a specific month, format: YYYY-MM")
    return p.parse_args()


def main():
    args = _parse_args()

    if args.workspace:
        workspace = Path(args.workspace)
    else:
        workspace = Path(__file__).resolve().parent

    archive_dir = workspace / "memory" / "archive"

    matches = search_archive(
        archive_dir=archive_dir,
        keywords=args.keywords,
        max_results=args.max_results,
        month=args.month,
    )

    print(format_results(matches, args.keywords))

    if not matches:
        sys.exit(1)


if __name__ == "__main__":
    main()
