// OpenStack operations for OpenStack Spot Manager
// Handles host migrations, aggregate operations, and VM management

// Global cache for GPU and aggregate data
window.gpuAggregatesCache = {
    data: null,
    timestamp: null,
    isValid: function() {
        return this.data && this.timestamp && (Date.now() - this.timestamp) < 600000; // 10 minutes TTL
    }
};

// Helper function to get currently selected GPU type from UI
function getCurrentGpuType() {
    const select = document.getElementById('gpuTypeSelect');
    return select ? select.value : null;
}

// Execute host migration between aggregates
function executeHostMigration(hostname, sourceAggregate, targetAggregate, operation) {
    return new Promise((resolve, reject) => {
        console.log(`🔄 Starting host migration: ${hostname} from ${sourceAggregate} to ${targetAggregate} (${operation})`);
        window.Logs.addToDebugLog('OpenStack', `Starting ${operation} operation for ${hostname}`, 'info', hostname);
        
        const endpoint = operation === 'remove' ? '/api/execute-migration' : '/api/execute-migration';
        
        window.Utils.fetchWithTimeout(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                host: hostname,
                source_aggregate: sourceAggregate,
                target_aggregate: targetAggregate,
                operation: operation
            })
        }, 45000) // 45 second timeout for migration operations
        .then(window.Utils.checkResponse)
        .then(response => response.json())
        .then(data => {
            console.log(`📊 Migration ${operation} result for ${hostname}:`, data);
            
            if (data.success) {
                console.log(`✅ Migration ${operation} successful for ${hostname}`);
                window.Logs.addToDebugLog('OpenStack', `${operation} operation completed successfully`, 'success', hostname);
                
                // Check if backend refreshed cache for specific GPU types
                if (data.refresh_frontend && data.affected_gpu_types && data.affected_gpu_types.length > 0) {
                    console.log(`🔄 Backend refreshed cache for GPU types: ${data.affected_gpu_types.join(', ')}`);
                    window.Logs.addToDebugLog('OpenStack', `Cache refreshed for GPU types: ${data.affected_gpu_types.join(', ')}`, 'info', hostname);
                    
                    // Store the affected GPU types for when user switches tabs
                    if (!window.refreshedGpuTypes) window.refreshedGpuTypes = new Set();
                    data.affected_gpu_types.forEach(gpuType => {
                        window.refreshedGpuTypes.add(gpuType);
                        // Invalidate parallel_data and gpuDataCache for affected types
                        if (window.loadedParallelData && window.loadedParallelData[gpuType]) {
                            delete window.loadedParallelData[gpuType];
                        }
                        if (window.gpuDataCache) {
                            window.gpuDataCache.delete(gpuType);
                        }
                        console.log(`📝 Invalidated caches for GPU type '${gpuType}'`);
                    });
                    
                    // If currently viewing one of the affected GPU types, refresh immediately
                    const currentGpuType = getCurrentGpuType(); // Function to get current GPU type from UI
                    if (currentGpuType && data.affected_gpu_types.includes(currentGpuType)) {
                        console.log(`🔄 Currently viewing affected GPU type '${currentGpuType}' - refreshing data...`);
                        setTimeout(() => {
                            // Force refresh the aggregate data for current GPU type
                            loadAggregateData(currentGpuType, false);
                        }, 1000);
                    }
                }
                
                resolve(data);
            } else {
                console.error(`❌ Migration ${operation} failed for ${hostname}:`, data.error);
                window.Logs.addToDebugLog('OpenStack', `${operation} operation failed: ${data.error}`, 'error', hostname);
                reject(new Error(data.error || `Migration ${operation} failed`));
            }
        })
        .catch(error => {
            console.error(`💥 Exception during migration ${operation} for ${hostname}:`, error);
            window.Logs.addToDebugLog('OpenStack', `Network error during ${operation}: ${error.message}`, 'error', hostname);
            reject(error);
        });
    });
}

