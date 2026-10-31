"""sequential-search: sequential statistical decision-making during graph traversal.

Math layer only -- domain interpretations live in the `sequentialist-search`
wrapper (see docs/ADR-001..006). What makes this package *sequential-search*
rather than *sequentialist-search* is that it contains no interpretation of
nodes, edges or observations; classical binary tests are its degenerate case.
"""

__version__ = "0.0.1"
