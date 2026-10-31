# RegImpact-SL — Phase 5.0: Full-Stack Integration & Role-Based Functionality Audit

**Date:** 2026-11-01  
**Auditor Roles:** Senior Full-Stack Software Architect, Backend Integration Engineer, Frontend QA Engineer, Application Security Auditor  
**Project:** RegImpact-SL  
**Governing Specification:** `RegImpact-SL_Project_Proposal_v4_FINAL.md`  
**Primary Audit Target:** Role-Based Access Control (RBAC), Frontend-Backend Authorization Coupling, User Persona Separation, and Security Boundary Integrity  
**Overall Audit Verdict:** **FAIL (SIGNIFICANT ROLE-SEPARATION AND SECURITY DEFECTS DETECTED)**

---

## 1. Executive Summary & Verdict

This audit was initiated to investigate why switching between **Admin**, **Reviewer**, and **SME User** experiences appears to produce the identical interface and behavior across the RegImpact-SL application.

### Key Audit Findings:
1. **Frontend Role Selection Is Purely Cosmetic:** Switching the role in the top navigation `RoleSwitcher` saves the value to `localStorage` and dispatches a local event, but **zero frontend views adapt their layout, navigation links, or action buttons**. 
   - The top navigation bar (`Navbar.tsx`) is static and displays the exact same three links (`Compliance Assessor`, `Reviewer Portal`, `Evaluation Dashboard`) to all users.
   - The main landing page (`/`) renders the identical food manufacturing SME profile form and compliance assessor for Admin, Reviewer, and SME roles alike.
   - An SME user can freely navigate to the administrative review portal (`/admin/reviews`) and access the PDF upload form.
2. **Critical Error-Masking Defect in Review Portal:** When an SME user navigates to `/admin/reviews`, the backend correctly returns `HTTP 403 Forbidden`. However, the frontend catch block swallows the 403 error into a temporary toast, leaves the internal `reviews` state empty (`[]`), and renders:
   > *"Review Queue Empty: All candidate statutory rules in the review queue have been reviewed."* (with a green checkmark icon).  
   The user is misled into believing the queue is empty rather than being informed that access is restricted.
3. **Critical Security Vulnerability in Backend Auth:** While the backend enforces `require_role()` on sensitive endpoints when `X-User-Role` is explicitly passed, line 100 of `backend/src/main.py` contains a critical security flaw:
   ```python
   def get_current_role(x_user_role: Optional[str] = Header(None, alias="X-User-Role")) -> str:
       if not x_user_role:
           return "admin"  # <-- CRITICAL SECURITY FLAW: Defaults to admin when header omitted
   ```
   **Any unauthenticated HTTP client that omits the `X-User-Role` header is automatically granted full administrative privileges (`role="admin"`).**
4. **Client-Spoofable Security Boundary:** There are no user accounts, passwords, sessions, or cryptographic tokens (JWTs) anywhere in the application. Authorization relies entirely on an unauthenticated client header (`X-User-Role`). Any client or script can spoof `"admin"` or `"reviewer"` by simply supplying that string in the header.

### Overall Verdict: **FAIL**
While core neuro-symbolic engine algorithms (layout-aware segmentation, BGE embeddings, live Gemini compilation, ContextAwareVerifier, and Kleene AST execution) are functionally sound, the application **fails to provide genuine role-based workflow separation, leaks administrative UI to unauthorized personas, masks authorization failures with misleading success states, and possesses an insecure authorization default**.

---

## 2. Role-Responsibility Matrix: Expected vs. Implemented

Based on Proposal v4 and the system design, the table below contrasts the expected access control against the actual implementation:

| Functionality / Workflow | Target Role | Expected Permission (Proposal v4) | Actual Backend Enforcement | Actual Frontend UI Behavior | Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Compliance Analysis** (`POST /analysis`) | SME | **Allowed** (Primary SME workflow) | Allowed (`sme_user`, `reviewer`, `admin`) | Available on `/` for all roles | **PASS** |
| | Reviewer | **Allowed** (Verification testing) | Allowed | Available on `/` | **PASS** |
| | Admin | **Allowed** (System testing) | Allowed | Available on `/` | **PASS** |
| **View Statutory Catalog** (`GET /regulations`) | SME | **Allowed** (View applicable rules) | Allowed (`sme_user`, `reviewer`, `admin`) | Displayed on `/` sidebar | **PASS** |
| | Reviewer | **Allowed** | Allowed | Displayed on `/` sidebar | **PASS** |
| | Admin | **Allowed** | Allowed | Displayed on `/` sidebar | **PASS** |
| **Evaluation Dashboard** (`GET /evaluation/results`) | Admin / Researcher | **Allowed** (Benchmark verification) | Allowed (`sme_user`, `reviewer`, `admin`) | Visible in Navbar for all roles | **PARTIAL** (Exposed to SME) |
| | SME | **Restricted / Hidden** (Internal research tool) | Allowed (No restriction) | Fully visible & clickable | **DEFECT** |
| **View Review Queue** (`GET /admin/reviews`) | Reviewer | **Allowed** (Adjudication queue) | Allowed (`reviewer`, `admin`) | Rendered on `/admin/reviews` | **PASS** |
| | Admin | **Allowed** (Supervisory audit) | Allowed | Rendered on `/admin/reviews` | **PASS** |
| | SME | **Forbidden** (Internal legal queue) | Enforced (`403 Forbidden`) | Link visible; page renders *"Queue Empty"* | **DEFECT** (Error Masked) |
| **Approve / Reject Rules** (`POST /admin/reviews/{id}/...`) | Reviewer | **Allowed** (With mandatory rationale) | Allowed (`reviewer`, `admin`) | Buttons active on `/admin/reviews` | **PASS** |
| | Admin | **Allowed** | Allowed | Buttons active | **PASS** |
| | SME | **Forbidden** | Enforced (`403 Forbidden`) | Hidden only because queue shows empty | **PASS WITH LIMITATIONS** |
| **Upload Regulatory Documents** (`POST /admin/documents/upload`) | Admin | **Allowed** (Corpus expansion) | Allowed (`admin` only) | Rendered under "Ingest Document" tab | **PASS** |
| | Reviewer | **Forbidden** (Read & adjudicate only) | Enforced (`403 Forbidden`) | Tab visible; upload fails with toast | **DEFECT** (UI exposed) |
| | SME | **Forbidden** | Enforced (`403 Forbidden`) | Tab visible; upload fails with toast | **DEFECT** (UI exposed) |
| **Manage System Data / DB** | Admin | **Allowed** (Corpus hygiene) | Omitted header defaults to admin | No UI controls implemented | **DEFECT** (Vulnerability) |

---

## 3. Frontend Audit Findings

