class DataTable {
    constructor(tableId, options = {}) {
        this.tableId = tableId;
        this.table = document.getElementById(tableId);
        this.options = {
            storageKey: options.storageKey || 'tableColumns',
            searchFields: options.searchFields || [], // Array of data-column values to search in
            filterConfigs: options.filterConfigs || [], // Array of filter configurations
            enableReorder: options.enableReorder || true,
            enableRowLinks: options.enableRowLinks || false, // NEW: Enable clickable rows
            ...options
        };
        
        this.draggedColumn = null;
        this.draggedIndex = null;
        this.dragOverColumn = null;
        this.initialX = 0;
        this.ghostElement = null;
        
        // Bind the methods to the class instance
        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.handleMouseUp = this.handleMouseUp.bind(this);
        
        this.init();
    }

    init() {
        this.setupColumnToggle();
        this.setupFilters();
        this.loadColumnPreferences();
        if (this.options.enableReorder) {
            this.setupColumnReorder();
        }
        // NEW: Setup clickable rows if enabled
        if (this.options.enableRowLinks) {
            this.setupClickableRows();
        }
        this.initialFilter();
    }

    setupColumnToggle() {
        const columnMenuButton = document.getElementById('column-menu-button');
        const columnMenu = document.getElementById('column-menu');

        if (columnMenuButton && columnMenu) {
            columnMenuButton.addEventListener('click', () => {
                columnMenu.classList.toggle('hidden');
            });

            // Close menu when clicking outside
            document.addEventListener('click', (event) => {
                if (!columnMenuButton.contains(event.target) && !columnMenu.contains(event.target)) {
                    columnMenu.classList.add('hidden');
                }
            });

            // Handle column toggle changes
            document.querySelectorAll('.column-toggle').forEach(toggle => {
                toggle.addEventListener('change', () => {
                    this.toggleColumn(toggle.dataset.column, toggle.checked);
                    this.saveColumnPreferences();
                });
            });
        }
    }

    setupFilters() {
        // Setup search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', () => this.filterTable());
        }