// Load aggregate data for a specific GPU type
function loadAggregateData(gpuType, isBackgroundLoad = false) {
    console.log(`📊 Loading aggregate data for ${gpuType} (background: ${isBackgroundLoad})`);
    window.Logs.addToDebugLog('OpenStack', `Loading aggregate data for ${gpuType}`, 'info');
    
    // Check if this GPU type needs fresh data due to recent migration
    const needsFreshData = window.refreshedGpuTypes && window.refreshedGpuTypes.has(gpuType);
    if (needsFreshData) {
        console.log(`🔄 GPU type '${gpuType}' marked for refresh - bypassing cache`);
        window.refreshedGpuTypes.delete(gpuType); // Remove flag after handling
    }
    
    // Check gpuDataCache first (unless fresh data is needed)
    if (!needsFreshData && window.gpuDataCache && window.gpuDataCache.has(gpuType)) {
        console.log(`✅ Loading ${gpuType} from gpuDataCache`);
        if (!isBackgroundLoad) {
            const cachedData = window.gpuDataCache.get(gpuType);
            window.Frontend.aggregateData = cachedData;
            window.Frontend.renderAggregateData(cachedData);
            window.Frontend.showMainContent();
        }
        return Promise.resolve(window.gpuDataCache.get(gpuType));
    }

    // Try processing from parallel_data client-side (no API call needed)
    if (!needsFreshData) {
        const processedData = processParallelDataForGpuType(gpuType);
        if (processedData) {
            console.log(`✅ Processed ${gpuType} from parallel_data cache (no API call)`);
            // Cache the processed data
            if (window.gpuDataCache) {
                window.gpuDataCache.set(gpuType, processedData);
            }
            window.Frontend.aggregateData = processedData;
            if (!isBackgroundLoad) {
                window.Frontend.renderAggregateData(processedData);
                window.Frontend.showMainContent();
            }
            return Promise.resolve(processedData);
        }
    }

    // Fallback: fetch from API (only when parallel_data is not available)
    if (!isBackgroundLoad) {
        window.Frontend.showLoading(true, `Loading ${gpuType} aggregate data...`, 'Discovering aggregates...', 10);
    }

    return window.Utils.fetchWithTimeout(`/api/aggregates/${gpuType}`, {}, 30000)
        .then(window.Utils.checkResponse)
        .then(response => {
            if (!isBackgroundLoad) {
                window.Frontend.updateLoadingProgress('Fetching host information...', 30);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                if (!isBackgroundLoad) {
                    window.Frontend.showNotification(data.error, 'danger');
                    window.Frontend.showLoading(false);
                }
                window.Logs.addToDebugLog('OpenStack', `Error loading aggregate data: ${data.error}`, 'error');
                throw new Error(data.error);
            }
            
            if (!isBackgroundLoad) {
                window.Frontend.updateLoadingProgress('Processing host data...', 60);
            }
            
            console.log(`✅ Loaded ${gpuType} aggregate data:`, data);
            console.log(`🔍 DEBUG: Fresh API data for ${gpuType}:`, {
                gpu_type: data.gpu_type,
                spot: data.spot?.name,
                ondemand: data.ondemand?.name,
                runpod: data.runpod?.name
            });
            window.Logs.addToDebugLog('OpenStack', `Successfully loaded aggregate data for ${gpuType}`, 'success');
            
            // Cache the data
            if (window.gpuDataCache) {
                window.gpuDataCache.set(gpuType, data);
                console.log(`📦 Cached data for ${gpuType}`);
            }
            window.Frontend.aggregateData = data;
            
            if (!isBackgroundLoad) {
                window.Frontend.updateLoadingProgress('Rendering interface...', 90);
                window.Frontend.renderAggregateData(data);
                window.Frontend.updateLoadingProgress('Complete!', 100);

                setTimeout(() => {
                    window.Frontend.showLoading(false);
                    window.Frontend.showMainContent();
                }, 500);
            }
            
            return data;
        })
        .catch(error => {
            console.error(`❌ Error loading aggregate data for ${gpuType}:`, error);
            window.Logs.addToDebugLog('OpenStack', `Failed to load aggregate data: ${error.message}`, 'error');
            
            if (!isBackgroundLoad) {
                window.Frontend.showNotification(`Failed to load ${gpuType} data: ${error.message}`, 'danger');
                window.Frontend.showLoading(false);
            }
            
            throw error;
        });
}

