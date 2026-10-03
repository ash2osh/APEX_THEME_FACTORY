#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

python3 - "$ROOT" <<'PY_EOF'
import os
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
errors = []

def add_error(rel_path: str, msg: str):
    errors.append((rel_path, msg))

def check_link(link_path: Path, expected: Path, name: str, missing_msg: str, wrong_msg_fmt: str) -> bool:
    is_text = link_path.is_file() and not link_path.is_symlink()
    if not link_path.is_symlink() and not is_text:
        add_error(name, missing_msg)
        return False
    try:
        if link_path.is_symlink():
            target = link_path.resolve()
        else:
            text = link_path.read_text(encoding="utf-8").strip()
            if not text or "\n" in text or len(text) > 500:
                add_error(name, missing_msg)
                return False
            target = (link_path.parent / text).resolve()
        if not expected.exists() or target != expected.resolve():
            add_error(name, wrong_msg_fmt.format(target=target, expected=expected.resolve()))
            return False
        return True
    except Exception as e:
        add_error(name, f"broken symlink: {e}")
        return False

# 1. AGENTS.md
agents_md = root / "AGENTS.md"
if not agents_md.exists() or not agents_md.is_file():
    add_error("AGENTS.md", "missing or not a regular file")
else:
    raw = agents_md.read_bytes()
    if len(raw) == 0:
        add_error("AGENTS.md", "file is empty")
    elif len(raw) > 32768:
        add_error("AGENTS.md", f"file size {len(raw)} bytes exceeds 32 KiB limit")

# 2. CLAUDE.md
claude_md = root / "CLAUDE.md"
check_link(claude_md, agents_md, "CLAUDE.md", "missing or not a symlink", "symlink resolves to {target}, expected AGENTS.md")

# 3. .agents/rules/apex-theme-factory.md
rule_path = root / ".agents/rules/apex-theme-factory.md"
if not rule_path.exists() or not rule_path.is_file():
    add_error(".agents/rules/apex-theme-factory.md", "missing or not a regular file")
else:
    text = rule_path.read_text(encoding="utf-8")
    if len(text) > 12000:
        add_error(".agents/rules/apex-theme-factory.md", f"character count {len(text)} exceeds 12000 limit")
    
    # Parse frontmatter
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        add_error(".agents/rules/apex-theme-factory.md", "missing opening '---' frontmatter delimiter on first line")
    else:
        closing_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_idx = i
                break
        if closing_idx == -1:
            add_error(".agents/rules/apex-theme-factory.md", "missing closing '---' frontmatter delimiter")
        else:
            fm = "\n".join(lines[1:closing_idx])
            if not re.search(r"^trigger:\s*always_on\s*$", fm, re.MULTILINE):
                add_error(".agents/rules/apex-theme-factory.md", "frontmatter missing 'trigger: always_on'")
            desc_match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if not desc_match or not desc_match.group(1).strip():
                add_error(".agents/rules/apex-theme-factory.md", "frontmatter missing non-empty description")

# 4. .agent/skills legacy compatibility symlink
legacy_link = root / ".agent/skills"
check_link(legacy_link, root / ".agents/skills", ".agent/skills", "missing or not a symlink", "symlink resolves to {target}, expected .agents/skills")

# 5. Canonical skills in .agents/skills/
skills_dir = root / ".agents/skills"
discovered_skills = {}
if not skills_dir.exists() or not skills_dir.is_dir():
    add_error(".agents/skills", "directory missing")
else:
    for item in sorted(skills_dir.iterdir()):
        if not item.is_dir():
            continue
        skill_file = item / "SKILL.md"
        if not skill_file.exists() or not skill_file.is_file():
            add_error(f".agents/skills/{item.name}/SKILL.md", "missing SKILL.md")
            continue
        
        content = skill_file.read_text(encoding="utf-8")
        slines = content.splitlines()
        if not slines or slines[0].strip() != "---":
            add_error(f".agents/skills/{item.name}/SKILL.md", "missing opening '---' frontmatter delimiter")
            continue
        
        s_closing = -1
        for idx in range(1, len(slines)):
            if slines[idx].strip() == "---":
                s_closing = idx
                break
        if s_closing == -1:
            add_error(f".agents/skills/{item.name}/SKILL.md", "missing closing '---' frontmatter delimiter")
            continue
        
        s_fm = "\n".join(slines[1:s_closing])
        name_matches = re.findall(r"^name:\s*([^\s]+)\s*$", s_fm, re.MULTILINE)
        if not name_matches:
            add_error(f".agents/skills/{item.name}/SKILL.md", "frontmatter missing 'name:'")
            continue
        if len(name_matches) > 1:
            add_error(f".agents/skills/{item.name}/SKILL.md", "multiple 'name:' definitions in frontmatter")
            continue
        
        skill_name = name_matches[0]
        if skill_name != item.name:
            add_error(f".agents/skills/{item.name}/SKILL.md", f"skill name '{skill_name}' does not match directory '{item.name}'")
        
        if skill_name in discovered_skills:
            add_error(f".agents/skills/{item.name}/SKILL.md", f"duplicate skill name '{skill_name}'")
        else:
            discovered_skills[skill_name] = item

        desc_match = re.search(r"^description:\s*(.+)$", s_fm, re.MULTILINE)
        if not desc_match or not desc_match.group(1).strip():
            add_error(f".agents/skills/{item.name}/SKILL.md", "frontmatter missing non-empty 'description:'")

# 6. .claude/skills/ symlinks
claude_skills_dir = root / ".claude/skills"
claude_link_count = 0
if not claude_skills_dir.exists() or not claude_skills_dir.is_dir():
    add_error(".claude/skills", "directory missing")
else:
    for skill_name, skill_path in sorted(discovered_skills.items()):
        link_path = claude_skills_dir / skill_name
        if check_link(link_path, skill_path, f".claude/skills/{skill_name}", "missing symlink", "resolves to {target}, expected {expected}"):
            claude_link_count += 1

# 7. Documentation path drift in .agents/README.md
readme_path = root / ".agents/README.md"
if not readme_path.exists() or not readme_path.is_file():
    add_error(".agents/README.md", "missing file")
else:
    readme_text = readme_path.read_text(encoding="utf-8")
    for req_path in (".agents/skills", ".claude/skills", ".agents/rules", ".agent/skills"):
        if req_path not in readme_text:
            add_error(".agents/README.md", f"documentation missing path '{req_path}'")

# Print all errors
for rel_path, msg in errors:
    print(f"ERROR path={rel_path} message={msg}")

status = "PASS" if not errors else "FAIL"
print(f"AGENT_LAYOUT status={status} skills={len(discovered_skills)} claude_links={claude_link_count} errors={len(errors)}")

sys.exit(0 if status == "PASS" else 1)
PY_EOF
