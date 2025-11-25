# GPU Resource Manager - Windmill Conversion

This directory contains the complete Windmill workspace conversion of the Flask-based GPU Resource Manager.

## Directory Structure

```
windmill/
├── f/gpu_manager/              # Main application folder
│   ├── scripts/                # Individual Python scripts (20+)
│   │   ├── openstack/         # OpenStack operations
│   │   ├── netbox/            # NetBox API operations
│   │   ├── host/              # Host management
│   │   ├── hyperstack/        # Hyperstack/RunPod operations
│   │   └── data/              # Data collection and caching
│   ├── flows/                  # Multi-step workflows (5+)
│   │   ├── migrate_host.flow/
│   │   ├── launch_runpod_vm.flow/
│   │   ├── refresh_data.flow/
│   │   ├── contract_operation.flow/
│   │   └── bulk_migration.flow/
│   └── apps/                   # UI applications
│       └── gpu_dashboard.app/  # Main dashboard
├── resources/                  # API credential templates
│   ├── openstack_connection.json
│   ├── netbox_api.json
│   └── hyperstack_api.json
└── variables/                  # Configuration variables
    └── config.json

```

## Windmill Workspace Concepts

### Scripts
- **Location**: `f/gpu_manager/scripts/`
- **Format**: Each script is a Python file with a `main()` function
- **Metadata**: Accompanying `.script.yaml` file for configuration
- **Auto-features**: Automatically exposed as APIs, webhooks, and UI forms

### Flows
- **Location**: `f/gpu_manager/flows/`
- **Format**: Directory per flow with `flow.yaml` and inline scripts
- **Purpose**: Multi-step orchestration with error handling, retries, approvals
- **Features**: Branching, parallel execution, manual approvals, error handlers

### Apps
- **Location**: `f/gpu_manager/apps/`
- **Format**: Directory with `app.yaml` defining UI layout
- **Components**: 60+ built-in components (tables, charts, forms, buttons)
- **Interactivity**: Frontend scripts, background runnables, reactive state

### Resources
- **Location**: `resources/`
- **Purpose**: Store API credentials, connection strings
- **Security**: Encrypted at rest, access-controlled
- **Types**: Custom resource types define schema for credentials

## How to Import to Windmill

### Option 1: Git Sync (Recommended)
1. Push this branch to GitHub
2. In Windmill UI: Settings → Workspace → Git Sync
3. Connect your repository and select `windmill-conversion` branch
4. Windmill will automatically sync all scripts, flows, and apps

### Option 2: Manual Import
1. Navigate to Windmill workspace
2. For each script:
   - Create new script in Windmill UI
   - Copy Python code from `scripts/` directory
   - Configure metadata from `.script.yaml`
3. For each flow:
   - Import `flow.yaml` via Windmill Flow builder
4. For the app:
   - Import `app.yaml` via Windmill App builder

### Option 3: CLI Import
```bash
# Install Windmill CLI
npm install -g windmill-cli

# Login to your Windmill instance
wmill login https://your-windmill-instance.com

# Sync workspace
wmill workspace sync push
```

## Configuration Steps

### 1. Create Resources
Before running scripts, create these resources in Windmill:

#### OpenStack Connection
- Type: `openstack_connection`
- Fields: auth_url, username, password, project_name, region_name
- Name: `openstack_prod`

#### NetBox API
- Type: `netbox_api`
- Fields: base_url, api_token
- Name: `netbox_prod`

#### Hyperstack API
- Type: `hyperstack_api`
- Fields: api_key, firewall_id_map (JSON)
- Name: `hyperstack_prod`

### 2. Set Variables
Create these workspace variables:

- `GPU_TYPES`: `["H100", "A100", "L40", "RTX-A6000"]`
- `CACHE_TTL_MINUTES`: `10`
- `PARALLEL_WORKERS`: `4`

### 3. Test Scripts
Test individual scripts before running flows:
1. `f/gpu_manager/scripts/data/get_gpu_types` - Should return GPU types
2. `f/gpu_manager/scripts/openstack/get_aggregates` - Should list aggregates
3. `f/gpu_manager/scripts/netbox/get_devices` - Should return NetBox data

### 4. Test Flows
Run flows in test mode first:
1. `migrate_host` - Test with dry-run parameter
2. `refresh_data` - Verify data loads correctly

### 5. Launch App
Open `f/gpu_manager/apps/gpu_dashboard` and verify:
- All tabs load
- Tables populate with data
- Filters work
- Actions trigger flows correctly

## Architecture Overview

### Data Flow
```
User opens App
    ↓
Background Runnables load data (every 10 min)
    ↓
Tables display hosts by GPU type and pool
    ↓
User selects host and target aggregate
    ↓
Button triggers migrate_host Flow
    ↓
Flow validates → removes → adds → verifies → updates cache
    ↓
App refreshes and shows updated host location
```

### Caching Strategy
- Windmill's native caching reduces API calls
- Background runnables refresh data periodically
- Manual refresh button forces immediate update
- Flows invalidate cache after operations

### Error Handling
- Scripts raise descriptive exceptions
- Flows have error handler branches
- App displays error notifications
- All operations logged in Windmill audit trail

## Key Differences from Flask Version

### What Changed
- **No Flask**: Windmill handles routing, requests, responses
- **Stateless**: Workers don't maintain state; use Windmill state
- **No globals**: No global cache dictionaries; use Windmill cache
- **Declarative UI**: App defined in YAML, not HTML/JS files

### What Improved
- **Auto APIs**: Every script is automatically an API
- **Built-in auth**: User permissions, OAuth, API keys included
- **Job queue**: Background processing, retries, monitoring
- **Audit logs**: All operations logged automatically
- **Version control**: Git sync out of the box
- **Scheduling**: UI-based cron scheduling

### What's Different
- **Drag-and-drop**: Simulated with row selection + buttons (not true drag-and-drop)
- **Real-time**: Polling-based (background runnables) vs potential WebSocket
- **Customization**: Less flexible than custom Flask routes

## Troubleshooting

### Scripts fail to import
- Check Python syntax (must have `main()` function)
- Verify dependencies in requirements
- Ensure type hints are correct

### Flows don't execute
- Verify all referenced scripts exist
- Check input parameter mappings
- Review error logs in Windmill UI

### App doesn't load data
- Check background runnables are enabled
- Verify resource credentials are correct
- Test underlying scripts independently

### Missing dependencies
- Add Python packages in Windmill workspace settings
- Or use `pip install` inline in scripts

## Support

For issues specific to:
- **Windmill**: https://docs.windmill.dev/ or Discord
- **This conversion**: See WINDMILL_ARCHITECTURE.md and MIGRATION_GUIDE.md
- **Original app**: See main README.md in repo root

## Next Steps

1. Review [WINDMILL_SETUP.md](./WINDMILL_SETUP.md) for detailed setup guide
2. Read [WINDMILL_ARCHITECTURE.md](./WINDMILL_ARCHITECTURE.md) to understand the architecture
3. Check [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for differences from Flask version
4. Import to your Windmill instance and test
5. Customize as needed for your environment

---

**Ready to import?** Follow the "How to Import to Windmill" section above to get started!
