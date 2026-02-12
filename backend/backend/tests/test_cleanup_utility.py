"""
Unit tests for the cleanup utility.

Tests the command-line cleanup utility for stale externalId mappings.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from keycloak.mappings import KeycloakMappingClient, ExternalIdMapping
from scim.push_groups import GroupPushHandler, ExternalIdConflictError


class TestExternalIdMapping(unittest.TestCase):
    """Test the ExternalIdMapping data class."""
    
    def test_mapping_creation(self):
        """Test creating a mapping from data."""
        data = {
            'externalId': '2ea7c8f7-7506-4b71-a53c-f307aedb647d',
            'keycloakGroupId': 'group-123',
            'name': 'grpAtlanProdWorkflowAdmin',
            'tenantId': 'apex.atlan.com',
            'status': 'ACTIVE'
        }
        
        mapping = ExternalIdMapping(data)
        
        self.assertEqual(mapping.external_id, '2ea7c8f7-7506-4b71-a53c-f307aedb647d')
        self.assertEqual(mapping.group_name, 'grpAtlanProdWorkflowAdmin')
        self.assertEqual(mapping.status, 'ACTIVE')
        self.assertFalse(mapping.is_orphaned())
    
    def test_orphaned_mapping(self):
        """Test detecting orphaned mappings."""
        data = {
            'externalId': 'test-id',
            'keycloakGroupId': None,
            'name': 'test-group',
            'status': 'ORPHANED'
        }
        
        mapping = ExternalIdMapping(data)
        self.assertTrue(mapping.is_orphaned())


class TestKeycloakMappingClient(unittest.TestCase):
    """Test the Keycloak mapping client."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = KeycloakMappingClient(
            base_url='https://test.keycloak.com',
            admin_token='test-token'
        )
    
    def test_client_initialization(self):
        """Test client is initialized correctly."""
        self.assertEqual(self.client.base_url, 'https://test.keycloak.com')
        self.assertEqual(self.client.admin_token, 'test-token')
        self.assertIn('Bearer test-token', self.client.headers['Authorization'])
    
    @patch.object(KeycloakMappingClient, '_query_mapping_from_api')
    def test_get_group_by_external_id(self, mock_query):
        """Test getting a group by externalId."""
        mock_query.return_value = {
            'externalId': 'test-id',
            'name': 'test-group'
        }
        
        result = self.client.get_group_by_external_id('test-tenant', 'test-id')
        
        mock_query.assert_called_once_with('test-tenant', 'test-id')
        self.assertIsNotNone(result)
        self.assertEqual(result['externalId'], 'test-id')


class TestGroupPushHandler(unittest.TestCase):
    """Test the SCIM group push handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=KeycloakMappingClient)
        self.handler = GroupPushHandler(self.mock_client, 'test-tenant')
    
    def test_handler_initialization(self):
        """Test handler is initialized correctly."""
        self.assertEqual(self.handler.tenant_id, 'test-tenant')
        self.assertEqual(self.handler.keycloak_client, self.mock_client)
    
    @patch.object(GroupPushHandler, '_check_external_id_mapping')
    @patch.object(GroupPushHandler, '_get_group_by_name')
    @patch.object(GroupPushHandler, '_create_group')
    def test_push_new_group(self, mock_create, mock_get, mock_check):
        """Test pushing a new group with no conflicts."""
        mock_check.return_value = None
        mock_get.return_value = None
        mock_create.return_value = {'success': True, 'group_id': 'new-group-123'}
        
        okta_group = {
            'name': 'testGroup',
            'externalId': 'test-external-id',
            'appInstanceId': 'app-123',
            'userGroupId': 'group-456'
        }
        
        result = self.handler.push_group(okta_group)
        
        mock_check.assert_called_once_with('test-external-id')
        mock_get.assert_called_once_with('testGroup')
        mock_create.assert_called_once_with(okta_group)
        self.assertTrue(result['success'])
    
    @patch.object(GroupPushHandler, '_check_external_id_mapping')
    @patch.object(GroupPushHandler, '_is_stale_mapping')
    @patch.object(GroupPushHandler, '_cleanup_stale_mapping')
    @patch.object(GroupPushHandler, '_get_group_by_name')
    @patch.object(GroupPushHandler, '_update_group')
    def test_push_group_with_stale_mapping(self, mock_update, mock_get, 
                                           mock_cleanup, mock_is_stale, mock_check):
        """Test pushing a group with a stale mapping."""
        existing_mapping = {
            'externalId': 'test-id',
            'keycloakGroupId': 'old-group-123',
            'name': 'oldName'
        }
        
        mock_check.return_value = existing_mapping
        mock_is_stale.return_value = True
        mock_cleanup.return_value = {'success': True}
        mock_get.return_value = {'id': 'group-123', 'name': 'testGroup'}
        mock_update.return_value = {'success': True}
        
        okta_group = {
            'name': 'testGroup',
            'externalId': 'test-id',
            'appInstanceId': 'app-123',
            'userGroupId': 'group-456'
        }
        
        result = self.handler.push_group(okta_group)
        
        mock_check.assert_called_once_with('test-id')
        mock_is_stale.assert_called_once_with(existing_mapping, okta_group)
        mock_cleanup.assert_called_once_with(existing_mapping)
        self.assertTrue(result['success'])
    
    @patch.object(GroupPushHandler, '_check_external_id_mapping')
    @patch.object(GroupPushHandler, '_is_stale_mapping')
    @patch.object(GroupPushHandler, '_cleanup_stale_mapping')
    def test_push_group_cleanup_failure(self, mock_cleanup, mock_is_stale, mock_check):
        """Test handling cleanup failure."""
        existing_mapping = {
            'externalId': 'test-id',
            'keycloakGroupId': 'old-group-123',
            'name': 'oldName'
        }
        
        mock_check.return_value = existing_mapping
        mock_is_stale.return_value = True
        mock_cleanup.return_value = {'success': False, 'error': 'Database error'}
        
        okta_group = {
            'name': 'testGroup',
            'externalId': 'test-id'
        }
        
        with self.assertRaises(ExternalIdConflictError):
            self.handler.push_group(okta_group)


class TestStaleMappingDetection(unittest.TestCase):
    """Test stale mapping detection logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=KeycloakMappingClient)
        self.handler = GroupPushHandler(self.mock_client, 'test-tenant')
    
    def test_name_mismatch_is_stale(self):
        """Test that name mismatch marks mapping as stale."""
        existing_mapping = {
            'externalId': 'test-id',
            'keycloakGroupId': 'group-123',
            'name': 'oldGroupName'
        }
        
        okta_group = {
            'name': 'newGroupName',
            'externalId': 'test-id'
        }
        
        result = self.handler._is_stale_mapping(existing_mapping, okta_group)
        self.assertTrue(result)
    
    def test_same_name_not_stale(self):
        """Test that same name doesn't mark mapping as stale."""
        existing_mapping = {
            'externalId': 'test-id',
            'keycloakGroupId': 'group-123',
            'name': 'testGroup'
        }
        
        okta_group = {
            'name': 'testGroup',
            'externalId': 'test-id'
        }
        
        # Mock the group exists check
        self.mock_client.get_group_by_id = Mock(return_value={'id': 'group-123'})
        
        result = self.handler._is_stale_mapping(existing_mapping, okta_group)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
