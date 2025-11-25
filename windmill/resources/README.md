# Resource Type Definitions

This directory contains JSON schema definitions for custom resource types used in the GPU Resource Manager.

## Resource Types

### 1. OpenStack Connection (`openstack_connection`)

Credentials for connecting to OpenStack cloud infrastructure.

**Required fields:**
- `auth_url`: OpenStack authentication URL
- `username`: OpenStack username
- `password`: OpenStack password
- `project_name`: Project/tenant name

**Optional fields:**
- `user_domain_name`: User domain (default: "Default")
- `project_domain_name`: Project domain (default: "Default")
- `region_name`: Region (default: "RegionOne")
- `interface`: API interface type (default: "public")
- `identity_api_version`: Identity API version (default: "3")

**Example:**
```json
{
  "auth_url": "https://openstack.example.com:5000/v3",
  "username": "admin",
  "password": "your-password",
  "project_name": "admin",
  "region_name": "RegionOne"
}
```

### 2. NetBox API (`netbox_api`)

Credentials for NetBox DCIM/IPAM API.

**Required fields:**
- `base_url`: NetBox base URL (e.g., https://netbox.example.com)
- `api_token`: NetBox API authentication token

**Example:**
```json
{
  "base_url": "https://netbox.example.com",
  "api_token": "your-netbox-api-token"
}
```

### 3. Hyperstack API (`hyperstack_api`)

Credentials for Hyperstack/RunPod cloud API.

**Required fields:**
- `api_key`: Hyperstack API key

**Optional fields:**
- `base_url`: API base URL (default: https://api.hyperstack.cloud/v1)
- `firewall_id_map`: Mapping of GPU types to firewall IDs
- `default_image_id`: Default VM image
- `default_network_id`: Default network

**Example:**
```json
{
  "api_key": "your-hyperstack-api-key",
  "firewall_id_map": {
    "H100": "fw-123456",
    "A100": "fw-789012",
    "L40": "fw-345678"
  }
}
```

## How to Create Resources in Windmill

### Method 1: Windmill UI

1. Navigate to **Resources** in the Windmill sidebar
2. Click **+ Resource**
3. Select the resource type (e.g., `openstack_connection`)
4. Fill in the required fields
5. Give it a name (e.g., `openstack_prod`)
6. Save

### Method 2: Import via Git Sync

If you're using Windmill's Git sync feature:

1. Create a file in your workspace: `resource/openstack_prod.json`
2. Add your credentials:
   ```json
   {
     "resource_type": "openstack_connection",
     "value": {
       "auth_url": "https://...",
       "username": "...",
       "password": "...",
       "project_name": "..."
     }
   }
   ```
3. Commit and sync

### Method 3: Windmill CLI

```bash
wmill resource add openstack_prod \
  --resource-type openstack_connection \
  --value '{"auth_url": "...", "username": "...", ...}'
```

## Security Notes

- **Passwords and API tokens are encrypted at rest** in Windmill's database
- Resources have **access controls** - you can restrict which users/groups can use them
- Use **separate resources for different environments** (dev, staging, prod)
- Never commit actual credentials to Git - use placeholders or environment variables

## Usage in Scripts

Scripts automatically inject resource values when you specify a parameter with a resource type:

```python
def main(openstack_connection: dict, hostname: str) -> dict:
    # openstack_connection will be automatically populated
    # with the selected resource's values
    conn = openstack.connect(
        auth_url=openstack_connection['auth_url'],
        username=openstack_connection['username'],
        ...
    )
```

## Troubleshooting

### "Resource not found" errors
- Verify the resource exists in Windmill UI
- Check the resource name matches exactly
- Ensure your user has permission to access the resource

### "Invalid credentials" errors
- Verify credentials are correct in the resource definition
- Test connectivity manually (e.g., `openstack --os-auth-url=... token issue`)
- Check network connectivity from Windmill workers

### "Missing required field" errors
- Ensure all required fields are populated in the resource
- Check the JSON schema for field names (case-sensitive)
