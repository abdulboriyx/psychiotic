#!/usr/bin/env python3
"""
translate.py — Translate wiki/ pages to Turkish, outputting to wiki-tr/.

Usage:
    python3 translate.py                                  # translate all wiki/ files + index.md
    python3 translate.py wiki/conditions/depression.md    # translate one file
    python3 translate.py wiki/conditions/ wiki/mechanisms/ # translate specific dirs
    python3 translate.py index.md                         # translate root index only

Requires: ANTHROPIC_API_KEY environment variable
"""

import os
import sys
import time
import anthropic

ROOT = os.path.dirname(os.path.abspath(__file__))
WIKI_DIR = os.path.join(ROOT, "wiki")
WIKI_TR_DIR = os.path.join(ROOT, "wiki-tr")
INDEX_EN = os.path.join(ROOT, "index.md")
INDEX_TR = os.path.join(ROOT, "index-tr.md")

SYSTEM_PROMPT = """You are a precise scientific and medical translator specialising in psychiatry and neuroscience.
Translate the provided markdown document from English to Turkish.

Rules — follow every one of these exactly:
1. Preserve all markdown formatting without any changes: headers (#, ##, ###), tables (| col |), bold (**text**), italic (*text*), bullet lists (- item), numbered lists, code blocks (```), horizontal rules (---).
2. Preserve all link PATHS exactly as written — only translate the visible display text inside [brackets]. Example: [Depression](../conditions/depression.md) → [Depresyon](../conditions/depression.md).
3. For scientific/technical terms: on the FIRST occurrence in the document, write the Turkish term followed by the English in parentheses. Example: "Epigenetik Düzenleme (Epigenetic Regulation)". On subsequent occurrences use Turkish only.
4. Do NOT translate: gene names (BDNF, RELN, GAD1, Nr3c1, etc.), drug names (fluoxetine, imipramine, MS275, etc.), chemical names (5mC, 5hmC, cAMP, NMDA, AMPA, etc.), citation keys, DOIs, file paths, or any text inside backticks.
5. Status labels must be translated accurately: Established → Kanıtlanmış, Hypothesis → Hipotez, Contested → Tartışmalı, Confirmed → Onaylanmış.
6. Return ONLY the translated markdown. Do not add any commentary, preamble, or explanation before or after."""

TRANSLATION_PROMPT = """Translate the following markdown document from English to Turkish, following all rules in your instructions.

---

{content}"""


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def translate_content(client: anthropic.Anthropic, content: str, filepath: str) -> str:
    print(f"  Translating: {os.path.relpath(filepath, ROOT)}")
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8096,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": TRANSLATION_PROMPT.format(content=content)}
        ],
    )
    return message.content[0].text


def output_path_for(input_path: str) -> str:
    """Map an input path to its Turkish output path."""
    abs_input = os.path.abspath(input_path)

    # index.md → index-tr.md
    if abs_input == INDEX_EN:
        return INDEX_TR

    # wiki/foo/bar.md → wiki-tr/foo/bar.md
    rel = os.path.relpath(abs_input, WIKI_DIR)
    if rel.startswith(".."):
        raise ValueError(f"Path {input_path} is not inside wiki/ or index.md")
    return os.path.join(WIKI_TR_DIR, rel)


def fix_index_links(content: str) -> str:
    """In index-tr.md, rewrite wiki/ link targets to wiki-tr/."""
    import re
    return re.sub(r'\(wiki/', '(wiki-tr/', content)


def translate_file(client: anthropic.Anthropic, filepath: str) -> None:
    abs_path = os.path.abspath(filepath)
    with open(abs_path, "r", encoding="utf-8") as f:
        content = f.read()

    translated = translate_content(client, content, abs_path)

    # Fix index link targets
    if abs_path == INDEX_EN:
        translated = fix_index_links(translated)

    out_path = output_path_for(filepath)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(translated)

    print(f"  → {os.path.relpath(out_path, ROOT)}")


def collect_md_files(paths: list[str]) -> list[str]:
    """Expand a list of file/directory paths to individual .md files."""
    result = []
    for p in paths:
        abs_p = os.path.abspath(p)
        if os.path.isfile(abs_p) and abs_p.endswith(".md"):
            result.append(abs_p)
        elif os.path.isdir(abs_p):
            for dirpath, _, filenames in os.walk(abs_p):
                for fname in sorted(filenames):
                    if fname.endswith(".md"):
                        result.append(os.path.join(dirpath, fname))
        else:
            print(f"Warning: skipping {p} (not a .md file or directory)")
    return result


def main() -> None:
    client = get_client()

    if len(sys.argv) > 1:
        targets = collect_md_files(sys.argv[1:])
    else:
        # Default: all wiki/ pages + root index.md
        targets = collect_md_files([WIKI_DIR]) + [INDEX_EN]

    if not targets:
        print("No .md files found to translate.")
        sys.exit(0)

    print(f"Translating {len(targets)} file(s) to Turkish...\n")

    for i, filepath in enumerate(targets):
        translate_file(client, filepath)
        if i < len(targets) - 1:
            time.sleep(0.5)  # avoid rate limiting between calls

    print(f"\nDone. {len(targets)} file(s) translated.")
    print(f"Turkish wiki: {os.path.relpath(WIKI_TR_DIR, ROOT)}/")
    if INDEX_EN in targets:
        print(f"Turkish index: {os.path.relpath(INDEX_TR, ROOT)}")


if __name__ == "__main__":
    main()
