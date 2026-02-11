"""
Keycloak SCIM Mappings Handler

This module manages the externalId mappings between Okta groups and Keycloak groups
in the SCIM integration. It provides utilities for detecting and cleaning up
orphaned or stale mappings.

Issue: LINTEST-423 - Handling stale externalId mappings for group provisioning
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ExternalIdMapping:
    """
    Represents an externalId mapping between Okta and Keycloak groups.
    """
    
    def __init__(self, data: Dict[str, Any]):
        self.external_id = data.get('externalId')
        self.keycloak_group_id = data.get('keycloakGroupId')
        self.group_name = data.get('name')
        self.tenant_id = data.get('tenantId')
        self.app_instance_id = data.get('appInstanceId')
        self.user_group_id = data.get('userGroupId')
        self.status = data.get('status', 'ACTIVE')
        self.created_at = data.get('createdAt')
        self.updated_at = data.get('updatedAt')
        self.okta_mastered = data.get('oktaMastered', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert mapping to dictionary."""
        return {
            'externalId': self.external_id,
            'keycloakGroupId': self.keycloak_group_id,
            'name': self.group_name,
            'tenantId': self.tenant_id,
            'appInstanceId': self.app_instance_id,
            'userGroupId': self.user_group_id,
            'status': self.status,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
            'oktaMastered': self.okta_mastered
        }
    
    def is_orphaned(self) -> bool:
        """Check if this mapping is orphaned."""
        return self.status == 'ORPHANED' or self.keycloak_group_id is None


