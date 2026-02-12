# Atlan Backend - SCIM Integration Modules

This directory contains backend modules for handling SCIM group provisioning from Okta to Keycloak/Atlan, with specific focus on resolving stale `externalId` mapping issues.

## Issue Resolution: LINTEST-423 / LINTEST-439

**Problem**: Okta Push Groups failing with stale `externalId` errors when trying to push groups to Atlan via SCIM.

**Root Cause**: When groups are deleted and recreated, or when SSO group mappings are removed and re-added, orphaned `externalId` mappings can remain in Keycloak's database. These stale mappings prevent new group pushes from succeeding.

**Solution**: This implementation provides:
1. Automatic detection and cleanup of stale `externalId` mappings during group push operations
2. A command-line utility for manual cleanup by support teams
3. Health checking capabilities to proactively detect mapping issues
4. Audit logging of all cleanup operations

## Directory Structure

```
backend/
├── scim/
│   ├── __init__.py
│   └── push_groups.py          # SCIM group push handler with stale mapping cleanup
├── keycloak/
│   ├── __init__.py
│   └── mappings.py              # Keycloak mapping client and validation
├── utils/
│   ├── __init__.py
│   └── cleanup_stale_external_ids.py  # Command-line cleanup utility
├── __init__.py
├── requirements.txt
└── README.md
```

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Usage

### 1. Automatic Cleanup During Group Push

The `GroupPushHandler` automatically detects and cleans up stale mappings:

```python
from backend.scim.push_groups import GroupPushHandler
from backend.keycloak.mappings import KeycloakMappingClient

# Initialize clients
keycloak_client = KeycloakMappingClient(
    base_url='https://keycloak.atlan.com',
    admin_token='YOUR_ADMIN_TOKEN'
)

# Create handler
handler = GroupPushHandler(keycloak_client, tenant_id='apex.atlan.com')

# Push group (automatically cleans up stale mappings)
okta_group = {
    'name': 'grpAtlanProdWorkflowAdmin',
    'externalId': '2ea7c8f7-7506-4b71-a53c-f307aedb647d',
    'appInstanceId': '0oa1poiu1n2RPznuC358',
    'userGroupId': '00g1seoy92p4ooqqf358'
}

result = handler.push_group(okta_group)
print(f"Push result: {result}")
```

### 2. Manual Cleanup Using Command-Line Utility

For the specific issue in LINTEST-423:

```bash
# Clean up the problematic group for apex.atlan.com
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --group grpAtlanProdWorkflowAdmin

# Or by externalId
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d
```

#### Command-Line Options

```bash
# Preview changes without applying (dry run)
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --group grpAtlanProdWorkflowAdmin \
    --dry-run

# Clean up all stale mappings for a tenant
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --all

# Run health check
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check

# Get JSON output for automation
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --group grpAtlanProdWorkflowAdmin \
    --output-json
```

### 3. Batch Cleanup

For cleaning up multiple stale mappings:

```python
from backend.scim.push_groups import batch_cleanup_stale_mappings
from backend.keycloak.mappings import KeycloakMappingClient

keycloak_client = KeycloakMappingClient(
    base_url='https://keycloak.atlan.com',
    admin_token='YOUR_ADMIN_TOKEN'
)

# Clean up specific groups
result = batch_cleanup_stale_mappings(
    keycloak_client,
    tenant_id='apex.atlan.com',
    group_names=['grpAtlanProdWorkflowAdmin']
)

print(f"Cleaned up: {len(result['cleaned_up'])} mappings")
print(f"Failed: {len(result['failed'])} mappings")
```

### 4. Health Checking

Proactively detect mapping issues:

```python
from backend.keycloak.mappings import KeycloakMappingClient, MappingHealthChecker

keycloak_client = KeycloakMappingClient(
    base_url='https://keycloak.atlan.com',
    admin_token='YOUR_ADMIN_TOKEN'
)

checker = MappingHealthChecker(keycloak_client)
report = checker.check_tenant_health('apex.atlan.com')

print(f"Health Status: {report['status']}")
print(f"Issues Found: {report['validation_report']['summary']['issues_found']}")

if report['recommendations']:
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
```

