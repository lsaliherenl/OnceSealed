"""Privacy layer: buyer identities, salted commitments, the auditor vault and retirement receipts.

Nothing here talks to the chain. The functions produce exactly the values the
RetirementRegistry contract expects; tests/vectors.json pins them for both sides.
"""
