# PRAMAAN — Frontend Design Context
**For design agents generating pages, components, and layout.**

Read this entire file before generating any UI. Every page, component, data shape, role
restriction, and design constraint is documented here. Do not invent pages or fields that
are not listed — use exactly what is specified.

---

## 1. Product Identity

**Name:** PRAMAAN — Secure Evidence Vault
**Audience:** Law enforcement officers, investigators, prosecutors, auditors, system admins.
Not a consumer product. Users are professional, non-technical government personnel.
**Tone:** Authoritative, minimal, functional. No playfulness. No marketing language.
**Tagline (for login screen only):** "Secure Evidence Vault"

---

## 2. Design System

### Theme
**Dark theme only.** No light mode. No toggle.

### Color Palette

```
Background layers (darkest → lightest):
  bg-base      #0a0c10   ← page background
  bg-surface   #111318   ← cards, sidebars, panels
  bg-elevated  #1a1d24   ← modals, dropdowns, popovers
  bg-input     #1e2028   ← form inputs, search fields

Borders:
  border-subtle   #2a2d35   ← card/panel borders
  border-active   #3a3d47   ← focused input borders

Text:
  text-primary   #e8eaf0   ← headings, labels
  text-secondary #8b8fa8   ← descriptions, timestamps, placeholders
  text-muted     #555869   ← disabled, deemphasized

Brand accent (blue — primary actions):
  accent          #3b82f6   ← primary buttons, links, active nav
  accent-hover    #2563eb
  accent-subtle   #1e3a5f   ← accent background for badges, selected rows

Status colors:
  success        #22c55e   ← DONE, ACTIVE, chain valid
  success-subtle #14391f
  warning        #f59e0b   ← LOW_CONFIDENCE, pending, HIGH priority
  warning-subtle #3d2c08
  danger         #ef4444   ← FAILED, violations, CRITICAL priority, errors
  danger-subtle  #3d1010
  info           #6366f1   ← UNDER_INVESTIGATION status, informational
  info-subtle    #1e1e4a

Severity colors (audit events):
  green  → normal operations (login, upload, case created)
  yellow → access/share events (download, share accessed, case viewed)
  orange → change events (delete, role change, account locked)
  red    → security events (UNAUTHORIZED_ACCESS_ATTEMPT, INTEGRITY_VIOLATION,
            AUDIT_CHAIN_BROKEN, LOGIN_FAILED, MFA_STEP_UP_FAILED)
```

### Typography

```
Font stack: "Inter", "system-ui", sans-serif
Monospace (hashes, IDs, tokens): "JetBrains Mono", "Fira Code", monospace

Scale:
  text-xs    11px / 0.75rem
  text-sm    13px / 0.8125rem
  text-base  14px / 0.875rem    ← default body
  text-md    15px / 0.9375rem
  text-lg    17px / 1.0625rem
  text-xl    20px / 1.25rem
  text-2xl   24px / 1.5rem
  text-3xl   30px / 1.875rem

Weight: 400 (body) · 500 (labels, table headers) · 600 (headings) · 700 (page titles only)
```

### Spacing & Layout

```
Base unit: 4px
Standard padding: 16px (panels), 24px (page content)
Border radius: 6px (inputs, badges), 8px (cards, modals), 4px (buttons)
Sidebar width: 220px (fixed, always visible on authenticated pages)
Top bar height: 56px
Max content width: 1280px (centered)
```

### Icons

**Use Lucide React icons exclusively.** No emoji anywhere in the UI.
`npm install lucide-react`

Key icon → use mapping:
```
Dashboard/Home       → LayoutDashboard
Cases                → FolderOpen
Documents            → FileText
Upload               → Upload
Download             → Download
Search               → Search
Audit log            → ClipboardList
Users / Admin        → Users
Profile              → UserCircle
Settings             → Settings
Sign document        → PenLine
Share                → Share2
Revoke / Delete      → Trash2
Lock / Security      → Shield
MFA / TOTP           → KeyRound
Step-up MFA prompt   → ShieldAlert
Chain valid          → ShieldCheck
Chain broken         → ShieldX
Integrity violation  → AlertTriangle
Warning              → AlertCircle
Info                 → Info
Success              → CheckCircle2
Error / Failed       → XCircle
Pending / Loading    → Loader2 (animated spin)
Refresh              → RefreshCw
Copy to clipboard    → Copy
Close / Dismiss      → X
Menu / More          → MoreVertical
External link        → ExternalLink
File types:
  PDF                → FileText (with accent)
  Image              → Image
  Audio/Video        → Film
  Document           → File
  Evidence           → FolderLock
Chevron expand       → ChevronDown / ChevronRight
Sort                 → ArrowUpDown
Filter               → Filter
Badge / Role         → BadgeCheck
Log out              → LogOut
Forensic             → Microscope
FIR                  → FileWarning
Charge sheet         → FileCheck2
Witness statement    → FileSignature
Court filing         → Building2
```

