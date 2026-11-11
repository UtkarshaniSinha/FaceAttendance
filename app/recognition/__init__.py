"""Face recognition engine (Phase 3).

Kept separate from attendance: nothing in this package records attendance.

    embedder.py  - YuNet detection + SFace embeddings (the only OpenCV-model code)
    matcher.py   - cosine similarity and match / unknown / ambiguous decisions
    service.py   - builds templates from consented enrolments and identifies captures
"""
