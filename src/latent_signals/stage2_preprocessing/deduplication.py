"""MinHash-based near-duplicate detection."""

from __future__ import annotations

from datasketch import MinHash, MinHashLSH


def build_minhash(text: str, num_perm: int = 128) -> MinHash:
    """Create a MinHash signature for a text string."""
    m = MinHash(num_perm=num_perm)
    # Use word-level 3-grams (shingles)
    words = text.lower().split()
    for i in range(len(words) - 2):
        shingle = " ".join(words[i : i + 3])
        m.update(shingle.encode("utf-8"))
    return m


def find_duplicates(
    texts: dict[str, str], threshold: float = 0.8, num_perm: int = 128
) -> set[str]:
    """Find near-duplicate document IDs using MinHash LSH.

    Args:
        texts: mapping of doc_id -> text
        threshold: Jaccard similarity threshold for dedup
        num_perm: number of permutations for MinHash

    Returns:
        Set of doc_ids that are duplicates (should be excluded).
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes: dict[str, MinHash] = {}

    for doc_id, text in texts.items():
        mh = build_minhash(text, num_perm)
        minhashes[doc_id] = mh

    duplicates: set[str] = set()
    for doc_id, mh in minhashes.items():
        if doc_id in duplicates:
            continue
        try:
            lsh.insert(doc_id, mh)
        except ValueError:
            # Already inserted (exact duplicate key)
            duplicates.add(doc_id)
            continue

        # Query for similar documents
        results = lsh.query(mh)
        for match_id in results:
            if match_id != doc_id:
                duplicates.add(match_id)

    return duplicates