### Component Conventions

- **Buttons:**
  - Primary: `bg-accent text-white` rounded-md, 34px height, 14px text, `hover:bg-accent-hover`
  - Secondary: `bg-bg-elevated border border-border-subtle text-text-primary`
  - Danger: `bg-danger text-white`
  - Ghost: transparent background, `text-text-secondary hover:text-text-primary hover:bg-bg-elevated`
  - Icon-only: 32px × 32px, rounded, ghost style
- **Inputs:** `bg-bg-input border border-border-subtle text-text-primary placeholder:text-text-muted`, focus ring `border-accent`
- **Table rows:** `hover:bg-bg-elevated`, alternating row tint `bg-bg-surface/50`
- **Badges:** uppercase, 11px, letter-spacing 0.05em, rounded-sm, colored per status
- **Modals:** `bg-bg-elevated` backdrop `bg-black/60`, shadow-2xl, max-w-lg default
- **Tooltips:** `bg-bg-elevated border border-border-subtle text-text-secondary`, appear on hover
- **Loading states:** `Loader2` icon spinning in `text-accent`, centered in its container
- **Empty states:** centered, muted icon + short message + optional CTA button

---

## 3. Role System (RBAC)

Every authenticated page and action must be gated correctly. The `user.role` value is one of:

| Role | Display name | What they see |
|------|-------------|---------------|
| `SUPER_ADMIN` | System Admin | Everything — all cases, all users, all audit logs |
| `CASE_OFFICER` | Case Officer | Their assigned cases, upload/manage docs, create shares |
| `INVESTIGATOR` | Investigator | Assigned cases, view/annotate/sign docs |
| `PROSECUTOR` | Prosecutor | Shared case files (read-only) |
| `AUDITOR` | Auditor | Audit log and chain verification only |
| `VIEWER` | (external) | Share link access only — no nav, no login |

Sidebar nav items visible by role:
- **Dashboard** (cases): SUPER_ADMIN, CASE_OFFICER, INVESTIGATOR, PROSECUTOR
- **Search**: SUPER_ADMIN, CASE_OFFICER, INVESTIGATOR, PROSECUTOR
- **Audit Log**: SUPER_ADMIN, AUDITOR
- **User Admin**: SUPER_ADMIN only
- **Profile**: all authenticated roles

---

## 4. Routing Map

```
/login                    LoginPage           — public
/mfa-setup                MfaSetupPage        — auth (first-time TOTP setup)
/change-password          ChangePasswordPage  — auth (forced on isFirstLogin)
/                         DashboardPage       — auth
/cases/:id                CaseDetailPage      — auth (members of that case + SUPER_ADMIN)
/search                   SearchPage          — auth
/audit                    AuditPage           — auth (SUPER_ADMIN, AUDITOR only)
/admin/users              UserAdminPage       — auth (SUPER_ADMIN only)
/profile                  ProfilePage         — auth
/share/:token             ShareAccessPage     — PUBLIC (no login, no nav)
*                         NotFoundPage        — public
```

---

## 5. Shell Layout (All Authenticated Pages)

```
┌─────────────────────────────────────────────────────┐
│  TOP BAR (56px, bg-surface, border-bottom)          │
│  [≡ logo]  PRAMAAN          [Search]  [👤 User menu]│
└─────────────────────────────────────────────────────┘
┌───────────┬─────────────────────────────────────────┐
│  SIDEBAR  │  PAGE CONTENT                           │
│  (220px)  │  (scrollable, bg-base, 24px padding)    │
│           │                                         │
│  Nav items│                                         │
│  with     │                                         │
│  Lucide   │                                         │
│  icons    │                                         │
│           │                                         │
│  [Logout] │                                         │
└───────────┴─────────────────────────────────────────┘
```