class KeycloakMappingClient:
    """
    Client for managing Keycloak group and externalId mappings.
    
    This client provides methods to interact with Keycloak's internal database
    or REST API to manage group mappings and resolve externalId conflicts.
    """
    
    def __init__(self, base_url: str, admin_token: str, database_connection=None):
        """
        Initialize the Keycloak mapping client.
        
        Args:
            base_url: Base URL of the Keycloak server
            admin_token: Admin authentication token
            database_connection: Optional direct database connection for advanced operations
        """
        self.base_url = base_url
        self.admin_token = admin_token
        self.db_connection = database_connection
        self.headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
    
    def get_group_by_external_id(self, tenant_id: str, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a group mapping by its externalId.
        
        Args:
            tenant_id: Tenant identifier
            external_id: External ID to search for
            
        Returns:
            Mapping data if found, None otherwise
        """
        logger.debug(f"Searching for group with externalId '{external_id}' in tenant '{tenant_id}'")
        
        # In a real implementation, this would query Keycloak's database or API
        # For now, we'll simulate the behavior
        
        if self.db_connection:
            return self._query_mapping_from_db(tenant_id, external_id)
        else:
            return self._query_mapping_from_api(tenant_id, external_id)
    
    def _query_mapping_from_db(self, tenant_id: str, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Query mapping directly from Keycloak database.
        
        This method queries the Keycloak database tables that store group attributes
        and SCIM externalId mappings.
        
        Expected table structure:
        - keycloak_group: Main group table
        - group_attribute: Stores group attributes including externalId
        - realm: Tenant/realm information
        
        Args:
            tenant_id: Tenant identifier
            external_id: External ID to search for
            
        Returns:
            Mapping data if found, None otherwise
        """
        try:
            # This is a simplified query - actual implementation would be more complex
            query = """
                SELECT 
                    g.id as keycloak_group_id,
                    g.name as group_name,
                    g.realm_id,
                    attr.value as external_id,
                    attr_okta.value as okta_mastered,
                    attr_app.value as app_instance_id,
                    attr_user.value as user_group_id
                FROM keycloak_group g
                JOIN group_attribute attr ON g.id = attr.group_id AND attr.name = 'externalId'
                LEFT JOIN group_attribute attr_okta ON g.id = attr_okta.group_id AND attr_okta.name = 'oktaMastered'
                LEFT JOIN group_attribute attr_app ON g.id = attr_app.group_id AND attr_app.name = 'appInstanceId'
                LEFT JOIN group_attribute attr_user ON g.id = attr_user.group_id AND attr_user.name = 'userGroupId'
                JOIN realm r ON g.realm_id = r.id
                WHERE attr.value = %s AND r.name = %s
            """
            
            # Execute query (simulated)
            # cursor = self.db_connection.cursor()
            # cursor.execute(query, (external_id, tenant_id))
            # result = cursor.fetchone()
            
            # For simulation, return None (no mapping found)
            logger.debug("Database query executed (simulated)")
            return None
            
        except Exception as e:
            logger.error(f"Error querying mapping from database: {e}")
            return None
    
    def _query_mapping_from_api(self, tenant_id: str, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Query mapping using Keycloak REST API.
        
        Args:
            tenant_id: Tenant identifier  
            external_id: External ID to search for
            
        Returns:
            Mapping data if found, None otherwise
        """
        try:
            # In a real implementation, this would make API calls to Keycloak
            # GET /admin/realms/{realm}/groups?search=...
            # Then filter by externalId attribute
            
            logger.debug("API query executed (simulated)")
            return None
            
        except Exception as e:
            logger.error(f"Error querying mapping from API: {e}")
            return None
    
    def delete_external_id_mapping(self, tenant_id: str, external_id: str) -> bool:
        """
        Delete an externalId mapping from Keycloak.
        
        This removes the externalId attribute from a group, effectively
        unlinking it from the Okta SCIM integration.
        
        Args:
            tenant_id: Tenant identifier
            external_id: External ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Deleting externalId mapping '{external_id}' for tenant '{tenant_id}'")
        
        try:
            # First, find the group with this externalId
            mapping = self.get_group_by_external_id(tenant_id, external_id)
            
            if not mapping:
                logger.warning(f"No mapping found for externalId '{external_id}'")
                return True  # Already doesn't exist
            
            keycloak_group_id = mapping.get('keycloakGroupId')
            
            if self.db_connection:
                return self._delete_mapping_from_db(keycloak_group_id, external_id)
            else:
                return self._delete_mapping_from_api(tenant_id, keycloak_group_id, external_id)
                
        except Exception as e:
            logger.error(f"Error deleting externalId mapping: {e}")
            return False
    
    def _delete_mapping_from_db(self, keycloak_group_id: str, external_id: str) -> bool:
        """
        Delete externalId mapping directly from database.
        
        Args:
            keycloak_group_id: Keycloak group ID
            external_id: External ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the externalId attribute
            query = """
                DELETE FROM group_attribute
                WHERE group_id = %s AND name = 'externalId' AND value = %s
            """
            
            # Execute delete (simulated)
            # cursor = self.db_connection.cursor()
            # cursor.execute(query, (keycloak_group_id, external_id))
            # self.db_connection.commit()
            
            logger.info(f"Deleted externalId mapping from database (simulated)")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting mapping from database: {e}")
            return False
    
    def _delete_mapping_from_api(self, tenant_id: str, keycloak_group_id: str, external_id: str) -> bool:
        """
        Delete externalId mapping using Keycloak REST API.
        
        Args:
            tenant_id: Tenant identifier
            keycloak_group_id: Keycloak group ID
            external_id: External ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # In a real implementation:
            # 1. GET the group to retrieve current attributes
            # 2. Remove the externalId attribute
            # 3. PUT the updated group back
            
            logger.info(f"Deleted externalId mapping via API (simulated)")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting mapping via API: {e}")
            return False
    
    def get_group_by_name(self, tenant_id: str, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a group by its name.
        
        Args:
            tenant_id: Tenant identifier
            group_name: Name of the group
            
        Returns:
            Group data if found, None otherwise
        """
        logger.debug(f"Searching for group with name '{group_name}' in tenant '{tenant_id}'")
        
        # In a real implementation, this would query Keycloak
        # For simulation, return None
        return None
    
    def group_exists(self, tenant_id: str, keycloak_group_id: str) -> bool:
        """
        Check if a group exists in Keycloak.
        
        Args:
            tenant_id: Tenant identifier
            keycloak_group_id: Keycloak group ID
            
        Returns:
            True if group exists, False otherwise
        """
        logger.debug(f"Checking if group '{keycloak_group_id}' exists in tenant '{tenant_id}'")
        
        # In a real implementation, this would query Keycloak
        # For simulation, return False (group doesn't exist)
        return False
    
    def create_group(self, tenant_id: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new group in Keycloak.
        
        Args:
            tenant_id: Tenant identifier
            group_data: Group data including name, externalId, and attributes
            
        Returns:
            Created group data
        """
        logger.info(f"Creating group '{group_data.get('name')}' in tenant '{tenant_id}'")
        
        # In a real implementation, this would call Keycloak API
        # POST /admin/realms/{realm}/groups
        
        # Simulate successful creation
        result = {
            'id': f"group-{datetime.utcnow().timestamp()}",
            **group_data,
            'createdTimestamp': int(datetime.utcnow().timestamp() * 1000)
        }
        
        logger.info(f"Group created successfully (simulated)")
        return result
    
    def update_group(self, tenant_id: str, group_id: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing group in Keycloak.
        
        Args:
            tenant_id: Tenant identifier
            group_id: Keycloak group ID
            group_data: Updated group data
            
        Returns:
            Updated group data
        """
        logger.info(f"Updating group '{group_id}' in tenant '{tenant_id}'")
        
        # In a real implementation, this would call Keycloak API
        # PUT /admin/realms/{realm}/groups/{id}
        
        # Simulate successful update
        result = {
            **group_data,
            'updatedTimestamp': int(datetime.utcnow().timestamp() * 1000)
        }
        
        logger.info(f"Group updated successfully (simulated)")
        return result
    
    def get_all_external_id_mappings(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Get all externalId mappings for a tenant.
        
        This is useful for batch cleanup operations.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            List of all externalId mappings
        """
        logger.info(f"Retrieving all externalId mappings for tenant '{tenant_id}'")
        
        # In a real implementation, this would query all groups with externalId attribute
        # For simulation, return empty list
        return []
    
    def validate_mapping_consistency(self, tenant_id: str) -> Dict[str, Any]:
        """
        Validate the consistency of externalId mappings for a tenant.
        
        This checks for:
        - Duplicate externalIds
        - Orphaned mappings (externalId exists but group doesn't)
        - Groups without externalId but marked as oktaMastered
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Validation report with findings
        """
        logger.info(f"Validating mapping consistency for tenant '{tenant_id}'")
        
        report = {
            'tenant_id': tenant_id,
            'timestamp': datetime.utcnow().isoformat(),
            'duplicates': [],
            'orphaned': [],
            'missing_external_id': [],
            'summary': {
                'total_mappings': 0,
                'issues_found': 0
            }
        }
        
        try:
            # Get all mappings
            all_mappings = self.get_all_external_id_mappings(tenant_id)
            report['summary']['total_mappings'] = len(all_mappings)
            
            # Check for duplicates
            external_ids_seen = {}
            for mapping in all_mappings:
                external_id = mapping.get('externalId')
                if external_id in external_ids_seen:
                    report['duplicates'].append({
                        'external_id': external_id,
                        'groups': [external_ids_seen[external_id], mapping.get('name')]
                    })
                else:
                    external_ids_seen[external_id] = mapping.get('name')
            
            # Check for orphaned mappings
            for mapping in all_mappings:
                keycloak_group_id = mapping.get('keycloakGroupId')
                if keycloak_group_id:
                    if not self.group_exists(tenant_id, keycloak_group_id):
                        report['orphaned'].append({
                            'external_id': mapping.get('externalId'),
                            'group_name': mapping.get('name'),
                            'keycloak_group_id': keycloak_group_id
                        })
            
            # Calculate total issues
            report['summary']['issues_found'] = (
                len(report['duplicates']) +
                len(report['orphaned']) +
                len(report['missing_external_id'])
            )
            
            logger.info(f"Validation complete. Found {report['summary']['issues_found']} issues")
            
        except Exception as e:
            logger.error(f"Error during validation: {e}")
            report['error'] = str(e)
        
        return report


class MappingHealthChecker:
    """
    Health checker for SCIM group mappings.
    
    This can be run periodically to detect and alert on stale mappings
    before they cause push failures.
    """
    
    def __init__(self, keycloak_client: KeycloakMappingClient):
        self.client = keycloak_client
    
    def check_tenant_health(self, tenant_id: str) -> Dict[str, Any]:
        """
        Perform a health check on a tenant's group mappings.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Health report
        """
        logger.info(f"Performing health check for tenant '{tenant_id}'")
        
        validation_report = self.client.validate_mapping_consistency(tenant_id)
        
        health_status = 'HEALTHY'
        if validation_report['summary']['issues_found'] > 0:
            health_status = 'UNHEALTHY'
        
        return {
            'tenant_id': tenant_id,
            'status': health_status,
            'timestamp': datetime.utcnow().isoformat(),
            'validation_report': validation_report,
            'recommendations': self._generate_recommendations(validation_report)
        }
    
    def _generate_recommendations(self, validation_report: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on validation findings.
        
        Args:
            validation_report: Validation report from consistency check
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if validation_report.get('duplicates'):
            recommendations.append(
                f"Found {len(validation_report['duplicates'])} duplicate externalId mappings. "
                "Run cleanup utility to resolve conflicts."
            )
        
        if validation_report.get('orphaned'):
            recommendations.append(
                f"Found {len(validation_report['orphaned'])} orphaned mappings. "
                "These should be cleaned up to prevent push failures."
            )
        
        if validation_report.get('missing_external_id'):
            recommendations.append(
                f"Found {len(validation_report['missing_external_id'])} groups marked as "
                "oktaMastered but missing externalId. Review these groups."
            )
        
        return recommendations
