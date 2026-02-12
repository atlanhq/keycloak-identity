#!/usr/bin/env python3
"""
Utility Script: Clean Up Stale External IDs for Okta SCIM Group Push

This script provides a command-line utility for support teams to clean up
stale externalId mappings that are blocking Okta Push Groups operations.

Usage:
    # Clean up a specific group for a tenant
    python cleanup_stale_external_ids.py --tenant apex.atlan.com --group grpAtlanProdWorkflowAdmin
    
    # Clean up all stale mappings for a tenant
    python cleanup_stale_external_ids.py --tenant apex.atlan.com --all
    
    # Dry run (preview without making changes)
    python cleanup_stale_external_ids.py --tenant apex.atlan.com --group grpAtlanProdWorkflowAdmin --dry-run
    
    # Clean up by specific externalId
    python cleanup_stale_external_ids.py --tenant apex.atlan.com --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d

Issue: LINTEST-423 / LINTEST-439 - Okta Push Groups stale externalId cleanup
"""

import argparse
import logging
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional

# Import our modules
sys.path.insert(0, '/workspace/backend')
from keycloak.mappings import KeycloakMappingClient, MappingHealthChecker
from scim.push_groups import batch_cleanup_stale_mappings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanupUtility:
    """
    Utility for cleaning up stale externalId mappings.
    """
    
    def __init__(self, keycloak_url: str, admin_token: Optional[str] = None, 
                 database_connection=None, dry_run: bool = False):
        """
        Initialize the cleanup utility.
        
        Args:
            keycloak_url: Base URL of Keycloak server
            admin_token: Admin authentication token (if using API)
            database_connection: Database connection (if using direct DB access)
            dry_run: If True, preview changes without applying them
        """
        self.client = KeycloakMappingClient(
            base_url=keycloak_url,
            admin_token=admin_token or "ADMIN_TOKEN_PLACEHOLDER",
            database_connection=database_connection
        )
        self.dry_run = dry_run
        
        if dry_run:
            logger.info("Running in DRY RUN mode - no changes will be made")
    
    def cleanup_by_group_name(self, tenant_id: str, group_name: str) -> Dict:
        """
        Clean up stale mapping for a specific group.
        
        Args:
            tenant_id: Tenant identifier
            group_name: Name of the group
            
        Returns:
            Cleanup result
        """
        logger.info(f"Cleaning up stale mapping for group '{group_name}' in tenant '{tenant_id}'")
        
        result = {
            'tenant_id': tenant_id,
            'group_name': group_name,
            'timestamp': datetime.utcnow().isoformat(),
            'dry_run': self.dry_run
        }
        
        try:
            # First, find the group
            group = self.client.get_group_by_name(tenant_id, group_name)
            
            if not group:
                result['status'] = 'NOT_FOUND'
                result['message'] = f"Group '{group_name}' not found in tenant '{tenant_id}'"
                logger.warning(result['message'])
                return result
            
            # Get the externalId
            external_id = group.get('externalId')
            
            if not external_id:
                result['status'] = 'NO_EXTERNAL_ID'
                result['message'] = f"Group '{group_name}' does not have an externalId"
                logger.warning(result['message'])
                return result
            
            result['external_id'] = external_id
            
            # Perform cleanup
            if not self.dry_run:
                cleanup_success = self.client.delete_external_id_mapping(tenant_id, external_id)
                
                if cleanup_success:
                    result['status'] = 'SUCCESS'
                    result['message'] = f"Successfully cleaned up externalId '{external_id}' for group '{group_name}'"
                    logger.info(result['message'])
                else:
                    result['status'] = 'FAILED'
                    result['message'] = f"Failed to clean up externalId '{external_id}' for group '{group_name}'"
                    logger.error(result['message'])
            else:
                result['status'] = 'DRY_RUN'
                result['message'] = f"Would clean up externalId '{external_id}' for group '{group_name}'"
                logger.info(result['message'])
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        
        return result
    
    def cleanup_by_external_id(self, tenant_id: str, external_id: str) -> Dict:
        """
        Clean up stale mapping by externalId.
        
        Args:
            tenant_id: Tenant identifier
            external_id: External ID to clean up
            
        Returns:
            Cleanup result
        """
        logger.info(f"Cleaning up externalId '{external_id}' in tenant '{tenant_id}'")
        
        result = {
            'tenant_id': tenant_id,
            'external_id': external_id,
            'timestamp': datetime.utcnow().isoformat(),
            'dry_run': self.dry_run
        }
        
        try:
            # Get the mapping
            mapping = self.client.get_group_by_external_id(tenant_id, external_id)
            
            if mapping:
                result['group_name'] = mapping.get('name')
                logger.info(f"Found mapping for group '{mapping.get('name')}'")
            else:
                logger.info(f"No mapping found for externalId '{external_id}' (may already be cleaned)")
            
            # Perform cleanup
            if not self.dry_run:
                cleanup_success = self.client.delete_external_id_mapping(tenant_id, external_id)
                
                if cleanup_success:
                    result['status'] = 'SUCCESS'
                    result['message'] = f"Successfully cleaned up externalId '{external_id}'"
                    logger.info(result['message'])
                else:
                    result['status'] = 'FAILED'
                    result['message'] = f"Failed to clean up externalId '{external_id}'"
                    logger.error(result['message'])
            else:
                result['status'] = 'DRY_RUN'
                result['message'] = f"Would clean up externalId '{external_id}'"
                logger.info(result['message'])
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            logger.error(f"Error during cleanup: {e}", exc_info=True)
        
        return result
    
    def cleanup_all_stale(self, tenant_id: str) -> Dict:
        """
        Clean up all stale mappings for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Cleanup summary
        """
        logger.info(f"Cleaning up all stale mappings for tenant '{tenant_id}'")
        
        result = {
            'tenant_id': tenant_id,
            'timestamp': datetime.utcnow().isoformat(),
            'dry_run': self.dry_run,
            'cleaned': [],
            'failed': [],
            'skipped': []
        }
        
        try:
            # Get all mappings
            all_mappings = self.client.get_all_external_id_mappings(tenant_id)
            logger.info(f"Found {len(all_mappings)} total mappings")
            
            for mapping in all_mappings:
                external_id = mapping.get('externalId')
                group_name = mapping.get('name')
                keycloak_group_id = mapping.get('keycloakGroupId')
                
                # Check if mapping is stale (group doesn't exist)
                if keycloak_group_id and not self.client.group_exists(tenant_id, keycloak_group_id):
                    logger.info(f"Found stale mapping: {group_name} ({external_id})")
                    
                    if not self.dry_run:
                        cleanup_success = self.client.delete_external_id_mapping(tenant_id, external_id)
                        
                        if cleanup_success:
                            result['cleaned'].append({
                                'group_name': group_name,
                                'external_id': external_id
                            })
                        else:
                            result['failed'].append({
                                'group_name': group_name,
                                'external_id': external_id,
                                'error': 'Deletion failed'
                            })
                    else:
                        result['cleaned'].append({
                            'group_name': group_name,
                            'external_id': external_id,
                            'note': 'Would be cleaned (dry run)'
                        })
                else:
                    result['skipped'].append({
                        'group_name': group_name,
                        'external_id': external_id,
                        'reason': 'Mapping is not stale'
                    })
            
            result['status'] = 'SUCCESS'
            result['summary'] = {
                'total_mappings': len(all_mappings),
                'cleaned': len(result['cleaned']),
                'failed': len(result['failed']),
                'skipped': len(result['skipped'])
            }
            
            logger.info(f"Cleanup complete: {result['summary']}")
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            logger.error(f"Error during batch cleanup: {e}", exc_info=True)
        
        return result
    
    def run_health_check(self, tenant_id: str) -> Dict:
        """
        Run a health check on tenant mappings.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Health check report
        """
        logger.info(f"Running health check for tenant '{tenant_id}'")
        
        checker = MappingHealthChecker(self.client)
        report = checker.check_tenant_health(tenant_id)
        
        return report