**Top bar:** Logo left = Shield icon + "PRAMAAN" in text-primary font-semibold. Right = user
name + role badge + dropdown (Profile, Logout). No global search in top bar — search is its
own page.

**Sidebar nav item (active state):** `bg-accent-subtle text-accent border-l-2 border-accent`
**Sidebar nav item (inactive):** `text-text-secondary hover:text-text-primary hover:bg-bg-elevated`

---

## 6. Pages — Detailed Spec

---

### 6.1 LoginPage `/login`

**Layout:** Full-screen centered, `bg-base`. No sidebar. No top bar.

```
┌──────────────────────────────────────┐
│                                      │
│      [Shield icon — accent]          │
│      PRAMAAN                         │
│      Secure Evidence Vault           │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  Email                         │  │
│  │  [input]                       │  │
│  │  Password                      │  │
│  │  [input — password type]       │  │
│  │                                │  │
│  │  [Sign In]  (primary button)   │  │
│  └────────────────────────────────┘  │
│                                      │
│  Error: text-danger, icon AlertCircle│
└──────────────────────────────────────┘
```

**MFA Step (shown after password success, replaces the form):**

```
┌────────────────────────────────────┐
│  [KeyRound icon]                   │
│  Two-Factor Authentication         │
│  Enter the 6-digit code from       │
│  your authenticator app.           │
│                                    │
│  [  _ _ _ _ _ _  ]  (OTP input)   │
│  Code refreshes every 30 seconds   │
│                                    │
│  [Verify]         [← Back]         │
└────────────────────────────────────┘
```

OTP input: monospace, large (2xl), centered, 6-digit only, auto-submit on 6th digit.

**Step-up MFA modal** (shown over any page when 401 MFA_REQUIRED is returned):
```
Modal overlay, bg-bg-elevated
  [ShieldAlert icon — warning color]
  Identity Re-Verification Required
  "This action requires a fresh authentication code."
  [OTP input]
  [Verify]   [Cancel]
```

---

### 6.2 MfaSetupPage `/mfa-setup`

**Layout:** Centered card, no sidebar. Shown on first login before dashboard.

```
┌─────────────────────────────────────────┐
│  [KeyRound icon]                        │
│  Set Up Two-Factor Authentication       │
│  Required before accessing the system.  │
│                                         │
│  Step 1: Scan this QR code              │
│  ┌───────────────┐                      │
│  │  [QR code     │  Or enter this code  │
│  │   image]      │  manually:           │
│  │               │  [monospace secret]  │
│  └───────────────┘                      │
│                                         │
│  Step 2: Enter the 6-digit code         │
│  to confirm setup                       │
│  [OTP input]                            │
│                                         │
│  [Activate MFA]  (primary button)       │
└─────────────────────────────────────────┘
```

---

### 6.3 ChangePasswordPage `/change-password`

**Layout:** Centered card, no sidebar.

Fields: Current password, New password (strength meter), Confirm new password.
Show password strength bar (4 segments: weak/fair/good/strong) below the new password field.
Requirements checklist appears as user types: ✓ 12 chars, ✓ uppercase, ✓ digit, ✓ special char.

---

### 6.4 DashboardPage `/` — Case List

**Layout:** Standard shell. Page title: "Cases" with [+ New Case] button (CASE_OFFICER, SUPER_ADMIN only).

**Top area:** Filter bar
```
[Search cases…]  [Status ▾]  [Priority ▾]  [My cases only ▼]
```

**Case grid (2 columns on medium, 3 on large):**
Each `CaseCard`:
```
┌────────────────────────────────────────┐
│  [FolderOpen icon]  #CR-2026-0042      │
│  Case Title (truncated at 2 lines)     │
│                                        │
│  [Status badge]  [Priority badge]      │
│                                        │
│  12 documents  ·  4 members            │
│  Created 3 days ago                    │
│                                        │
│  [View Case →]                         │
└────────────────────────────────────────┘
```

Status badge colors: OPEN=info, UNDER_INVESTIGATION=warning, CLOSED=success, ARCHIVED=text-muted

Priority badge colors: LOW=text-muted, NORMAL=info, HIGH=warning, CRITICAL=danger

**Empty state (no cases):** `FolderOpen` icon muted, "No cases assigned to you." + [Create Case] if CASE_OFFICER.

**Create Case modal:**
Fields: Case Number, Title, Description (textarea), Status (select), Priority (select).

