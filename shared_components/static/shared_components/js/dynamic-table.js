// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

class DynamicTable {
    constructor(container) {
        console.log("Initializing DynamicTable");
        
        // Debug logging
        console.log("Container:", container);
        console.log("Dataset:", {
            tableId: container.dataset.tableId,
            contentType: container.dataset.contentType,
            apiUrl: container.dataset.apiUrl,
            tableConfig: container.dataset.tableConfig
        });

        this.container = container;
        this.tableId = container.dataset.tableId;
        this.contentType = container.dataset.contentType;
        this.apiUrl = container.dataset.apiUrl;
        console.log("API URL:", this.apiUrl);  // Debug log
        this.selectedRows = new Set();
        this.resizingColumn = null;
        this.draggedColumn = null;
        
        // Debug log the initialization parameters
        console.log("Table Configuration:", {
            tableId: this.tableId,
            contentType: this.contentType,
            apiUrl: this.apiUrl,
            container: container.innerHTML
        });

        this.initializeTable();
        this.setupEventListeners();
        this.setupDragAndDrop();
        this.setupResizing();
    }

    async initializeTable() {
        console.log("Initializing table state");
        this.state = {
            page: 1,
            pageSize: 10,
            sortColumn: null,
            sortDirection: null,
            filters: [],
            search: '',
            view: 'grid',
            columnPreferences: this.loadColumnPreferences()
        };

        await this.fetchData();
        this.updateColumnVisibility();
    }

    loadColumnPreferences() {
        const key = `table_${this.tableId}_columns`;
        const saved = localStorage.getItem(key);
        return saved ? JSON.parse(saved) : {};
    }

    saveColumnPreferences() {
        const key = `table_${this.tableId}_columns`;
        localStorage.setItem(key, JSON.stringify(this.state.columnPreferences));
    }

    setupEventListeners() {
        // Search
        const searchInput = this.container.querySelector('.table-search');
        searchInput?.addEventListener('input', debounce((e) => this.handleSearch(e), 300));

        // Column visibility toggles
        this.container.querySelectorAll('.column-toggle').forEach(toggle => {
            toggle.addEventListener('change', (e) => this.handleColumnToggle(e));
        });

        // Sorting
        this.container.querySelectorAll('th[data-field-path]').forEach(th => {
            th.addEventListener('click', (e) => this.handleSort(e));
        });

        // Row selection
        this.container.querySelector('.select-all-checkbox')?.addEventListener('change', (e) => {
            this.handleSelectAll(e);
        });

        // View switching
        this.container.addEventListener('switch-view', (e) => {
            this.switchView(e.detail);
        });

        // Export
        this.container.addEventListener('export-data', (e) => {
            this.exportData(e.detail);
        });

        // Custom events for modals
        this.setupModalEvents();
    }

    setupModalEvents() {
        // Column editor events
        document.addEventListener('save-column', async (e) => {
            const columnData = e.detail;
            await this.saveColumn(columnData);
        });

        // Filter editor events
        document.addEventListener('apply-filters', (e) => {
            this.state.filters = e.detail;
            this.fetchData();
        });

        // Row editor events
        document.addEventListener('save-row', async (e) => {
            const rowData = e.detail;
            await this.saveRow(rowData);
        });
    }

    setupDragAndDrop() {
        const table = this.container.querySelector('table');
        const headers = table.querySelectorAll('th[data-column-id]');
        
        headers.forEach(header => {
            header.setAttribute('draggable', 'true');
            
            header.addEventListener('dragstart', (e) => {
                this.draggedColumn = header;
                header.classList.add('opacity-50');
            });

            header.addEventListener('dragover', (e) => {
                e.preventDefault();
                const targetColumn = e.target.closest('th');
                if (targetColumn && this.draggedColumn !== targetColumn) {
                    this.showDropIndicator(targetColumn);
                }
            });

            header.addEventListener('drop', (e) => {
                e.preventDefault();
                const targetColumn = e.target.closest('th');
                if (targetColumn && this.draggedColumn !== targetColumn) {
                    this.reorderColumn(this.draggedColumn, targetColumn);
                }
                this.hideDropIndicators();
                this.draggedColumn.classList.remove('opacity-50');
                this.draggedColumn = null;
            });

            header.addEventListener('dragend', () => {
                this.hideDropIndicators();
                if (this.draggedColumn) {
                    this.draggedColumn.classList.remove('opacity-50');
                    this.draggedColumn = null;
                }
            });
        });
    }

