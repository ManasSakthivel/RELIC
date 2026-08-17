"""
RELIC (legacy_contract) — top-level package init.
"""

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

__version__ = "0.1.0"