---

### 6.5 CaseDetailPage `/cases/:id`

**Layout:** Standard shell. Breadcrumb: Cases / Case #XX — Title.

**Tab bar (4 tabs):**
```
[FileText Documents]  [ClipboardList Activity]  [Users Members]  [Info Overview]
```

#### Tab: Documents (default)

**Toolbar:**
```
[Upload ↑ Document]  |  [Search docs…]  [DocType ▾]  [Sort ▾]
```

**Document list (table):**

| Icon | Filename | Type | Size | OCR | Uploaded | Actions |
|------|----------|------|------|-----|----------|---------|

- Icon column: FileText/FileWarning/Microscope/FileSignature/Building2 based on doc_type
- OCR column: badge — "Verified" (success), "Low confidence" (warning), "Failed" (danger), "—" (not applicable)
- Actions: `[Download ↓]` `[Sign ✍]` `[Share ↗]` `[⋮]` (more: Delete, View signatures)
- Sign and Share show step-up MFA modal on click
- Delete: confirmation modal + step-up MFA

**Upload area (shown when upload button clicked, slides down above table):**
```
┌─────────────────────────────────────────────────────┐
│   [Upload icon, large]                              │
│   Drag & drop files here, or click to browse       │
│   PDF, DOCX, XLSX, JPG, PNG, TIFF, MP4, WAV        │
│   Maximum 500 MB per file                          │
│                                                     │
│   [Doc type selector — required]                   │
│   [Tags input — optional]                          │
│   [Upload button]                                  │
└─────────────────────────────────────────────────────┘
```

Upload in progress: progress bar (accent color), filename, cancel button.

**Document detail panel (slides in from right on row click, 400px):**
```
┌─────────────────────────────────┐
│  [X]  document_name.pdf        │
│                                 │
│  Type    FIR                    │
│  Size    2.4 MB                 │
│  Chunks  3                      │
│  Status  ACTIVE                 │
│                                 │
│  [OCR Status]                   │
│  Verified — confidence 94%      │
│                                 │
│  [Signatures]                   │
│  ✓ Insp. Ravi Kumar — Aug 27   │
│  (no more signatures)           │
│                                 │
│  Tags: [fir] [2026]             │
│                                 │
│  Uploaded by: name              │
│  Uploaded: date                 │
│                                 │
│  [Download]  [Sign]  [Share]   │
└─────────────────────────────────┘
```

#### Tab: Activity (Audit feed, case-scoped)

Timeline list, newest first:
```
[event-icon]  Actor Name (Role)
              DOCUMENT_DOWNLOADED "evidence_photo.pdf"
              192.168.1.45 · Aug 27, 14:32
```
Severity color on the event icon. No pagination — infinite scroll or "Load more".

#### Tab: Members

Table: Name | Role | Department | Added | Actions (Remove — SUPER_ADMIN/CASE_OFFICER).
[+ Add Member] button → modal with user search + role selector.

#### Tab: Overview

Case metadata grid: Number, Title, Status (editable select for CASE_OFFICER/SUPER_ADMIN),
Priority, Description, Created by, Created at. [Save Changes] button.

---

### 6.6 SearchPage `/search`

**Layout:** Standard shell. Page title: "Search Documents"

**Search input:** full-width, prominent (text-lg), with `Search` icon left, clear button right.

**Filter sidebar (left, 240px, collapsible on mobile):**
```
Document type     [checkbox list]
Date range        [from] — [to]
Tags              [tag input]
Case              [searchable select]
OCR status        [checkbox: Verified / Low confidence / Not applicable]
```

**Results area (right, fills remaining width):**

Table with columns: Doc type icon | Filename | Case | Type | Date | Size | Relevance bar

- "Relevance bar" = thin horizontal bar, accent color, proportional to ts_rank score
- Result row click → opens the CaseDetailPage document panel in context
- Case column links back to `/cases/:id`
- Highlighted search term in filename using `<mark>` styled as `bg-accent/20 text-accent`

**Empty results:** `Search` icon muted, "No documents match your search." No suggestions.

**No query state:** `Search` icon large, "Search across all your case documents." subtitle.

---

### 6.7 AuditPage `/audit`

Accessible only to SUPER_ADMIN and AUDITOR.

**Layout:** Standard shell. Page title: "Audit Log"

