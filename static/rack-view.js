/**
 * Rack View Module for GRM
 * Displays physical rack elevations showing server locations
 * NexGen-owned = green, Investor-owned = grey/transparent
 */

class RackView {
    constructor() {
        this.U_HEIGHT_PX = 18;  // Pixels per rack unit
        this.RACK_WIDTH = 220;  // Width of each rack in pixels
        this.rackData = null;
        this.sites = [];
        this.filters = {
            site: 'CA1',  // Default site
            gpuType: '',
            showNexgen: true,
            showInvestors: true
        };
        this.isLoading = false;
        this.initialized = false;
    }

    /**
     * Initialize the rack view
     */
    async init() {
        if (this.initialized) return;

        console.log('Initializing Rack View...');

        // Load available sites
        await this.loadSites();

        // Set up event listeners
        this.setupEventListeners();

        this.initialized = true;
        console.log('Rack View initialized');
    }

    /**
     * Load available datacenter sites
     */
    async loadSites() {
        try {
            const response = await fetch('/api/rack-visualization/sites');
            const data = await response.json();
            this.sites = data.sites || [];
            this.populateSiteFilter();
        } catch (error) {
            console.error('Failed to load sites:', error);
            this.sites = [{ name: 'CA1', slug: 'ca1' }];  // Default fallback
            this.populateSiteFilter();
        }
    }

    /**
     * Populate the site filter dropdown
     */
    populateSiteFilter() {
        const select = document.getElementById('rackSiteFilter');
        if (!select) return;

        select.innerHTML = '<option value="">All Sites</option>';
        this.sites.forEach(site => {
            const option = document.createElement('option');
            option.value = site.name;
            option.textContent = site.name;
            if (site.name === 'CA1') option.selected = true;
            select.appendChild(option);
        });
    }

    /**
     * Set up event listeners for filters
     */
    setupEventListeners() {
        // Site filter
        const siteFilter = document.getElementById('rackSiteFilter');
        if (siteFilter) {
            siteFilter.addEventListener('change', (e) => {
                this.filters.site = e.target.value;
                this.loadData();
            });
        }

        // GPU type filter
        const gpuFilter = document.getElementById('rackGpuFilter');
        if (gpuFilter) {
            gpuFilter.addEventListener('change', (e) => {
                this.filters.gpuType = e.target.value;
                this.loadData();
            });
        }

        // Owner checkboxes
        const nexgenCheck = document.getElementById('rackShowNexgen');
        const investorsCheck = document.getElementById('rackShowInvestors');

        if (nexgenCheck) {
            nexgenCheck.addEventListener('change', (e) => {
                this.filters.showNexgen = e.target.checked;
                this.applyFilters();
            });
        }

        if (investorsCheck) {
            investorsCheck.addEventListener('change', (e) => {
                this.filters.showInvestors = e.target.checked;
                this.applyFilters();
            });
        }
    }

    /**
     * Load rack data from the API
     */
    async loadData() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(true);

