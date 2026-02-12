#!/usr/bin/env python3
"""Generate README.md from YAML front matter in learning plan files."""

import glob
import os
import re
import sys

CATEGORY_ORDER = [
    "Spring & Spring Boot",
    "JVM Internals",
    "Build Tools",
    "Data & Messaging",
    "APIs & Protocols",
    "Observability",
    "Infrastructure",
    "Languages & Paradigms",
    "NewSQL",
]

EXCLUDED_FILES = {"README.md", "CLAUDE.md"}


def parse_front_matter(filepath):
    """Parse YAML front matter from a markdown file using regex."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?\n)---\s*\n", content, re.DOTALL)
    if not match:
        return None

    front_matter = {}
    for line in match.group(1).splitlines():
        m = re.match(r'^(\w+)\s*:\s*"(.+)"$', line)
        if not m:
            m = re.match(r"^(\w+)\s*:\s*'(.+)'$", line)
        if not m:
            m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
        if m:
            front_matter[m.group(1)] = m.group(2).strip()

    return front_matter


def generate_readme():
    """Generate README.md from plan files with YAML front matter."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_files = sorted(glob.glob(os.path.join(script_dir, "*.md")))

    # Collect plans grouped by category
    categories = {}
    for filepath in md_files:
        filename = os.path.basename(filepath)
        if filename in EXCLUDED_FILES:
            continue

        fm = parse_front_matter(filepath)
        if fm is None:
            print(f"warning: {filename} has no front matter, skipping", file=sys.stderr)
            continue

        title = fm.get("title")
        category = fm.get("category")
        description = fm.get("description")

        if not all([title, category, description]):
            print(
                f"warning: {filename} missing required front matter fields, skipping",
                file=sys.stderr,
            )
            continue

        categories.setdefault(category, []).append(
            {"title": title, "description": description, "filename": filename}
        )

    # Sort entries within each category by title
    for entries in categories.values():
        entries.sort(key=lambda e: e["title"].lower())

    # Order categories: predefined order first, then unknown alphabetically
    ordered_categories = []
    for cat in CATEGORY_ORDER:
        if cat in categories:
            ordered_categories.append(cat)
    unknown = sorted(set(categories.keys()) - set(CATEGORY_ORDER))
    ordered_categories.extend(unknown)

    # Count total plans
    total = sum(len(categories[c]) for c in ordered_categories)

    # Build README
    lines = []
    lines.append("# Claude Learning Plans")
    lines.append("")
    lines.append(
        "Structured, multi-week learning curricula for senior engineers who want"
        " deep mastery of backend, infrastructure, and systems topics."
    )
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(
        f"This repository contains {total} self-paced learning plans generated with"
        " Claude. Each plan follows a phased, project-based format designed for"
        " working engineers — typically 12–16 weeks of focused study with curated"
        " resources, hands-on milestones, and progressive complexity. Topics range"
        " from Spring Boot internals to Kubernetes, Go, and distributed data systems."
    )
    lines.append("")
    lines.append("## Plans by Category")

    for cat in ordered_categories:
        lines.append("")
        lines.append(f"### {cat}")
        lines.append("")
        for entry in categories[cat]:
            lines.append(
                f"- [{entry['title']}]({entry['filename']})"
                f" — {entry['description']}"
            )

    lines.append("")
    lines.append("## How to Use These Plans")
    lines.append("")
    lines.append("Each plan is a standalone Markdown file structured around:")
    lines.append("")
    lines.append(
        "1. **Phases** — Progressive stages from foundations to advanced topics,"
        " typically spanning 12–16 weeks."
    )
    lines.append(
        "2. **Milestones** — Concrete projects and exercises at each phase to"
        " validate understanding."
    )
    lines.append(
        "3. **Curated Resources** — Books, documentation, talks, and blog posts"
        " selected for each topic."
    )
    lines.append("")
    lines.append(
        "Pick a plan that matches your current learning goal, work through the"
        " phases at your own pace, and use the milestones to gauge progress."
    )
    lines.append("")  # trailing newline

    readme_path = os.path.join(script_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    generate_readme()
