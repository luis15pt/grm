# Windmill Setup Guide for GPU Resource Manager

This guide walks you through setting up the GPU Resource Manager in your Windmill instance.

## Prerequisites

- Windmill instance (self-hosted or cloud) - https://www.windmill.dev/
- Git repository access
- OpenStack admin credentials
- NetBox API access
- (Optional) Hyperstack/RunPod API access

## Quick Start

### Option 1: Git Sync (Recommended)

1. **Push this branch to GitHub**
   ```bash
   git push origin windmill-conversion
   ```

2. **Configure Windmill Git Sync**
   - In Windmill UI: Settings → Workspace → Git Sync
   - Connect your repository
   - Select branch: `windmill-conversion`
   - Set folder: `windmill/`
   - Enable auto-sync

3. **Windmill will automatically import**:
   - All scripts (20+ Python scripts)
   - Flows (migrate_host, etc.)
   - Apps (GPU dashboard)
   - Resource type definitions

### Option 2: Manual Upload

If Git sync is not available:

1. **Create Resource Types**
   - Go to Windmill UI → Resources → Resource Types
   - Create `openstack_connection` using `resources/openstack_connection.json`
   - Create `netbox_api` using `resources/netbox_api.json`
   - Create `hyperstack_api` using `resources/hyperstack_api.json`

2. **Import Scripts**
   - Go to Scripts → Add Script
   - For each `.py` file in `f/gpu_manager/scripts/`:
     - Copy the Python code
     - Set path: `f/gpu_manager/scripts/{category}/{scriptname}`
     - Use corresponding `.script.yaml` for metadata
     - Save

3. **Import Flows**
   - Go to Flows → Add Flow
   - Import each `flow.yaml` from `f/gpu_manager/flows/`

4. **Import App**
   - Go to Apps → Add App
   - Import `gpu_dashboard.app/app.yaml`

### Option 3: CLI Import

```bash
# Install Windmill CLI
npm install -g windmill-cli

# Login to your instance
wmill login https://your-windmill-instance.com

# Sync workspace
cd windmill
wmill workspace sync push
```

## Step-by-Step Configuration

### Step 1: Create Resources

Create resource instances with your actual credentials.

#### OpenStack Connection

1. Navigate to **Resources** → **+ Resource**
2. Type: `openstack_connection`
3. Name: `openstack_prod`
4. Fill in values:
   ```json
   {
     "auth_url": "https://your-openstack.com:5000/v3",
     "username": "admin",
     "password": "your-password",
     "project_name": "admin",
     "user_domain_name": "Default",
     "project_domain_name": "Default",
     "region_name": "RegionOne",
     "interface": "public",
     "identity_api_version": "3"
   }
   ```

#### NetBox API

1. Type: `netbox_api`
2. Name: `netbox_prod`
3. Fill in:
   ```json
   {
     "base_url": "https://your-netbox.com",
     "api_token": "your-netbox-token"
   }
   ```

#### Hyperstack API (Optional)

1. Type: `hyperstack_api`
2. Name: `hyperstack_prod`
3. Fill in:
   ```json
   {
     "api_key": "your-hyperstack-key",
     "firewall_id_map": {
       "H100": "your-h100-firewall-id",
       "A100": "your-a100-firewall-id"
     }
   }
   ```

### Step 2: Test Individual Scripts

Before running flows or the app, test key scripts:

#### Test 1: GPU Aggregates Discovery

1. Go to **Scripts** → `f/gpu_manager/scripts/openstack/discover_gpu_aggregates`
2. Click **Run**
3. Select resource: `openstack_prod`
4. Expected result: JSON with H100, A100, L40, etc. aggregates

#### Test 2: NetBox Devices

1. Go to **Scripts** → `f/gpu_manager/scripts/netbox/get_all_gpu_devices`
2. Click **Run**
3. Select resource: `netbox_prod`
4. Expected result: List of active and inactive GPU devices

#### Test 3: Host Information

1. Go to **Scripts** → `f/gpu_manager/scripts/host/get_host_vms`
2. Enter a valid hostname (e.g., `gpu-host-001`)
3. Select resource: `openstack_prod`
4. Expected result: List of VMs on that host

### Step 3: Test Data Collection

The master data collection script orchestrates everything:

1. Go to **Scripts** → `f/gpu_manager/scripts/data/get_parallel_data`
2. Click **Run**
3. Select both resources:
   - `openstack_connection`: `openstack_prod`
   - `netbox_api`: `netbox_prod`
4. Expected result: Complete GPU infrastructure organized by type
5. **Note**: First run may take 30-60 seconds; subsequent runs use cache

### Step 4: Test Migration Flow

Test the host migration workflow:

1. Go to **Flows** → `f/gpu_manager/flows/migrate_host`
2. Click **Run**
3. Fill in parameters:
   - `openstack_connection`: `openstack_prod`
   - `hostname`: A valid host (e.g., `gpu-host-001`)
   - `source_aggregate`: Current aggregate (e.g., `H100-n3-spot`)
   - `target_aggregate`: Target aggregate (e.g., `H100-n3`)
   - `dry_run`: `true` (for testing)
4. Expected result: Validation passes, but no actual migration (dry run)

### Step 5: Launch the Dashboard App

