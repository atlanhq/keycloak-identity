# LINTEST-423: Fix for Okta Push Groups Stale ExternalId Issue

## Issue Summary

**Ticket**: LINTEST-423  
**Tenant**: apex.atlan.com  
**Customer**: Flo Barot Jr  
**Affected Group**: grpAtlanProdWorkflowAdmin

### Problem

Customer was unable to push the `grpAtlanProdWorkflowAdmin` Okta group to Atlan via SCIM Push Groups. The error indicated a stale `externalId` mapping:

```
Failed on 01-23-2026 05:57:01PM UTC: Unable to update Group Push mapping target App group 
`grpAtlanProdWorkflowAdmin`: Error while trying to get the group `grpAtlanProdWorkflowAdmin` 
with the externalId `2ea7c8f7-7506-4b71-a53c-f307aedb647d`
```

### Root Cause

When Okta groups are:
1. Deleted and recreated
2. Unlinked and re-linked
3. SSO mappings are removed and re-added

The `externalId` mapping in Keycloak's database can become orphaned or stale. This occurs because:

- The Keycloak group may be deleted, but the `externalId` attribute mapping remains in the database
- The `externalId` references a group that no longer exists or has been recreated with a different internal ID
- Keycloak's SCIM endpoint cannot resolve the stale mapping, causing push operations to fail

### Previous Attempts (All Failed)

Customer and support team tried:
- ✗ Removing SSO group mapping in Atlan
- ✗ Creating an Atlan group with matching name
- ✗ Unlinking and re-linking the group from Okta using "Link Group"
- ✗ Multiple delete/recreate cycles

None of these UI-level operations cleared the orphaned `externalId` from Keycloak's database.

## Solution Implemented

### Architecture

The fix consists of three main components:

1. **SCIM Push Groups Handler** (`backend/scim/push_groups.py`)
   - Automatic detection of stale `externalId` mappings
   - Cleanup logic integrated into group push workflow
   - Audit logging of all cleanup operations

2. **Keycloak Mappings Client** (`backend/keycloak/mappings.py`)
   - Database/API interface for managing `externalId` mappings
   - Validation and consistency checking
   - Health monitoring capabilities

3. **Cleanup Utility** (`backend/utils/cleanup_stale_external_ids.py`)
   - Command-line tool for manual intervention
   - Support for single group, batch, or full tenant cleanup
   - Dry-run mode for safe previewing

### How It Works

#### Automatic Cleanup Flow

```
Okta Push Request
       ↓
Check for existing externalId mapping
       ↓
Is mapping stale? ← (Check if referenced group exists)
   ↓           ↓
  No          Yes
   ↓           ↓
Update     Cleanup stale mapping
Group          ↓
           Create audit log entry
                ↓
           Retry group push
                ↓
           Success
```

#### Stale Mapping Detection

A mapping is considered stale if ANY of the following are true:

1. **Name Mismatch**: Group name in mapping doesn't match Okta group name
2. **Missing Reference**: Keycloak group referenced by the mapping doesn't exist
3. **Orphaned Status**: Mapping is explicitly marked as `ORPHANED` in the database

### Implementation Details

#### Key Classes

**GroupPushHandler**
```python
class GroupPushHandler:
    def push_group(self, okta_group: Dict[str, Any]) -> Dict[str, Any]:
        # Step 1: Check for existing externalId mapping
        # Step 2: Detect if mapping is stale
        # Step 3: Clean up stale mapping if needed
        # Step 4: Push group (create or update)
```

**KeycloakMappingClient**
```python
class KeycloakMappingClient:
    def delete_external_id_mapping(self, tenant_id: str, external_id: str) -> bool:
        # Removes the orphaned externalId attribute from Keycloak database
        # Supports both direct DB access and REST API methods
```

**MappingHealthChecker**
```python
class MappingHealthChecker:
    def check_tenant_health(self, tenant_id: str) -> Dict[str, Any]:
        # Proactively detects:
        # - Duplicate externalIds
        # - Orphaned mappings
        # - Inconsistent state
```

## Usage for LINTEST-423

### Immediate Fix for apex.atlan.com

To resolve the immediate issue for the customer:

```bash
# Set environment variables
export KEYCLOAK_ADMIN_TOKEN="your-admin-token"
export KEYCLOAK_URL="https://keycloak.atlan.com"

# Clean up the stale mapping for grpAtlanProdWorkflowAdmin
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d

# Or by group name
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --group grpAtlanProdWorkflowAdmin
```

### Post-Cleanup Verification

After running the cleanup:

1. **Verify Cleanup Success**:
   ```bash
   python backend/utils/cleanup_stale_external_ids.py \
       --tenant apex.atlan.com \
       --health-check
   ```

2. **Customer Re-attempts Push**:
   - Customer goes to Okta admin console
   - Navigates to Applications → Atlan → Push Groups
   - Attempts to push `grpAtlanProdWorkflowAdmin` again
   - Should now succeed

3. **Monitor Audit Logs**:
   - Check audit logs for the cleanup operation
   - Verify new group push was successful
   - Confirm no errors in Keycloak logs

### Expected Outcomes

✓ Stale `externalId` mapping removed from Keycloak database  
✓ Okta Push Groups operation succeeds for `grpAtlanProdWorkflowAdmin`  
✓ Customer can manage Workflow Admins via Okta  
✓ Audit trail created for compliance  