    setupResizing() {
        const headers = this.container.querySelectorAll('th[data-column-id]');
        
        headers.forEach(header => {
            const resizeHandle = header.querySelector('.column-resize-handle');
            
            resizeHandle?.addEventListener('mousedown', (e) => {
                e.preventDefault();
                this.resizingColumn = {
                    element: header,
                    startWidth: header.offsetWidth,
                    startX: e.pageX
                };
                
                document.addEventListener('mousemove', this.handleResize);
                document.addEventListener('mouseup', () => {
                    this.resizingColumn = null;
                    document.removeEventListener('mousemove', this.handleResize);
                }, { once: true });
            });
        });
    }

    handleResize = (e) => {
        if (!this.resizingColumn) return;
        
        const diff = e.pageX - this.resizingColumn.startX;
        const newWidth = Math.max(100, this.resizingColumn.startWidth + diff);
        this.resizingColumn.element.style.width = `${newWidth}px`;
    }

    async handleSearch(event) {
        this.state.search = event.target.value;
        this.state.page = 1;
        await this.fetchData();
    }

    async handleSort(event) {
        const th = event.currentTarget;
        const fieldPath = th.dataset.fieldPath;

        if (this.state.sortColumn === fieldPath) {
            this.state.sortDirection = this.state.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.state.sortColumn = fieldPath;
            this.state.sortDirection = 'asc';
        }

        this.updateSortIndicators();
        await this.fetchData();
    }

