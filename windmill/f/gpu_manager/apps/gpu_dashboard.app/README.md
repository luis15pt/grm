# GPU Dashboard App

This is a simplified example of the GPU Resource Manager dashboard built for Windmill.

## Structure

- `app.yaml`: Main app definition (declarative UI)
- `inline_scripts/`: Frontend scripts for interactivity (if needed)

## Components

### 1. GPU Type Selector (Tabs)
- H100, A100, L40, RTX-A6000, Out of Stock
- Sets `state.selectedGpuType`

### 2. Pool Type Selector (Sub-tabs)
- On-Demand, Spot, RunPod, Contract
- Sets `state.selectedPoolType`
- Hidden for "Out of Stock" view

### 3. Host Table (AgGrid)
- Displays hosts for selected GPU type + pool
- Columns: Hostname, Aggregate, VMs, GPU Usage, Tenant, Owner, NVLinks
- Row selection: Click to select host for migration

### 4. Migration Actions Panel
- Shows selected host
- Dropdown to choose target aggregate
- "Validate Migration" button: Checks if migration is allowed
- "Execute Migration" button: Triggers migration flow
- "Refresh Data" button: Force data reload

### 5. Background Runnable
- Auto-loads data every 10 minutes
- Calls `f/gpu_manager/scripts/data/get_parallel_data`
- Populates table automatically

## How to Use

1. **Select GPU Type**: Click tab (H100, A100, etc.)
2. **Select Pool**: Click sub-tab (On-Demand, Spot, etc.)
3. **Select Host**: Click row in table
4. **Choose Target**: Use dropdown to select target aggregate
5. **Validate**: (Optional) Check if migration is allowed
6. **Migrate**: Click "Execute Migration" to start flow
7. **Monitor**: Flow progress shown in Windmill UI
8. **Refresh**: Table auto-refreshes or click button

## Customization

### Add More Filters

Edit `app.yaml` to add filter components:

```yaml
- id: owner_filter
  type: selectcomponent
  configuration:
    label: "Filter by Owner"
    items:
      - Investors
      - Nexgen Cloud
```

### Add Charts

Add visualization components:

```yaml
- id: gpu_usage_chart
  type: chartcomponent
  configuration:
    type: bar
    data:
      expr: "results.gpu_data.summary"
```

### Add More Actions

Add buttons that trigger different flows:

```yaml
- id: bulk_migrate_button
  type: buttoncomponent
  configuration:
    label: "Bulk Migrate"
    runnable:
      type: runnableByPath
      path: f/gpu_manager/flows/bulk_migration
```

## Limitations (Simplified Version)

This example is simplified for demonstration. The full production version would include:

1. **Dynamic aggregate dropdowns**: Populated from discovery script
2. **Real-time progress**: Show flow execution status
3. **Error toasts**: Display validation/execution errors
4. **Loading states**: Skeleton loaders while data loads
5. **Confirmation dialogs**: "Are you sure?" before migrations
6. **Command log viewer**: Show recent operations
7. **Advanced filters**: By tenant, owner, GPU usage, etc.
8. **Drag-and-drop** (if possible in Windmill): More intuitive UX

## Building the Full Version

To create a production-ready dashboard:

1. **Connect data sources**: Wire background runnables to table
2. **State management**: Use frontend scripts for complex state
3. **Error handling**: Add try-catch in inline scripts
4. **Permissions**: Configure resource access per user role
5. **Styling**: Customize CSS for branding
6. **Mobile responsive**: Test on mobile devices
7. **Performance**: Optimize data loading and caching

## Testing

1. **Preview Mode**: Apps → gpu_dashboard → Preview
2. **Test with mock data**: Hardcode sample data in table
3. **Test migrations**: Use dry_run=true first
4. **Monitor logs**: Check background runnable logs
5. **Test permissions**: Different users, different resources

## Deployment

```bash
# Option 1: Git Sync (automatic)
git push origin windmill-conversion
# Windmill auto-deploys

# Option 2: CLI
wmill app push f/gpu_manager/apps/gpu_dashboard

# Option 3: UI
# Apps → Import → Upload app.yaml
```

## Support

For Windmill app development:
- Docs: https://docs.windmill.dev/docs/apps/app_configuration_settings/app_component_library
- Discord: https://discord.com/invite/V7PM2YHsPB
- Examples: https://hub.windmill.dev/apps