// Load overall GPU usage data across all GPU types — computed from cached parallel_data (no API calls)
async function loadOverallGpuUsage() {
    console.log('📊 Computing overall GPU usage from cached parallel data...');

    // Show loading state
    document.getElementById('totalGpuUsage').textContent = 'Loading...';
    document.getElementById('gpuUsagePercentage').textContent = '';
    document.getElementById('availableHostsCount').textContent = '0';
    document.getElementById('inUseHostsCount').textContent = '0';

    try {
        const parallelData = window.loadedParallelData;
        if (!parallelData) {
            console.warn('Parallel data not loaded yet, skipping overall GPU usage');
            return;
        }

        let totalGpuUsed = 0;
        let totalGpuCapacity = 0;
        let totalAvailableHosts = 0;
        let totalInUseHosts = 0;

        Object.keys(parallelData).forEach(gpuType => {
            if (gpuType.startsWith('_')) return;
            const gpuData = parallelData[gpuType];
            if (!gpuData) return;

            // Sum GPU summaries from each pool
            ['ondemand', 'runpod', 'spot', 'contract'].forEach(category => {
                const summary = gpuData[category]?.gpu_summary;
                if (summary) {
                    totalGpuUsed += summary.gpu_used || 0;
                    totalGpuCapacity += summary.gpu_capacity || 0;
                }
            });

            // Count hosts
            const hosts = gpuData.hosts || [];
            hosts.forEach(host => {
                if ((host.vm_count || 0) > 0) {
                    totalInUseHosts++;
                } else {
                    totalAvailableHosts++;
                }
            });
        });

        const totalGpuPercentage = totalGpuCapacity > 0 ? Math.round((totalGpuUsed / totalGpuCapacity) * 100) : 0;

        // Update UI elements
        const totalGpuElement = document.getElementById('totalGpuUsage');
        const gpuPercentElement = document.getElementById('gpuUsagePercentage');
        const availableHostsElement = document.getElementById('availableHostsCount');
        const inUseHostsElement = document.getElementById('inUseHostsCount');

        totalGpuElement.textContent = `${totalGpuUsed}/${totalGpuCapacity} GPUs`;
        totalGpuElement.className = 'badge bg-primary fs-6';

        gpuPercentElement.textContent = `${totalGpuPercentage}%`;
        gpuPercentElement.className = 'badge bg-success fs-6 ms-2';

        availableHostsElement.textContent = totalAvailableHosts;
        availableHostsElement.className = 'badge bg-success fs-6';

        inUseHostsElement.textContent = totalInUseHosts;
        inUseHostsElement.className = 'badge bg-warning fs-6';

        document.getElementById('gpuProgressBar').style.width = `${totalGpuPercentage}%`;
        document.getElementById('gpuProgressText').textContent = `${totalGpuPercentage}%`;

        const progressBar = document.getElementById('gpuProgressBar');
        progressBar.className = 'progress-bar';
        if (totalGpuPercentage < 50) {
            progressBar.classList.add('bg-success');
        } else if (totalGpuPercentage < 80) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-danger');
        }

        window.Logs?.addToDebugLog('OpenStack', `Overall GPU usage computed from cache: ${totalGpuUsed}/${totalGpuCapacity} (${totalGpuPercentage}%)`, 'info');

    } catch (error) {
        console.error('Error computing overall GPU usage:', error);
        window.Logs?.addToDebugLog('OpenStack', `Error computing overall GPU usage: ${error.message}`, 'error');
        document.getElementById('totalGpuUsage').textContent = 'Error loading data';
        document.getElementById('gpuUsagePercentage').textContent = 'N/A';
        document.getElementById('availableHostsCount').textContent = '0';
        document.getElementById('inUseHostsCount').textContent = '0';
    }
}

