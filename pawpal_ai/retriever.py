"""Small TF-IDF retriever over the markdown files in knowledge/.

No external service or API key: retrieval is deterministic, so results are reproducible and
every answer can be traced to a named source file and section.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"
STOP = set("a an and are as at be but by can do does for from how i if in is it its my of on or "
           "should so than that the their there they this to up was we what when which with you "
           "your best good often much many".split())


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [_stem(w) for w in words if w not in STOP and len(w) > 1]


def _stem(w: str) -> str:
    for suffix in ("ing", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[: -len(suffix)]
    return w


@dataclass(frozen=True)
class Chunk:
    source: str       # file name, used as the citation
    heading: str
    text: str
    species: tuple[str, ...]


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


class KnowledgeBase:
    def __init__(self, directory: Path = KNOWLEDGE_DIR) -> None:
        self.chunks = self._load(directory)
        self._tokens = [Counter(tokenize(c.heading + " " + c.heading + " " + c.text)) for c in self.chunks]
        n = len(self.chunks) or 1
        df = Counter(t for toks in self._tokens for t in toks)
        self._idf = {t: math.log((n + 1) / (d + 1)) + 1 for t, d in df.items()}

    @staticmethod
    def _load(directory: Path) -> list[Chunk]:
        chunks: list[Chunk] = []
        for path in sorted(directory.glob("*.md")):
            species: tuple[str, ...] = ("dog", "cat")
            heading, body = None, []

            def flush() -> None:
                if heading and body:
                    chunks.append(Chunk(path.name, heading, " ".join(body).strip(), species))

            for line in path.read_text().splitlines():
                if line.startswith("species:"):
                    species = tuple(s.strip() for s in line.split(":", 1)[1].split(","))
                elif line.startswith("## "):
                    flush()
                    heading, body = line[3:].strip(), []
                elif line.strip() and not line.startswith("topic:"):
                    body.append(line.strip())
            flush()
        return chunks

    def retrieve(self, query: str, species: str | None = None, k: int = 2, min_score: float = 0.15) -> list[Hit]:
        """Top-k chunks by cosine similarity; chunks for another species are never returned."""
        q = Counter(tokenize(query))
        if not q or not self.chunks:
            return []
        qvec = {t: c * self._idf.get(t, 0) for t, c in q.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        hits = []
        for chunk, toks in zip(self.chunks, self._tokens):
            if species and species not in chunk.species:
                continue
            dvec = {t: c * self._idf[t] for t, c in toks.items()}
            dnorm = math.sqrt(sum(v * v for v in dvec.values())) or 1.0
            dot = sum(v * dvec.get(t, 0) for t, v in qvec.items())
            score = dot / (qnorm * dnorm)
            if score >= min_score:
                hits.append(Hit(chunk, round(score, 3)))
        return sorted(hits, key=lambda h: -h.score)[:k]
