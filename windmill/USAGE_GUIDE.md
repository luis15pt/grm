# GPU Resource Manager - Usage Guide

This guide shows you how to use the Windmill scripts and workflows to manage your GPU infrastructure **without a frontend**.

## Overview

The GPU Resource Manager provides:
- **Scripts**: Individual operations (get hosts, migrate, deploy VMs)
- **Flows**: Multi-step workflows (migration with validation, RunPod deployment)
- **API Access**: Every script/flow is auto-exposed as an API

## Quick Start

### 1. List All Hosts

Get a complete view of your GPU infrastructure:

```bash
# Via Windmill UI
Scripts → f/gpu_manager/scripts/utility/list_hosts_by_pool → Run
# Select resources: openstack_prod, netbox_prod
# Leave filters empty to see everything

# Via API
curl -X POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/scripts/utility/list_hosts_by_pool \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "openstack_connection": "$res:openstack_prod",
    "netbox_api": "$res:netbox_prod"
  }'
```

**Output:**
```json
{
  "H100": {
    "ondemand": [{hostname: "gpu-h100-001", vm_count: 2, ...}, ...],
    "spot": [{hostname: "gpu-h100-spot-001", vm_count: 0, ...}, ...],
    "runpod": [...],
    "contract": [...]
  },
  "A100": {...},
  "summary": {
    "total_hosts": 150,
    "by_gpu_type": {"H100": 50, "A100": 60, "L40": 40},
    "by_pool_type": {"ondemand": 80, "spot": 40, "runpod": 20, "contract": 10}
  }
}
```

### 2. Filter Hosts

Get specific hosts:

```bash
# H100 hosts only
list_hosts_by_pool(gpu_type="H100")

# Spot hosts only
list_hosts_by_pool(pool_type="spot")

# Investor-owned hosts only
list_hosts_by_pool(owner_filter="Investors")

# H100 spot hosts owned by Investors
list_hosts_by_pool(gpu_type="H100", pool_type="spot", owner_filter="Investors")
```

### 3. Migrate a Single Host

Move a host from spot to on-demand:

```bash
# Via Windmill UI
Flows → f/gpu_manager/flows/migrate_host → Run
# Fill in:
#   openstack_connection: openstack_prod
#   hostname: gpu-h100-spot-001
#   source_aggregate: H100-n3-spot
#   target_aggregate: H100-n3
#   dry_run: false

# Via API
curl -X POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/flows/migrate_host \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "openstack_connection": "$res:openstack_prod",
    "hostname": "gpu-h100-spot-001",
    "source_aggregate": "H100-n3-spot",
    "target_aggregate": "H100-n3",
    "dry_run": false
  }'
```

**What happens:**
1. ✅ Validates migration (GPU types match, no VMs if spot)
2. 🔄 Removes host from source aggregate (retry 3x)
3. ➕ Adds host to target aggregate (retry 3x)
4. ✔️ Verifies host is in target aggregate
5. 📊 Returns success with details

**Output:**
```json
{
  "success": true,
  "message": "Successfully migrated gpu-h100-spot-001 from H100-n3-spot to H100-n3",
  "hostname": "gpu-h100-spot-001",
  "source_aggregate": "H100-n3-spot",
  "target_aggregate": "H100-n3",
  "validation": {...},
  "verification": {...}
}
```

### 4. Bulk Migrate Multiple Hosts

Move many hosts at once:

```bash
# Via Windmill UI
Flows → f/gpu_manager/flows/bulk_migrate_hosts → Run
# Fill in:
#   openstack_connection: openstack_prod
#   hostnames: ["gpu-h100-spot-001", "gpu-h100-spot-002", "gpu-h100-spot-003"]
#   source_aggregate: H100-n3-spot
#   target_aggregate: H100-n3
#   parallel: true
#   max_workers: 5

# Via API
curl -X POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/flows/bulk_migrate_hosts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "openstack_connection": "$res:openstack_prod",
    "hostnames": ["gpu-h100-spot-001", "gpu-h100-spot-002", "gpu-h100-spot-003"],
    "source_aggregate": "H100-n3-spot",
    "target_aggregate": "H100-n3",
    "parallel": true,
    "max_workers": 5
  }'
```

