"""
app/rag/chunker.py
──────────────────
Parses Markdown knowledge base files into structured chunks.
Each chunk corresponds to an H2 section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class Chunk:
    chunk_id: str
    scheme_id: str
    scheme_name: str
    section: str
    language: str
    source_id: str
    source_priority: str
    financial_terms_status: str
    last_verified: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "section": self.section,
            "language": self.language,
            "source_id": self.source_id,
            "source_priority": self.source_priority,
            "financial_terms_status": self.financial_terms_status,
            "last_verified": self.last_verified,
            "text": self.text,
        }

def _normalize_section_name(name: str) -> str:
    """Normalizes H2 headers to standard section identifiers."""
    name = name.strip().lower()
    if "overview" in name:
        return "overview"
    if "eligibility" in name:
        return "eligibility_criteria"
    if "financial terms" in name:
        return "financial_terms"
    if "activities" in name or "courses" in name:
        return "eligible_activities"
    if "channel partner" in name:
        return "channel_partners"
    if "verification" in name:
        return "verification_notes"
    return name.replace(" ", "_")

def parse_knowledge_file(path: Path) -> list[Chunk]:
    """Reads a Markdown file and returns a list of Chunks."""
    content = path.read_text(encoding="utf-8")
    
    # Extract YAML frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        raise ValueError(f"No YAML frontmatter found in {path}")
        
    frontmatter_text = frontmatter_match.group(1)
    body_text = content[frontmatter_match.end():]
    
    # Parse basic YAML (key: value format without complex structures)
    metadata: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            metadata[key.strip()] = val.strip()
            
    # Extract required fields (failing fast if missing)
    try:
        scheme_id = metadata["scheme_id"]
        scheme_name = metadata["scheme_name"]
        language = metadata["language"]
        source_id = metadata["source_id"]
        source_priority = metadata["source_priority"]
        fin_status = metadata["financial_terms_status"]
        last_verified = metadata["last_verified"]
    except KeyError as e:
        raise ValueError(f"Missing required metadata {e} in {path}")
        
    # Split on H2 headers (\n## )
    # Using lookahead/lookbehind to keep the splitting robust.
    # A chunk starts with "## " and goes until the next "## " or EOF.
    # The file might have content before the first H2 (like an H1 title).
    
    chunks: list[Chunk] = []
    
    # Find all sections starting with ##
    sections = re.split(r"\n(?=## )", "\n" + body_text)
    
    chunk_idx = 0
    for section_text in sections:
        section_text = section_text.strip()
        if not section_text:
            continue
            
        if section_text.startswith("## "):
            # It's an H2 section
            lines = section_text.splitlines()
            header_line = lines[0].replace("## ", "").strip()
            normalized_section = _normalize_section_name(header_line)
            
            chunk = Chunk(
                chunk_id=f"{scheme_id}__{normalized_section}__{chunk_idx}",
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                section=normalized_section,
                language=language,
                source_id=source_id,
                source_priority=source_priority,
                financial_terms_status=fin_status,
                last_verified=last_verified,
                text=section_text,
            )
            chunks.append(chunk)
            chunk_idx += 1
            
    return chunks

def load_all_chunks(kb_dir: Path) -> list[Chunk]:
    all_chunks = []
    for md_file in kb_dir.glob("*.md"):
        all_chunks.extend(parse_knowledge_file(md_file))
    return all_chunks
