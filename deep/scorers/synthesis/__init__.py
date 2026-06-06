"""Synthesis layer — aggregates per-instrument scores into higher-order profiles.

Unlike scorers/ (which apply one published instrument to one passage), the
synthesis layer reads the *_scores.json artifacts that score_session.py emits
and rolls them up into the interpretive documents described in method.md §5.2.

Currently:
    profile.py — per-model Kerberos Psyche Profile (LLM synthesizer)
"""
