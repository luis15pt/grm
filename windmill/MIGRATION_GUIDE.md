# Migration Guide: Flask to Windmill

This guide explains the key differences between the Flask version and Windmill version of the GPU Resource Manager, and how to adapt your workflows.

## High-Level Differences

| Aspect | Flask Version | Windmill Version |
|--------|---------------|------------------|
| **Architecture** | Monolithic web app | Distributed scripts + flows + app |
| **State** | Global variables, thread locks | Stateless scripts, Windmill PostgreSQL |
| **Caching** | Manual (dictionaries + TTL) | Built-in (Windmill native) |
| **API** | Manual Flask routes | Auto-generated per script |
| **UI** | Custom HTML/JS/CSS | Declarative YAML (Windmill components) |
| **Auth** | Custom or None | Built-in RBAC |
| **Deployment** | Gunicorn + reverse proxy | Windmill workers + queue |
| **Scaling** | Vertical only | Horizontal (add workers) |

## Code Mapping

### Flask Routes → Windmill Scripts

#### Example 1: Get GPU Types

**Flask (`app_routes.py`):**
```python
@app.route('/api/gpu-types', methods=['GET'])
def get_gpu_types():
    try:
        gpu_aggregates = discover_gpu_aggregates()
        return jsonify({'success': True, 'gpu_types': list(gpu_aggregates.keys())})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Windmill (`f/gpu_manager/scripts/openstack/discover_gpu_aggregates.py`):**
```python
def main(openstack_connection: dict) -> dict:
    """Discover GPU aggregates from OpenStack"""
    conn = openstack.connect(...openstack_connection)
    aggregates = list(conn.compute.aggregates())
    # ... processing ...
    return gpu_aggregates  # Auto-JSONified, auto-API'd
```

**Access:**
- Flask: `GET http://your-flask-app.com/api/gpu-types`
- Windmill: `POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/scripts/openstack/discover_gpu_aggregates`

#### Example 2: Host Migration

**Flask (`app_routes.py`):**
```python
@app.route('/api/execute-migration', methods=['POST'])
def execute_migration():
    data = request.json
    hostname = data['hostname']
    source_agg = data['source_aggregate']
    target_agg = data['target_aggregate']

    # Validation
    validation_result = validate_migration(...)
    if not validation_result['valid']:
        return jsonify({'success': False, 'error': validation_result['message']}), 400

    # Remove from source
    remove_result = remove_host_from_aggregate(...)
    if not remove_result['success']:
        return jsonify({'success': False, 'error': 'Remove failed'}), 500

    # Add to target
    add_result = add_host_to_aggregate(...)
    if not add_result['success']:
        # Rollback?
        return jsonify({'success': False, 'error': 'Add failed'}), 500

    return jsonify({'success': True})
```

**Windmill (`f/gpu_manager/flows/migrate_host.flow/flow.yaml`):**
```yaml
# Declarative workflow with automatic error handling, retries
modules:
  - id: validate
    summary: "Validate migration"
    value:
      type: script
      path: f/gpu_manager/scripts/openstack/validate_migration
      stop_after_if:
        expr: "result.valid === false"

  - id: remove
    summary: "Remove from source"
    value:
      type: script
      path: f/gpu_manager/scripts/openstack/remove_host_from_aggregate
      retry:
        constant: {attempts: 3, seconds: 5}

  - id: add
    summary: "Add to target"
    value:
      type: script
      path: f/gpu_manager/scripts/openstack/add_host_to_aggregate
      retry:
        constant: {attempts: 3, seconds: 5}
```

### Global State → Windmill Resources & Cache

**Flask (`modules/parallel_agents.py`):**
```python
# Global cache (risky - lost on restart, thread-safety issues)
_parallel_cache = {}
_cache_timestamps = {}
_cache_lock = threading.Lock()

def get_all_data_parallel():
    global _parallel_cache

    with _cache_lock:
        if cache_valid(_cache_timestamps.get('all_data')):
            return _parallel_cache['all_data']

        data = expensive_operation()
        _parallel_cache['all_data'] = data
        _cache_timestamps['all_data'] = time.time()
        return data
```

