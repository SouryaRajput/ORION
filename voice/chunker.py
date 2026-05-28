# -----------------------
# SMART CHUNKER
# Splits text into natural speech segments
# with pause hints for human-like delivery.
# -----------------------

import re


def chunk_for_speech(text: str):
    """
    Splits text into natural speech chunks with pause timings.
    
    Returns a list of (chunk_text, pause_ms) tuples.
    pause_ms is the pause AFTER speaking this chunk.
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    # Step 1: Split on sentence boundaries (.!?) preserving the punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()

        # Short sentence (≤ 15 words) → keep as one chunk
        if len(words) <= 15:
            chunks.append((sentence, 250))
            continue

        # Long sentence → split on clause boundaries (, ; — :)
        clauses = re.split(r'(?<=[,;:\u2014\u2013])\s+', sentence)

        for i, clause in enumerate(clauses):
            clause = clause.strip()
            if not clause:
                continue

            clause_words = clause.split()

            # If a clause is still very long (>25 words), force-split at ~15 words
            if len(clause_words) > 25:
                for j in range(0, len(clause_words), 15):
                    sub = " ".join(clause_words[j:j + 15])
                    if sub:
                        # Mid-clause forced split → short pause
                        chunks.append((sub, 60))
            else:
                # Last clause in sentence → sentence-end pause
                if i == len(clauses) - 1:
                    chunks.append((clause, 250))
                else:
                    # Clause boundary → medium pause
                    chunks.append((clause, 120))

    # Fix: last chunk should have a longer "final" pause
    if chunks:
        last_text, _ = chunks[-1]
        chunks[-1] = (last_text, 350)

    return chunks
