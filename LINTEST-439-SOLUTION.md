# LINTEST-439 Solution Summary

## Problem Statement

Customer on **apex.atlan.com** (Flo Barot Jr) is unable to push the Okta group `grpAtlanProdWorkflowAdmin` to Atlan via SCIM Push Groups. The operation consistently fails with a stale `externalId` error:

```
Failed on 01-23-2026 05:57:01PM UTC: Unable to update Group Push mapping target App group 
`grpAtlanProdWorkflowAdmin`: Error while trying to get the group `grpAtlanProdWorkflowAdmin` 
with the externalId `2ea7c8f7-7506-4b71-a53c-f307aedb647d`
```

## Root Cause

When Okta groups are deleted and recreated, or when SSO group mappings are removed and re-added, orphaned `externalId` mappings can remain in Keycloak's database. These stale mappings prevent new group pushes from succeeding because:

1. The Keycloak group may be deleted, but the `externalId` attribute mapping remains in the database
2. The `externalId` references a group that no longer exists or has been recreated with a different internal ID
3. Keycloak's SCIM endpoint cannot resolve the stale mapping, causing push operations to fail

## Solution Implemented

This branch implements a comprehensive solution to detect and clean up stale `externalId` mappings:

### Components

1. **SCIM Push Groups Handler** (`backend/scim/push_groups.py`)
   - Automatic detection of stale `externalId` mappings during group push operations
   - Cleanup logic integrated into the group push workflow
   - Audit logging of all cleanup operations

2. **Keycloak Mappings Client** (`backend/keycloak/mappings.py`)
   - Database/API interface for managing `externalId` mappings
   - Validation and consistency checking
   - Health monitoring capabilities

3. **Cleanup Utility** (`backend/utils/cleanup_stale_external_ids.py`)
   - Command-line tool for manual intervention by support teams
   - Support for single group, batch, or full tenant cleanup
   - Dry-run mode for safe previewing of changes

## Quick Start - Resolving LINTEST-439

### Prerequisites

```bash
cd backend
pip install -r requirements.txt
```

### Environment Setup

```bash
export KEYCLOAK_ADMIN_TOKEN="your-admin-token"
export KEYCLOAK_URL="https://keycloak.atlan.com"
```

### Resolution Steps

#### Option 1: Clean up by externalId (Recommended for this case)

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d
```

#### Option 2: Clean up by group name

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --group grpAtlanProdWorkflowAdmin
```

#### Option 3: Preview changes first (Dry Run)

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d \
    --dry-run
```

### Verification

After running the cleanup, verify success:

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check
```

### Customer Action

Once cleanup is complete, the customer should:

1. Navigate to Okta admin console
2. Go to Applications → Atlan → Push Groups
3. Attempt to push `grpAtlanProdWorkflowAdmin` again
4. The push should now succeed

## Expected Results

✅ Stale `externalId` mapping removed from Keycloak database  
✅ Okta Push Groups operation succeeds for `grpAtlanProdWorkflowAdmin`  
✅ Customer can manage Workflow Admins via Okta  
✅ Audit trail created for compliance  

## Additional Features

### Health Check

Run proactive health checks to detect issues before they cause failures:

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check
```

### Batch Cleanup

Clean up all stale mappings for a tenant:

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --all
```

### JSON Output

Get structured output for automation:

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --group grpAtlanProdWorkflowAdmin \
    --output-json
```

## Relationship to LINTEST-423

LINTEST-439 is a recurrence of the same issue that was addressed in LINTEST-423:
- Same tenant (apex.atlan.com)
- Same group (grpAtlanProdWorkflowAdmin)
- Same error pattern (stale externalId mapping)
- Same externalId (2ea7c8f7-7506-4b71-a53c-f307aedb647d)

The recurrence suggests that while this fix addresses the symptom (cleaning up stale mappings), the root cause (creation of stale mappings) may require a deeper product-level fix in Keycloak's SCIM implementation.

## Prevention

### Short-Term

- Support team can use the cleanup utility to quickly resolve issues
- Health checks can proactively detect stale mappings
- Documented runbook for common scenarios

### Medium-Term (Recommended)

1. **Automatic Integration**: Integrate cleanup logic into Keycloak's SCIM endpoint
2. **Periodic Cleanup Job**: Schedule daily cleanup job for all tenants
3. **Enhanced Monitoring**: Set up alerts for stale mapping detection

### Long-Term (Product Fix)

1. **Prevent Stale Mappings**: Modify Keycloak to properly clean up externalId mappings when groups are deleted
2. **Cascading Deletes**: Ensure that when a group is deleted, all associated metadata is removed
3. **SCIM Spec Compliance**: Review Keycloak's SCIM implementation for full RFC 7644 compliance

## Documentation

- **Backend Module README**: [backend/README.md](backend/README.md)
- **LINTEST-423 Fix Documentation**: [docs/LINTEST-423-fix-documentation.md](docs/LINTEST-423-fix-documentation.md)
- **LINTEST-439 Application**: [docs/LINTEST-439-fix-application.md](docs/LINTEST-439-fix-application.md)

## Files Changed

```
backend/
├── __init__.py                           (NEW)
├── README.md                             (NEW - updated for LINTEST-439)
├── requirements.txt                      (NEW)
├── keycloak/
│   ├── __init__.py                       (NEW)
│   └── mappings.py                       (NEW - updated for LINTEST-439)
├── scim/
│   ├── __init__.py                       (NEW)
│   └── push_groups.py                    (NEW - updated for LINTEST-439)
└── utils/
    ├── __init__.py                       (NEW)
    └── cleanup_stale_external_ids.py     (NEW - updated for LINTEST-439)

docs/
├── LINTEST-423-fix-documentation.md      (NEW - updated for LINTEST-439)
└── LINTEST-439-fix-application.md        (NEW)
```

## Support

For issues or questions:
- **Platform Team**: platform-team@atlan.com
- **On-Call**: PagerDuty escalation
- **Documentation**: Update relevant files with learnings

## Next Steps

1. **Deploy**: Deploy the backend modules to production environment
2. **Execute**: Run the cleanup utility for apex.atlan.com
3. **Verify**: Confirm customer can successfully push groups from Okta
4. **Monitor**: Set up monitoring for this tenant to detect future occurrences
5. **Plan**: Schedule work to integrate automatic cleanup into SCIM workflow