// Get GPU types from the backend
function loadGpuTypes() {
    console.log('📊 Loading available GPU types');
    
    // Check if required dependencies are available
    if (!window.Utils) {
        console.error('❌ Utils module not available for loadGpuTypes');
        return;
    }
    if (!window.Logs) {
        console.error('❌ Logs module not available for loadGpuTypes');
        return;
    }
    
    window.Logs.addToDebugLog('OpenStack', 'Loading available GPU types', 'info');
    
    console.log('🌐 Making API call to /api/gpu-types...');
    window.Utils.fetchWithTimeout('/api/gpu-types', {}, 20000)
        .then(window.Utils.checkResponse)
        .then(response => response.json())
        .then(data => {
            console.log('✅ GPU types API response:', data);
            
            if (!data || !data.gpu_types) {
                console.error('❌ Invalid response from /api/gpu-types:', data);
                window.Logs.addToDebugLog('OpenStack', 'Invalid response from gpu-types API', 'error');
                return;
            }
            
            // Cache the aggregates data for contract loading
            window.gpuAggregatesCache.data = data.aggregates;
            window.gpuAggregatesCache.timestamp = Date.now();
            console.log('💾 Cached GPU aggregates data for contract loading');
            
            // Make aggregates data globally available to avoid any API calls
            window.loadedAggregatesData = data.aggregates;
            
            // Store full parallel data if available (for contracts optimization)
            if (data.parallel_data) {
                window.loadedParallelData = data.parallel_data;
                console.log('💾 Cached full parallel data for contract optimization');
            }
            
            console.log('✅ Available GPU types:', data.gpu_types);
            window.Logs.addToDebugLog('OpenStack', `Found ${data.gpu_types.length} GPU types`, 'success');
            
            const select = document.getElementById('gpuTypeSelect');
            if (!select) {
                console.error('❌ GPU type select element not found!');
                window.Logs.addToDebugLog('OpenStack', 'GPU type select element not found', 'error');
                return;
            }
            
            console.log('🧹 Clearing existing options...');
            // Clear existing options except the default
            select.innerHTML = '<option value="">Select GPU Type...</option>';
            
            console.log('💾 Storing GPU types for background loading...');
            // Store available GPU types for background loading
            if (!window.Frontend) {
                console.warn('⚠️ Frontend module not yet available, deferring GPU types storage...');
                // Try again after a short delay to allow frontend.js to fully load
                setTimeout(() => {
                    if (window.Frontend) {
                        window.Frontend.availableGpuTypes = data.gpu_types;
                        console.log('✅ GPU types stored after frontend module loaded');
                        
                        // Skip loading overall GPU usage on initial load - will be populated on first refresh
                    }
                }, 100);
            } else {
                window.Frontend.availableGpuTypes = data.gpu_types;
                
                // Skip loading overall GPU usage on initial load - will be populated on first refresh
            }
            
            // Add discovered GPU types
            console.log(`🎯 Adding ${data.gpu_types.length} GPU types to selector...`);
            data.gpu_types.forEach((gpuType, index) => {
                console.log(`  Adding option ${index + 1}: ${gpuType}`);
                const option = document.createElement('option');
                option.value = gpuType;
                option.textContent = gpuType;
                select.appendChild(option);
            });
            
            console.log(`📊 Total options in select: ${select.options.length}`);
            
            // Show preload button if there are types to preload
            if (data.gpu_types.length > 1) {
                console.log('👀 Showing preload button...');
                const preloadBtn = document.getElementById('preloadAllBtn');
                if (preloadBtn) {
                    preloadBtn.style.display = 'inline-block';
                } else {
                    console.warn('⚠️ Preload button not found');
                }
            }
            
            // Auto-select GPU type from URL if specified
            if (window.urlGpuType && data.gpu_types.includes(window.urlGpuType)) {
                console.log(`🎯 Auto-selecting GPU type from URL: ${window.urlGpuType}`);
                select.value = window.urlGpuType;
                window.currentGpuType = window.urlGpuType;
                
                // Trigger the change event to load the data
                const event = new Event('change');
                select.dispatchEvent(event);
                
                window.Logs.addToDebugLog('OpenStack', `Auto-selected and loaded: ${window.urlGpuType}`, 'success');
                delete window.urlGpuType; // Clean up
            }
            
            console.log('✅ GPU types loaded successfully');
            
            // Update System Info tab
            if (window.SystemInfo && typeof window.SystemInfo.updateSystemInfo === 'function') {
                window.SystemInfo.updateSystemInfo({
                    gpuTypes: data.gpu_types,
                    aggregates: data.aggregates
                });
            }
            
            // Hide progress modal if it's showing (initial load / branch switch)
            const progressModal = document.getElementById('refreshProgressModal');
            if (progressModal) {
                const modal = bootstrap.Modal.getInstance(progressModal);
                if (modal && progressModal.classList.contains('show')) {
                    console.log('🏁 Initial loading completed - hiding progress modal');
                    // Populate real counts before showing completion
                    if (window.updateProgressCountsFromData && data.parallel_data) {
                        window.updateProgressCountsFromData(data.parallel_data);
                    }
                    // Update progress to 100% and show completion message
                    if (typeof updateProgress === 'function') {
                        updateProgress('complete', 'Loading completed!', 100);
                    }
                    setTimeout(() => {
                        modal.hide();
                    }, 2000); // Give user time to see counts + completion
                }
            }
        })
        .catch(error => {
            console.error('❌ Error loading GPU types:', error);
            window.Logs.addToDebugLog('OpenStack', `Error loading GPU types: ${error.message}`, 'error');
            window.Frontend.showNotification('Failed to load GPU types', 'error');
            
            // Hide progress modal on error (if showing)
            const progressModal = document.getElementById('refreshProgressModal');
            if (progressModal) {
                const modal = bootstrap.Modal.getInstance(progressModal);
                if (modal && progressModal.classList.contains('show')) {
                    console.log('❌ Initial loading failed - hiding progress modal');
                    if (typeof updateProgress === 'function') {
                        updateProgress('error', 'Loading failed - please try refresh', 100);
                    }
                    setTimeout(() => {
                        modal.hide();
                    }, 2000);
                }
            }
        });
}

// Preview migration before execution
function previewMigration(hostname, sourceType, targetType) {
    console.log(`📋 Previewing migration: ${hostname} from ${sourceType} to ${targetType}`);
    window.Logs.addToDebugLog('OpenStack', `Previewing migration for ${hostname}`, 'info', hostname);
    
    // Get source aggregate from card
    const sourceCard = document.querySelector(`[data-host="${hostname}"]`);
    let sourceAggregate = '';
    if (sourceCard) {
        const aggregateHeader = sourceCard.closest('.card').querySelector('.card-header');
        if (aggregateHeader) {
            const aggregateSpan = aggregateHeader.querySelector('span');
            if (aggregateSpan) {
                sourceAggregate = aggregateSpan.textContent.trim();
            }
        }
    }
    
    // Get target aggregate name from the new three-column structure
    let targetAggregate = '';
    if (targetType === 'ondemand' && window.Frontend.aggregateData.ondemand.name) {
        targetAggregate = window.Frontend.aggregateData.ondemand.name;
    } else if (targetType === 'runpod' && window.Frontend.aggregateData.runpod.name) {
        targetAggregate = window.Frontend.aggregateData.runpod.name;
    } else if (targetType === 'spot' && window.Frontend.aggregateData.spot.name) {
        targetAggregate = window.Frontend.aggregateData.spot.name;
    }
    
    window.Utils.fetchWithTimeout('/api/preview-migration', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            host: hostname,
            source_aggregate: sourceAggregate,
            target_aggregate: targetAggregate
        })
    }, 15000)
    .then(window.Utils.checkResponse)
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            window.Frontend.showNotification(data.error, 'danger');
            window.Logs.addToDebugLog('OpenStack', `Migration preview failed: ${data.error}`, 'error', hostname);
            return;
        }
        
        console.log(`✅ Migration preview successful for ${hostname}:`, data);
        window.Logs.addToDebugLog('OpenStack', `Migration preview successful`, 'success', hostname);
        
        window.Frontend.showMigrationModal(data, sourceType === 'spot');
    })
    .catch(error => {
        console.error(`❌ Error previewing migration for ${hostname}:`, error);
        window.Logs.addToDebugLog('OpenStack', `Migration preview error: ${error.message}`, 'error', hostname);
        window.Frontend.showNotification(`Error previewing migration: ${error.message}`, 'danger');
    });
}

