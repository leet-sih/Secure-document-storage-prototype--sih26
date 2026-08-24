"""
test_audit_chain.py — audit hash-chain integrity (needs real Postgres: advisory lock).

Source: audit_trail_plan.md "Testing Plan". These prove tamper-evidence — the compliance
headline of the whole project. Fill in bodies.
"""

import pytest


def test_first_event_has_genesis_prev_hash():
    pytest.skip("TODO")


def test_sequential_events_form_valid_chain():
    pytest.skip("TODO")


def test_verify_detects_modified_event():
    """Mutate one row's event_type in the DB -> verify_chain reports first_break_at that row."""
    pytest.skip("TODO")


def test_verify_detects_deleted_event():
    pytest.skip("TODO")


def test_concurrent_records_do_not_fork_chain():
    """Parallel record() calls under advisory lock still produce a single valid chain."""
    pytest.skip("TODO")
