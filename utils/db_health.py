"""
Database health check — verifies all required tables exist.

Run this at startup (or on a dedicated page) to tell the user exactly which
SQL migrations they still need to run.
"""
from __future__ import annotations

from typing import Dict, List
import streamlit as st


# All tables the app expects, grouped by migration that creates them
REQUIRED_TABLES = {
    "schema.sql": [
        "profiles", "products", "orders", "order_items", "agreements",
        "fraud_logs", "favorites", "cart_items", "ai_predictions", "notifications",
    ],
    "migration_v2.sql": ["messages"],
    "migration_v3.sql": ["user_preferences"],
    "migration_v4.sql": ["merchant_requests"],
}


@st.cache_data(ttl=60, show_spinner=False)
def check_all_tables() -> Dict[str, Dict]:
    """Check which required tables exist. Returns a dict keyed by migration file.

    Each value is {"tables": [(name, exists_bool), ...], "all_present": bool}
    """
    from database.connection import get_supabase_client

    try:
        client = get_supabase_client()
    except Exception:
        # If we can't even get a client, return empty result
        return {mig: {"tables": [(t, False) for t in tables], "all_present": False, "error": "no_client"}
                for mig, tables in REQUIRED_TABLES.items()}

    result: Dict[str, Dict] = {}
    for migration, tables in REQUIRED_TABLES.items():
        table_status: List[tuple] = []
        for table in tables:
            exists = _table_exists(client, table)
            table_status.append((table, exists))
        result[migration] = {
            "tables": table_status,
            "all_present": all(exists for _, exists in table_status),
        }
    return result


def _table_exists(client, table_name: str) -> bool:
    """Check if a table exists by trying a lightweight SELECT on it."""
    try:
        client.table(table_name).select("*").limit(1).execute()
        return True
    except Exception as e:
        err = str(e).lower()
        # PGRST205 = "schemaCacheMiss" — table doesn't exist
        # Also catch "does not exist" in the message
        if "pgrst205" in err or "does not exist" in err or "could not find" in err:
            return False
        # If it's a 401 or other auth error, the table MIGHT exist but we can't
        # verify — assume it exists to avoid false negatives
        if "401" in err or "unauthorized" in err:
            return True
        return False


def render_db_health_warning():
    """Show a warning banner if any required tables are missing.

    Call this at the top of any page that uses database tables.
    Returns True if all tables are present, False if some are missing.
    """
    try:
        status = check_all_tables()
    except Exception:
        return True  # don't block the page if check fails

    missing_migrations = [
        mig for mig, info in status.items()
        if not info.get("all_present", False)
    ]

    if not missing_migrations:
        return True  # all good

    # Show a warning with specific instructions
    missing_count = sum(
        sum(1 for _, exists in status[mig]["tables"] if not exists)
        for mig in missing_migrations
    )
    st.warning(
        f"⚠️ Database setup incomplete — {missing_count} table(s) missing. "
        f"Some features will not work until you run the SQL migrations below."
    )

    with st.expander("📋 Click to see which migrations to run", expanded=False):
        for mig in missing_migrations:
            info = status[mig]
            missing_tables = [name for name, exists in info["tables"] if not exists]
            if missing_tables:
                st.markdown(f"**Run `supabase/{mig}`** in Supabase SQL Editor to create:")
                st.markdown(f"  • Missing: {', '.join(missing_tables)}")
                st.markdown(f"  • Already present: {', '.join(n for n, e in info['tables'] if e) or 'none'}")
                st.markdown("")

    return False


def is_table_available(table_name: str) -> bool:
    """Quick check: is a specific table available?"""
    try:
        status = check_all_tables()
        for mig_info in status.values():
            for name, exists in mig_info["tables"]:
                if name == table_name:
                    return exists
        return False
    except Exception:
        return True  # don't block if check fails
