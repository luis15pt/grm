# GRM - GPU Resource Manager

*The CRM for GPU Infrastructure*

A comprehensive web-based management platform for GPU compute resources across multiple cloud providers, providing unified control over OpenStack, RunPod, contract hardware, and multi-cloud resource management.

## Overview

GRM (GPU Resource Manager) is a Flask-based application that enables efficient management of GPU resources across multiple platforms and resource pools (OpenStack on-demand/spot, RunPod cloud instances, contract hardware). Like how CRM revolutionized customer management, GRM provides a unified interface for GPU infrastructure management with real-time monitoring, drag-and-drop operations, and automated resource optimization.

## Features

### Core Functionality
- **Multi-Platform GPU Management**: Unified interface for OpenStack, RunPod, and contract hardware
- **Real-time GPU Monitoring**: Track GPU utilization and VM counts across all platforms
- **Drag-and-Drop Operations**: Intuitive interface for resource migrations between pools
- **Modular Column System**: Clean, uniform layout with consistent spacing and headers
- **Contract Management**: Dedicated interface for multi-tenant contract hardware management
- **Background Data Loading**: Automatic preloading with intelligent multi-level caching

### Advanced Features
- **Intelligent Cache Updates**: Instant UI feedback - VM launches and host migrations appear immediately without waiting for cache expiry
- **RunPod Integration**: Deploy VMs directly to RunPod platform via Hyperstack API
- **NetBox Integration**: Automatic tenant and owner group classification
- **NetBox Branch Switching**: Switch between NetBox branches with automatic cache invalidation
- **Parallel Data Collection**: 4-agent concurrent system reduces load times from ~300s to ~30s
- **Smart Caching**: Multi-level TTL-based caching with targeted updates
- **Bulk Operations**: Concurrent processing for large-scale operations
- **Command Logging**: Complete audit trail of all operations
- **Responsive Design**: Bootstrap-based UI that works on all devices

### Rack View
- **Physical Rack Visualization**: Visual rack elevation view showing device positions and U-heights
- **Global Search**: Search across all racks and devices
- **Color-Coded Aggregates**: Visual distinction between spot, on-demand, and contract aggregates
- **GPU Usage Indicators**: Yellow highlighting for in-use devices, segmented GPU bar visualization
- **Investor Availability Stats**: Summary of available capacity for investors
- **Platform Icons**: Visual identification of device platforms

### Aggregate Variants
- **Drain Aggregates**: Support for maintenance/drain modes (A100-n3-Drain, RTX-A6000-n3-Drain)
- **NVLink Variants**: Separate column display for NVLink-enabled aggregates
- **Drain Variants**: Displayed as separate columns alongside NVLink variants

### Supported GPU Types
- **L40**: High-performance compute GPUs
- **RTX-A6000**: Professional workstation GPUs
- **A100**: Data center AI/ML GPUs
- **H100**: Next-generation AI training GPUs
- **RTX 5090**: Latest generation consumer/prosumer GPUs (with NVIDIA UVM stability fix)

## Performance

### Intelligent Caching System
- **Parallel Data Collection**: 4-agent concurrent system processes 100+ hosts in ~30s vs previous ~300s
- **Smart Cache Updates**: VM launches and host migrations update cache instantly instead of waiting 10 minutes
- **Multi-Level TTL Caching**: NetBox (30min), Aggregates (1hr), Parallel data (10min) with targeted invalidation
- **Real-Time Feedback**: UI shows changes immediately without manual refresh

### Optimization Results
- **10x Faster**: Data collection optimized from 5+ minutes to <30 seconds
- **Instant Updates**: Operations appear in UI immediately vs 10-minute cache wait
- **Reduced API Load**: Intelligent caching minimizes redundant OpenStack API calls
- **Better UX**: No more "refresh and wait" - changes appear instantly

## Quick Start

### Prerequisites
- OpenStack environment with properly configured aggregates
- Python 3.8+ and pip
- Network access to OpenStack APIs

### Installation
```bash
# Clone the repository
git clone https://github.com/your-org/grm.git
cd grm

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OpenStack credentials

# Run the application
python app.py
```

Navigate to `http://localhost:6969` to access the web interface.

## Documentation

- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Complete setup and deployment instructions
- **[API Documentation](API_DOCUMENTATION.md)** - REST API endpoints and examples
- **[Architecture Overview](ARCHITECTURE.md)** - System design and component interactions
- **[Frontend Guide](FRONTEND_DOCUMENTATION.md)** - JavaScript modules and UI components

## Configuration

### Required Environment Variables
```bash
# OpenStack Authentication
OS_AUTH_URL=https://your-openstack.com:5000/v3
OS_USERNAME=your-username
OS_PASSWORD=your-password
OS_PROJECT_NAME=your-project
OS_USER_DOMAIN_NAME=Default
OS_PROJECT_DOMAIN_NAME=Default
```

### Optional Integrations
```bash
# NetBox DCIM Integration
NETBOX_URL=https://your-netbox.com
NETBOX_API_KEY=your-netbox-token

# RunPod/Hyperstack Integration
HYPERSTACK_API_KEY=your-hyperstack-key
RUNPOD_API_KEY=your-runpod-key
```

## Screenshots

### Main Dashboard
![Dashboard](docs/images/dashboard.png)
*Real-time GPU utilization across all resource pools*

### Host Migration
![Migration](docs/images/migration.png)
*Drag-and-drop host migration between aggregates*

### Contract Management
![Contract](docs/images/contract.png)
*Dedicated contract aggregate management interface*

### Rack View
![Rack View](docs/images/rack-view.png)
*Physical rack elevation visualization with color-coded aggregates and GPU usage indicators*

## Architecture

The system consists of:
- **Flask Backend**: REST API server with OpenStack integration
- **JavaScript Frontend**: Responsive web interface with real-time updates
- **External Integrations**: OpenStack, NetBox, Hyperstack APIs
- **Background Processing**: Concurrent data loading and caching

## Development

### Local Development
```bash
# Run in development mode with auto-reload
export FLASK_ENV=development
python app.py
```

### Testing
```bash
# Run test suite
python -m pytest tests/

# Test specific components
python -m pytest tests/test_api.py
```

## Production Deployment

### Using Gunicorn
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:6969 app:app
```

### Using Docker
```bash
# Build container
docker build -t grm .

# Run container
docker run -p 6969:6969 --env-file .env grm
```

See [Deployment Guide](DEPLOYMENT_GUIDE.md) for complete production setup instructions.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- All credentials are managed via environment variables
- API keys are masked in logs and UI
- Comprehensive input validation on all endpoints
- Secure session management

## Support

- **Issues**: Report issues on GitHub Issues
- **Discussions**: Community discussions on GitHub Discussions
- **Documentation**: Complete docs in the `/docs` directory

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Windmill Version 🌬️

**NEW**: This project has been converted to Windmill for improved scalability, maintainability, and enterprise features!

### What is Windmill?

[Windmill](https://www.windmill.dev/) is an open-source developer platform that turns scripts into auto-generated UIs, APIs, and workflows. The Windmill version of GRM provides:

- **Enterprise-grade orchestration**: Built-in job queue, retries, error handling
- **Better scalability**: Horizontal scaling with worker pools
- **Native caching**: PostgreSQL-backed caching across workers
- **Automatic APIs**: Every script is auto-exposed as an API
- **Built-in RBAC**: User permissions, audit logs, encrypted credentials
- **Git-based deployment**: Version control with auto-deployment
- **No manual server management**: Windmill handles everything

### Getting Started with Windmill Version

```bash
# Switch to Windmill conversion branch
git checkout windmill-conversion

# Navigate to Windmill workspace
cd windmill/

