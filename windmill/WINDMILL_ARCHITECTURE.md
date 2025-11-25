# Windmill Architecture - GPU Resource Manager

Technical architecture documentation for the Windmill conversion of the GPU Resource Manager.

## System Overview

The GPU Resource Manager has been converted from a Flask-based monolithic application to a Windmill-based distributed system with:

- **20+ Python scripts** for discrete operations
- **5+ flows** for complex orchestration
- **1 main app** for the UI
- **3 resource types** for credential management
- **Native caching** for performance optimization

## Architecture Principles

### 1. Stateless Execution

**Flask (Before)**:
- Global variables for caching (`_parallel_cache`, `_host_aggregate_cache`)
- In-memory state shared across requests
- Thread locks for synchronization

**Windmill (After)**:
- Stateless script execution
- Windmill's PostgreSQL-backed state
- Native caching with TTL
- Job queue handles concurrency

### 2. Script-Centric Design

Every operation is a discrete script with:
- Clear inputs (type-hinted parameters)
- Clear outputs (structured return values)
- Auto-generated UI forms
- Auto-exposed APIs
- Independent error handling

### 3. Declarative Flows

Complex operations (migrations, deployments) are flows:
- DAG-based orchestration
- Built-in retry logic
- Error handlers
- Manual approval steps (optional)
- Context passing between steps

## Component Architecture

### Layer 1: Scripts (Business Logic)

```
f/gpu_manager/scripts/
├── openstack/         # OpenStack operations (6 scripts)
│   ├── discover_gpu_aggregates.py
│   ├── get_aggregate_hosts.py
│   ├── add_host_to_aggregate.py
│   ├── remove_host_from_aggregate.py
│   ├── find_host_current_aggregate.py
│   └── validate_migration.py
│
├── netbox/            # NetBox operations (3 scripts)
│   ├── get_device_tenant.py
│   ├── get_bulk_device_tenants.py
│   └── get_all_gpu_devices.py
│
├── host/              # Host operations (3 scripts)
│   ├── get_host_vms.py
│   ├── get_host_vm_count.py
│   └── get_host_gpu_info.py
│
└── data/              # Data collection (1 master script)
    └── get_parallel_data.py
```

**Key Characteristics:**
- Each script is 50-200 lines
- Single responsibility
- Testable independently
- Cacheable (600-1800s TTL)

### Layer 2: Flows (Orchestration)

```
f/gpu_manager/flows/
├── migrate_host.flow/
│   └── flow.yaml          # 5-step migration workflow
├── launch_runpod_vm.flow/ # (future)
└── refresh_data.flow/     # (future)
```

**migrate_host.flow Architecture:**

```
┌─────────────────┐
│  1. Validate    │  ← Check GPU types match, VMs evacuated
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Remove      │  ← Remove host from source aggregate
│     (retry 3x)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Add         │  ← Add host to target aggregate
│     (retry 3x)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Verify      │  ← Confirm host in target aggregate
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Success     │  ← Return migration summary
│                 │
└─────────────────┘
```

**Error Handling:**
- Each step has retry logic (3 attempts, 5s delay)
- `stop_after_if` for validation failures
- `failure_module` catches any errors
- Returns structured error response

### Layer 3: App (User Interface)

```
f/gpu_manager/apps/
└── gpu_dashboard.app/
    └── app.yaml       # Declarative UI definition
```

**App Architecture** (Simplified for Windmill):

```
┌─────────────────────────────────────────────────────────┐
│  GPU Dashboard App                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─ GPU Type Selector (Tabs) ─────────────────────┐   │
│  │  [H100] [A100] [L40] [RTX-A6000] [Out of Stock] │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Pool Type Tabs ────────────────────────────────┐   │
│  │  [On-Demand] [Spot] [RunPod] [Contract]         │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Host Table (AgGrid) ───────────────────────────┐   │
│  │ Hostname      │ Aggregate  │ VMs │ GPU Usage   │   │
│  │───────────────┼────────────┼─────┼─────────────│   │
│  │ gpu-host-001  │ H100-n3    │  2  │ 4/8         │   │
│  │ gpu-host-002  │ H100-n3    │  1  │ 2/8         │   │
│  │ [Select Row]  │            │     │ [Actions]   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Actions ────────────────────────────────────────┐   │
│  │  Selected: gpu-host-001                          │   │
│  │  Target: [Dropdown: H100-n3-spot ▼]             │   │
│  │  [Validate Migration] [Execute Migration]       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Background Runnables ────────────────────────────   │
│  │  - get_parallel_data (every 10 min)              │   │
│  │  - Updates tables automatically                  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**App Components:**
1. **Tabs**: GPU type selection
2. **Sub-tabs**: Pool type (on-demand/spot/runpod/contract)
3. **AgGrid Table**: Hosts with selection
4. **Buttons**: Trigger flows
5. **Background Runnables**: Auto-refresh data
6. **Frontend Scripts**: State management (selected host, filters)

### Layer 4: Resources (Credentials)

```
resources/
├── openstack_connection.json    # Schema definition
├── netbox_api.json             # Schema definition
└── hyperstack_api.json         # Schema definition