**Top row:**
```
[ChainVerifyBadge]    "4,821 events recorded"      [Verify Chain]
```

`ChainVerifyBadge`:
- Default: `[Shield icon]  Chain not yet verified` (text-muted)
- Valid: `[ShieldCheck icon — success] Chain Valid — 4,821 events` (success color)
- Broken: `[ShieldX icon — danger] Tampering Detected — first break at event #3042` (danger color, pulsing border)
- Loading: `[Loader2 spinning]  Verifying…`

**Filter bar:**
```
[Event type ▾]  [Role / Actor ▾]  [Case ▾]  [From date]  [To date]  [Clear filters]
```

**Audit table:**

| # | Timestamp | Event | Actor | Target | IP | Details |
|---|-----------|-------|-------|--------|----|---------|

- `#` = BIGSERIAL id, monospace, text-muted
- Timestamp: date + time, text-secondary
- Event: colored dot (severity) + event type in ALL_CAPS, monospace small
- Actor: name + role badge (or "System" for system events)
- Target: type + short ID (truncated UUID)
- IP: monospace, text-secondary
- Details: expand chevron → reveals `metadata` JSON in a `<pre>` block, dark background

**Severity dot colors** per event type group:
- Green dot: LOGIN, LOGOUT, DOCUMENT_UPLOADED, CASE_CREATED, MFA_VERIFIED, MFA_STEP_UP_VERIFIED
- Yellow dot: DOCUMENT_DOWNLOADED, DOCUMENT_PREVIEWED, SHARE_LINK_ACCESSED, CASE_ACCESSED
- Orange dot: DOCUMENT_DELETED, ROLE_CHANGED, ACCOUNT_LOCKED, DOCUMENT_SHARED, SHARE_LINK_REVOKED
- Red dot: UNAUTHORIZED_ACCESS_ATTEMPT, INTEGRITY_VIOLATION, AUDIT_CHAIN_BROKEN, LOGIN_FAILED, MFA_STEP_UP_FAILED

**Pagination:** "Showing 1–50 of 4,821 events" + prev/next + page jump.

---

### 6.8 UserAdminPage `/admin/users`

SUPER_ADMIN only.

**Layout:** Standard shell. Page title: "User Management"

**Toolbar:**
```
[Search users…]    [Role ▾]    [Status ▾]    [+ Create User]
```

**Users table:**

| Name | Email | Role | Department | Status | Last Login | Actions |
|------|-------|------|------------|--------|------------|---------|

- Role: colored badge (`BadgeCheck` icon)
- Status: ACTIVE (success dot) / LOCKED (warning dot) / INACTIVE (muted dot)
- Last login: relative time ("2 hours ago") + tooltip with exact datetime
- Actions: [Edit role] [Deactivate] — both trigger step-up MFA modal

**Create User modal:**
Fields: Full name, Email, Role (select), Department (select).
On create: shows generated temporary password ONCE in a `<code>` block with Copy button and
"This password will not be shown again" warning (danger-subtle background).

**Edit Role modal:**
Current role → new role selector. Step-up MFA required before submit. AuditEvent: ROLE_CHANGED.

---

### 6.9 ProfilePage `/profile`

**Layout:** Standard shell. Page title: "My Profile"

**Two-column layout:**

Left card: Identity
```
[UserCircle icon — large]
Full name (editable)
Email (read-only)
Department
Role badge
Member since date
```

Right card: Security
```
Password
  [Change Password]

Two-Factor Authentication
  Status: Enabled [KeyRound icon, success]
  [Re-configure MFA]  (triggers MFA setup flow)

Active Session
  Token expires in: 6h 43m
  [Sign Out of All Devices] — not in prototype
```

---

### 6.10 ShareAccessPage `/share/:token`

**Layout:** Full-screen centered, `bg-base`. No sidebar. No top bar. PUBLIC — no login.

```
┌────────────────────────────────────────┐
│  [Shield icon]  PRAMAAN                │
│  Secure Evidence Vault                 │
│                                        │
│  ┌─────────────────────────────────┐   │
│  │ [FileText icon]                 │   │
│  │ evidence_photo.pdf              │   │
│  │ FIR  ·  2.4 MB                  │   │
│  │ Expires in: 18 hours            │   │
│  │                                 │   │
│  │ This link is restricted to:     │   │
│  │ prosecutor@court.gov.in         │   │
│  │                                 │   │
│  │ Email (required)                │   │
│  │ [input: enter your email]       │   │
│  │                                 │   │
│  │ [Download Document]             │   │
│  └─────────────────────────────────┘   │
│                                        │
│  Accessed links are logged.            │
└────────────────────────────────────────┘
```

