"""
seed_rjav.py — populate the dashboard for rjav@dot.com with realistic demo data.

USAGE:
    python scripts/seed_rjav.py          # adds data (idempotent — skips existing case numbers)
    python scripts/seed_rjav.py --wipe   # removes all cases owned/membered by rjav then re-seeds

Run from codebase/backend/ with the venv active and DB running.
"""

import hashlib
import secrets
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── path bootstrap so we can import from app/ ─────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.core.security import hash_password
from app.extensions import db
from app.models.audit_event import AuditEvent
from app.models.case import Case
from app.models.case_member import CaseMember
from app.models.department import Department
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.audit_service import audit_service
from app.core.audit_events import AuditEventType

TARGET_EMAIL = "rjav@dot.com"

# ── Case definitions ───────────────────────────────────────────────────────────

CASES = [
    {
        "case_number": "FIR-2026-DL-4471",
        "title": "Online Banking Fraud — Phishing Ring",
        "description": (
            "Organised phishing syndicate impersonating State Bank of India. "
            "Victims across Delhi NCR defrauded of ₹2.3 Cr. Digital forensics "
            "and call-record analysis ongoing."
        ),
        "status": "UNDER_INVESTIGATION",
        "priority": "CRITICAL",
        "category": "Cybercrime",
    },
    {
        "case_number": "FIR-2026-DL-3892",
        "title": "Dark-Web Narcotics Distribution Network",
        "description": (
            "Suspected Tor-based marketplace used to coordinate drug deliveries "
            "within the city. Coordination with NCB ongoing. Servers under "
            "court-ordered monitoring since July 2026."
        ),
        "status": "UNDER_INVESTIGATION",
        "priority": "HIGH",
        "category": "Narcotics",
    },
    {
        "case_number": "FIR-2026-MH-1120",
        "title": "Corporate Data Breach — Exfiltration via Insider",
        "description": (
            "Former employee of a private defence contractor allegedly exfiltrated "
            "classified project files. Forensic image of workstation acquired. "
            "Chain-of-custody log attached."
        ),
        "status": "OPEN",
        "priority": "HIGH",
        "category": "Cybercrime",
    },
    {
        "case_number": "FIR-2026-UP-0877",
        "title": "Child Exploitation Material — Network Takedown",
        "description": (
            "Coordinated operation with INTERPOL. Three servers seized. "
            "Digital evidence submitted to forensic lab for hash-verification. "
            "Case is multi-jurisdictional."
        ),
        "status": "UNDER_INVESTIGATION",
        "priority": "CRITICAL",
        "category": "Cybercrime",
    },
    {
        "case_number": "FIR-2026-KA-0541",
        "title": "UPI Mule Account Network",
        "description": (
            "Network of 47 mule bank accounts used to layer proceeds from "
            "phone-porting fraud. Transaction graph analysis complete. "
            "Charge sheet under preparation."
        ),
        "status": "CLOSED",
        "priority": "NORMAL",
        "category": "Financial Fraud",
    },
    {
        "case_number": "FIR-2026-DL-2205",
        "title": "Ransomware Attack — Municipal Water Authority",
        "description": (
            "LockBit variant deployed against Delhi Jal Board SCADA systems. "
            "Backups partially encrypted. No ransom paid. Recovery timeline 6 weeks."
        ),
        "status": "OPEN",
        "priority": "CRITICAL",
        "category": "Cybercrime",
    },
    {
        "case_number": "FIR-2025-DL-9901",
        "title": "Cryptocurrency Exchange — Wash Trading Scheme",
        "description": (
            "Domestic crypto exchange manipulated trading volumes to attract "
            "retail investors. Exchange now suspended. SEBI referral pending."
        ),
        "status": "ARCHIVED",
        "priority": "NORMAL",
        "category": "Financial Fraud",
    },
    {
        "case_number": "FIR-2026-RJ-0312",
        "title": "Deepfake Election Disinformation Campaign",
        "description": (
            "AI-generated video clips of political figures circulated on "
            "social media during Rajasthan by-election period. Source IPs "
            "traced to three states. ECI notified."
        ),
        "status": "UNDER_INVESTIGATION",
        "priority": "HIGH",
        "category": "Cybercrime",
    },
]

