"""Bonito Studio — chat-first front door for the Bonito platform.

Studio replaces the post-auth landing with a clean BDR-style chat surface.
It reuses Origami's orchestrator, tool registry, and SSE protocol wholesale.
The two net-new pieces are:

  - `prompt.py`   — BDR-flavored system prompt + snapshot rendering helper
  - `snapshot.py` — single-query org snapshot used to ground the first turn

See `docs/BONITO-STUDIO-PLAN.md` for the build plan.
"""