// Get VM details for a specific host
function getHostVmDetails(hostname) {
    console.log(`📋 Getting VM details for ${hostname}`);
    window.Logs.addToDebugLog('OpenStack', `Getting VM details for ${hostname}`, 'info', hostname);
    
    return window.Utils.fetchWithTimeout(`/api/host-vms/${hostname}`, {}, 15000)
        .then(window.Utils.checkResponse)
        .then(response => response.json())
        .then(data => {
            console.log(`✅ VM details retrieved for ${hostname}:`, data);
            window.Logs.addToDebugLog('OpenStack', `Retrieved VM details for ${hostname}`, 'success', hostname);
            return data;
        })
        .catch(error => {
            console.error(`❌ Error getting VM details for ${hostname}:`, error);
            window.Logs.addToDebugLog('OpenStack', `Error getting VM details: ${error.message}`, 'error', hostname);
            throw error;
        });
}

// Generate commands for host migration operations
function generateMigrationCommands(operation) {
    const commands = [];
    
    // 1. Remove from source aggregate
    commands.push({
        type: 'aggregate-remove',
        hostname: operation.hostname,
        parent_operation: 'migration',
        title: `Remove ${operation.hostname} from ${operation.sourceAggregate}`,
        description: `Removes the compute host from the source aggregate to prepare for migration`,
        command: `nova aggregate-remove-host ${operation.sourceAggregate} ${operation.hostname}`,
        verification_commands: [
            `nova aggregate-show ${operation.sourceAggregate}`,
            `nova hypervisor-show ${operation.hostname}`
        ],
        estimated_duration: '30s',
        dependencies: [],
        timestamp: new Date().toISOString()
    });
    
    // 2. Wait for propagation
    commands.push({
        type: 'wait-command',
        hostname: operation.hostname,
        parent_operation: 'migration',
        title: 'Wait for aggregate membership propagation',
        description: 'Allows OpenStack services to recognize the host removal before adding to new aggregate',
        command: `sleep 60  # Wait for OpenStack aggregate membership to propagate`,
        verification_commands: [
            'nova service-list',
            'nova aggregate-list'
        ],
        estimated_duration: '60s',
        dependencies: ['aggregate-remove'],
        timestamp: new Date().toISOString()
    });
    
    // 3. Add to target aggregate
    commands.push({
        type: 'aggregate-add',
        hostname: operation.hostname,
        parent_operation: 'migration',
        title: `Add ${operation.hostname} to ${operation.targetAggregate}`,
        description: `Adds the compute host to the target aggregate to complete the migration`,
        command: `nova aggregate-add-host ${operation.targetAggregate} ${operation.hostname}`,
        verification_commands: [
            `nova aggregate-show ${operation.targetAggregate}`,
            `nova hypervisor-show ${operation.hostname}`
        ],
        estimated_duration: '30s',
        dependencies: ['wait-command'],
        timestamp: new Date().toISOString()
    });
    
    return commands;
}