## Key Features

### Stale Mapping Detection

A mapping is considered stale if:
- The group name doesn't match the current Okta group
- The referenced Keycloak group no longer exists
- The mapping is marked as ORPHANED in the database

### Automatic Cleanup

When a stale mapping is detected during a group push:
1. The system logs the stale mapping details
2. Attempts to delete the orphaned `externalId` mapping
3. Creates an audit log entry for compliance
4. Proceeds with the group push operation

### Safety Features

- **Dry Run Mode**: Preview changes before applying them
- **Audit Logging**: All cleanup operations are logged with full context
- **Error Handling**: Graceful failure with detailed error messages
- **Validation**: Consistency checks before and after operations

## Troubleshooting

### Issue: Group push still fails after cleanup

**Solution**: Verify the cleanup was successful and the externalId was actually removed:

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check \
    --verbose
```

### Issue: Cannot find group by name

**Solution**: The group may have been deleted. Clean up by externalId instead:

```bash
python backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d
```

### Issue: Permission denied errors

**Solution**: Ensure the admin token has sufficient permissions:
- `manage-groups` role in the target realm
- `view-users` role for validation operations

## API Reference

### GroupPushHandler

Main handler for SCIM group push operations.

**Methods**:
- `push_group(okta_group)`: Push a group with automatic stale mapping cleanup
- `_check_external_id_mapping(external_id)`: Check for existing mappings
- `_is_stale_mapping(existing_mapping, okta_group)`: Determine if mapping is stale
- `_cleanup_stale_mapping(mapping)`: Clean up a stale mapping

### KeycloakMappingClient

Client for interacting with Keycloak group mappings.

**Methods**:
- `get_group_by_external_id(tenant_id, external_id)`: Get mapping by externalId
- `delete_external_id_mapping(tenant_id, external_id)`: Delete a mapping
- `get_all_external_id_mappings(tenant_id)`: Get all mappings for a tenant
- `validate_mapping_consistency(tenant_id)`: Run consistency validation

### MappingHealthChecker

Health checking for SCIM group mappings.

**Methods**:
- `check_tenant_health(tenant_id)`: Perform health check
- `_generate_recommendations(validation_report)`: Generate actionable recommendations

## Production Deployment

### Environment Variables

```bash
export KEYCLOAK_ADMIN_TOKEN="your-admin-token"
export KEYCLOAK_URL="https://keycloak.atlan.com"
```

### Database Access (Optional)

For direct database access (faster than API):

```python
import psycopg2

db_connection = psycopg2.connect(
    host="keycloak-db.internal",
    database="keycloak",
    user="keycloak_admin",
    password="secure_password"
)

keycloak_client = KeycloakMappingClient(
    base_url='https://keycloak.atlan.com',
    admin_token='YOUR_ADMIN_TOKEN',
    database_connection=db_connection
)
```

### Monitoring

Set up monitoring for:
- Group push failures (should decrease after deployment)
- Stale mapping cleanup operations (audit logs)
- Health check results (run periodically)

### Scheduled Health Checks

Recommended: Run daily health checks for all tenants:

```bash
# Add to cron
0 2 * * * /usr/bin/python3 /path/to/backend/utils/cleanup_stale_external_ids.py \
    --tenant apex.atlan.com \
    --health-check \
    --output-json >> /var/log/keycloak-health-checks.log
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review audit logs for cleanup operations
3. Run health check to identify issues
4. Contact the platform team with the health check report

## Related Issues

- **LINTEST-423**: Okta Push Groups stale externalId / orphaned mapping (apex)
- Similar issues in other tenants (Tide, Prima) following the same pattern

## Future Improvements

1. **Automatic Periodic Cleanup**: Background job to clean up stale mappings
2. **Okta Integration**: Direct Okta API integration for validation
3. **Dashboard**: Web UI for viewing and managing mappings
4. **Alerting**: Automatic alerts when stale mappings are detected
5. **Prevention**: Logic to prevent stale mappings from occurring in the first place