1. Go to **Apps** → `f/gpu_manager/apps/gpu_dashboard`
2. Click **Preview** or **Deploy**
3. The app should:
   - Load GPU types in tabs
   - Display hosts in tables
   - Show VM counts and GPU usage
   - Provide migration actions

## Configuration Variables

Set these in Windmill workspace variables:

```json
{
  "GPU_TYPES": ["H100", "A100", "L40", "RTX-A6000", "H100-SXM5", "H200-SXM5"],
  "CACHE_TTL_MINUTES": 10,
  "DEFAULT_AGGREGATE_PATTERN": "^([A-Z0-9-]+)-n3",
  "ENABLE_CONTRACT_POOLS": true
}
```

## Scheduling Background Jobs

For real-time-ish updates, schedule the data collection script:

1. Go to **Scripts** → `f/gpu_manager/scripts/data/get_parallel_data`
2. Click **Schedule**
3. Set cron expression: `*/10 * * * *` (every 10 minutes)
4. Configure resources:
   - `openstack_connection`: `openstack_prod`
   - `netbox_api`: `netbox_prod`
5. Save

The cached results will be available to all scripts and the app.

## Permissions & Access Control

### User Roles

Configure access in Windmill:

- **Admins**: Full access to all scripts, flows, and apps
- **Operators**: Can run flows (migrations), view dashboard
- **Viewers**: Read-only access to dashboard

### Resource Permissions

For each resource:
1. Go to **Resources** → (resource name) → **Permissions**
2. Add users/groups with appropriate access
3. Recommended:
   - `openstack_prod`: Admins + Operators
   - `netbox_prod`: Admins + Operators + Viewers
   - `hyperstack_prod`: Admins only

## Python Dependencies

Windmill needs these Python packages. Add them in:
**Settings** → **Workspace** → **Dependencies** → **Python**

```txt
openstack>=3.3.0
requests>=2.31.0
```

Or use requirements per script (inline in script settings).

## Troubleshooting

### Scripts fail with "Module not found"

- **Solution**: Add Python dependencies (see above)
- Or: Use Windmill's **dedicated workers** with pre-installed packages

### "Resource not found" errors

- **Solution**: Verify resource names match exactly (`openstack_prod`, not `openstack_production`)
- Check resource permissions

### Data collection is slow

- **Solution**:
  - Increase cache TTL in script metadata
  - Use dedicated workers for parallel scripts
  - Schedule background collection instead of on-demand

### Migration flow fails

- **Solution**:
  - Check validation step output (step 'a')
  - Verify OpenStack CLI is installed on workers
  - Test individual scripts (remove, add) manually first

### App doesn't load data

- **Solution**:
  - Check background runnables are configured
  - Run `get_parallel_data` manually to prime cache
  - Verify resources are accessible to app context

### OpenStack CLI commands time out

- **Solution**:
  - Increase timeout in scripts (currently 30s)
  - Check network connectivity from Windmill workers
  - Verify OpenStack endpoint is reachable

## Performance Optimization

### 1. Use Caching Aggressively

- Scripts have `cache_ttl` set (600-1800 seconds)
- Windmill caches results automatically
- Adjust TTL based on data volatility

### 2. Background Runnables in Apps

Configure in app settings:
```yaml
background_runnables:
  - id: gpu_data
    path: f/gpu_manager/scripts/data/get_parallel_data
    recompute_interval: 600  # 10 minutes
```

### 3. Dedicated Workers

For heavy scripts (parallel data collection):
- Settings → Workers → Add Dedicated Worker
- Assign to specific scripts
- Pre-install all dependencies

### 4. Parallel Execution

The `get_parallel_data` script calls other scripts using `wmill.run_script_sync()`.
These can be parallelized further using Windmill's flow system.

## Next Steps

1. **Customize the App UI**
   - Modify `gpu_dashboard.app/app.yaml`
   - Add custom filters, charts, or views
   - Match your branding

2. **Add More Flows**
   - Bulk migrations
   - Automated spot-to-on-demand failover
   - Health check workflows

3. **Integrate Alerts**
   - Use Windmill webhooks to send alerts
   - Slack/Discord/PagerDuty integrations
   - Email notifications on migration failures

4. **Create Dashboards**
   - Use Windmill's chart components
   - Visualize GPU utilization trends
   - Track migration history

5. **API Access**
   - All scripts are auto-exposed as APIs
   - Use webhooks for external integrations
   - Generate API tokens for programmatic access

## Support & Documentation

- **Windmill Docs**: https://docs.windmill.dev/
- **This Project**: See `WINDMILL_ARCHITECTURE.md` for technical details
- **Migration Guide**: See `MIGRATION_GUIDE.md` for differences from Flask version

## Security Best Practices

1. **Never commit credentials** - Use Windmill resources, not .env files
2. **Use separate resources** for dev/staging/prod
3. **Audit logs** - Windmill logs all operations automatically
4. **Rotate credentials** regularly
5. **Restrict permissions** - Use role-based access control
6. **Enable 2FA** for Windmill users
7. **Use HTTPS** for Windmill instance
8. **Network isolation** - Run workers in private networks if possible

---

**Ready to go?** Follow the Quick Start section and you'll be up and running in minutes!