### 3.1 Static Navigation Bar (`Navbar.tsx`)
- In [`frontend/src/components/Navbar.tsx`](file:///C:/Users/HP/Desktop/PROJECTS/RegImpact-SL/frontend/src/components/Navbar.tsx#L48-L68), `navLinks` is a static constant:
  ```typescript
  const navLinks = [
    { name: "Compliance Assessor", href: "/", icon: FileCheck2 },
    { name: "Reviewer Portal", href: "/admin/reviews", icon: Scale },
    { name: "Evaluation Dashboard", href: "/evaluation", icon: BarChart3 },
  ];
  ```
- **Defect:** Navigation links are never filtered against `getCurrentUserRole()`. An SME user sees identical navigation links to an Admin.

### 3.2 Main Landing Page (`/` — `page.tsx`)
- The main page contains **zero role checks or conditional rendering blocks**.
- Whether the active role is Admin, Reviewer, or SME, the page exclusively renders the SME Food Manufacturing Profile Form (`ProfileForm.tsx`) alongside benchmark scenarios ("Bottled Mixed Fruit Jam").
- Admins do not have an administrative overview (e.g. ingested corpus overview, system health status, rule statistics).
- Reviewers do not have a dedicated reviewer landing view.

### 3.3 Review Portal Error Swallowing (`/admin/reviews/page.tsx`)
- Located in [`frontend/src/app/admin/reviews/page.tsx`](file:///C:/Users/HP/Desktop/PROJECTS/RegImpact-SL/frontend/src/app/admin/reviews/page.tsx#L51-L62):
  ```typescript
  const fetchQueue = useCallback(async () => {
    setLoading(true);
    try {
      const items = await getPendingReviews();
      setReviews(items);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load review queue.";
      setToastMessage({ type: "error", text: msg });
    } finally {
      setLoading(false);
    }
  }, []);
  ```
- When an SME user visits `/admin/reviews`:
  1. `getPendingReviews()` sends `"X-User-Role": "sme_user"`.
  2. The backend responds with `HTTP 403 Forbidden` (`Access forbidden: role 'sme_user' is not authorized`).
  3. The error is caught, `reviews` remains `[]`, and `loading` becomes `false`.
  4. The page renders:
     ```tsx
     <CheckCircle2 className="w-5 h-5 text-emerald-400" />
     <h3 className="text-sm font-semibold text-zinc-100">Review Queue Empty</h3>
     <p className="text-xs text-zinc-400 max-w-md mx-auto">
       All candidate statutory rules in the review queue have been reviewed.
     </p>
     ```
  5. **Impact:** The SME user is shown a misleading success message stating that all regulatory rules are reviewed, instead of an explicit "Access Denied / Unauthorized Role" gate.
  6. The second tab (`Ingest Document (PDF)`) remains fully clickable and interactive.

### 3.4 Internal Page Reviewer Role Disconnect
- Inside `/admin/reviews/page.tsx` (lines 34–35, 206–215), the page maintains independent state:
  ```typescript
  const [reviewerId, setReviewerId] = useState("legal_officer_sl");
  const [reviewerRole, setReviewerRole] = useState("PRIMARY_ANNOTATOR");
  ```
- This page-level role dropdown (`PRIMARY_ANNOTATOR`, `SECONDARY_ANNOTATOR`, `EXPERT_ADJUDICATOR`) is completely decoupled from the global `RoleSwitcher` (`admin`, `reviewer`, `sme_user`).

---

## 4. Backend Audit & Security Analysis

### 4.1 Critical Default-to-Admin Flaw (`backend/src/main.py`)
Lines 98–108 of [`backend/src/main.py`](file:///C:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/main.py#L98-L108):
```python
VALID_ROLES: Set[str] = {"sme_user", "reviewer", "admin"}

def get_current_role(x_user_role: Optional[str] = Header(None, alias="X-User-Role")) -> str:
    """Extract and validate role from X-User-Role header. Default to 'admin' when omitted."""
    if not x_user_role:
        return "admin"  # <-- CRITICAL SECURITY FLAW
    role = x_user_role.strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid X-User-Role '{x_user_role}'. Valid roles are: {', '.join(sorted(VALID_ROLES))}",
        )
    return role
```

#### Security Implications:
1. **Unauthenticated Admin Access:** Any script, attacker, or external client that sends an HTTP request without custom headers is treated by the server as an **Administrator**.
2. **Endpoint Bypass:** An attacker calling `GET /admin/reviews` or `POST /admin/documents/upload` without an `X-User-Role` header completely bypasses `require_role({"admin"})`.
3. **Verified Live Proof:**
   - `GET /admin/reviews` with `X-User-Role: sme_user` -> `HTTP 403 Forbidden` (Enforced)
   - `GET /admin/reviews` with **no header** -> **`HTTP 200 OK` (Bypassed! Returned 11 items)**

### 4.2 Client-Controlled Identity & Absence of User Model
1. **No User Database Table:** PostgreSQL public schema contains exactly 5 tables (`clauses`, `document_pages`, `human_review_audit`, `rules`, `source_documents`). There is no `users`, `accounts`, `sessions`, or `credentials` relation.
2. **No Authentication Boundary:** The application does not use session cookies, JWT bearer tokens, or password hashes. The client unilaterally dictates its role via `X-User-Role`.

---

## 5. Live HTTP & Integration Verification Evidence

Automated probe tests were executed against the live Uvicorn service on `http://localhost:8000`:

```text
=== ROLE-BASED ACCESS CONTROL AUDIT RESULTS ===

--- Endpoint: GET /health ---
  [No Header   ] Status: 200 | keys: ['status']
  [admin       ] Status: 200 | keys: ['status']
  [reviewer    ] Status: 200 | keys: ['status']
  [sme_user    ] Status: 200 | keys: ['status']
  [invalid_role] Status: 200 | keys: ['status']

--- Endpoint: GET /regulations ---
  [No Header   ] Status: 200 | returned 88 items (Bypassed to admin)
  [admin       ] Status: 200 | returned 88 items
  [reviewer    ] Status: 200 | returned 88 items
  [sme_user    ] Status: 200 | returned 88 items
  [invalid_role] Status: 400 | detail: Invalid X-User-Role 'hacker'

--- Endpoint: GET /evaluation/results ---
  [No Header   ] Status: 200 | keys: ['status', 'is_empirical_result', 'quarantine_notice']
  [admin       ] Status: 200 | keys: ['status', 'is_empirical_result', 'quarantine_notice']
  [reviewer    ] Status: 200 | keys: ['status', 'is_empirical_result', 'quarantine_notice']
  [sme_user    ] Status: 200 | keys: ['status', 'is_empirical_result', 'quarantine_notice']
  [invalid_role] Status: 400 | detail: Invalid X-User-Role 'hacker'

--- Endpoint: GET /admin/reviews ---
  [No Header   ] Status: 200 | returned 11 items  <-- VULNERABILITY (Admin Leak)
  [admin       ] Status: 200 | returned 11 items
  [reviewer    ] Status: 200 | returned 11 items
  [sme_user    ] Status: 403 | detail: Access forbidden: role 'sme_user' is not authorized
  [invalid_role] Status: 400 | detail: Invalid X-User-Role 'hacker'

--- Endpoint: POST /admin/documents/upload ---
  [No Header   ] Status: 422 | detail: [{'loc': ['body', 'file'], 'msg': 'Field required'}] <-- (Role gate bypassed)
  [admin       ] Status: 422 | detail: [{'loc': ['body', 'file'], 'msg': 'Field required'}]
  [reviewer    ] Status: 403 | detail: Access forbidden: role 'reviewer' is not authorized
  [sme_user    ] Status: 403 | detail: Access forbidden: role 'sme_user' is not authorized
  [invalid_role] Status: 400 | detail: Invalid X-User-Role 'hacker'

--- Endpoint: POST /admin/reviews/{id}/approve (Negative Test Probe) ---
  [No Header   ] Status: 404 | detail: Rule not found (Passed auth check)
  [admin       ] Status: 404 | detail: Rule not found (Passed auth check)
  [reviewer    ] Status: 404 | detail: Rule not found (Passed auth check)
  [sme_user    ] Status: 403 | detail: Access forbidden: role 'sme_user' is not authorized
```

---

## 6. Identified Defects Ranked by Severity

| Defect ID | Severity | Component | Defect Title & Description | Impact |
|:---:|:---:|:---|:---|:---|
| **SEC-01** | **CRITICAL** | `backend/src/main.py` | **Default to Admin on Missing Header**<br>`get_current_role()` assigns role `"admin"` when `X-User-Role` is absent. | Any unauthenticated client or script gains full administrative upload and review rights by simply omitting the header. |
| **SEC-02** | **HIGH** | Full-Stack | **Unauthenticated Client-Spoofable RBAC**<br>Security model relies entirely on untrusted client HTTP header without cryptographic signing, tokens, or sessions. | Users can self-elevate privileges by selecting a different option in the UI or tampering with requests. |
| **UI-01** | **HIGH** | `frontend/src/app/admin/reviews/page.tsx` | **Masked 403 Error Displays Misleading "Queue Empty" State**<br>When an SME user loads `/admin/reviews`, the 403 error is caught and renders an emerald checkmark stating all rules are reviewed. | Severely confuses users and conceals unauthorized access from auditing. |
| **UI-02** | **HIGH** | `frontend/src/components/Navbar.tsx` | **Static Navigation Bar Lacks Role-Based Filtering**<br>`navLinks` displays Admin Reviewer Portal and Evaluation links to SME users. | Violates user persona separation; exposes internal routes to unauthorized users. |
| **UI-03** | **MEDIUM** | `frontend/src/app/admin/reviews/page.tsx` | **Upload Form Exposed to Reviewers and SME Users**<br>The "Ingest Document (PDF)" tab is visible and interactive for all roles, failing only upon form submission. | Poor UX; exposes administrative document ingestion tools to non-admin roles. |
| **UI-04** | **MEDIUM** | `frontend/src/app/page.tsx` | **Main Dashboard Lacks Role Adaptability**<br>The landing page exclusively serves the SME persona; Admins and Reviewers have no tailored dashboard view. | Admin and Reviewer personas lack central monitoring controls on the home route. |
| **ARCH-01**| **LOW** | `frontend/src/services/api.ts` | **Role Synchronization via Local Window Events**<br>Role switching uses a custom window event (`regimpact:role_change`) rather than a unified React context provider. | Components do not reliably re-render across navigation without manual listeners. |

---

## 7. Existing Core Functionality Confirmed Intact

The identified integration defects pertain strictly to **role presentation, authorization defaulting, and route-gating UX**. The underlying core functionality remains 100% verified and operational:
1. **Document Ingestion Service:** Extracts pages, calculates SHA-256 hashes, and preserves verbatim PDF text.
2. **Layout-Aware Segmentation:** Parses complex multi-page Sri Lankan Gazettes into structured clauses with cross-page stitching, schedules, and tables.
3. **Local Vector Search:** Generates 768-dimensional normalized dense vectors with `BAAI/bge-base-en-v1.5` in pgvector.
4. **Live Gemini Compilation:** `GeminiLLMClient` (`gemini-2.5-flash-lite`) active and compiling structured rules.
5. **Context-Aware Evidence Grounding:** `ContextAwareVerifier` rejects ungrounded dates and ungrounded obligations.
6. **Quarantined Persistence:** Rules are strictly saved as `PENDING_REVIEW`.
7. **Deterministic Applicability Engine:** Kleene 3-valued boolean logic (`TRUE`, `FALSE`, `UNKNOWN`) executes safely, strictly isolating unapproved rules as `OutcomeStatus.UNSUPPORTED` coverage gaps.

---

## 8. Minimal Recommended Remediation Roadmap

To resolve these defects while preserving all existing working components and avoiding architectural overreach:

### Step 1: Secure Backend Role Default (`SEC-01`, `SEC-02`)
In [`backend/src/main.py`](file:///C:/Users/HP/Desktop/PROJECTS/RegImpact-SL/backend/src/main.py#L98-L108):
- Change `get_current_role()` so that if `X-User-Role` is missing, it defaults to `"sme_user"` (the least privileged role), **never** `"admin"`.
- If an endpoint requires `{"reviewer", "admin"}` and no header or an invalid header is provided, it must strictly return `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`.

### Step 2: Implement Reactive RBAC Context in Frontend (`ARCH-01`, `UI-02`)
- Create an `AuthContext` (or use a reactive role hook) that provides the current role to all components.
- In `Navbar.tsx`, filter `navLinks` based on the active role:
  - **SME User:** Only sees `Compliance Assessor` (`/`).
  - **Reviewer:** Sees `Compliance Assessor` (`/`) and `Reviewer Portal` (`/admin/reviews`).
  - **Admin:** Sees `Compliance Assessor` (`/`), `Reviewer Portal` (`/admin/reviews`), and `Evaluation Dashboard` (`/evaluation`).

### Step 3: Implement Explicit Access Denied Screen on Admin Reviews (`UI-01`, `UI-03`)
In `frontend/src/app/admin/reviews/page.tsx`:
- Detect when `getPendingReviews()` returns an authorization error (HTTP 403).
- Instead of setting `reviews = []` and rendering "Queue Empty", render a dedicated **"Access Denied: Reviewer or Admin Role Required"** view with a button to switch roles or return home.
- Hide the "Ingest Document (PDF)" tab unless the active role is `"admin"`.

### Step 4: Adapt Main Page Experience by Role (`UI-04`)
In `frontend/src/app/page.tsx`:
- If active role is `admin`, display administrative shortcut badges (e.g. Ingested Documents count, Pending Reviews count, Engine Health).
- If active role is `sme_user`, highlight the SME business configuration steps and action checklist.

---

## 9. Final Conclusion

The audit conclusively explains why switching between Admin and SME user experiences produces the same interface:
1. **Frontend navigation and pages do not adapt to role state.**
2. **The Reviewer Portal swallows 403 Forbidden errors and renders a false "Queue Empty" message.**
3. **The backend defaults to Admin when headers are omitted, undermining security boundaries.**

All core algorithms remain healthy. Implementing the 4 minimal remediation steps above will fully align the application with the governing Proposal v4 specification.