def main():
    """
    Main entry point for the cleanup utility.
    """
    parser = argparse.ArgumentParser(
        description='Clean up stale externalId mappings for Okta SCIM Group Push',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean up specific group for apex.atlan.com
  %(prog)s --tenant apex.atlan.com --group grpAtlanProdWorkflowAdmin

  # Clean up by externalId
  %(prog)s --tenant apex.atlan.com --external-id 2ea7c8f7-7506-4b71-a53c-f307aedb647d

  # Clean up all stale mappings (dry run)
  %(prog)s --tenant apex.atlan.com --all --dry-run

  # Run health check
  %(prog)s --tenant apex.atlan.com --health-check
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--tenant',
        required=True,
        help='Tenant identifier (e.g., apex.atlan.com)'
    )
    
    # Operation mode (mutually exclusive)
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument(
        '--group',
        help='Group name to clean up'
    )
    operation_group.add_argument(
        '--external-id',
        help='External ID to clean up'
    )
    operation_group.add_argument(
        '--all',
        action='store_true',
        help='Clean up all stale mappings'
    )
    operation_group.add_argument(
        '--health-check',
        action='store_true',
        help='Run health check only (no cleanup)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    parser.add_argument(
        '--keycloak-url',
        default='https://keycloak.atlan.com',
        help='Keycloak server URL (default: https://keycloak.atlan.com)'
    )
    parser.add_argument(
        '--admin-token',
        help='Keycloak admin token (can also use KEYCLOAK_ADMIN_TOKEN env var)'
    )
    parser.add_argument(
        '--output-json',
        action='store_true',
        help='Output results in JSON format'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get admin token from args or environment
    import os
    admin_token = args.admin_token or os.environ.get('KEYCLOAK_ADMIN_TOKEN')
    
    if not admin_token and not args.dry_run:
        logger.warning("No admin token provided. Functionality may be limited.")
    
    # Initialize utility
    utility = CleanupUtility(
        keycloak_url=args.keycloak_url,
        admin_token=admin_token,
        dry_run=args.dry_run
    )
    
    # Execute operation
    result = None
    
    try:
        if args.health_check:
            result = utility.run_health_check(args.tenant)
        elif args.group:
            result = utility.cleanup_by_group_name(args.tenant, args.group)
        elif args.external_id:
            result = utility.cleanup_by_external_id(args.tenant, args.external_id)
        elif args.all:
            result = utility.cleanup_all_stale(args.tenant)
        
        # Output results
        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print("\n" + "="*60)
            print(f"Cleanup Utility Results - {datetime.utcnow().isoformat()}")
            print("="*60)
            
            if args.health_check:
                print(f"\nTenant: {result['tenant_id']}")
                print(f"Status: {result['status']}")
                print(f"\nIssues Found: {result['validation_report']['summary']['issues_found']}")
                
                if result.get('recommendations'):
                    print("\nRecommendations:")
                    for rec in result['recommendations']:
                        print(f"  - {rec}")
            else:
                print(f"\nTenant: {result['tenant_id']}")
                print(f"Status: {result.get('status', 'UNKNOWN')}")
                
                if args.all:
                    summary = result.get('summary', {})
                    print(f"\nSummary:")
                    print(f"  Total Mappings: {summary.get('total_mappings', 0)}")
                    print(f"  Cleaned: {summary.get('cleaned', 0)}")
                    print(f"  Failed: {summary.get('failed', 0)}")
                    print(f"  Skipped: {summary.get('skipped', 0)}")
                else:
                    print(f"\nMessage: {result.get('message', 'No message')}")
                    
                if result.get('error'):
                    print(f"\nError: {result['error']}")
            
            print("="*60 + "\n")
        
        # Exit with appropriate code
        if result.get('status') in ['SUCCESS', 'DRY_RUN', 'HEALTHY']:
            sys.exit(0)
        elif result.get('status') == 'NOT_FOUND':
            sys.exit(1)
        else:
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
