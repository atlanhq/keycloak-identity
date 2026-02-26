# AGENTS.md — Keycloak Identity AI Agent Guidelines

> **Version:** 4.0  
> **Last Updated:** 2026-02-26  
> **Applies To:** All AI agents working on this repository  
> **Companion File:** See `CLAUDE.md` for the lean version.

---

## Security

### Owners & Contact
- **Security Team:** #collab-platform-security on Slack.
- **Manual Security Review:** Changes to authentication flows, token handling, identity providers, authorization policies, themes, or security configurations → **request security review**.

### Quickstart
1) Identify: **Java/Keycloak Core**, **Auth Flows**, **Token Handling**, **Themes**, **Config**.  
2) Apply **Security Invariants** to every change.  
3) CRITICAL → **block**. HIGH/MEDIUM/LOW → **flag with fix**.

**Tags:** `[MUST]` = required | `[REDLINE]` = forbidden | `[SHOULD]` = best practice

### Security Invariants (Always Apply)
- **[MUST] No secrets in code or logs** (private keys, client secrets, tokens, passwords).
- **[MUST] Authentication flows must not be weakened** — no bypassing MFA, reducing token validation.
- **[MUST] Token handling must be secure** — proper signing, validation, expiry.
- **[MUST] Pin supply chain:** Java deps→exact versions, images→**version/SHA**.
- **[MUST] All code in approved GitHub organizations** (AtlanHQ).

#### Secret Discovery Protocol
If you discover a secret → treat as **CRITICAL**. Do NOT commit/push. Flag with 🔒 SECURITY REVIEW. Recommend rotation. Notify Security team.

### Code Type Security Matrix

| Code Type | Key Risks |
|-----------|-----------|
| **Auth Flows** | Authentication bypass, MFA weakening, session fixation |
| **Token Handling** | Token forgery, improper validation, excessive token lifetime |
| **Identity Providers** | SAML/OIDC misconfiguration, redirect URI manipulation |
| **Themes/Frontend** | XSS, CSRF, credential harvesting via phishing |
| **Authorization** | Broken access control, privilege escalation, role misconfiguration |

### Authentication Flow Security
- **[MUST]** Never weaken authentication flows (remove MFA steps, skip validation)
- **[MUST]** Session tokens must be invalidated on logout
- **[MUST]** Brute-force protection must remain enabled
- **[MUST]** Password policies must meet minimum complexity requirements
- **[REDLINE]** Disabling MFA, allowing plaintext passwords, bypassing auth checks

### Token Handling Security
- **[MUST]** Tokens signed with strong algorithms (RS256+); no `none` algorithm
- **[MUST]** Validate token expiry, issuer, audience on every check
- **[MUST]** Refresh tokens must have bounded lifetime and rotation
- **[MUST]** Never log tokens or include in URLs
- **[REDLINE]** Accepting unsigned tokens; disabling token validation

### Identity Provider Security
- **[MUST]** SAML/OIDC redirect URIs must be strictly validated (no open redirects)
- **[MUST]** SAML assertions must be signed and validated
- **[SHOULD]** Use PKCE for OAuth2 flows

### Theme/Frontend Security
- **[MUST]** All user inputs sanitized to prevent XSS
- **[MUST]** CSRF tokens on all forms
- **[MUST]** No inline JavaScript in templates
- **[REDLINE]** Rendering unsanitized user input

### Security Review Format
```txt
🔒 SECURITY REVIEW
Issue: [description]
Severity: CRITICAL | HIGH | MEDIUM | LOW
Location: [file:line]
Recommended Fix: [concrete fix]
```

### Severity Rules
| Severity | Criteria | Action |
|----------|----------|--------|
| **CRITICAL** | Auth bypass, token forgery, credential exposure | **Block** |
| **HIGH** | MFA weakening, session fixation, XSS in login pages | **Block** |
| **MEDIUM** | Unpinned deps, missing CSRF, verbose errors | **Flag** |
| **LOW** | Best practice gaps | **Note** |

### Security Checklist
- [ ] No secrets in code/config/logs
- [ ] Auth flows not weakened
- [ ] Tokens properly signed, validated, and expired
- [ ] SAML/OIDC redirect URIs strictly validated
- [ ] Themes sanitize all inputs (no XSS)
- [ ] CSRF tokens on all forms
- [ ] Dependencies and images pinned
- [ ] SCA scanning (Snyk) configured

## Version History
- **v4.0 (2026-02-26):** Initial AGENTS.md with security section for Keycloak identity management.