**Windmill:**
```python
# No global state - Windmill handles caching automatically
# Set in script metadata (.script.yaml):
#   cache_ttl: 600  # 10 minutes

def main(openstack_connection: dict, netbox_api: dict) -> dict:
    """Get all GPU data (Windmill caches this automatically)"""
    data = expensive_operation()
    return data  # Cached for 600 seconds
```

### Environment Variables → Resources

**Flask (`.env`):**
```bash
OS_AUTH_URL=https://openstack.example.com:5000/v3
OS_USERNAME=admin
OS_PASSWORD=secret123
OS_PROJECT_NAME=admin
NETBOX_URL=https://netbox.example.com
NETBOX_API_KEY=token123
```

**Windmill (Resource: `openstack_prod`):**
```json
{
  "auth_url": "https://openstack.example.com:5000/v3",
  "username": "admin",
  "password": "secret123",  // ← Encrypted at rest
  "project_name": "admin"
}
```

**Usage:**
```python
# Flask
conn = openstack.connect(
    auth_url=os.getenv('OS_AUTH_URL'),
    username=os.getenv('OS_USERNAME'),
    ...
)

# Windmill (resource auto-injected)
def main(openstack_connection: dict):
    conn = openstack.connect(
        auth_url=openstack_connection['auth_url'],
        username=openstack_connection['username'],
        ...
    )
```

## Feature Mapping

### ✅ Fully Supported (Exact Parity)

| Feature | Flask | Windmill | Notes |
|---------|-------|----------|-------|
| GPU aggregate discovery | ✓ | ✓ | Same logic, converted to script |
| Host migration | ✓ | ✓ | Flow-based with retries |
| VM count retrieval | ✓ | ✓ | Same OpenStack SDK calls |
| GPU usage info | ✓ | ✓ | Same calculation logic |
| NetBox integration | ✓ | ✓ | Same API calls |
| Tenant classification | ✓ | ✓ | Same owner group logic |
| NVLink detection | ✓ | ✓ | Same NetBox custom fields |
| Contract aggregates | ✓ | ✓ | Same pattern matching |
| Spot/On-demand pools | ✓ | ✓ | Same aggregate types |

### 🔄 Modified (Different Implementation)

| Feature | Flask | Windmill | Difference |
|---------|-------|----------|------------|
| **Caching** | Manual (dicts + locks) | Native (PostgreSQL) | Windmill handles it |
| **Parallel execution** | ThreadPoolExecutor | Sequential + cache | Windmill's cache makes it fast enough |
| **Real-time updates** | Potential WebSockets | Background runnables | Polling-based (10min) |
| **Drag-and-drop UI** | Custom JS | Row selection + buttons | Simpler, but functional |
| **Command logging** | Custom append to list | Windmill audit logs | Built-in, better |
| **Error handling** | Try-catch per route | Flow failure handlers | More robust |

### ⚠️ Not Yet Implemented (Future Work)

| Feature | Flask | Windmill | Plan |
|---------|-------|----------|------|
| RunPod VM launch | ✓ | ⏳ | Flow needs to be created |
| Hyperstack operations | ✓ | ⏳ | Scripts need to be created |
| Bulk migrations | ✓ | ⏳ | Flow for concurrent migrations |
| Contract operations | ✓ | ⏳ | Dedicated flow |
| Customer view | ✓ | ⏳ | Separate app with filters |
| Global search | ✓ | ⏳ | AgGrid built-in search |

## UI/UX Differences

### Flask UI

- **Layout**: Custom 4-column flex layout
- **Drag-and-drop**: Native HTML5 drag-and-drop
- **Styling**: Custom CSS (style.css, 63KB)
- **Interactivity**: Vanilla JavaScript (script.js, frontend.js)
- **Filtering**: Custom filter controls
- **Search**: Global search across all hosts

### Windmill UI

- **Layout**: Tabs (GPU types) + Sub-tabs (pools) + AgGrid tables
- **Selection**: Click row → select host, choose target dropdown → migrate button
- **Styling**: Windmill's built-in theme (customizable via CSS overrides)
- **Interactivity**: Declarative YAML + frontend scripts (React-based)
- **Filtering**: AgGrid's built-in column filters
- **Search**: AgGrid's quick search

**Visual Comparison:**