    handleSelectAll(event) {
        const checked = event.target.checked;
        const checkboxes = this.container.querySelectorAll('tbody .row-checkbox');
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
            const rowId = checkbox.dataset.rowId;
            if (checked) {
                this.selectedRows.add(rowId);
            } else {
                this.selectedRows.delete(rowId);
            }
        });

        this.updateBulkActions();
    }

    async saveColumn(columnData) {
        try {
            const response = await fetch(`${this.apiUrl}columns/`, {
                method: columnData.id ? 'PUT' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(columnData)
            });

            if (!response.ok) throw new Error('Failed to save column');
            
            await this.fetchData();
            this.updateColumnVisibility();
        } catch (error) {
            console.error('Error saving column:', error);
            this.showError('Failed to save column');
        }
    }

    async saveRow(rowData) {
        try {
            const response = await fetch(this.apiUrl, {
                method: rowData.id ? 'PUT' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(rowData)
            });

            if (!response.ok) throw new Error('Failed to save row');
            
            await this.fetchData();
        } catch (error) {
            console.error('Error saving row:', error);
            this.showError('Failed to save row');
        }
    }

    async fetchData() {
        try {
            console.log("Fetching data with state:", this.state);
            console.log("Using API URL:", this.apiUrl);
            
            const response = await fetch(this.apiUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            console.log("Response status:", response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("Received data:", data);

            if (!data || !data.results) {
                throw new Error('Invalid data format received from API');
            }

            await this.renderTable(data);
            this.renderPagination(data);
        } catch (error) {
            console.error("Error fetching data:", error);
            this.showError(`Failed to load data: ${error.message}`);
        }
    }

    async renderTable(data) {
        console.log("Starting table render with data:", data);
        const tbody = this.container.querySelector('tbody');
        
        if (!tbody) {
            console.error("Could not find tbody element");
            return;
        }

        // Clear existing content
        tbody.innerHTML = '';

        if (!data.results || data.results.length === 0) {
            console.log("No data to display");
            tbody.innerHTML = `
                <tr>
                    <td colspan="100%" class="px-3 py-4 text-sm text-gray-500 text-center">
                        No data available
                    </td>
                </tr>
            `;
            return;
        }

        // Get all visible headers and their field paths
        const headers = Array.from(this.container.querySelectorAll('th[data-field-path]'));
        console.log("Found headers:", headers.map(h => ({
            fieldPath: h.dataset.fieldPath,
            dataType: h.dataset.dataType,
            text: h.textContent
        })));

        // Create rows
        data.results.forEach((row, index) => {
            console.log(`Processing row ${index}:`, row);
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-gray-50';
            
            // Add checkbox column
            const checkboxTd = document.createElement('td');
            checkboxTd.className = 'w-12 px-3 py-4';
            checkboxTd.innerHTML = `
                <input type="checkbox" 
                       class="row-checkbox form-checkbox"
                       data-row-id="${row.id}"
                       ${this.selectedRows.has(row.id) ? 'checked' : ''}>
            `;
            tr.appendChild(checkboxTd);

            // Add data columns
            headers.forEach(header => {
                const fieldPath = header.dataset.fieldPath;
                const dataType = header.dataset.dataType;
                console.log(`Creating cell for ${fieldPath}:`, row[fieldPath]);

                const td = document.createElement('td');
                td.className = 'px-3 py-4 text-sm text-gray-500';
                const value = row[fieldPath];
                td.textContent = value !== undefined ? value : '';
                tr.appendChild(td);
            });

            // Add actions column
            const actionsTd = document.createElement('td');
            actionsTd.className = 'px-3 py-4 text-sm text-right';
            actionsTd.innerHTML = `
                <div class="flex justify-end space-x-2">
                    <button class="text-indigo-600 hover:text-indigo-900"
                            onclick="document.dispatchEvent(new CustomEvent('edit-row', { detail: { id: '${row.id}' } }))">
                        Edit
                    </button>
                    <button class="text-red-600 hover:text-red-900"
                            onclick="if(confirm('Are you sure?')) document.dispatchEvent(new CustomEvent('delete-row', { detail: { id: '${row.id}' } }))">
                        Delete
                    </button>
                </div>
            `;
            tr.appendChild(actionsTd);

            tbody.appendChild(tr);
        });

        console.log("Table render complete");
    }

    renderPagination(data) {
        const container = this.container.querySelector('.pagination-controls');
        if (!container) return;

        const totalPages = Math.ceil(data.count / this.state.pageSize);
        
        container.innerHTML = `
            <div class="flex items-center justify-between space-x-2">
                <button class="btn-secondary ${this.state.page === 1 ? 'opacity-50 cursor-not-allowed' : ''}"
                        ${this.state.page === 1 ? 'disabled' : ''}
                        data-action="previous">
                    Previous
                </button>
                <span class="text-sm text-gray-700">
                    Page ${this.state.page} of ${totalPages}
                </span>
                <button class="btn-secondary ${this.state.page === totalPages ? 'opacity-50 cursor-not-allowed' : ''}"
                        ${this.state.page === totalPages ? 'disabled' : ''}
                        data-action="next">
                    Next
                </button>
            </div>
        `;

        container.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', async (e) => {
                const action = e.target.dataset.action;
                if (action === 'previous' && this.state.page > 1) {
                    this.state.page--;
                } else if (action === 'next' && this.state.page < totalPages) {
                    this.state.page++;
                }
                await this.fetchData();
            });
        });
    }

    showError(message) {
        console.error("Error:", message);
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    formatCellValue(row, column) {
        const value = this.getNestedValue(row, column.field_path);
        
        switch (column.data_type) {
            case 'email':
                return `<a href="mailto:${value}" class="text-indigo-600 hover:text-indigo-900">${value}</a>`;
            case 'url':
                return `<a href="${value}" target="_blank" class="text-indigo-600 hover:text-indigo-900">${value}</a>`;
            case 'boolean':
                return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    value ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }">${value ? 'Yes' : 'No'}</span>`;
            case 'date':
                return value ? new Date(value).toLocaleDateString() : '';
            case 'choice':
                return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">${value}</span>`;
            case 'number':
                return value?.toLocaleString() || '';
            default:
                return value || '';
        }
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => 
            current ? current[key] : undefined, obj);
    }

    renderActions(row) {
        return `
            <div class="flex justify-end space-x-2">
                <button class="text-indigo-600 hover:text-indigo-900"
                        onclick="document.dispatchEvent(new CustomEvent('edit-row', { detail: { id: '${row.id}' } }))">
                    Edit
                </button>
                <button class="text-red-600 hover:text-red-900"
                        onclick="if(confirm('Are you sure you want to delete this record?')) this.deleteRow('${row.id}')">
                    Delete
                </button>
            </div>
        `;
    }

    async deleteRow(rowId) {
        try {
            const response = await fetch(`${this.apiUrl}${rowId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });

            if (!response.ok) throw new Error('Failed to delete row');
            
            await this.fetchData();
            this.showSuccess('Record deleted successfully');
        } catch (error) {
            console.error('Error deleting row:', error);
            this.showError('Failed to delete record');
        }
    }

    updateColumnVisibility() {
        Object.entries(this.state.columnPreferences).forEach(([columnId, isVisible]) => {
            const cells = this.container.querySelectorAll(`[data-column-id="${columnId}"]`);
            cells.forEach(cell => {
                cell.style.display = isVisible ? '' : 'none';
            });
        });
    }

    updateSortIndicators() {
        this.container.querySelectorAll('th.sortable .sort-indicator').forEach(indicator => {
            const th = indicator.closest('th');
            const fieldPath = th.dataset.fieldPath;
            
            if (fieldPath === this.state.sortColumn) {
                indicator.textContent = this.state.sortDirection === 'asc' ? '↑' : '↓';
            } else {
                indicator.textContent = '↕️';
            }
        });
    }

    setupRowEventListeners() {
        // Add event listeners for row actions
        this.container.querySelectorAll('.row-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.handleRowAction(e));
        });

        this.container.querySelectorAll('.row-actions').forEach(actions => {
            actions.addEventListener('click', (e) => this.handleRowAction(e));
        });
    }

    handleRowAction(event) {
        const action = event.target.dataset.action;
        const rowId = event.target.dataset.rowId;

        switch (action) {
            case 'edit':
                this.handleEdit(rowId);
                break;
            case 'view':
                this.handleView(rowId);
                break;
            case 'delete':
                this.handleDelete(rowId);
                break;
            default:
                console.warn(`Unknown row action: ${action}`);
        }
    }

    handleEdit(rowId) {
        // Implement the edit logic
        console.log(`Editing row with ID: ${rowId}`);
    }

    handleView(rowId) {
        // Implement the view logic
        console.log(`Viewing row with ID: ${rowId}`);
    }

    handleDelete(rowId) {
        // Implement the delete logic
        console.log(`Deleting row with ID: ${rowId}`);
    }

    handleColumnToggle(event) {
        const columnId = event.target.dataset.columnId;
        const isVisible = event.target.checked;
        
        this.state.columnPreferences[columnId] = isVisible;
        this.saveColumnPreferences();
        this.updateColumnVisibility();
    }

    switchView(viewType) {
        this.state.view = viewType;
        this.saveViewPreference();
        this.renderView();
    }

    renderView() {
        switch (this.state.view) {
            case 'grid':
                this.renderGridView();
                break;
            case 'kanban':
                this.renderKanbanView();
                break;
            case 'calendar':
                this.renderCalendarView();
                break;
        }
    }

    renderGridView() {
        this.container.querySelector('table').style.display = 'table';
        this.container.querySelector('.kanban-view')?.style.display = 'none';
        this.container.querySelector('.calendar-view')?.style.display = 'none';
    }

    renderKanbanView() {
        // Implementation for Kanban view
        console.log('Kanban view not implemented yet');
    }

    renderCalendarView() {
        // Implementation for Calendar view
        console.log('Calendar view not implemented yet');
    }

    async exportData(format) {
        try {
            const response = await fetch(`${this.apiUrl}export/?format=${format}`, {
                headers: {
                    'X-CSRFToken': this.getCsrfToken()
                }
            });

            if (!response.ok) throw new Error('Failed to export data');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `export.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error exporting data:', error);
            this.showError('Failed to export data');
        }
    }

    showDropIndicator(targetColumn) {
        this.hideDropIndicators();
        const indicator = document.createElement('div');
        indicator.className = 'absolute inset-y-0 w-1 bg-indigo-500';
        
        const rect = targetColumn.getBoundingClientRect();
        const tableRect = this.container.querySelector('table').getBoundingClientRect();
        
        if (this.draggedColumn.offsetLeft < targetColumn.offsetLeft) {
            indicator.style.right = '0';
            targetColumn.appendChild(indicator);
        } else {
            indicator.style.left = '0';
            targetColumn.appendChild(indicator);
        }
    }

    hideDropIndicators() {
        this.container.querySelectorAll('.drop-indicator').forEach(indicator => {
            indicator.remove();
        });
    }

    async reorderColumn(draggedColumn, targetColumn) {
        const draggedId = draggedColumn.dataset.columnId;
        const targetId = targetColumn.dataset.columnId;
        
        try {
            const response = await fetch(`${this.apiUrl}columns/reorder/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({
                    dragged_id: draggedId,
                    target_id: targetId
                })
            });

            if (!response.ok) throw new Error('Failed to reorder columns');
            
            await this.fetchData();
        } catch (error) {
            console.error('Error reordering columns:', error);
            this.showError('Failed to reorder columns');
        }
    }

    showSuccess(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }

    saveViewPreference() {
        localStorage.setItem(`table_${this.tableId}_view`, this.state.view);
    }

    loadViewPreference() {
        return localStorage.getItem(`table_${this.tableId}_view`) || 'grid';
    }
}

// Initialize tables
document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Content Loaded - Initializing tables");
    const containers = document.querySelectorAll('.dynamic-table-container');
    console.log("Found table containers:", containers.length);  // Debug log
    containers.forEach(container => {
        new DynamicTable(container);
    });
}); 