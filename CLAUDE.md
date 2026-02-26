# CLAUDE.md — Keycloak Identity (Claude Code Edition)

> **Full Policy:** See `AGENTS.md` for comprehensive details.

---

## Security

### Owners & Contact
- **Security Team:** #collab-platform-security on Slack.
- **Manual Review:** Changes to auth flows, token handling, identity providers, themes, authorization → request security review.

### Security Invariants
- **[MUST] No secrets in code or logs** (private keys, client secrets, tokens, passwords).
- **[MUST] Auth flows must not be weakened** — no bypassing MFA or reducing validation.
- **[MUST] Token handling secure** — proper signing (RS256+), validation, expiry.
- **[MUST] Pin supply chain:** Java deps→exact versions, images→version/SHA.
- **[MUST] All code in approved GitHub organizations** (AtlanHQ).

### Secret Discovery Protocol
Secret found → **CRITICAL**. Do NOT commit. Flag with 🔒 SECURITY REVIEW. Recommend rotation. Notify Security.

### Key Rules
- **[MUST]** Tokens: signed (RS256+), validate expiry/issuer/audience, never log
- **[MUST]** SAML/OIDC: strict redirect URI validation, signed assertions
- **[MUST]** Themes: sanitize inputs (no XSS), CSRF tokens on forms
- **[REDLINE]** Disabling MFA; `none` algorithm; accepting unsigned tokens; plaintext passwords

### Security Checklist
- [ ] No secrets in code/config/logs
- [ ] Auth flows not weakened
- [ ] Tokens properly signed and validated
- [ ] Redirect URIs strictly validated
- [ ] Themes sanitize inputs, CSRF tokens present
- [ ] Dependencies and images pinned
- [ ] SCA scanning (Snyk) configured

> **Full details:** See `AGENTS.md § Security`.