```
Flask:                           Windmill:
┌──────┬──────┬──────┬──────┐   ┌─────────────────────────┐
│On-Dem│Spot  │RunPod│Contr │   │ [H100] [A100] [L40]    │
│      │      │      │      │   │                         │
│ Host │ Host │ Host │ Host │   │ ┌─[On-Demand][Spot]──┐ │
│ Host │ Host │ Host │ Host │   │ │                     │ │
│ Host │ Host │ Host │ Host │   │ │  AgGrid Table       │ │
│ ↓↑   │ ↓↑   │ ↓↑   │ ↓↑   │   │ │  - Hostname         │ │
│      │      │      │      │   │ │  - VMs              │ │
│      │      │      │      │   │ │  - GPU Usage        │ │
└──────┴──────┴──────┴──────┘   │ │  [Select] [Migrate] │ │
Drag hosts between columns       │ └─────────────────────┘ │
                                 │                         │
                                 └─────────────────────────┘
                                 Select row → button action
```

**Trade-off:**
- Flask: More intuitive (drag-and-drop), custom styling
- Windmill: Simpler to maintain, declarative, better for complex tables

## API Access

### Flask API

**Endpoints:** Custom routes in `app_routes.py`

```bash
# Get GPU types
curl http://localhost:6969/api/gpu-types

# Get aggregate data
curl http://localhost:6969/api/aggregates/H100/ondemand

# Execute migration
curl -X POST http://localhost:6969/api/execute-migration \
  -H "Content-Type: application/json" \
  -d '{"hostname": "gpu-host-001", "source_aggregate": "H100-n3-spot", "target_aggregate": "H100-n3"}'
```

**Auth:** None (or custom middleware)

### Windmill API

**Endpoints:** Auto-generated for every script

```bash
# Discover GPU aggregates
curl -X POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/scripts/openstack/discover_gpu_aggregates \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"openstack_connection": "$res:openstack_prod"}'

# Execute migration flow
curl -X POST https://windmill.com/api/w/workspace/jobs/run/f/gpu_manager/flows/migrate_host \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "openstack_connection": "$res:openstack_prod",
    "hostname": "gpu-host-001",
    "source_aggregate": "H100-n3-spot",
    "target_aggregate": "H100-n3"
  }'

# Check job status
curl https://windmill.com/api/w/workspace/jobs/completed/JOB_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Auth:** Required (Windmill tokens)

## Performance Comparison

### Data Loading

| Metric | Flask (Optimized) | Windmill |
|--------|-------------------|----------|
| **Cold start** (no cache) | ~30 seconds | ~30-60 seconds (first run) |
| **Warm load** (cached) | <1 second | <1 second |
| **Cache invalidation** | Manual (clear cache function) | Automatic (TTL expiry) |
| **Concurrent users** | Limited by Flask workers | Unlimited (job queue) |
| **Cache persistence** | Lost on restart | Persisted (PostgreSQL) |

### Migration Operations

| Metric | Flask | Windmill |
|--------|-------|----------|
| **Validation** | Immediate | Immediate |
| **Execution** | 5-10 seconds | 5-10 seconds |
| **Retry logic** | Manual | Built-in (3 attempts) |
| **Error recovery** | Manual rollback | Declarative failure handler |
| **Audit trail** | Custom logging | Built-in audit logs |

## Workflow Changes

### Flask Workflow (Typical User)

1. Open `http://localhost:6969`
2. Wait for data to load (~1 sec if cached)
3. Find host in appropriate column
4. Drag host to target column
5. Confirm migration in popup
6. Wait for operation to complete
7. See host in new location

### Windmill Workflow (Typical User)

1. Open Windmill → Apps → `gpu_dashboard`
2. Wait for background runnable to load data (~1 sec if cached)
3. Select GPU type tab (e.g., H100)
4. Select pool tab (e.g., Spot)
5. Click row to select host
6. Choose target aggregate from dropdown
7. Click "Migrate Host" button
8. Flow executes (with progress indicator)
9. Refresh button or wait for auto-refresh
10. See host in new location

**Difference:** More clicks in Windmill, but more explicit and auditable.

## Development Workflow

### Flask Development

```bash
# Edit code
vim app_routes.py

# Restart server
pkill -f "python app.py"
python app.py

# Test
curl http://localhost:6969/api/...
```

