# LINTEST-439: Application of Stale ExternalId Fix

## Overview

This document describes the application of the stale externalId cleanup fix to resolve LINTEST-439, which is a recurrence of the same issue previously addressed in LINTEST-423.

## Issue Details

**Ticket**: LINTEST-439  
**Title**: Okta Push Groups: stale externalId / orphaned mapping for grpAtlanProdWorkflowAdmin (apex) (copy) Test 2 (copy) (copy)  
**Tenant**: https://apex.atlan.com/  
**Affected Group**: grpAtlanProdWorkflowAdmin  
**ExternalId**: 2ea7c8f7-7506-4b71-a53c-f307aedb647d  

### Error Message

```
Failed on 01-23-2026 05:57:01PM UTC: Unable to update Group Push mapping target App group 
`grpAtlanProdWorkflowAdmin`: Error while trying to get the group `grpAtlanProdWorkflowAdmin` 
with the externalId `2ea7c8f7-7506-4b71-a53c-f307aedb647d` and id 
`com.saasure.db.dto.platform.entity.AppGroup@4091a703[status=ACTIVE,name=grpAtlanProdWorkflowAdmin,
description=<null>,externalId=2ea7c8f7-7506-4b71-a53c-f307aedb647d,appInstanceId=0oa1poiu1n2RPznuC358,
userGroupId=00g1seoy92p4ooqqf358,oktaMastered=true,pushed=false,changeStatus=<null>,data=<null>,
objectClass=]`
```

## Relationship to LINTEST-423

LINTEST-439 is the same issue as LINTEST-423:
- Same tenant (apex.atlan.com)
- Same group (grpAtlanProdWorkflowAdmin)
- Same error pattern (stale externalId mapping)
- Same externalId (2ea7c8f7-7506-4b71-a53c-f307aedb647d)

The fix implemented for LINTEST-423 has been applied to this branch to resolve LINTEST-439.

## Solution Applied

### 1. Cherry-picked LINTEST-423 Fix

The complete fix from LINTEST-423 (commit `0fbb4643c9`) has been cherry-picked into the LINTEST-439 branch. This includes:

- **backend/scim/push_groups.py**: SCIM group push handler with automatic stale mapping cleanup
- **backend/keycloak/mappings.py**: Keycloak mapping client for externalId management
- **backend/utils/cleanup_stale_external_ids.py**: Command-line cleanup utility
- **backend/README.md**: Comprehensive documentation
- **docs/LINTEST-423-fix-documentation.md**: Detailed fix documentation

### 2. Updated Documentation

Documentation has been updated to reference both LINTEST-423 and LINTEST-439, acknowledging that this is a recurring issue that may affect the same tenant/group multiple times.

## Resolution Steps for apex.atlan.com

To resolve this specific instance of the issue, follow these steps:

### Step 1: Set Environment Variables

```bash
export KEYCLOAK_ADMIN_TOKEN="your-admin-token"
export KEYCLOAK_URL="https://keycloak.atlan.com"
```

### Step 2: Run Dry-Run to Preview Changes

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d \
    --dry-run
```

### Step 3: Execute Cleanup

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d
```