**Expired / revoked / exhausted state:**
```
[ShieldX icon — danger]
This link is no longer valid.

It may have expired, been revoked, or reached its
maximum number of uses.

Contact the issuing officer for a new link.
```

---

### 6.11 NotFoundPage `*`

```
[Search icon — large, muted]
404
Page not found.
[← Go to Dashboard]   (if authenticated)
[← Go to Login]       (if not)
```

---

## 7. Reusable Components

### 7.1 AppShell

Wraps all authenticated pages. Contains sidebar, top bar, and `<main>` content area.
Sidebar collapses to icon-only at 768px. Nav items: icon + label.

### 7.2 ProtectedRoute

Route guard. Props: `roles?: Role[]`. Redirects:
- `status === "loading"` → full-page spinner
- `status === "anon"` → `/login`
- `user.isFirstLogin` → `/change-password`
- `!user.mfaEnabled` → `/mfa-setup`
- role not in `roles` prop → 403 inline message ("You don't have permission to view this page.")

### 7.3 CaseCard

Props: `CaseSummary`. Dark card with hover lift (`translateY(-2px)`, shadow increase).

### 7.4 DocumentUploader

Drag-and-drop zone. Client-side validation: max 500 MB, MIME type from allowlist. Shows
file preview list with remove buttons before upload. Progress bar per file.

### 7.5 DocumentList

Sortable, filterable table. Columns: type icon, filename, doc type badge, size,
OCR status badge, uploaded date, actions. Row click opens DocumentDetailPanel.

### 7.6 DocumentDetailPanel

Slide-in from right (400px), overlay on mobile. Shows all document metadata, signatures,
OCR status, and action buttons. Close with X or Escape key.

### 7.7 ShareModal

Triggered from document actions. Fields:
- Recipient email (required, validated RFC 5321)
- Expiry (1h / 6h / 12h / 24h / 48h — select)
- Max uses (1 / 3 / 5 / 10 — select, unlimited SUPER_ADMIN only)
- Note (textarea, optional)

On success: shows generated URL in a `bg-bg-input border border-border-subtle` block,
`Copy` button, "⚠ This URL will not be shown again." in warning-subtle.

### 7.8 StepUpMfaModal

Appears as full-screen overlay when any API call returns `{ code: "MFA_REQUIRED" }`.
Has ShieldAlert icon, title, OTP input, Verify and Cancel buttons. On success: retries
the original request. On cancel: dismisses without completing the action.

### 7.9 AuditTable

Paginated table of audit events. Severity dot, event type, actor, target, IP, expand row.
Expanded row shows `metadata` JSON as formatted `<pre>`.

### 7.10 ChainVerifyBadge

Calls `GET /api/v1/audit/verify` on [Verify Chain] button click. Displays three states:
valid (ShieldCheck, success), broken (ShieldX, danger, shows `first_break_at`), loading.
On "broken": shows `first_break_at` event ID in a danger-subtle banner with full explanation.

### 7.11 OcrStatusBadge

Props: `status: string, confidence?: number`
- `DONE` → `CheckCircle2` icon, success color, "Verified (94%)"
- `LOW_CONFIDENCE` → `AlertCircle` icon, warning color, "Low confidence (72%)"
- `FAILED` → `XCircle` icon, danger color, "OCR failed"
- `PENDING` → `Loader2` icon spinning, text-muted, "Processing…"
- `NOT_APPLICABLE` → renders nothing

### 7.12 SignaturePanel

List of Ed25519 signatures on a document. Each row: user name, role, date signed,
verification status (`ShieldCheck` / `ShieldX`). [Sign Document] button triggers step-up MFA.

### 7.13 StatusBadge / PriorityBadge

Small pill badges. Uppercase, 11px, letter-spacing.

Status: OPEN (info), UNDER_INVESTIGATION (warning), CLOSED (success), ARCHIVED (muted)
Priority: LOW (muted), NORMAL (info), HIGH (warning), CRITICAL (danger)

### 7.14 RoleBadge

