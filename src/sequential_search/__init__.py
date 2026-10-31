"""sequential-search: sequential statistical decision-making during graph traversal.

Math layer only -- domain interpretations live in the interpretation layer
(`sequentialist-core`, `sequentialist-visuals`; see docs/ADR-001..008). What
makes this package *sequential-search* rather than *sequentialist-* is that it
contains no interpretation of nodes, edges or observations; classical binary
tests are its degenerate case.
"""

__version__ = "0.0.1"