        try {
            const params = new URLSearchParams();
            if (this.filters.site) params.append('site', this.filters.site);
            if (this.filters.gpuType) params.append('gpu_type', this.filters.gpuType);

            const url = `/api/rack-visualization?${params.toString()}`;
            console.log('Loading rack data:', url);

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            this.rackData = await response.json();
            console.log('Rack data loaded:', this.rackData);

            this.render();
        } catch (error) {
            console.error('Failed to load rack data:', error);
            this.showError(error.message);
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    /**
     * Render the rack visualization
     */
    render() {
        if (!this.rackData) return;

        this.renderSummary();
        this.renderRacks();
    }

    /**
     * Render the summary panel
     */
    renderSummary() {
        const summaryEl = document.getElementById('rackViewSummary');
        if (!summaryEl || !this.rackData.summary) return;

        const summary = this.rackData.summary;
        const byOwner = summary.by_owner || {};
        const byGpu = summary.by_gpu_type || {};
        const totals = summary.totals || {};

        // Calculate availability (Empty vs In Use) from rack data - NexGen only
        let emptyCount = 0;
        let inUseCount = 0;
        if (this.rackData.racks) {
            this.rackData.racks.forEach(rack => {
                if (rack.devices) {
                    rack.devices.forEach(device => {
                        // Only count NexGen devices for availability
                        if (device.owner_group === 'Nexgen Cloud') {
                            if ((device.gpu_used || 0) > 0) {
                                inUseCount++;
                            } else {
                                emptyCount++;
                            }
                        }
                    });
                }
            });
        }

        // Build GPU breakdown HTML
        let gpuBreakdownHtml = '';
        Object.entries(byGpu).forEach(([gpu, counts]) => {
            const decomCount = counts.decommissioning || 0;
            const decomText = decomCount > 0 ? ` <span class="text-warning">(${decomCount} for sale)</span>` : '';
            gpuBreakdownHtml += `
                <span class="badge bg-secondary me-2">
                    ${gpu}: ${counts.nexgen || 0}${decomText}
                </span>
            `;
        });

        summaryEl.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="summary-card">
                        <h6 class="text-muted mb-2">OWNERSHIP</h6>
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-success"><i class="fas fa-building"></i> NexGen:</span>
                            <strong>${byOwner['Nexgen Cloud']?.total || 0}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-secondary"><i class="fas fa-users"></i> Investors:</span>
                            <strong>${byOwner['Investors']?.total || 0}</strong>
                        </div>
                        <hr class="my-2">
                        <div class="d-flex justify-content-between">
                            <span><strong>Total:</strong></span>
                            <strong>${totals.total_devices || 0}</strong>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="summary-card">
                        <h6 class="text-muted mb-2">NEXGEN AVAILABILITY</h6>
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-success"><i class="fas fa-server"></i> Empty:</span>
                            <strong>${emptyCount}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-warning"><i class="fas fa-circle"></i> In Use:</span>
                            <strong>${inUseCount}</strong>
                        </div>
                        <hr class="my-2">
                        <div class="d-flex justify-content-between">
                            <span class="text-danger"><i class="fas fa-tag"></i> For Sale:</span>
                            <strong>${totals.for_sale || 0}</strong>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="summary-card">
                        <h6 class="text-muted mb-2">STATUS</h6>
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-success"><i class="fas fa-check-circle"></i> Active:</span>
                            <strong>${(byOwner['Nexgen Cloud']?.active || 0) + (byOwner['Investors']?.active || 0)}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-muted"><i class="fas fa-th"></i> Racks:</span>
                            <strong>${totals.total_racks || 0}</strong>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="summary-card">
                        <h6 class="text-muted mb-2">GPU BREAKDOWN</h6>
                        <div class="gpu-breakdown">
                            ${gpuBreakdownHtml || '<span class="text-muted">No GPU data</span>'}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render all racks in the grid
     */
    renderRacks() {
        const gridEl = document.getElementById('rackGrid');
        if (!gridEl || !this.rackData.racks) return;

        if (this.rackData.racks.length === 0) {
            gridEl.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="fas fa-server fa-3x mb-3"></i>
                    <h5>No racks found</h5>
                    <p>Try adjusting your filters or select a different site.</p>
                </div>
            `;
            return;
        }

        let html = '';
        this.rackData.racks.forEach(rack => {
            html += this.renderRack(rack);
        });

        gridEl.innerHTML = html;

        // Add tooltips
        this.attachTooltips();
    }

    /**
     * Render a single rack
     */
    renderRack(rack) {
        const uHeight = rack.u_height || 42;
        const rackHeight = uHeight * this.U_HEIGHT_PX;
        const isVirtual = rack.is_virtual || false;

        // Generate U number labels
        let uLabels = '';
        for (let u = uHeight; u >= 1; u--) {
            const labelClass = u % 5 === 0 ? 'u-label-major' : 'u-label-minor';
            uLabels += `<div class="u-label ${labelClass}" style="height: ${this.U_HEIGHT_PX}px;">${u}</div>`;
        }

        // Render devices
        let devicesHtml = '';
        rack.devices.forEach(device => {
            devicesHtml += this.renderDevice(device, uHeight);
        });

        const rackClass = isVirtual ? 'rack-unit rack-virtual' : 'rack-unit';

        return `
            <div class="${rackClass}" data-rack-id="${rack.id}">
                <div class="rack-header">
                    <strong>${rack.name}</strong>
                    <span class="rack-device-count">${rack.devices.length}</span>
                </div>
                <div class="rack-body" style="height: ${rackHeight}px;">
                    <div class="rack-u-labels">${uLabels}</div>
                    <div class="rack-devices">
                        ${devicesHtml}
                    </div>
                </div>
                <div class="rack-footer">
                    <small class="text-muted">${rack.site}</small>
                </div>
            </div>
        `;
    }

    /**
     * Render a device within a rack
     */
    renderDevice(device, rackUHeight) {
        const position = device.position || 1;
        const uHeight = device.u_height || 4;

        // Calculate position (U1 is at bottom)
        const bottomPx = (position - 1) * this.U_HEIGHT_PX;
        const heightPx = uHeight * this.U_HEIGHT_PX;

        // GPU usage data
        const gpuUsed = device.gpu_used || 0;
        const gpuCapacity = device.gpu_capacity || 8;
        const gpuUsageRatio = device.gpu_usage_ratio || `${gpuUsed}/${gpuCapacity}`;
        const isInUse = gpuUsed > 0;
        const usagePercent = gpuCapacity > 0 ? (gpuUsed / gpuCapacity) : 0;

        // Determine device class based on owner, status, and GPU usage
        let deviceClass = 'rack-device';
        let inlineStyle = `bottom: ${bottomPx}px; height: ${heightPx}px;`;

        // Owner label
        const ownerLabel = device.owner_group === 'Nexgen Cloud' ? 'NGC' : 'INV';
        const isNexgen = device.owner_group === 'Nexgen Cloud';

        if (!isNexgen) {
            // Investor devices: blue if empty (0/8), grey if in use
            if (gpuUsed === 0) {
                deviceClass += ' device-investor-empty';
            } else {
                deviceClass += ' device-investor';
            }
        } else {
            // NexGen devices: gradient from yellow (low usage) to red (full usage)
            if (device.status === 'decommissioning') {
                deviceClass += ' device-nexgen decommissioning';
            } else if (isInUse) {
                // Calculate color gradient: yellow (low) -> orange (mid) -> red (full)
                const bgColor = this.getUsageColor(usagePercent);
                inlineStyle += ` background: ${bgColor};`;
                deviceClass += ' device-in-use-gradient';
            } else {
                deviceClass += ' device-nexgen';
            }
        }

        // Check visibility based on filters
        if (device.owner_group === 'Nexgen Cloud' && !this.filters.showNexgen) {
            deviceClass += ' device-hidden';
        }
        if (device.owner_group === 'Investors' && !this.filters.showInvestors) {
            deviceClass += ' device-hidden';
        }

        // Use full hostname
        const displayName = device.hostname || '?';

        // Status indicator
        const statusIcon = device.status === 'decommissioning' ? '<i class="fas fa-tag"></i>' : '';

        return `
            <div class="${deviceClass}"
                 style="${inlineStyle}"
                 data-hostname="${device.hostname}"
                 data-position="${position}"
                 data-owner="${device.owner_group}"
                 data-gpu="${device.gpu_type || 'Unknown'}"
                 data-status="${device.status}"
                 data-tenant="${device.tenant}"
                 data-nvlinks="${device.nvlinks}"
                 data-gpu-used="${gpuUsed}"
                 data-gpu-capacity="${gpuCapacity}"
                 data-gpu-ratio="${gpuUsageRatio}">
                <div class="device-info">
                    <span class="device-name">${displayName}</span>
                    <span class="device-owner-badge">${ownerLabel}</span>
                </div>
                <div class="device-stats">
                    <span class="device-gpu-usage">${gpuUsageRatio}</span>
                    ${device.nvlinks ? '<i class="fas fa-link nvlink-icon"></i>' : ''}
                    ${statusIcon}
                </div>
            </div>
        `;
    }

    /**
     * Calculate color based on GPU usage percentage (yellow -> orange -> red)
     */
    getUsageColor(percent) {
        // percent: 0 = not used (shouldn't reach here), 0.125 = 1/8, 1 = 8/8
        // Color: light yellow (#fff3cd) -> orange (#fd7e14) -> red (#dc3545)

        if (percent <= 0.25) {
            // Light yellow to yellow
            return `linear-gradient(135deg, #fff3cd, #ffc107)`;
        } else if (percent <= 0.5) {
            // Yellow to orange
            return `linear-gradient(135deg, #ffc107, #fd7e14)`;
        } else if (percent <= 0.75) {
            // Orange to dark orange
            return `linear-gradient(135deg, #fd7e14, #e55100)`;
        } else {
            // Dark orange to red
            return `linear-gradient(135deg, #e55100, #dc3545)`;
        }
    }

    /**
     * Shorten hostname for display in small rack units
     */
    shortenHostname(hostname) {
        if (!hostname) return '?';
        // Extract last part after last dash, or first 8 chars
        const parts = hostname.split('-');
        if (parts.length > 1) {
            return parts[parts.length - 1];
        }
        return hostname.substring(0, 8);
    }

    /**
     * Attach tooltips to devices
     */
    attachTooltips() {
        const devices = document.querySelectorAll('.rack-device');

        devices.forEach(device => {
            device.addEventListener('mouseenter', (e) => this.showTooltip(e, device));
            device.addEventListener('mouseleave', () => this.hideTooltip());
        });
    }

    /**
     * Show device tooltip
     */
    showTooltip(event, deviceEl) {
        const hostname = deviceEl.dataset.hostname;
        const position = deviceEl.dataset.position;
        const owner = deviceEl.dataset.owner;
        const gpu = deviceEl.dataset.gpu;
        const status = deviceEl.dataset.status;
        const tenant = deviceEl.dataset.tenant;
        const nvlinks = deviceEl.dataset.nvlinks === 'true';
        const gpuUsed = parseInt(deviceEl.dataset.gpuUsed) || 0;
        const gpuCapacity = parseInt(deviceEl.dataset.gpuCapacity) || 8;
        const gpuRatio = deviceEl.dataset.gpuRatio || `${gpuUsed}/${gpuCapacity}`;

        const ownerBadge = owner === 'Nexgen Cloud'
            ? '<span class="badge bg-success">NexGen</span>'
            : '<span class="badge bg-secondary">Investor</span>';

        const statusBadge = status === 'decommissioning'
            ? '<span class="badge bg-warning">For Sale</span>'
            : '<span class="badge bg-success">Active</span>';

        const nvlinkBadge = nvlinks
            ? '<span class="badge bg-info">NVLinks</span>'
            : '';

        // GPU usage badge - yellow/warning if in use, green if available
        const gpuUsageBadge = gpuUsed > 0
            ? `<span class="badge bg-warning text-dark">${gpuRatio} In Use</span>`
            : `<span class="badge bg-success">${gpuRatio} Available</span>`;

        let tooltip = document.getElementById('rackDeviceTooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'rackDeviceTooltip';
            tooltip.className = 'rack-tooltip';
            document.body.appendChild(tooltip);
        }

        tooltip.innerHTML = `
            <div class="tooltip-header">${hostname}</div>
            <div class="tooltip-body">
                <div class="tooltip-row">
                    <span class="tooltip-label">U Position:</span>
                    <span class="tooltip-value">U${position}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">Owner:</span>
                    <span class="tooltip-value">${ownerBadge}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">Tenant:</span>
                    <span class="tooltip-value">${tenant}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">GPU Type:</span>
                    <span class="tooltip-value">${gpu}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">GPU Usage:</span>
                    <span class="tooltip-value">${gpuUsageBadge}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">Status:</span>
                    <span class="tooltip-value">${statusBadge} ${nvlinkBadge}</span>
                </div>
            </div>
        `;

        // Position tooltip
        const rect = deviceEl.getBoundingClientRect();
        tooltip.style.left = `${rect.right + 10}px`;
        tooltip.style.top = `${rect.top}px`;
        tooltip.classList.add('show');
    }

    /**
     * Hide device tooltip
     */
    hideTooltip() {
        const tooltip = document.getElementById('rackDeviceTooltip');
        if (tooltip) {
            tooltip.classList.remove('show');
        }
    }

    /**
     * Apply visibility filters without reloading data
     */
    applyFilters() {
        const devices = document.querySelectorAll('.rack-device');

        devices.forEach(device => {
            const owner = device.dataset.owner;
            let visible = true;

            if (owner === 'Nexgen Cloud' && !this.filters.showNexgen) {
                visible = false;
            }
            if (owner === 'Investors' && !this.filters.showInvestors) {
                visible = false;
            }

            device.classList.toggle('device-hidden', !visible);
        });
    }

    /**
     * Show/hide loading indicator
     */
    showLoading(show) {
        const loader = document.getElementById('rackViewLoader');
        const content = document.getElementById('rackViewContent');

        if (loader) loader.style.display = show ? 'block' : 'none';
        if (content) content.style.display = show ? 'none' : 'block';
    }

    /**
     * Show error message
     */
    showError(message) {
        const gridEl = document.getElementById('rackGrid');
        if (gridEl) {
            gridEl.innerHTML = `
                <div class="text-center text-danger py-5">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <h5>Error Loading Rack Data</h5>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="rackView.loadData()">
                        <i class="fas fa-sync"></i> Retry
                    </button>
                </div>
            `;
        }
    }

    /**
     * Show the rack view
     */
    show() {
        const container = document.getElementById('rackViewContainer');
        const aggregateView = document.getElementById('hostsRow');

        if (container) {
            container.style.display = 'block';
            this.init().then(() => this.loadData());
        }
        if (aggregateView) aggregateView.style.display = 'none';
    }

    /**
     * Hide the rack view
     */
    hide() {
        const container = document.getElementById('rackViewContainer');
        const aggregateView = document.getElementById('hostsRow');

        if (container) container.style.display = 'none';
        if (aggregateView) aggregateView.classList.remove('d-none');
    }
}

// Global instance
const rackView = new RackView();

/**
 * Toggle between Aggregate View and Rack View
 */
function toggleRackView(showRack) {
    const aggregateBtn = document.getElementById('aggregateViewBtn');
    const rackBtn = document.getElementById('rackViewBtn');

    if (showRack) {
        rackView.show();
        if (aggregateBtn) aggregateBtn.classList.remove('active');
        if (rackBtn) rackBtn.classList.add('active');
    } else {
        rackView.hide();
        if (aggregateBtn) aggregateBtn.classList.add('active');
        if (rackBtn) rackBtn.classList.remove('active');
    }
}