Props: `role: Role`. Colored pill + `BadgeCheck` icon. Colors:
- SUPER_ADMIN → accent
- CASE_OFFICER → info
- INVESTIGATOR → warning
- PROSECUTOR → success
- AUDITOR → text-secondary
- VIEWER → text-muted

### 7.15 ConfirmModal

Generic destructive action confirmation. Props: `title, description, confirmLabel, onConfirm`.
Confirm button is danger style. Shows `Loader2` inside button while in flight.

### 7.16 SessionTimeout

Shows a subtle banner at the bottom: "Your session expires in 10 minutes." with a
[Stay logged in] button (not implemented in prototype — hidden in prototype).

---

## 8. Data Shapes (TypeScript)

```typescript
// types/index.ts

type Role = "SUPER_ADMIN" | "CASE_OFFICER" | "INVESTIGATOR"
          | "PROSECUTOR" | "AUDITOR" | "VIEWER";

interface CurrentUser {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  mfaEnabled: boolean;
  isFirstLogin: boolean;
}

type CaseStatus = "OPEN" | "UNDER_INVESTIGATION" | "CLOSED" | "ARCHIVED";
type CasePriority = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";

interface CaseSummary {
  id: string;
  caseNumber: string;          // e.g. "CR-2026-0042"
  title: string;
  status: CaseStatus;
  priority: CasePriority;
  documentCount: number;
  memberCount: number;
  createdAt: string;           // ISO 8601
}

type DocType = "FIR" | "POLICE_REPORT" | "INVESTIGATION_RECORD"
  | "WITNESS_STATEMENT" | "CHARGE_SHEET" | "COURT_FILING"
  | "EVIDENCE_RECORD" | "FORENSIC_REPORT" | "LEGAL_NOTICE"
  | "JUDGMENT" | "OTHER";

interface DocumentMeta {
  id: string;
  caseId: string;
  filename: string;
  originalFilename: string;
  title?: string;
  docType: DocType;
  mimeType: string;
  fileSizeBytes: number;
  totalChunks: number;
  integrityHash: string;       // SHA-256, 64 hex chars
  status: "UPLOADING" | "ACTIVE" | "FAILED" | "DELETED";
  tags: string[];
  ocrStatus: "NOT_APPLICABLE" | "PENDING" | "DONE" | "LOW_CONFIDENCE" | "FAILED";
  ocrConfidence?: number;      // 0.0 – 1.0
  uploadedBy: string;          // user display name
  createdAt: string;
}

interface AuditEventRow {
  id: number;                  // BIGSERIAL, monospace display
  eventType: string;           // AuditEventType enum value
  actor?: { id: string; email: string; fullName: string; role: Role };
  targetType?: string;
  targetId?: string;
  caseId?: string;
  ipAddress?: string;
  userAgent?: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}

interface ShareLink {
  id: string;
  createdBy: { fullName: string; email: string };
  allowedEmail: string;        // always set — no anonymous links
  expiresAt: string;
  maxUses: number;
  useCount: number;
  isRevoked: boolean;
  isExpired: boolean;
  note?: string;
  createdAt: string;
}

interface DocumentSignature {
  id: string;
  signedBy: { id: string; fullName: string; role: Role };
  signedAt: string;
  integrityHashAtSign: string;
  isValid: boolean;            // re-verified on fetch
}

interface CaseMember {
  userId: string;
  fullName: string;
  email: string;
  role: Role;
  department: string;
  addedAt: string;
}
```

---

## 9. API Endpoints Reference

All authenticated calls go through `apiFetch(path, init)` from `lib/apiClient.ts`.
Base path: `/api/v1`. Token attached automatically from localStorage.