# See setup guide
cat WINDMILL_SETUP.md
```

### Key Documentation

- **[WINDMILL_SETUP.md](windmill/WINDMILL_SETUP.md)** - Complete setup and configuration guide
- **[WINDMILL_ARCHITECTURE.md](windmill/WINDMILL_ARCHITECTURE.md)** - Technical architecture details
- **[MIGRATION_GUIDE.md](windmill/MIGRATION_GUIDE.md)** - Differences from Flask version

### Windmill vs Flask Comparison

| Feature | Flask Version | Windmill Version |
|---------|---------------|------------------|
| **Deployment** | Manual (Gunicorn + Docker) | Auto-deploy via Git sync |
| **Scaling** | Vertical only | Horizontal (add workers) |
| **Caching** | Manual (in-memory dicts) | Native (PostgreSQL) |
| **APIs** | Manual Flask routes | Auto-generated |
| **Auth/RBAC** | Custom or none | Built-in |
| **Audit logs** | Custom logging | Built-in |
| **Error handling** | Manual try-catch | Flow-based with retries |
| **State persistence** | Lost on restart | PostgreSQL-backed |

### Which Version to Use?

**Use Flask Version if:**
- You prefer traditional web app architecture
- You want full control over UI/UX
- You have specific Flask integrations
- You're running on a single server

**Use Windmill Version if:**
- You want enterprise features (RBAC, audit logs)
- You need horizontal scaling
- You prefer declarative workflows
- You want Git-based deployment
- You need multi-tenant support
- You want automatic API generation

### Structure

The Windmill version is organized as:

```
windmill/
├── f/gpu_manager/
│   ├── scripts/          # 20+ Python scripts (business logic)
│   │   ├── openstack/   # OpenStack operations
│   │   ├── netbox/      # NetBox integration
│   │   ├── host/        # Host management
│   │   └── data/        # Data collection
│   ├── flows/           # Multi-step workflows
│   │   └── migrate_host.flow/
│   └── apps/            # UI applications
│       └── gpu_dashboard.app/
├── resources/           # Credential schemas
├── WINDMILL_SETUP.md    # Setup guide
├── WINDMILL_ARCHITECTURE.md  # Technical docs
└── MIGRATION_GUIDE.md   # Migration guide
```

### Quick Deploy to Windmill

1. **Set up Windmill instance** (https://www.windmill.dev/)
2. **Configure Git Sync** in Windmill UI
3. **Point to this repo** (windmill-conversion branch)
4. **Auto-deploys** all scripts, flows, and apps
5. **Create resources** (OpenStack, NetBox credentials)
6. **Launch dashboard** and start managing GPUs!

### Features Implemented

✅ **19 Core Scripts**:
- **OpenStack** (6): Aggregate discovery, host migration, validation
- **NetBox** (3): Device tenant lookups, GPU inventory
- **Host** (3): VM counts, GPU usage info
- **Hyperstack** (3): VM deployment, firewall, status checks
- **Data** (1): Master parallel data collection
- **Utility** (1): List/filter hosts by pool/GPU/owner

✅ **3 Orchestration Flows**:
- **migrate_host**: Complete single host migration with validation
- **launch_runpod_vm**: Deploy VM on RunPod with firewall
- **bulk_migrate_hosts**: Parallel bulk migration workflow

✅ **3 Resource Types**:
- OpenStack connection credentials
- NetBox API credentials
- Hyperstack/RunPod API credentials

✅ **API Access**:
- Every script auto-exposed as REST API
- Webhook support for external triggers
- Token-based authentication

### Usage Examples

**List all H100 spot hosts:**
```bash
# Via Windmill UI
Scripts → list_hosts_by_pool → Run
gpu_type: "H100", pool_type: "spot"
```

**Migrate a single host:**
```bash
# Via Windmill UI
Flows → migrate_host → Run
hostname: "gpu-h100-spot-001"
source: "H100-n3-spot", target: "H100-n3"
```

**Bulk migrate multiple hosts:**
```bash
# Via API
curl -X POST .../bulk_migrate_hosts \
  -d '{"hostnames": ["host1", "host2", "host3"], ...}'
```

**Deploy RunPod VM:**
```bash
# Via Windmill UI
Flows → launch_runpod_vm → Run
hostname: "runpod-h100-new-001"
```

See **[USAGE_GUIDE.md](windmill/USAGE_GUIDE.md)** for detailed examples!

### Future Enhancements

**Potential additions:**
- Frontend dashboard (once workflows are solid)
- Automated idle host detection
- Cost optimization workflows
- Slack/Discord notification integrations
- Advanced reporting and analytics

### Support

For Windmill-specific questions:
- **Windmill Docs**: https://docs.windmill.dev/
- **Discord**: https://discord.com/invite/V7PM2YHsPB
- **Issues**: Open an issue with [Windmill] prefix

---

## Acknowledgments

- OpenStack SDK for cloud integration
- Bootstrap for responsive UI framework (Flask version)
- Font Awesome for icons and visual elements
- Windmill for the enterprise orchestration platform