### Step 4: Verify Success

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check
```

### Step 5: Customer Retry

After successful cleanup:
1. Customer navigates to Okta admin console
2. Goes to Applications → Atlan → Push Groups
3. Attempts to push `grpAtlanProdWorkflowAdmin` again
4. Push should now succeed

## Why This Issue Recurred

The recurrence of this issue (same tenant, same group) suggests:

1. **Root Cause Not Fully Addressed**: While the cleanup utility fixes the symptom, the underlying issue that creates stale mappings may still exist in the SCIM/Keycloak workflow.

2. **Manual Intervention Required**: The cleanup is currently a manual process. Without automatic detection and cleanup integrated into the SCIM push workflow, the issue can recur.

3. **Group Lifecycle Events**: Each time the group is deleted/recreated or unlinked/re-linked in Okta, there's a potential for creating new stale mappings.

## Prevention for Future Occurrences

### Short-Term (Already Implemented)

1. **Manual Cleanup Utility**: Support team can quickly resolve issues using the cleanup script
2. **Health Checks**: Proactive detection of stale mappings before they cause push failures
3. **Documentation**: Clear runbook for support team to follow

### Medium-Term (Recommended)

1. **Automatic Integration**: Integrate the automatic cleanup logic into Keycloak's SCIM endpoint
   - Modify Keycloak's group push handler to detect and clean stale mappings
   - Ensure cleanup happens automatically before push operations

2. **Periodic Cleanup Job**: Schedule daily cleanup job for all tenants
   ```bash
   # Cron job to run daily at 2 AM
   0 2 * * * /usr/bin/python3 /path/to/backend/utils/cleanup_stale_external_ids.py \
       --tenant apex.atlan.com \
       --all \
       --output-json >> /var/log/keycloak-cleanup.log
   ```

3. **Enhanced Monitoring**: Set up alerts for stale mapping detection
   - Alert when health checks find issues
   - Track frequency of manual cleanups
   - Identify tenants with recurring problems

### Long-Term (Product Fix)

1. **Prevent Stale Mappings**: Modify Keycloak to properly clean up externalId mappings when groups are deleted
   
2. **Cascading Deletes**: Ensure that when a group is deleted, all associated metadata (including externalId attributes) are also removed

3. **SCIM Spec Compliance**: Review Keycloak's SCIM implementation for compliance with RFC 7644, particularly around resource lifecycle management

## Testing and Validation

### Test Scenarios

1. **Basic Cleanup**:
   - Verify the cleanup utility successfully removes the stale externalId
   - Confirm Okta push succeeds after cleanup

2. **Idempotency**:
   - Run cleanup multiple times
   - Verify no errors when mapping doesn't exist

3. **Edge Cases**:
   - Group doesn't exist in Keycloak
   - Multiple mappings with same externalId
   - ExternalId doesn't exist in database

### Validation Checklist

- [ ] Cleanup utility runs without errors
- [ ] Stale mapping is removed from Keycloak database
- [ ] Health check shows no issues after cleanup
- [ ] Customer can successfully push group from Okta
- [ ] Audit log entry created for cleanup operation
- [ ] No side effects on other groups or tenants

## Rollout

### Phase 1: Immediate Fix (apex.atlan.com)

1. Deploy backend modules to production
2. Run cleanup for the affected group
3. Verify customer success
4. Monitor for 24 hours

### Phase 2: Preventive Measures

1. Set up periodic health checks for apex.atlan.com
2. Create alerts for stale mapping detection
3. Document in runbook for support team
4. Train support team on cleanup utility

### Phase 3: Product Integration

1. Integrate automatic cleanup into SCIM workflow
2. Deploy to staging environment
3. Test with multiple tenants
4. Deploy to production with monitoring

## Monitoring

### Metrics to Track

- **Group Push Success Rate**: Should be 100% after cleanup
- **Cleanup Operations**: Track frequency (should decrease over time with automatic integration)
- **Health Check Failures**: Alert on new stale mappings
- **Customer Tickets**: Monitor for similar issues on other tenants

### Dashboard

Recommended dashboard panels:
1. Group push success/failure rate by tenant
2. Stale mapping cleanup operations over time
3. Health check status for all tenants
4. Top groups/tenants with mapping issues

## References

- **LINTEST-423**: Original fix implementation
- **LINTEST-439**: Current issue (this document)
- **Backend README**: [/backend/README.md](../backend/README.md)
- **LINTEST-423 Documentation**: [LINTEST-423-fix-documentation.md](./LINTEST-423-fix-documentation.md)

## Support

For issues or questions:
- **Platform Team**: platform-team@atlan.com
- **On-Call**: PagerDuty escalation
- **Documentation Updates**: Submit PR to this file

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-02-12 | Applied LINTEST-423 fix to LINTEST-439 branch | Cursor Agent |
| 2026-02-12 | Created LINTEST-439 application documentation | Cursor Agent |
