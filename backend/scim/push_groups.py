"""
SCIM Push Groups Handler for Okta to Atlan Integration

This module handles the SCIM group provisioning from Okta to Atlan/Keycloak,
with specific handling for stale externalId mappings that can cause push failures.

Issue: LINTEST-423 - Okta Push Groups: stale externalId / orphaned mapping
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ExternalIdConflictError(Exception):
    """Raised when an externalId conflict is detected."""
    pass


class GroupPushHandler:
    """
    Handles SCIM group push operations from Okta to Keycloak/Atlan.
    
    This handler includes logic to detect and resolve stale externalId mappings
    that can occur when groups are deleted and recreated, or when mappings become
    orphaned in the database.
    """
    
    def __init__(self, keycloak_client, tenant_id: str):
        """
        Initialize the GroupPushHandler.
        
        Args:
            keycloak_client: Client for interacting with Keycloak API
            tenant_id: Tenant identifier (e.g., 'apex.atlan.com')
        """
        self.keycloak_client = keycloak_client
        self.tenant_id = tenant_id
        self.retry_count = 3
    
    def push_group(self, okta_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push a group from Okta to Keycloak/Atlan via SCIM.
        
        This method includes automatic detection and cleanup of stale externalId
        mappings to prevent push failures.
        
        Args:
            okta_group: Dictionary containing Okta group data
                - name: Group name
                - externalId: External identifier from Okta
                - appInstanceId: Okta app instance ID
                - userGroupId: Okta user group ID
                
        Returns:
            Dictionary with push result
            
        Raises:
            ExternalIdConflictError: If externalId conflict cannot be resolved
        """
        group_name = okta_group.get('name')
        external_id = okta_group.get('externalId')
        
        logger.info(f"Attempting to push group '{group_name}' with externalId '{external_id}' to tenant '{self.tenant_id}'")
        
        # Step 1: Check for existing group with same externalId
        existing_mapping = self._check_external_id_mapping(external_id)
        
        if existing_mapping:
            # Check if the existing mapping is stale
            if self._is_stale_mapping(existing_mapping, okta_group):
                logger.warning(f"Detected stale externalId mapping for '{group_name}': {existing_mapping}")
                
                # Attempt to clean up the stale mapping
                cleanup_result = self._cleanup_stale_mapping(existing_mapping)
                
                if not cleanup_result['success']:
                    raise ExternalIdConflictError(
                        f"Failed to cleanup stale externalId mapping for group '{group_name}': {cleanup_result['error']}"
                    )
                
                logger.info(f"Successfully cleaned up stale mapping for '{group_name}'")
        
        # Step 2: Check if group exists in Keycloak by name
        existing_group = self._get_group_by_name(group_name)
        
        if existing_group:
            # Update existing group
            return self._update_group(existing_group, okta_group)
        else:
            # Create new group
            return self._create_group(okta_group)
    
    def _check_external_id_mapping(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if an externalId mapping already exists in Keycloak.
        
        Args:
            external_id: The external ID to check
            
        Returns:
            Existing mapping data if found, None otherwise
        """
        try:
            return self.keycloak_client.get_group_by_external_id(
                self.tenant_id, 
                external_id
            )
        except Exception as e:
            logger.error(f"Error checking externalId mapping: {e}")
            return None
    
    def _is_stale_mapping(self, existing_mapping: Dict[str, Any], okta_group: Dict[str, Any]) -> bool:
        """
        Determine if an existing mapping is stale.
        
        A mapping is considered stale if:
        1. The group name doesn't match the current Okta group
        2. The Keycloak group referenced no longer exists
        3. The mapping metadata indicates it's orphaned
        
        Args:
            existing_mapping: The existing mapping data from Keycloak
            okta_group: The current Okta group data
            
        Returns:
            True if mapping is stale, False otherwise
        """
        # Check if group names match
        if existing_mapping.get('name') != okta_group.get('name'):
            logger.debug(f"Group name mismatch: existing='{existing_mapping.get('name')}', okta='{okta_group.get('name')}'")
            return True
        
        # Check if the referenced Keycloak group exists
        keycloak_group_id = existing_mapping.get('keycloakGroupId')
        if keycloak_group_id:
            try:
                group_exists = self.keycloak_client.group_exists(
                    self.tenant_id,
                    keycloak_group_id
                )
                if not group_exists:
                    logger.debug(f"Referenced Keycloak group {keycloak_group_id} no longer exists")
                    return True
            except Exception as e:
                logger.error(f"Error checking group existence: {e}")
                return True
        
        # Check if the mapping is marked as orphaned
        if existing_mapping.get('status') == 'ORPHANED':
            logger.debug("Mapping is marked as ORPHANED")
            return True
        
        return False
    
    def _cleanup_stale_mapping(self, mapping: Dict[str, Any]) -> Dict[str, bool]:
        """
        Clean up a stale externalId mapping.
        
        This removes the orphaned mapping from Keycloak's database to allow
        a fresh group push to succeed.
        
        Args:
            mapping: The stale mapping data
            
        Returns:
            Dictionary with 'success' boolean and optional 'error' message
        """
        external_id = mapping.get('externalId')
        
        try:
            logger.info(f"Cleaning up stale mapping for externalId: {external_id}")
            
            # Remove the externalId mapping from Keycloak
            self.keycloak_client.delete_external_id_mapping(
                self.tenant_id,
                external_id
            )
            
            # Log the cleanup for audit trail
            self._log_cleanup_action(mapping)
            
            return {'success': True}
            
        except Exception as e:
            error_msg = f"Failed to cleanup mapping: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _log_cleanup_action(self, mapping: Dict[str, Any]):
        """
        Log cleanup action for audit purposes.
        
        Args:
            mapping: The mapping that was cleaned up
        """
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': self.tenant_id,
            'action': 'CLEANUP_STALE_EXTERNAL_ID',
            'external_id': mapping.get('externalId'),
            'group_name': mapping.get('name'),
            'mapping_data': mapping
        }
        
        logger.info(f"Audit: {audit_entry}")
        
        # In production, this would write to an audit log table
        # self.keycloak_client.write_audit_log(audit_entry)
    
    def _get_group_by_name(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a group from Keycloak by name.
        
        Args:
            group_name: Name of the group
            
        Returns:
            Group data if found, None otherwise
        """
        try:
            return self.keycloak_client.get_group_by_name(
                self.tenant_id,
                group_name
            )
        except Exception as e:
            logger.error(f"Error getting group by name: {e}")
            return None
    
    def _create_group(self, okta_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new group in Keycloak.
        
        Args:
            okta_group: Okta group data
            
        Returns:
            Result of group creation
        """
        group_name = okta_group.get('name')
        external_id = okta_group.get('externalId')
        
        logger.info(f"Creating new group '{group_name}' with externalId '{external_id}'")
        
        group_data = {
            'name': group_name,
            'externalId': external_id,
            'attributes': {
                'oktaMastered': ['true'],
                'appInstanceId': [okta_group.get('appInstanceId')],
                'userGroupId': [okta_group.get('userGroupId')],
                'createdAt': [datetime.utcnow().isoformat()]
            }
        }
        
        try:
            result = self.keycloak_client.create_group(
                self.tenant_id,
                group_data
            )
            
            logger.info(f"Successfully created group '{group_name}'")
            return {
                'success': True,
                'action': 'created',
                'group': result
            }
            
        except Exception as e:
            logger.error(f"Failed to create group '{group_name}': {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_group(self, existing_group: Dict[str, Any], okta_group: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing group in Keycloak.
        
        Args:
            existing_group: Existing group data from Keycloak
            okta_group: Updated group data from Okta
            
        Returns:
            Result of group update
        """
        group_name = okta_group.get('name')
        external_id = okta_group.get('externalId')
        
        logger.info(f"Updating existing group '{group_name}' with externalId '{external_id}'")
        
        # Merge attributes
        updated_data = {
            'id': existing_group.get('id'),
            'name': group_name,
            'externalId': external_id,
            'attributes': {
                **existing_group.get('attributes', {}),
                'oktaMastered': ['true'],
                'appInstanceId': [okta_group.get('appInstanceId')],
                'userGroupId': [okta_group.get('userGroupId')],
                'updatedAt': [datetime.utcnow().isoformat()]
            }
        }
        
        try:
            result = self.keycloak_client.update_group(
                self.tenant_id,
                existing_group.get('id'),
                updated_data
            )
            
            logger.info(f"Successfully updated group '{group_name}'")
            return {
                'success': True,
                'action': 'updated',
                'group': result
            }
            
        except Exception as e:
            logger.error(f"Failed to update group '{group_name}': {e}")
            return {
                'success': False,
                'error': str(e)
            }


def batch_cleanup_stale_mappings(keycloak_client, tenant_id: str, group_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Batch cleanup utility for stale externalId mappings.
    
    This can be used by support teams to clean up orphaned mappings for a tenant.
    
    Args:
        keycloak_client: Client for interacting with Keycloak API
        tenant_id: Tenant identifier
        group_names: Optional list of specific group names to clean up.
                     If None, scans all groups for stale mappings.
                     
    Returns:
        Summary of cleanup operations
    """
    logger.info(f"Starting batch cleanup for tenant '{tenant_id}'")
    
    results = {
        'tenant_id': tenant_id,
        'timestamp': datetime.utcnow().isoformat(),
        'cleaned_up': [],
        'failed': [],
        'skipped': []
    }
    
    try:
        # Get all externalId mappings for the tenant
        all_mappings = keycloak_client.get_all_external_id_mappings(tenant_id)
        
        for mapping in all_mappings:
            group_name = mapping.get('name')
            external_id = mapping.get('externalId')
            
            # Filter by group names if provided
            if group_names and group_name not in group_names:
                results['skipped'].append({
                    'group_name': group_name,
                    'external_id': external_id,
                    'reason': 'Not in target group list'
                })
                continue
            
            # Check if mapping is stale
            handler = GroupPushHandler(keycloak_client, tenant_id)
            
            # Create a dummy Okta group for staleness check
            # In production, this would fetch from Okta API
            okta_group = {'name': group_name, 'externalId': external_id}
            
            if handler._is_stale_mapping(mapping, okta_group):
                cleanup_result = handler._cleanup_stale_mapping(mapping)
                
                if cleanup_result['success']:
                    results['cleaned_up'].append({
                        'group_name': group_name,
                        'external_id': external_id
                    })
                else:
                    results['failed'].append({
                        'group_name': group_name,
                        'external_id': external_id,
                        'error': cleanup_result.get('error')
                    })
        
        logger.info(f"Batch cleanup completed. Cleaned: {len(results['cleaned_up'])}, Failed: {len(results['failed'])}, Skipped: {len(results['skipped'])}")
        
    except Exception as e:
        logger.error(f"Batch cleanup failed: {e}")
        results['error'] = str(e)
    
    return results