```
POST   /auth/login               { email, password }
POST   /auth/mfa/verify          { temp_token, totp_code }
POST   /auth/mfa/setup           → { otpauth_uri, qr_code_base64 }
POST   /auth/mfa/confirm         { totp_code }
POST   /auth/mfa/step-up         { totp_code } → { access_token }
POST   /auth/logout
POST   /auth/change-password     { current_password, new_password }

GET    /users/me                 → CurrentUser
GET    /users                    → User[] (SUPER_ADMIN)
POST   /users                    { full_name, email, role, department_id } (step-up)
PATCH  /users/:id/role           { role } (step-up)
PATCH  /users/:id/deactivate     (step-up)

GET    /cases                    → CaseSummary[]
POST   /cases                    { case_number, title, description, status, priority }
GET    /cases/:id                → CaseDetail
PATCH  /cases/:id                { status?, priority?, description? }
GET    /cases/:id/members        → CaseMember[]
POST   /cases/:id/members        { user_id, role }
DELETE /cases/:id/members/:uid

GET    /cases/:id/documents      → DocumentMeta[]
POST   /cases/:id/documents      multipart/form-data { file, doc_type, tags[] }
GET    /documents/:id            → DocumentMeta
GET    /documents/:id/download   → binary stream
DELETE /documents/:id            (step-up)
GET    /documents/:id/signatures → DocumentSignature[]
POST   /documents/:id/sign       (step-up)
POST   /documents/:id/share      { expires_in_hours, max_uses, allowed_email, note } (step-up)
GET    /documents/:id/shares     → ShareLink[]
DELETE /documents/:id/shares/:sid

GET    /documents/search         ?q=&doc_type=&from_date=&to_date=&case_id=&tags=&ocr_status=

GET    /audit                    ?page=&limit=&event_type=&actor_id=&case_id=&from_date=&to_date=
GET    /audit/cases/:id          → AuditEventRow[]
GET    /audit/verify             → { total_events, chain_valid, first_break_at, verified_at }

GET    /share/:token/info        → { filename, doc_type, file_size_bytes, expires_at, requires_email, is_valid }
POST   /share/:token/download    { email } → binary stream
```

---

## 10. State Management

`AuthContext.tsx` (React Context + useReducer) provides:
```typescript
interface AuthContextValue {
  user: CurrentUser | null;
  status: "loading" | "authed" | "anon";
  setSession(accessToken: string, user: CurrentUser): void;
  clear(): void;
}
```

Token lives in `localStorage` key `"dms_access_token"`. `apiFetch()` reads it directly.

**Step-up MFA flow:**
When any `apiFetch()` call receives `{ status: 401, body: { code: "MFA_REQUIRED" } }`,
show `StepUpMfaModal`. On successful step-up (new token returned), call `setSession()` with
new token, keep same `user`, then retry the original request.

---

## 11. Design Do's and Don'ts

**Do:**
- Use Lucide icons for every visual indicator — never emoji or text symbols like ✓ or ✗
- Use monospace font for hashes, UUIDs, case numbers, IPs, token strings, TOTP codes
- Use relative timestamps ("3 hours ago") with tooltip showing full ISO datetime
- Add `title` and `aria-label` to all icon-only buttons
- Show loading states on every async operation — use `Loader2` spinning
- Truncate long filenames with `text-ellipsis` and show full name in tooltip
- Confirm all destructive actions with `ConfirmModal`
- Show step-up MFA for: sign, share, delete, role change, create user, deactivate user

**Don't:**
- No emojis anywhere in the UI
- No light theme, no theme toggle
- No inline styles — only Tailwind classes
- No `console.log` with user data
- No document content stored in component state beyond the active operation
- No "Loading…" text without an icon
- Don't show 403 errors — show 404-equivalent ("not found") per RBAC policy
- Don't show raw UUIDs in user-facing text — use names/case numbers instead
- Don't display `prev_hash` or `this_hash` fields from audit events to users

---

## 12. File Creation Order (suggested)

1. `types/index.ts` — types first (already partially exists)
2. `lib/apiClient.ts` — HTTP layer
3. `store/AuthContext.tsx` — session state
4. `hooks/useAuth.ts` — login/logout/bootstrap logic
5. `components/ProtectedRoute.tsx` — route guard
6. `App.tsx` — full route map
7. `components/AppShell.tsx` — layout (sidebar + topbar)
8. `pages/LoginPage.tsx`
9. `pages/MfaSetupPage.tsx`
10. `pages/ChangePasswordPage.tsx`
11. `pages/DashboardPage.tsx` + `components/CaseCard.tsx`
12. `pages/CaseDetailPage.tsx` + document-related components
13. `pages/SearchPage.tsx`
14. `pages/AuditPage.tsx` + `components/ChainVerifyBadge.tsx`
15. `pages/UserAdminPage.tsx`
16. `pages/ProfilePage.tsx`
17. `pages/ShareAccessPage.tsx`
18. `pages/NotFoundPage.tsx`
19. Shared components: OcrStatusBadge, StepUpMfaModal, ShareModal, ConfirmModal, etc.