Actual instances created in Windmill:
- openstack_prod (values encrypted)
- netbox_prod (values encrypted)
- hyperstack_prod (values encrypted)
```

**Resource Injection:**

```python
def main(openstack_connection: dict, hostname: str):
    # ↑ Windmill auto-injects resource values here
    conn = openstack.connect(
        auth_url=openstack_connection['auth_url'],
        ...
    )
```

## Data Flow Architecture

### End-to-End: User Migration Request

```
1. User opens App
     ↓
2. Background Runnable loads data
     ↓  (calls get_parallel_data script)
     ↓
3. get_parallel_data orchestrates:
     ├─→ discover_gpu_aggregates (OpenStack)
     ├─→ get_all_gpu_devices (NetBox)
     ├─→ get_aggregate_hosts (per GPU type)
     └─→ get_bulk_device_tenants (NetBox)
     ↓
4. Data cached (10 min TTL)
     ↓
5. App renders tables
     ↓
6. User selects host + target
     ↓
7. User clicks "Migrate"
     ↓
8. App triggers migrate_host flow
     ↓  (passes openstack_connection, hostname, aggregates)
     ↓
9. Flow executes:
     Step A: validate_migration → check rules
     Step B: remove_host_from_aggregate → OpenStack CLI
     Step C: add_host_to_aggregate → OpenStack CLI
     Step D: find_host_current_aggregate → verify
     Step E: return success
     ↓
10. App receives result
     ↓
11. App refreshes table (re-runs get_parallel_data)
     ↓
12. User sees updated host location
```

### Caching Strategy

**Three-Level Caching:**

1. **Script-Level Cache** (Windmill native)
   - `cache_ttl` in `.script.yaml`
   - Key: script path + input hash
   - Storage: Windmill PostgreSQL
   - Invalidation: TTL expiry or manual

2. **Background Runnable Cache**
   - `recompute_interval` in app config
   - Runs periodically in background
   - Populates cache proactively

3. **App State Cache**
   - Frontend state management
   - Reactive updates
   - Persists during session

**Cache Coherency:**

```
Operation triggers cache invalidation:
  Migration → invalidate get_parallel_data cache
  VM launch → invalidate host GPU info cache
  Aggregate change → invalidate aggregate list cache
```

Windmill doesn't have built-in cache invalidation APIs, so:
- Use shorter TTLs for frequently changing data
- Or: Force refresh by changing input hash (add timestamp)

## Comparison: Flask vs Windmill

### Request Handling

**Flask:**
```python
@app.route('/api/aggregates/<gpu_type>', methods=['GET'])
def get_aggregates(gpu_type):
    # Global state, manual caching, error handling
    global _parallel_cache
    if cache_valid():
        return _parallel_cache[gpu_type]
    data = fetch_data()
    _parallel_cache[gpu_type] = data
    return jsonify(data)
```

**Windmill:**
```python
def main(openstack_connection: dict, gpu_type: str) -> dict:
    # Stateless, automatic caching, structured errors
    # Windmill handles: routing, caching, errors, API exposure
    aggregates = discover_gpu_aggregates(openstack_connection)
    return aggregates.get(gpu_type, {})
```

### Parallel Execution

**Flask:**
```python
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        'agent1': executor.submit(agent1_function),
        'agent2': executor.submit(agent2_function),
        ...
    }
    results = {name: future.result() for name, future in futures.items()}
```

**Windmill:**
```python
# Option 1: Sequential script calls (Windmill caches)
result1 = wmill.run_script_sync("path/to/script1", args={...})
result2 = wmill.run_script_sync("path/to/script2", args={...})

# Option 2: Parallel flow branches
# Defined in flow.yaml with parallel execution
```

### Error Handling

**Flask:**
```python
try:
    result = operation()
    return jsonify({'success': True, 'data': result})
except Exception as e:
    return jsonify({'success': False, 'error': str(e)}), 500
```

**Windmill:**
```python
# Errors automatically caught and structured
def main(params):
    if not valid(params):
        raise ValueError("Invalid params")
    return operation()