// Execute OpenStack network commands using SDK
function executeNetworkCommand(command) {
    return new Promise((resolve, reject) => {
        console.log(`🌐 Executing OpenStack network command: ${command}`);
        window.Logs.addToDebugLog('OpenStack', `Executing network command: ${command}`, 'info');
        
        // Parse command to determine operation
        if (command.includes('server list --all-projects --name')) {
            // Extract server name from command: openstack server list --all-projects --name "server_name"
            const nameMatch = command.match(/--name\s+[\"']?([^\"'\s]+)[\"']?/);
            const serverName = nameMatch ? nameMatch[1] : null;
            
            if (!serverName) {
                reject(new Error('Could not parse server name from command'));
                return;
            }
            
            // Call backend to get server UUID via SDK
            window.Utils.fetchWithTimeout('/api/openstack/server/get-uuid', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ server_name: serverName })
            }, 30000)
            .then(window.Utils.checkResponse)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    resolve(data.server_uuid);
                } else {
                    reject(new Error(data.error || 'Server UUID lookup failed'));
                }
            })
            .catch(error => reject(error));
            
        } else if (command.includes('network show')) {
            // Extract network name from command
            const networkMatch = command.match(/network show ["\']?([^"'\s]+)["\']?/);
            const networkName = networkMatch ? networkMatch[1] : null;
            
            if (!networkName) {
                reject(new Error('Could not parse network name from command'));
                return;
            }
            
            // Call backend to find network via SDK
            window.Utils.fetchWithTimeout('/api/openstack/network/show', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ network_name: networkName })
            }, 30000)
            .then(window.Utils.checkResponse)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    resolve(data.network_id);
                } else {
                    reject(new Error(data.error || 'Network lookup failed'));
                }
            })
            .catch(error => reject(error));
            
        } else if (command.includes('port create')) {
            // Extract port details from command
            const networkMatch = command.match(/--network ["\']?([^"'\s]+)["\']?/);
            const nameMatch = command.match(/--name ["\']?([^"'\s]+)["\']?/);
            
            const networkName = networkMatch ? networkMatch[1] : null;
            const portName = nameMatch ? nameMatch[1] : null;
            
            if (!networkName || !portName) {
                reject(new Error('Could not parse network name or port name from command'));
                return;
            }
            
            // Call backend to create port via SDK
            window.Utils.fetchWithTimeout('/api/openstack/port/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    network_name: networkName,
                    port_name: portName
                })
            }, 30000)
            .then(window.Utils.checkResponse)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    resolve(data.port_id);
                } else {
                    reject(new Error(data.error || 'Port creation failed'));
                }
            })
            .catch(error => reject(error));
            
        } else if (command.includes('server add network')) {
            // Extract server and network from command: openstack server add network <server_name> <network_name>
            const parts = command.split(' ');
            const addIndex = parts.indexOf('add');
            const networkKeywordIndex = parts.indexOf('network');
            
            if (addIndex === -1 || networkKeywordIndex === -1 || networkKeywordIndex + 2 >= parts.length) {
                reject(new Error('Could not parse server or network from command'));
                return;
            }
            
            const serverName = parts[networkKeywordIndex + 1];  // First argument after 'network'
            const networkName = parts[networkKeywordIndex + 2]; // Second argument after 'network'
            
            // Call backend to attach network via SDK
            window.Utils.fetchWithTimeout('/api/openstack/server/add-network', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    server_name: serverName,
                    network_name: networkName
                })
            }, 30000)
            .then(window.Utils.checkResponse)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    resolve('Network attached successfully');
                } else {
                    reject(new Error(data.error || 'Network attachment failed'));
                }
            })
            .catch(error => reject(error));
            
        } else {
            reject(new Error(`Unsupported OpenStack command: ${command}`));
        }
    });
}


