/**
 * Variant Column Settings Manager
 * Settings modal for configuring which aggregate suffixes appear as separate columns.
 */
window.VariantSettings = (function() {
    'use strict';

    async function openSettingsModal() {
        const body = document.getElementById('variantSettingsBody');
        body.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin fa-2x"></i><p class="mt-2">Loading settings...</p></div>';

        const modal = new bootstrap.Modal(document.getElementById('variantSettingsModal'));
        modal.show();

        try {
            const response = await fetch('/api/settings/variant-columns');
            if (!response.ok) throw new Error('Failed to load settings');
            const data = await response.json();
            renderSettingsModal(data.settings, data.discovered_suffixes || [], data.discovered_variants || []);
        } catch (error) {
            body.innerHTML = `<div class="alert alert-danger">Failed to load settings: ${error.message}</div>`;
        }
    }

    function renderSettingsModal(settings, discoveredSuffixes, discoveredVariants) {
        const body = document.getElementById('variantSettingsBody');
        const activeSuffixes = (settings.split_suffixes || []).map(s => s.toLowerCase());

        // Union of active + discovered suffixes
        const allSuffixesSet = new Set();
        (settings.split_suffixes || []).forEach(s => allSuffixesSet.add(s));
        discoveredSuffixes.forEach(s => allSuffixesSet.add(s));
        const allSuffixes = Array.from(allSuffixesSet).sort();

        let html = `
            <p class="text-muted mb-3">
                Select which aggregate suffixes should appear as separate columns
                in the on-demand view. Unchecked suffixes will have their hosts
                merged into the base on-demand column.
            </p>

            <h6 class="mb-2"><i class="fas fa-columns me-1"></i> Split Suffixes</h6>
            <div class="mb-3" id="suffixCheckboxes">
        `;

        if (allSuffixes.length === 0) {
            html += '<p class="text-muted fst-italic">No suffixes discovered yet.</p>';
        } else {
            allSuffixes.forEach(suffix => {
                const isChecked = activeSuffixes.includes(suffix.toLowerCase());
                const isDiscovered = discoveredSuffixes.map(s => s.toLowerCase()).includes(suffix.toLowerCase());
                const badge = isDiscovered ? '' : ' <span class="badge bg-secondary">custom</span>';
                html += `
                    <div class="form-check">
                        <input class="form-check-input suffix-checkbox" type="checkbox"
                               value="${suffix}" id="suffix_${suffix}" ${isChecked ? 'checked' : ''}>
                        <label class="form-check-label" for="suffix_${suffix}">
                            <code>-${suffix}</code>${badge}
                        </label>
                    </div>
                `;
            });
        }

        html += `</div>`;

        // Custom suffix input
        html += `
            <h6 class="mb-2 mt-3"><i class="fas fa-plus me-1"></i> Add Custom Suffix</h6>
            <div class="input-group input-group-sm mb-3">
                <span class="input-group-text">-</span>
                <input type="text" class="form-control" id="customSuffixInput"
                       placeholder="e.g., Maintenance">
                <button class="btn btn-outline-primary" type="button"
                        onclick="VariantSettings.addCustomSuffix()">Add</button>
            </div>
        `;

        // Discovered variants table
        if (discoveredVariants.length > 0) {
            // Group by gpu_type, only show non-base variants
            const nonBase = discoveredVariants.filter(v => {
                // base variant has no suffix beyond -n3
                return v.aggregate !== v.gpu_type + '-n3';
            });

            if (nonBase.length > 0) {
                html += `
                    <h6 class="mb-2 mt-3"><i class="fas fa-eye me-1"></i> Discovered Variant Aggregates</h6>
                    <div class="table-responsive" style="max-height: 200px; overflow-y: auto;">
                        <table class="table table-sm table-striped mb-0">
                            <thead><tr>
                                <th>GPU Type</th>
                                <th>Aggregate</th>
                            </tr></thead>
                            <tbody>
                `;
                nonBase.forEach(v => {
                    html += `<tr><td>${v.gpu_type}</td><td><code>${v.aggregate}</code></td></tr>`;
                });
                html += `</tbody></table></div>`;
            }
        }

        if (settings.updated_at) {
            html += `<p class="text-muted small mt-3 mb-0">Last saved: ${new Date(settings.updated_at).toLocaleString()}</p>`;
        }

        body.innerHTML = html;
    }

    function addCustomSuffix() {
        const input = document.getElementById('customSuffixInput');
        const value = input.value.trim();
        if (!value) return;

        // Check if already exists
        const existing = document.getElementById(`suffix_${value}`);
        if (existing) {
            existing.checked = true;
            input.value = '';
            return;
        }

        const container = document.getElementById('suffixCheckboxes');
        const div = document.createElement('div');
        div.className = 'form-check';
        div.innerHTML = `
            <input class="form-check-input suffix-checkbox" type="checkbox"
                   value="${value}" id="suffix_${value}" checked>
            <label class="form-check-label" for="suffix_${value}">
                <code>-${value}</code> <span class="badge bg-info">new</span>
            </label>
        `;
        container.appendChild(div);
        input.value = '';
    }

    async function saveSettings() {
        const checkboxes = document.querySelectorAll('.suffix-checkbox:checked');
        const suffixes = Array.from(checkboxes).map(cb => cb.value);

        const saveBtn = document.querySelector('#variantSettingsModal .btn-primary');
        const origText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';
        saveBtn.disabled = true;

        try {
            const response = await fetch('/api/settings/variant-columns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ split_suffixes: suffixes })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Unknown error');
            }

            // Reload frontend settings cache
            if (window.Frontend && window.Frontend.loadVariantColumnSettings) {
                await window.Frontend.loadVariantColumnSettings();
            }

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('variantSettingsModal'));
            modal.hide();

            // Show notification
            if (window.CacheManager && window.CacheManager.showNotification) {
                window.CacheManager.showNotification('Variant column settings saved. Refreshing...', 'success');
            }

            // Clear all frontend caches and reload current GPU type
            if (window.gpuDataCache) window.gpuDataCache.clear();
            window.loadedParallelData = null;

            // Reload current view
            const gpuSelect = document.getElementById('gpuTypeSelect');
            if (gpuSelect && gpuSelect.value) {
                gpuSelect.dispatchEvent(new Event('change'));
            }

        } catch (error) {
            alert('Failed to save settings: ' + error.message);
        } finally {
            saveBtn.innerHTML = origText;
            saveBtn.disabled = false;
        }
    }

    console.log('✅ Variant Settings module loaded');

    return {
        openSettingsModal,
        addCustomSuffix,
        saveSettings
    };
})();