### Windmill Development

```bash
# Edit script
vim windmill/f/gpu_manager/scripts/openstack/discover_gpu_aggregates.py

# Commit to Git
git add .
git commit -m "Update aggregate discovery"
git push

# Windmill Git Sync auto-deploys

# Test in Windmill UI
# Scripts → discover_gpu_aggregates → Run
```

**Or (faster for iteration):**

```bash
# Edit script locally
vim windmill/f/gpu_manager/scripts/openstack/discover_gpu_aggregates.py

# Use Windmill CLI to sync immediately
wmill script push f/gpu_manager/scripts/openstack/discover_gpu_aggregates \
  --path-to-script discover_gpu_aggregates.py

# Test in UI immediately
```

## Deployment Differences

### Flask Deployment

```bash
# Clone repo
git clone ...
cd openstack-spot-manager

# Install deps
pip install -r requirements.txt

# Configure
cp .env.example .env
vim .env  # Add credentials

# Run
python app.py
# Or: gunicorn app:app -w 4 -b 0.0.0.0:6969
```

**Scaling:**
- Vertical: Increase Gunicorn workers
- Horizontal: Load balancer + multiple instances (but shared cache problem!)

### Windmill Deployment

```bash
# Option 1: Configure Git Sync in Windmill UI
# Settings → Git Sync → Connect repo → Done

# Option 2: CLI sync
wmill workspace sync push

# No additional deployment needed:
# - Workers auto-scale
# - Cache in PostgreSQL (shared across workers)
# - No manual process management
```

**Scaling:**
- Horizontal: Add more Windmill worker nodes
- Automatic load balancing via job queue

## Migration Checklist

If you're transitioning from Flask to Windmill:

- [ ] **Export configurations**
  - [ ] Copy `.env` values to Windmill resources
  - [ ] Document any custom settings

- [ ] **Test core operations**
  - [ ] Aggregate discovery
  - [ ] Host VM counts
  - [ ] NetBox integration
  - [ ] Host migration (dry-run first!)

- [ ] **Train users**
  - [ ] Show new UI (row selection vs drag-and-drop)
  - [ ] Explain migration workflow
  - [ ] Demonstrate error handling

- [ ] **Run in parallel** (recommended)
  - [ ] Keep Flask running for 1-2 weeks
  - [ ] Users test Windmill version
  - [ ] Compare results between both
  - [ ] Gradually shift traffic

- [ ] **Cutover**
  - [ ] Announce deprecation of Flask version
  - [ ] Point users to Windmill URL
  - [ ] Monitor for issues
  - [ ] Decommission Flask after burn-in period

## Troubleshooting

### "It worked in Flask but not Windmill"

**Common causes:**

1. **Environment differences**
   - Solution: Verify resources have correct credentials
   - Check: OpenStack endpoints, NetBox URLs

2. **Caching behavior**
   - Flask had manual cache control
   - Windmill uses TTL-based caching
   - Solution: Adjust `cache_ttl` in `.script.yaml` files

3. **Permissions**
   - Windmill requires explicit resource permissions
   - Solution: Grant user access to resources

4. **Python dependencies**
   - Windmill workers might not have same packages
   - Solution: Add to workspace dependencies

### "Migration failed in Windmill"

**Debug steps:**

1. Check flow execution logs (Runs → select job → View logs)
2. Identify which step failed (validate/remove/add/verify)
3. Run that step's script individually with same inputs
4. Check OpenStack credentials in resource
5. Verify network connectivity from Windmill workers

### "Performance is worse in Windmill"

**Optimization:**

1. **Increase cache TTL**: Scripts run less frequently
2. **Use background runnables**: Pre-populate cache
3. **Add dedicated workers**: For heavy operations
4. **Check worker resources**: CPU/memory sufficient?

## Getting Help

- **Windmill Docs**: https://docs.windmill.dev/
- **Windmill Discord**: https://discord.com/invite/V7PM2YHsPB
- **This Project**: See `WINDMILL_ARCHITECTURE.md` for technical details

---

**Bottom Line:** The Windmill version trades some UI intuitiveness for significantly better scalability, maintainability, security, and operational excellence. The underlying business logic is identical.