# ── Documents per case (index → list of doc specs) ────────────────────────────

DOCS_PER_CASE = [
    # FIR-2026-DL-4471 (phishing ring)
    [
        {"title": "First Information Report",         "doc_type": "FIR",                "filename": "FIR_4471.pdf",           "size": 84_210,   "tags": ["fir", "phishing"]},
        {"title": "Bank Transaction Analysis",        "doc_type": "FORENSIC_REPORT",    "filename": "bank_txn_analysis.pdf",  "size": 412_800,  "tags": ["forensics", "banking"]},
        {"title": "Victim Statements — Batch 1",     "doc_type": "WITNESS_STATEMENT",  "filename": "victim_stmts_b1.pdf",    "size": 231_040,  "tags": ["witness", "victim"]},
        {"title": "Phishing Kit Forensic Image",      "doc_type": "EVIDENCE_RECORD",    "filename": "phishing_kit.img",       "size": 52_428_800, "tags": ["forensics", "malware"]},
        {"title": "Section 66C IT Act Charge Sheet",  "doc_type": "CHARGE_SHEET",       "filename": "charge_sheet_4471.pdf",  "size": 178_640,  "tags": ["charge-sheet"]},
    ],
    # FIR-2026-DL-3892 (dark-web narcotics)
    [
        {"title": "FIR — Dark-Web Narcotics",        "doc_type": "FIR",                "filename": "FIR_3892.pdf",           "size": 76_800,   "tags": ["fir", "narcotics"]},
        {"title": "CDR Analysis Report",              "doc_type": "INVESTIGATION_RECORD","filename": "cdr_analysis.pdf",      "size": 306_100,  "tags": ["telecom", "cdr"]},
        {"title": "Seized Substance Lab Report",      "doc_type": "FORENSIC_REPORT",    "filename": "lab_report_narco.pdf",   "size": 145_920,  "tags": ["forensics", "lab"]},
        {"title": "Court Monitoring Order",           "doc_type": "COURT_FILING",       "filename": "court_order_monitor.pdf","size": 54_600,   "tags": ["court", "order"]},
    ],
    # FIR-2026-MH-1120 (insider data breach)
    [
        {"title": "Complaint — Data Breach",          "doc_type": "FIR",                "filename": "FIR_1120.pdf",           "size": 67_200,   "tags": ["fir", "breach"]},
        {"title": "Forensic Disk Image Report",       "doc_type": "FORENSIC_REPORT",    "filename": "disk_forensics.pdf",     "size": 892_400,  "tags": ["forensics", "disk"]},
        {"title": "Chain of Custody Log",             "doc_type": "EVIDENCE_RECORD",    "filename": "coc_log.pdf",            "size": 38_400,   "tags": ["chain-of-custody"]},
    ],
    # FIR-2026-UP-0877 (CSAM network)
    [
        {"title": "INTERPOL Red Notice Reference",    "doc_type": "LEGAL_NOTICE",       "filename": "interpol_notice.pdf",    "size": 92_160,   "tags": ["interpol", "international"]},
        {"title": "Server Seizure Report",            "doc_type": "EVIDENCE_RECORD",    "filename": "server_seizure.pdf",     "size": 215_040,  "tags": ["evidence", "seizure"]},
        {"title": "Hash Verification Report",         "doc_type": "FORENSIC_REPORT",    "filename": "hash_verification.pdf",  "size": 330_240,  "tags": ["forensics", "hash"]},
        {"title": "Victim Identification — Redacted", "doc_type": "INVESTIGATION_RECORD","filename": "victim_id_redacted.pdf", "size": 184_320,  "tags": ["victim", "redacted"]},
        {"title": "Court Filing — Custody Extension", "doc_type": "COURT_FILING",       "filename": "custody_ext.pdf",        "size": 47_616,   "tags": ["court"]},
    ],
    # FIR-2026-KA-0541 (mule accounts)
    [
        {"title": "FIR — Mule Account Network",      "doc_type": "FIR",                "filename": "FIR_0541.pdf",           "size": 81_920,   "tags": ["fir", "financial-fraud"]},
        {"title": "Transaction Graph Export",         "doc_type": "INVESTIGATION_RECORD","filename": "txn_graph.pdf",         "size": 1_024_000,"tags": ["graph", "transactions"]},
        {"title": "Charge Sheet — Section 420 IPC",  "doc_type": "CHARGE_SHEET",       "filename": "charge_sheet_0541.pdf",  "size": 204_800,  "tags": ["charge-sheet", "ipc"]},
        {"title": "Judgment — Sessions Court",        "doc_type": "JUDGMENT",           "filename": "judgment_sessions.pdf",  "size": 138_240,  "tags": ["judgment"]},
    ],
    # FIR-2026-DL-2205 (ransomware)
    [
        {"title": "Incident Report — SCADA Attack",  "doc_type": "FIR",                "filename": "FIR_2205.pdf",           "size": 102_400,  "tags": ["fir", "ransomware", "scada"]},
        {"title": "Malware Sample Analysis",          "doc_type": "FORENSIC_REPORT",    "filename": "lockbit_analysis.pdf",   "size": 665_600,  "tags": ["malware", "lockbit"]},
        {"title": "CERT-In Coordination Report",      "doc_type": "INVESTIGATION_RECORD","filename": "certin_report.pdf",     "size": 256_000,  "tags": ["certin", "coordination"]},
    ],
    # FIR-2025-DL-9901 (crypto wash trading) — ARCHIVED
    [
        {"title": "FIR — Wash Trading",              "doc_type": "FIR",                "filename": "FIR_9901.pdf",           "size": 75_264,   "tags": ["fir", "crypto"]},
        {"title": "SEBI Referral Letter",             "doc_type": "LEGAL_NOTICE",       "filename": "sebi_referral.pdf",     "size": 45_056,   "tags": ["sebi", "referral"]},
        {"title": "Exchange Audit Report",            "doc_type": "FORENSIC_REPORT",    "filename": "exchange_audit.pdf",    "size": 512_000,  "tags": ["audit", "exchange"]},
        {"title": "Final Investigation Report",       "doc_type": "POLICE_REPORT",      "filename": "final_report_9901.pdf", "size": 348_160,  "tags": ["final-report"]},
    ],
    # FIR-2026-RJ-0312 (deepfake)
    [
        {"title": "Complaint — Deepfake Disinformation","doc_type": "FIR",             "filename": "FIR_0312.pdf",           "size": 88_064,   "tags": ["fir", "deepfake"]},
        {"title": "AI-Generated Video Analysis",      "doc_type": "FORENSIC_REPORT",   "filename": "ai_video_forensics.pdf", "size": 2_097_152,"tags": ["forensics", "ai", "deepfake"]},
        {"title": "Social Media Platform Response",   "doc_type": "LEGAL_NOTICE",      "filename": "platform_response.pdf",  "size": 61_440,   "tags": ["social-media", "platform"]},
        {"title": "ECI Notification",                 "doc_type": "LEGAL_NOTICE",      "filename": "eci_notification.pdf",   "size": 39_936,   "tags": ["eci", "election"]},
    ],
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def _fake_hash(*parts: str) -> str:
    """Deterministic SHA-256 from string parts — stable across re-runs."""
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _ago(days: float = 0, hours: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)


# ── Wipe ──────────────────────────────────────────────────────────────────────

def _wipe(rjav: User) -> None:
    """Remove all cases where rjav is a member (plus their docs/chunks/audit events)."""
    member_rows = CaseMember.query.filter_by(user_id=rjav.id).all()
    case_ids = list({m.case_id for m in member_rows})

    if not case_ids:
        print("  Nothing to wipe.")
        return

    from sqlalchemy import text
    # Delete in FK order; audit_events don't have a FK but filter by case_id (text col)
    case_id_strs = [str(cid) for cid in case_ids]
    for cid in case_ids:
        # chunks → documents → case_members → cases
        doc_ids = [d.id for d in Document.query.filter_by(case_id=cid).all()]
        for did in doc_ids:
            DocumentChunk.query.filter_by(document_id=did).delete()
        Document.query.filter_by(case_id=cid).delete()
        CaseMember.query.filter_by(case_id=cid).delete()

    for cid_str in case_id_strs:
        db.session.execute(
            text("DELETE FROM audit_events WHERE case_id = :cid"),
            {"cid": cid_str},
        )

    for cid in case_ids:
        Case.query.filter_by(id=cid).delete()

    db.session.commit()
    print(f"  Wiped {len(case_ids)} case(s) and their documents/audit events.")


# ── Seed ──────────────────────────────────────────────────────────────────────

def _seed(rjav: User) -> None:
    # Collect other demo users to populate members
    investigator = User.query.filter_by(email="inv.patel@police.in").first()
    prosecutor   = User.query.filter_by(email="prosecutor@court.in").first()
    inv_rao      = User.query.filter_by(email="inv.rao@forensics.in").first()
    inv_singh    = User.query.filter_by(email="inv.singh@police.in").first()

    created_cases: list[Case] = []

    for i, cdef in enumerate(CASES):
        if Case.query.filter_by(case_number=cdef["case_number"]).first():
            print(f"  SKIP (exists): {cdef['case_number']}")
            continue

        # ── Create case ──
        offset_days = (len(CASES) - i) * 12  # staggered creation dates
        created_ts  = _ago(days=offset_days)

        case = Case(
            case_number=cdef["case_number"],
            title=cdef["title"],
            description=cdef["description"],
            status=cdef["status"],
            priority=cdef["priority"],
            category=cdef.get("category"),
            created_by=rjav.id,
            lead_officer_id=rjav.id,
            department_id=rjav.department_id,
            created_at=created_ts,
            updated_at=_ago(days=offset_days // 3),
        )

        if cdef["status"] == "CLOSED":
            case.closed_at = _ago(days=offset_days // 4)
        if cdef["status"] == "ARCHIVED":
            case.closed_at  = _ago(days=offset_days // 2)
            case.archived_at = _ago(days=offset_days // 3)

        db.session.add(case)
        db.session.flush()

        # ── Membership: rjav as CASE_OFFICER ──
        db.session.add(CaseMember(
            case_id=case.id, user_id=rjav.id,
            role="CASE_OFFICER", added_by=rjav.id,
            added_at=created_ts,
        ))

        # ── Additional members ──
        extras = []
        if investigator:
            extras.append((investigator, "INVESTIGATOR"))
        if inv_rao and i % 2 == 0:
            extras.append((inv_rao, "INVESTIGATOR"))
        if inv_singh and i % 3 == 0:
            extras.append((inv_singh, "INVESTIGATOR"))
        if prosecutor and cdef["status"] in ("CLOSED", "ARCHIVED", "UNDER_INVESTIGATION"):
            extras.append((prosecutor, "PROSECUTOR"))

        for extra_user, extra_role in extras:
            db.session.add(CaseMember(
                case_id=case.id, user_id=extra_user.id,
                role=extra_role, added_by=rjav.id,
                added_at=_ago(days=offset_days - 2),
            ))

        db.session.flush()

        # ── Audit: CASE_CREATED ──
        audit_service.record(
            AuditEventType.CASE_CREATED.value,
            actor_user_id=rjav.id,
            target_type="case",
            target_id=case.id,
            case_id=case.id,
            ip_address="10.0.0.1",
            metadata={"case_number": case.case_number, "title": case.title},
        )

        # ── Documents ──
        doc_specs = DOCS_PER_CASE[i] if i < len(DOCS_PER_CASE) else []
        for j, dspec in enumerate(doc_specs):
            doc_created = _ago(days=offset_days - j * 2 - 1)
            doc_id      = uuid.uuid4()
            chunk_hash  = _fake_hash("chunk", str(doc_id), "0")
            integ_hash  = _fake_hash("integrity", str(doc_id))
            iv_hex      = secrets.token_hex(12)   # 12 bytes → 24 hex chars
            storage_key = secrets.token_hex(16)

            doc = Document(
                id=doc_id,
                case_id=case.id,
                filename=dspec["filename"],
                original_filename=dspec["filename"],
                title=dspec["title"],
                mime_type="application/pdf",
                doc_type=dspec["doc_type"],
                file_size_bytes=dspec["size"],
                total_chunks=1,
                integrity_hash=integ_hash,
                status="ACTIVE",
                tags=dspec.get("tags", []),
                ocr_status="DONE" if j % 3 != 0 else "NOT_APPLICABLE",
                ocr_confidence=0.87 + (j % 5) * 0.02,
                ocr_language="eng+hin",
                ocr_page_count=max(1, dspec["size"] // 80_000),
                uploaded_by=rjav.id,
                created_at=doc_created,
                updated_at=doc_created,
            )
            db.session.add(doc)
            db.session.flush()

            # One stub chunk (download will fail gracefully — list view fine)
            db.session.add(DocumentChunk(
                document_id=doc_id,
                chunk_index=0,
                storage_key=storage_key,
                iv_hex=iv_hex,
                chunk_hash=chunk_hash,
                size_bytes=dspec["size"],
            ))

            audit_service.record(
                AuditEventType.DOCUMENT_UPLOADED.value,
                actor_user_id=rjav.id,
                target_type="document",
                target_id=doc_id,
                case_id=case.id,
                ip_address="10.0.0.1",
                metadata={
                    "filename": dspec["filename"],
                    "doc_type": dspec["doc_type"],
                    "size_bytes": dspec["size"],
                },
            )

        # ── A few extra activity audit events per case ──
        if investigator:
            audit_service.record(
                AuditEventType.CASE_MEMBER_ADDED.value,
                actor_user_id=rjav.id,
                target_type="user",
                target_id=investigator.id,
                case_id=case.id,
                ip_address="10.0.0.1",
                metadata={"role": "INVESTIGATOR"},
            )
        if cdef["status"] != "OPEN":
            audit_service.record(
                AuditEventType.CASE_UPDATED.value,
                actor_user_id=rjav.id,
                target_type="case",
                target_id=case.id,
                case_id=case.id,
                ip_address="10.0.0.1",
                metadata={"status": cdef["status"]},
            )

        created_cases.append(case)
        print(f"  Created: {case.case_number} — {case.title[:50]}")

    db.session.commit()
    print(f"\n  Done. {len(created_cases)} case(s) seeded for {TARGET_EMAIL}.")


# ── Entry point ───────────────────────────────────────────────────────────────

def run(wipe: bool = False) -> None:
    rjav = User.query.filter_by(email=TARGET_EMAIL).first()
    if rjav is None:
        # Create the account if it doesn't exist
        dept = Department.query.filter_by(name="Cybercrime Unit").first()
        if dept is None:
            print("ERROR: Cybercrime Unit department not found. Run seed.py first.")
            return
        rjav = User(
            email=TARGET_EMAIL,
            password_hash=hash_password("Rjav@1234"),
            full_name="Rajav Singh",
            employee_id="DL-CO-RJAV",
            role="CASE_OFFICER",
            department_id=dept.id,
            is_first_login=False,
        )
        db.session.add(rjav)
        db.session.commit()
        print(f"  Created user {TARGET_EMAIL} (CASE_OFFICER, Cybercrime Unit)")
    else:
        print(f"  Found user {TARGET_EMAIL} — {rjav.full_name} ({rjav.role})")

    if wipe:
        print("  Wiping existing rjav data…")
        _wipe(rjav)

    _seed(rjav)


if __name__ == "__main__":
    wipe = "--wipe" in sys.argv
    app = create_app()
    with app.app_context():
        run(wipe=wipe)