// Process parallel_data client-side to produce the same shape as /api/aggregates/<gpu_type>
// This mirrors the Python logic in app_routes.py:264-551 (process_hosts_from_parallel_data + response assembly)
function processParallelDataForGpuType(gpuType) {
    if (!window.loadedParallelData) return null;

    const gpuData = window.loadedParallelData[gpuType];
    if (!gpuData) return null;

    const config = gpuData.config || {};
    const allHosts = gpuData.hosts || [];

    // Special handling for outofstock
    if (gpuType === 'outofstock') {
        const hostsData = gpuData.hosts || [];
        return {
            gpu_type: 'outofstock',
            outofstock: {
                name: gpuData.name || 'Out of Stock',
                hosts: hostsData,
                gpu_summary: gpuData.gpu_summary || { gpu_used: 0, gpu_capacity: 0, gpu_usage_ratio: '0/0' }
            },
            performance_stats: { total_time: 0, total_hosts: hostsData.length, hosts_per_second: 0, method: 'client_cache' }
        };
    }

    // Classify hosts by assignment (mirrors app_routes.py:278-329)
    const ondemandHostnames = [];
    const runpodHostnames = [];
    const spotHostnames = [];
    const contractHostnames = [];
    const ondemandHostVariants = {};
    const contractHostMappings = {};

    for (const hostData of allHosts) {
        const hostname = hostData.hostname;
        const aggregate = hostData.aggregate;
        const assignment = hostData._assignment;

        if (assignment === 'runpod' || (config.runpod && aggregate === config.runpod)) {
            runpodHostnames.push(hostname);
        } else if (assignment === 'spot' || (config.spot && aggregate === config.spot)) {
            spotHostnames.push(hostname);
        } else if (assignment === 'ondemand') {
            ondemandHostnames.push(hostname);
            let matchedVariant = false;
            if (config.ondemand_variants) {
                for (const variant of config.ondemand_variants) {
                    if (aggregate === variant.aggregate) {
                        ondemandHostVariants[hostname] = variant.variant;
                        matchedVariant = true;
                        break;
                    }
                }
            }
            if (!matchedVariant && aggregate) {
                ondemandHostVariants[hostname] = aggregate;
            }
        } else if (config.ondemand_variants) {
            for (const variant of config.ondemand_variants) {
                if (aggregate === variant.aggregate) {
                    ondemandHostnames.push(hostname);
                    ondemandHostVariants[hostname] = variant.variant;
                    break;
                }
            }
        }

        // Contracts can coexist with other types
        if (assignment === 'contract' || config.contracts) {
            if (config.contracts) {
                for (const contract of config.contracts) {
                    if (aggregate === contract.aggregate) {
                        if (!contractHostnames.includes(hostname)) {
                            contractHostnames.push(hostname);
                        }
                        contractHostMappings[hostname] = {
                            contract_aggregate: contract.aggregate,
                            contract_name: contract.name
                        };
                        break;
                    }
                }
            }
        }
    }

    // Process hosts for each pool (mirrors app_routes.py:335-407)
    function processHosts(hostnameList, aggregateType) {
        const processed = [];
        for (const hostname of hostnameList) {
            const hostInfo = allHosts.find(h => h.hostname === hostname);
            if (!hostInfo) continue;

            const tenantInfo = hostInfo.tenant_info || {
                tenant: hostInfo.tenant || 'Unknown',
                owner_group: hostInfo.owner_group || 'Investors',
                nvlinks: hostInfo.nvlinks || false,
                netbox_device_id: hostInfo.netbox_device_id || null,
                netbox_url: hostInfo.netbox_url || null
            };

            const host = {
                name: hostname,
                vm_count: hostInfo.vm_count || 0,
                has_vms: (hostInfo.vm_count || 0) > 0,
                tenant: tenantInfo.tenant,
                owner_group: tenantInfo.owner_group,
                nvlinks: tenantInfo.nvlinks,
                netbox_device_id: tenantInfo.netbox_device_id,
                netbox_url: tenantInfo.netbox_url,
                gpu_used: hostInfo.gpu_used || 0,
                gpu_capacity: hostInfo.gpu_capacity || 8,
                gpu_usage_ratio: hostInfo.gpu_usage_ratio || '0/8'
            };

            if (aggregateType === 'ondemand' && ondemandHostVariants[hostname]) {
                host.variant = ondemandHostVariants[hostname];
            } else if (aggregateType === 'contracts' && contractHostMappings[hostname]) {
                host.contract_aggregate = contractHostMappings[hostname].contract_aggregate;
                host.contract_name = contractHostMappings[hostname].contract_name;
            }

            processed.push(host);
        }
        return processed;
    }

    const ondemandData = processHosts(ondemandHostnames, 'ondemand');
    const runpodData = processHosts(runpodHostnames, 'runpod');
    const spotData = processHosts(spotHostnames, 'spot');
    const contractData = processHosts(contractHostnames, 'contracts');

    // GPU summaries from pre-calculated backend data
    const defaultSummary = { gpu_used: 0, gpu_capacity: 0, gpu_usage_ratio: '0/0' };
    const ondemandGpuSummary = gpuData.ondemand?.gpu_summary || defaultSummary;
    const runpodGpuSummary = gpuData.runpod?.gpu_summary || defaultSummary;
    const spotGpuSummary = gpuData.spot?.gpu_summary || defaultSummary;
    const contractGpuSummary = gpuData.contract?.gpu_summary || defaultSummary;
    const outofstockGpuSummary = gpuData.outofstock?.gpu_summary || defaultSummary;
    const outofstockHosts = gpuData.outofstock?.hosts || [];

    // Overall GPU summary
    const totalGpuUsed = ondemandGpuSummary.gpu_used + runpodGpuSummary.gpu_used + spotGpuSummary.gpu_used + contractGpuSummary.gpu_used;
    const totalGpuCapacity = ondemandGpuSummary.gpu_capacity + runpodGpuSummary.gpu_capacity + spotGpuSummary.gpu_capacity + contractGpuSummary.gpu_capacity;
    const gpuUsagePercentage = totalGpuCapacity > 0 ? Math.round((totalGpuUsed / totalGpuCapacity) * 1000) / 10 : 0;

    // Build on-demand name
    let ondemandName = config.ondemand || 'N/A';
    if (config.ondemand_variants && config.ondemand_variants.length > 1) {
        ondemandName = `${gpuType}-n3 (${config.ondemand_variants.length} variants)`;
    } else if (config.ondemand_variants && config.ondemand_variants.length === 1) {
        ondemandName = config.ondemand_variants[0].variant;
    }

    const totalHosts = ondemandHostnames.length + runpodHostnames.length + spotHostnames.length + contractHostnames.length;

    return {
        gpu_type: gpuType,
        ondemand: {
            name: ondemandName,
            hosts: ondemandData,
            gpu_summary: ondemandGpuSummary,
            variants: config.ondemand_variants || []
        },
        runpod: {
            name: config.runpod || 'N/A',
            hosts: runpodData,
            gpu_summary: runpodGpuSummary
        },
        spot: {
            name: config.spot || 'N/A',
            hosts: spotData,
            gpu_summary: spotGpuSummary
        },
        contracts: {
            name: `Contracts (${(config.contracts || []).length} contracts)`,
            hosts: contractData,
            gpu_summary: contractGpuSummary,
            contracts_list: config.contracts || []
        },
        outofstock: {
            name: 'Out of Stock',
            hosts: outofstockHosts,
            gpu_summary: outofstockGpuSummary
        },
        gpu_overview: {
            total_gpu_used: totalGpuUsed,
            total_gpu_capacity: totalGpuCapacity,
            gpu_usage_ratio: `${totalGpuUsed}/${totalGpuCapacity}`,
            gpu_usage_percentage: gpuUsagePercentage
        },
        performance_stats: {
            total_time: 0,
            total_hosts: totalHosts,
            hosts_per_second: 0,
            method: 'client_cache'
        }
    };
}