## Prevention

### Automatic Detection and Cleanup

With this fix deployed, future occurrences are handled automatically:

1. **Group Push Workflow**: All group pushes now include stale mapping detection
2. **Automatic Cleanup**: Stale mappings are cleaned up before push attempts
3. **Audit Logging**: All cleanup operations are logged for tracking

### Proactive Monitoring

Set up periodic health checks:

```bash
# Add to cron - run daily at 2 AM
0 2 * * * /usr/bin/python3 /path/to/backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check \
    --output-json >> /var/log/keycloak-health-checks.log
```

### Best Practices for Support Team

When encountering similar issues:

1. **First Response**: Run health check
   ```bash
   python backend/utils/cleanup_stale_external_ids.py \
       --tenant <tenant-id> \
       --health-check
   ```

2. **If Stale Mappings Found**: Use dry-run to preview
   ```bash
   python backend/utils/cleanup_stale_external_ids.py \
       --tenant <tenant-id> \
       --group <group-name> \
       --dry-run
   ```

3. **Execute Cleanup**: Remove the `--dry-run` flag
   ```bash
   python backend/utils/cleanup_stale_external_ids.py \
       --tenant <tenant-id> \
       --group <group-name>
   ```

4. **Verify**: Run health check again to confirm

## Testing

### Manual Testing

1. **Test Stale Mapping Detection**:
   ```python
   from backend.scim.push_groups import GroupPushHandler
   from backend.keycloak.mappings import KeycloakMappingClient
   
   client = KeycloakMappingClient(
       base_url='https://keycloak-test.atlan.com',
       admin_token='test-token'
   )
   
   handler = GroupPushHandler(client, 'test-tenant')
   
   # Create a stale mapping scenario
   # ... test code ...
   ```

2. **Test Cleanup Utility**:
   ```bash
   # Use test tenant
   python backend/utils/cleanup_stale_external_ids.py \
       --tenant test.atlan.com \
       --group testGroup \
       --dry-run
   ```

### Automated Testing

Unit tests should cover:
- Stale mapping detection logic
- Cleanup operation success/failure scenarios
- Error handling and edge cases
- Audit logging

## Rollout Plan

### Phase 1: apex.atlan.com (Immediate)

1. Deploy backend modules to production
2. Run cleanup utility for apex.atlan.com
3. Verify customer can push groups successfully
4. Monitor for 24 hours

### Phase 2: Other Affected Tenants

Based on historical tickets, run cleanup for:
- Tide tenant (similar externalId issues)
- Prima tenant (atlan_roleguest issues)
- Any other tenants with SCIM push failures

### Phase 3: Production Integration

1. Integrate automatic cleanup into production SCIM workflow
2. Deploy health check monitoring
3. Set up alerting for mapping issues
4. Update runbooks for support team

## Monitoring and Alerting

### Metrics to Track

1. **Group Push Success Rate**: Should increase after deployment
2. **Stale Mapping Cleanup Operations**: Track frequency and patterns
3. **Health Check Failures**: Alert when issues are detected
4. **Audit Log Volume**: Monitor for unusual cleanup activity

### Recommended Alerts

```
Alert: Stale Mapping Detected
Condition: Health check finds orphaned mappings
Action: Automatic cleanup + notify support team

Alert: Group Push Failure
Condition: Group push fails after cleanup attempt
Action: Escalate to engineering team

Alert: High Cleanup Volume
Condition: >10 cleanups in 1 hour for a tenant
Action: Investigate root cause
```

## Known Limitations

1. **Database Access**: Direct database access provides faster operations but requires additional permissions
2. **API Rate Limits**: Using Keycloak REST API may be subject to rate limiting for large batch operations
3. **Concurrent Operations**: Concurrent group pushes for the same group may race during cleanup
4. **Historical Data**: Cannot prevent stale mappings that already exist; can only clean them up

## Future Enhancements

### Short Term

- [ ] Add unit tests for all modules
- [ ] Create integration tests with test Keycloak instance
- [ ] Add metrics/prometheus integration
- [ ] Build web dashboard for viewing mappings

### Medium Term

- [ ] Prevent stale mappings at the source (Keycloak modification)
- [ ] Automatic periodic cleanup background job
- [ ] Integration with Okta API for validation
- [ ] Enhanced audit logging with external log aggregation

### Long Term

- [ ] Root cause fix in Keycloak SCIM implementation
- [ ] Contribute fix back to Keycloak open source project
- [ ] Replace manual SSO group management with fully automated system

## Related Documentation

- [Backend Module README](../backend/README.md)
- [SCIM Push Groups Handler](../backend/scim/push_groups.py)
- [Keycloak Mappings Client](../backend/keycloak/mappings.py)
- [Cleanup Utility](../backend/utils/cleanup_stale_external_ids.py)

## References

- **Linear Issue**: [LINTEST-423](https://linear.app/issue/LINTEST-423)
- **Keycloak SCIM Spec**: [RFC 7644](https://tools.ietf.org/html/rfc7644)
- **Okta SCIM Documentation**: [Okta SCIM Guide](https://developer.okta.com/docs/guides/scim-provisioning-integration-overview/)

## Support Contact

For issues, questions, or enhancements:
- **Platform Team**: platform-team@atlan.com
- **On-Call**: Use PagerDuty for urgent issues
- **Documentation**: Update this file with learnings and improvements