**What happens:**
1. ✅ Validates ALL migrations first (fails fast if any are invalid)
2. 🔄 Executes migrations in parallel (up to 5 at once)
3. 📊 Returns summary with successes and failures

**Output:**
```json
{
  "success": true,
  "message": "Migrated 3/3 hosts from H100-n3-spot to H100-n3",
  "total": 3,
  "successes": 3,
  "failures": 0,
  "success_hostnames": ["gpu-h100-spot-001", "gpu-h100-spot-002", "gpu-h100-spot-003"],
  "failure_hostnames": []
}
```

### 5. Deploy VM on RunPod

Launch a new VM on the RunPod platform:

```bash
# Via Windmill UI
Flows → f/gpu_manager/flows/launch_runpod_vm → Run
# Fill in:
#   hyperstack_api: hyperstack_prod
#   hostname: runpod-h100-new-001
#   assign_floating_ip: true
#   max_wait_seconds: 300

# Via API
curl -X POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/flows/launch_runpod_vm \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "hyperstack_api": "$res:hyperstack_prod",
    "hostname": "runpod-h100-new-001",
    "assign_floating_ip": true,
    "max_wait_seconds": 300
  }'
```

**What happens:**
1. 🔍 Determines GPU type and flavor from hostname
2. 🚀 Deploys VM on Hyperstack (retry 3x)
3. ⏳ Waits for VM to become ACTIVE (polls every 10s, max 5min)
4. 🔥 Attaches appropriate firewall rules (based on GPU type)
5. ✅ Final verification and returns details

**Output:**
```json
{
  "success": true,
  "message": "Successfully deployed runpod-h100-new-001 on RunPod",
  "hostname": "runpod-h100-new-001",
  "vm_id": "vm-abc123",
  "ip_address": "192.168.1.100",
  "status": "ACTIVE",
  "flavor": "n3-H100x8",
  "firewall_id": "fw-h100-production"
}
```

## Common Workflows

### Workflow 1: Move Idle Spot Hosts to On-Demand

**Use Case**: Prevent spot hosts from being reclaimed

```bash
# Step 1: List all spot hosts with 0 VMs
list_hosts_by_pool(pool_type="spot", gpu_type="H100")
# Manually review output, identify hosts with vm_count=0

# Step 2: Bulk migrate them
bulk_migrate_hosts(
  hostnames=["gpu-h100-spot-001", "gpu-h100-spot-005", ...],
  source_aggregate="H100-n3-spot",
  target_aggregate="H100-n3",
  parallel=true
)
```

### Workflow 2: Deploy New RunPod Capacity

**Use Case**: Add more RunPod instances for a customer

```bash
# Deploy 3 new H100 VMs
for i in {1..3}:
    launch_runpod_vm(
        hostname=f"customer-h100-{i:03d}",
        assign_floating_ip=true
    )
```

### Workflow 3: Contract Hardware Redistribution

**Use Case**: Move hosts between contract aggregates

```bash
# Get hosts in old contract
list_hosts_by_pool(pool_type="contract", gpu_type="A100")
# Review output for "Contract-OldCustomer" aggregate

# Migrate to new contract
bulk_migrate_hosts(
  hostnames=["..."],
  source_aggregate="Contract-OldCustomer-24xA100",
  target_aggregate="Contract-NewCustomer-24xA100"
)
```

## Advanced Usage

### Monitoring Job Status

Every script/flow creates a job. Monitor via:

**Windmill UI:**
```
Runs → Select job → View logs and results
```