// Get contract aggregates directly from already loaded data (no API calls needed)
function getContractAggregatesDirectly(gpuType) {
    console.log(`📋 Getting contract aggregates directly for GPU type: ${gpuType}`);
    
    // Check if we have access to the full parallel data structure
    // We need window.loadedParallelData which should contain the complete data structure
    if (!window.loadedParallelData) {
        console.warn('⚠️ Full parallel data not available - need to make API call');
        return null;
    }
    
    if (!window.loadedParallelData[gpuType]) {
        console.warn(`⚠️ No parallel data found for GPU type: ${gpuType}`);
        return null;
    }
    
    const gpuData = window.loadedParallelData[gpuType];
    const config = gpuData.config;
    const allHostsData = gpuData.hosts || [];
    
    if (!config.contracts || !Array.isArray(config.contracts)) {
        console.log(`📋 No contracts found for GPU type: ${gpuType}`);
        return {
            gpu_type: gpuType,
            contracts: []
        };
    }
    
    console.log(`🔍 Found ${config.contracts.length} contracts in parallel data for ${gpuType}`);
    
    // Build contract details by filtering hosts that belong to each contract aggregate
    const contractDetails = [];
    
    config.contracts.forEach(contract => {
        const aggregateName = contract.aggregate;
        
        // Filter hosts that belong to this contract aggregate
        const contractHosts = allHostsData.filter(host => 
            host.aggregate === aggregateName || 
            (host.host_data && host.host_data.aggregate === aggregateName)
        );
        
        console.log(`📋 Contract ${contract.name} (${aggregateName}): ${contractHosts.length} hosts`);
        
        contractDetails.push({
            aggregate: aggregateName,
            name: contract.name,
            hosts: contractHosts,
            host_count: contractHosts.length
        });
    });
    
    const totalHosts = contractDetails.reduce((sum, contract) => sum + contract.hosts.length, 0);
    console.log(`✅ Retrieved ${contractDetails.length} contracts with ${totalHosts} total hosts for ${gpuType}`);
    
    return {
        gpu_type: gpuType,
        contracts: contractDetails
    };
}

// Get contract aggregates from cached data (faster than API call)
function getContractAggregatesFromCache(gpuType) {
    console.log(`📋 Getting contract aggregates from cache for GPU type: ${gpuType}`);
    
    if (!window.gpuAggregatesCache.isValid()) {
        console.warn('⚠️ GPU aggregates cache is invalid or expired');
        return null;
    }
    
    const aggregatesData = window.gpuAggregatesCache.data;
    if (!aggregatesData || !aggregatesData[gpuType]) {
        console.warn(`⚠️ No cached data found for GPU type: ${gpuType}`);
        return null;
    }
    
    const gpuData = aggregatesData[gpuType];
    
    
    // Extract contract information from the cached data
    const contracts = [];
    
    // The contracts are stored directly in the 'contracts' key
    if (gpuData.contracts && Array.isArray(gpuData.contracts)) {
        gpuData.contracts.forEach(contract => {
            contracts.push({
                aggregate: contract.aggregate,
                name: contract.name,
                hosts: [], // Will be populated if we have host data
                host_count: 0 // Will be updated if we have host data
            });
        });
    }
    
    console.log(`✅ Found ${contracts.length} contracts in cache for ${gpuType}`);
    
    return {
        gpu_type: gpuType,
        contracts: contracts,
        config: gpuData
    };
}

// Export OpenStack module
console.log('OpenStack module loaded');

// Export OpenStack functions
window.OpenStack = {
    executeHostMigration,
    loadAggregateData,
    loadGpuTypes,
    loadOverallGpuUsage,
    previewMigration,
    getHostVmDetails,
    generateMigrationCommands,
    executeNetworkCommand,
    getContractAggregatesFromCache,
    getContractAggregatesDirectly,
    processParallelDataForGpuType
};