        // Setup all filter dropdowns
        this.options.filterConfigs.forEach(config => {
            const filter = document.getElementById(`${config.id}-filter`);
            if (filter) {
                filter.addEventListener('change', () => this.filterTable());
            }
        });
    }

    setupColumnReorder() {
        const thead = this.table.querySelector('thead tr');
        const headers = thead.querySelectorAll('th:not(:last-child)');

        headers.forEach((th, index) => {
            th.style.cursor = 'move';
            th.style.userSelect = 'none'; // Prevent text selection while dragging

            th.addEventListener('mousedown', (e) => {
                e.preventDefault(); // Prevent text selection
                
                this.draggedColumn = th;
                this.draggedIndex = index;
                this.initialX = e.clientX;
                
                // Create and position ghost element
                const ghost = this.createGhostElement(th);
                document.body.appendChild(ghost);
                this.ghostElement = ghost;
                
                // Add dragging class
                th.classList.add('dragging');
                
                // Add document-level event listeners
                document.addEventListener('mousemove', this.handleMouseMove);
                document.addEventListener('mouseup', this.handleMouseUp);
            });
        });

        // Add this to your existing drag-and-drop initialization code
        document.querySelectorAll('th[data-column]').forEach(th => {
            if (th.dataset.column !== 'actions') {  // Skip actions column
                th.addEventListener('dragstart', handleDragStart);
                th.addEventListener('dragover', handleDragOver);
                th.addEventListener('drop', handleDrop);
            }
        });
    }

    createGhostElement(th) {
        const ghost = document.createElement('div');
        ghost.className = 'column-ghost';
        
        // Get the column index
        const columnIndex = Array.from(th.parentNode.children).indexOf(th);
        
        // Get all cells in this column including header
        const columnCells = [th, ...this.table.querySelectorAll(`tbody tr td:nth-child(${columnIndex + 1})`)];
        
        // Calculate total height of the table
        const tableRect = this.table.getBoundingClientRect();
        const headerRect = th.getBoundingClientRect();
        
        // Set ghost dimensions and position
        ghost.style.width = `${headerRect.width}px`;
        ghost.style.height = `${tableRect.height}px`;
        ghost.style.top = `${tableRect.top + window.scrollY}px`;
        ghost.style.left = `${headerRect.left}px`;
        
        return ghost;
    }

    handleMouseMove(e) {
        if (!this.draggedColumn || !this.ghostElement) return;

        // Calculate the movement
        const deltaX = e.clientX - this.initialX;
        this.ghostElement.style.transform = `translateX(${deltaX}px)`;

        // Find the header we're currently over
        const headers = Array.from(this.draggedColumn.parentNode.children);
        const mouseX = e.clientX;

        // Find closest header
        let closestHeader = null;
        let minDistance = Infinity;

        headers.forEach(header => {
            if (header !== this.draggedColumn && !header.classList.contains('actions-column')) {
                const rect = header.getBoundingClientRect();
                const headerCenter = rect.left + rect.width / 2;
                const distance = Math.abs(mouseX - headerCenter);
                
                if (distance < minDistance) {
                    minDistance = distance;
                    closestHeader = header;
                }
            }
        });

        // Update drop indicator
        if (closestHeader !== this.dragOverColumn) {
            this.clearDropZoneHighlight();
            if (closestHeader) {
                this.highlightDropZone(closestHeader);
                this.dragOverColumn = closestHeader;
            }
        }
    }

    handleMouseUp(e) {
        if (this.draggedColumn && this.dragOverColumn) {
            const targetIndex = Array.from(this.draggedColumn.parentNode.children)
                .indexOf(this.dragOverColumn);
            
            if (targetIndex !== this.draggedIndex) {
                this.reorderColumns(this.draggedIndex, targetIndex);
            }
        }

        this.cleanup();
    }

    cleanup() {
        if (this.ghostElement) {
            this.ghostElement.remove();
            this.ghostElement = null;
        }

        if (this.draggedColumn) {
            this.draggedColumn.classList.remove('dragging');
            this.draggedColumn = null;
        }

        this.clearDropZoneHighlight();
        this.dragOverColumn = null;
        this.draggedIndex = null;

        document.removeEventListener('mousemove', this.handleMouseMove);
        document.removeEventListener('mouseup', this.handleMouseUp);
    }

    highlightDropZone(element) {
        this.clearDropZoneHighlight();
        element.classList.add('drop-zone-highlight');
    }

    clearDropZoneHighlight() {
        this.table.querySelectorAll('.drop-zone-highlight').forEach(el => {
            el.classList.remove('drop-zone-highlight');
        });
    }

    reorderColumns(fromIndex, toIndex) {
        const rows = Array.from(this.table.querySelectorAll('tr'));
        
        rows.forEach(row => {
            const cells = Array.from(row.children);
            const movedCell = cells[fromIndex];
            
            if (fromIndex < toIndex) {
                row.insertBefore(movedCell, cells[toIndex + 1]);
            } else {
                row.insertBefore(movedCell, cells[toIndex]);
            }
        });

        this.saveColumnOrder();
    }

    saveColumnOrder() {
        const headers = Array.from(this.table.querySelectorAll('thead th'));
        const order = headers.map(th => th.dataset.column).filter(Boolean);
        localStorage.setItem(`${this.options.storageKey}_order`, JSON.stringify(order));
    }

    toggleColumn(column, isVisible) {
        document.querySelectorAll(`#${this.tableId} [data-column="${column}"]`)
            .forEach(cell => {
                if (isVisible) {
                    cell.classList.remove('hidden');
                } else {
                    cell.classList.add('hidden');
                }
            });
    }

    loadColumnPreferences() {
        const preferences = JSON.parse(localStorage.getItem(this.options.storageKey) || '{}');
        
        document.querySelectorAll('.column-toggle').forEach(toggle => {
            const column = toggle.dataset.column;
            const isVisible = preferences.hasOwnProperty(column) ? preferences[column] : true;
            
            toggle.checked = isVisible;
            this.toggleColumn(column, isVisible);
        });
    }

    saveColumnPreferences() {
        const preferences = {};
        document.querySelectorAll('.column-toggle').forEach(toggle => {
            preferences[toggle.dataset.column] = toggle.checked;
        });
        localStorage.setItem(this.options.storageKey, JSON.stringify(preferences));
    }

    filterTable() {
        const searchTerm = document.getElementById('search-input')?.value.toLowerCase() || '';
        const filterValues = this.getFilterValues();
        
        const tableRows = Array.from(document.querySelectorAll(`#${this.tableId} tbody tr`))
            .filter(row => !row.classList.contains('empty-row'));

        let visibleCount = 0;

        tableRows.forEach(row => {
            const matchesSearch = this.matchesSearch(row, searchTerm);
            const matchesFilters = this.matchesFilters(row, filterValues);

            if (matchesSearch && matchesFilters) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        this.toggleEmptyMessage(visibleCount === 0);
    }

    matchesSearch(row, searchTerm) {
        if (!searchTerm) return true;

        return this.options.searchFields.some(field => {
            const cell = row.querySelector(`[data-column="${field}"]`);
            return cell?.textContent?.toLowerCase().includes(searchTerm);
        });
    }

    matchesFilters(row, filterValues) {
        return this.options.filterConfigs.every(config => {
            const filterValue = filterValues[config.id];
            if (!filterValue) return true;

            const cell = row.querySelector(`[data-column="${config.column}"]`);
            const cellText = config.getContent ? 
                config.getContent(cell) : 
                cell?.textContent?.toLowerCase() || '';

            return cellText.includes(filterValue.toLowerCase());
        });
    }

    getFilterValues() {
        const values = {};
        this.options.filterConfigs.forEach(config => {
            const filter = document.getElementById(`${config.id}-filter`);
            if (filter) {
                values[config.id] = filter.value;
            }
        });
        return values;
    }

    toggleEmptyMessage(show) {
        const emptyMessage = document.querySelector(`#${this.tableId} .empty-row`);
        if (emptyMessage) {
            emptyMessage.style.display = show ? '' : 'none';
        }
    }

    initialFilter() {
        this.filterTable();
    }

    // NEW: Add this method to handle clickable rows
    setupClickableRows() {
        const clickableRows = this.table.querySelectorAll('tbody tr[data-href]');
        clickableRows.forEach(row => {
            // Visual hover effects
            row.addEventListener('mouseover', () => {
                row.classList.add('row-hover');
            });
            
            row.addEventListener('mouseout', () => {
                row.classList.remove('row-hover');
            });
            
            // Row click handler
            row.addEventListener('click', (event) => {
                // Don't navigate if clicking on action buttons/links or action column
                if (!event.target.closest('a, button') && 
                    !event.target.closest('td[data-column="actions"]')) {
                    window.location.href = row.dataset.href;
                }
            });
        });
        
        // Stop propagation for action column clicks
        this.table.querySelectorAll('td[data-column="actions"]').forEach(cell => {
            cell.addEventListener('click', (event) => {
                event.stopPropagation();
            });
        });
        
        // Also stop propagation for any buttons and links inside rows
        this.table.querySelectorAll('tr[data-href] a, tr[data-href] button').forEach(element => {
            element.addEventListener('click', (event) => {
                event.stopPropagation();
            });
        });
    }
}

// Initialize tables when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const tables = document.querySelectorAll('[id$="-table"]');
    tables.forEach(table => {
        // Check if this table should have clickable rows
        const hasRowLinks = table.querySelector('tbody tr[data-href]') !== null;
        
        new DataTable(table.id, {
            storageKey: table.id,
            enableReorder: true,
            enableRowLinks: hasRowLinks // Enable row links based on presence of data-href
        });
    });

    // Example initialization for another table
    // if (document.getElementById('another-table')) {
    //     new DataTable('another-table', {
    //         storageKey: 'anotherTableColumns',
    //         searchFields: ['id', 'title'],
    //         filterConfigs: [
    //             {
    //                 id: 'category',
    //                 column: 'category'
    //             }
    //         ]
    //     });
    // }
});