**API:**
```bash
# Get job status
curl https://windmill.com/api/w/workspace/jobs/completed/JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Scheduling Recurring Operations

**Use Case**: Automatically move idle spot hosts every hour

```bash
# In Windmill UI
Scripts → bulk_migrate_hosts → Schedule
# Set cron: 0 * * * * (every hour)
# Configure parameters:
#   - Query for idle hosts first (custom script)
#   - Pass results to bulk_migrate_hosts
```

### Error Handling

All flows have built-in error handling:

```json
// Example failure response
{
  "success": false,
  "message": "Migration failed: Host has 2 VMs still running",
  "hostname": "gpu-h100-spot-001",
  "error": {
    "message": "Cannot migrate spot host gpu-h100-spot-001: 2 VMs still running. VMs must be evacuated before migration."
  },
  "partial_results": {
    "validation": {...}
  }
}
```

**Retry logic:**
- Validation failures: No retry (fix issue first)
- API timeouts: Auto-retry 3x with 5s delay
- VM deployment: Auto-retry 3x with 10s delay

### Dry Run Mode

Test migrations without executing:

```bash
migrate_host(
  hostname="gpu-h100-spot-001",
  source_aggregate="H100-n3-spot",
  target_aggregate="H100-n3",
  dry_run=true  # ← Only validates, doesn't execute
)
```

**Output:**
```json
{
  "success": true,
  "message": "DRY RUN: Would migrate gpu-h100-spot-001 from H100-n3-spot to H100-n3",
  "validation": {
    "valid": true,
    "source_gpu": "H100",
    "target_gpu": "H100",
    "vm_count": 0
  },
  "dry_run": true
}
```

## API Integration

### Generate API Token

```bash
# In Windmill UI
Settings → Tokens → Create Token
# Copy token for use in scripts
```

### Python Example

```python
import requests

WINDMILL_URL = "https://windmill.com"
TOKEN = "your-token"

def list_hosts(gpu_type=None):
    response = requests.post(
        f"{WINDMILL_URL}/api/w/workspace/jobs/run/f/gpu_manager/scripts/utility/list_hosts_by_pool",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "openstack_connection": "$res:openstack_prod",
            "netbox_api": "$res:netbox_prod",
            "gpu_type": gpu_type
        }
    )
    job_id = response.json()["id"]

    # Poll for completion
    while True:
        status = requests.get(
            f"{WINDMILL_URL}/api/w/workspace/jobs/completed/{job_id}",
            headers={"Authorization": f"Bearer {TOKEN}"}
        ).json()

        if status.get("type") == "CompletedJob":
            return status["result"]

        time.sleep(1)

# Use it
hosts = list_hosts(gpu_type="H100")
print(f"Found {len(hosts['H100']['spot'])} H100 spot hosts")
```

## Troubleshooting

### "Validation failed" errors

**Problem**: Migration rejected during validation

**Solutions:**
- Check GPU types match: `H100 → H100` ✅, `H100 → A100` ❌
- For spot hosts: Ensure VM count is 0
- Verify aggregates exist in OpenStack

### "Timeout waiting for VM" errors

**Problem**: RunPod VM didn't become ACTIVE in time

**Solutions:**
- Increase `max_wait_seconds` parameter (default 300s)
- Check Hyperstack API status
- Verify sufficient capacity for flavor

### "Resource not found" errors

**Problem**: Missing credentials resource

**Solutions:**
- Verify resource exists: Resources → openstack_prod
- Check resource permissions for your user
- Ensure resource name matches exactly

## Best Practices

1. **Always list first**: Use `list_hosts_by_pool` to see current state before operations
2. **Use dry run**: Test migrations with `dry_run=true` first
3. **Bulk operations**: Use `bulk_migrate_hosts` for >3 hosts (parallel execution)
4. **Monitor jobs**: Check Runs tab after triggering flows
5. **Filter by owner**: Use `owner_filter` to avoid touching wrong hosts
6. **Schedule wisely**: Use cron schedules for recurring tasks

## Next Steps

- **Automate workflows**: Create custom scripts that chain operations
- **Add notifications**: Integrate Slack/Discord webhooks for alerts
- **Create reports**: Schedule scripts to generate daily summaries
- **Extend functionality**: Add custom scripts for your specific needs

---

**Need help?** Check the Windmill docs or see WINDMILL_SETUP.md for configuration details.