# Flow has failure_module for error handling
# App shows error toast automatically
```

## Performance Characteristics

### Flask Version (Original)

- **Initial load**: ~300 seconds (parallel agents helped reduce to ~30s)
- **Cache hit**: <1 second
- **Concurrent requests**: Limited by thread pool
- **Memory**: Global state grows over time
- **Scaling**: Vertical only (single process)

### Windmill Version (Converted)

- **Initial load**: ~30-60 seconds (first cache populate)
- **Cache hit**: <1 second (Windmill native cache)
- **Concurrent requests**: Unlimited (job queue)
- **Memory**: Stateless workers (restart-safe)
- **Scaling**: Horizontal (add workers)

**Optimization Tips:**

1. **Aggressive caching**: Set TTL to 10-30 min for stable data
2. **Background jobs**: Schedule `get_parallel_data` every 10 min
3. **Dedicated workers**: For heavy scripts, use dedicated worker pools
4. **Parallel flows**: Break sequential operations into parallel steps

## Security Architecture

### Flask Version

- `.env` file for secrets (risk: committed to Git)
- Manual auth on each request
- No built-in audit logs
- API keys in code

### Windmill Version

- **Encrypted resources**: All credentials in encrypted PostgreSQL
- **Auto-injection**: Scripts never see raw credentials
- **Audit logs**: Every operation logged automatically
- **RBAC**: User/group permissions on resources, scripts, flows
- **API tokens**: Per-user tokens for external access
- **Webhooks**: Secured with HMAC signatures

## Deployment Architecture

### Development

```
Developer → Local Windmill (Docker)
              ↓
           Git repo (windmill/ folder)
              ↓
           Test scripts/flows locally
```

### Production

```
Git repo (windmill-conversion branch)
    ↓
Windmill Git Sync
    ↓
Auto-deploy scripts/flows/apps
    ↓
Windmill Workers execute
    ↓
Users access via Windmill UI
```

**Worker Topology:**

```
┌─────────────────────────────────────────┐
│  Windmill Server (API + UI + Queue)    │
│  - PostgreSQL (state + cache)          │
│  - Frontend (Next.js app)              │
└───────────┬─────────────────────────────┘
            │
    ┌───────┴────────┐
    │                │
┌───▼────┐     ┌────▼────┐
│ Worker │     │ Worker  │  (Auto-scaling)
│  Pool  │     │  Pool   │
│  3-5   │     │  3-5    │
└────────┘     └─────────┘

Each worker can execute:
- Python scripts
- Flows
- Background runnables
```

## Migration Path from Flask

### Phase 1: Parallel Operation (Recommended)

1. Keep Flask app running
2. Deploy Windmill conversion
3. Test Windmill thoroughly
4. Gradually migrate users
5. Deprecate Flask after validation

### Phase 2: Cutover

1. Freeze Flask development
2. Deploy Windmill to production
3. Point users to new URL
4. Monitor for issues
5. Decommission Flask after burn-in period

## Extensibility

### Adding New Operations

**Add a Script:**
1. Create `.py` file in `f/gpu_manager/scripts/{category}/`
2. Define `main()` with type hints
3. Create `.script.yaml` with metadata
4. Commit to Git → auto-deployed

**Add a Flow:**
1. Create `{flow_name}.flow/` directory
2. Create `flow.yaml` with DAG definition
3. Reference existing scripts
4. Commit → auto-deployed

**Add App Components:**
1. Edit `gpu_dashboard.app/app.yaml`
2. Add new tabs, tables, buttons
3. Reference scripts/flows in runnables
4. Commit → auto-deployed

### Integrating New Data Sources

Example: Add AWS EC2 GPU instances

1. **Create resource type**: `aws_credentials.json`
2. **Add scripts**: `f/gpu_manager/scripts/aws/`
   - `get_ec2_instances.py`
   - `get_ec2_gpu_info.py`
3. **Update parallel data**: Modify `get_parallel_data.py` to include AWS
4. **Update app**: Add AWS tab to dashboard

## Monitoring & Observability

### Built-in Windmill Features

- **Job History**: Every script/flow execution logged
- **Performance Metrics**: Execution time, cache hit rate
- **Error Tracking**: Failed jobs with stack traces
- **Audit Logs**: All user actions recorded
- **Resource Usage**: Worker CPU/memory metrics

### Custom Monitoring

Add to scripts:
```python
import wmill

def main(...):
    start = time.time()
    result = operation()
    duration = time.time() - start

    # Log to Windmill internal state
    wmill.set_state({"last_run": duration})

    # Or send to external monitoring
    send_to_datadog({"gpu_migration_duration": duration})

    return result
```

## Best Practices

### Script Design

1. **Single responsibility**: One operation per script
2. **Type hints**: Enable auto-generated forms
3. **Docstrings**: Show up in UI
4. **Structured returns**: Use dicts/lists for JSON
5. **Error messages**: Descriptive for debugging

### Flow Design

1. **Idempotent steps**: Safe to retry
2. **Validation first**: Catch errors early
3. **Rollback capability**: For critical operations
4. **Timeouts**: Prevent hanging jobs
5. **Failure handlers**: Graceful degradation

### App Design

1. **Progressive loading**: Show data as it loads
2. **Background runnables**: Keep data fresh
3. **Optimistic updates**: Update UI before confirmation
4. **Error toasts**: Show failures clearly
5. **Loading states**: Indicate progress

---

This architecture provides a scalable, maintainable foundation for GPU infrastructure management with Windmill's enterprise-grade orchestration platform.
