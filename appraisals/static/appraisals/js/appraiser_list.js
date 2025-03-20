/**
 * Appraiser Management Interface JavaScript
 * Handles table functionality, tab switching, filtering, and modal operations
 */

document.addEventListener('DOMContentLoaded', function() {
    // ----- Initialize Tab System -----
    initTabs();
    
    // ----- Initialize Tables -----
    initMainTable();
    initRolesTable();
    
    // ----- Initialize Form Handlers -----
    initAssignForm();
});

// ----- Tab Management Functions -----

function initTabs() {
    // Add click handlers to all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            showTab(this.dataset.tab);
        });
    });

    // Initialize the first tab
    if (document.querySelectorAll('.tab-button').length > 0) {
        document.querySelectorAll('.tab-button')[0].click();
    }
}

function showTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Show selected tab content
    const selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.classList.remove('hidden');
    }
    
    // Update tab button styles
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('border-indigo-500', 'text-indigo-600');
        button.classList.add('border-transparent', 'text-gray-500');
    });
    
    // Highlight active tab
    const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
    if (activeButton) {
        activeButton.classList.remove('border-transparent', 'text-gray-500');
        activeButton.classList.add('border-indigo-500', 'text-indigo-600');
    }
}

// ----- Main Table Functions -----

function initMainTable() {
    const searchInput = document.getElementById('search-input');
    const departmentFilter = document.getElementById('department-filter');
    const tableRows = document.querySelectorAll('#appraisers-table tbody tr');
    const selectAllCheckbox = document.getElementById('select-all');
    const employeeCheckboxes = document.querySelectorAll('.employee-checkbox');
    
    // Add event listeners for filtering
    if (searchInput) searchInput.addEventListener('input', filterMainTable);
    if (departmentFilter) departmentFilter.addEventListener('change', filterMainTable);
    
    // Select all functionality
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            employeeCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
        });
    }
    
    // Initialize column visibility
    initColumnVisibility();
    
    // Initialize sorting
    initTableSorting();
    
    // Filter function for main table
    function filterMainTable() {
        if (!searchInput || !departmentFilter) return;
        
        const searchTerm = searchInput.value.toLowerCase();
        const departmentValue = departmentFilter.value.toLowerCase();

        tableRows.forEach(row => {
            if (row.children.length === 1) return; // Skip empty state row

            const name = row.querySelector('[data-column="employee"]')?.textContent.trim().toLowerCase() || '';
            const department = row.querySelector('[data-column="department"]')?.textContent.trim().toLowerCase() || '';

            const matchesSearch = searchTerm === '' || name.includes(searchTerm);
            const matchesDepartment = departmentValue === '' || department === departmentValue;

            row.style.display = (matchesSearch && matchesDepartment) ? '' : 'none';
        });
    }
}

// ----- Column Visibility Functions -----

function initColumnVisibility() {
    // Load saved preferences
    loadColumnPreferences();
    
    // Handle column toggle changes
    document.querySelectorAll('.column-toggle').forEach(toggle => {
        toggle.addEventListener('change', function() {
            const column = this.dataset.column;
            const isVisible = this.checked;
            
            document.querySelectorAll(`[data-column="${column}"]`).forEach(cell => {
                if (isVisible) {
                    cell.classList.remove('hidden');
                } else {
                    cell.classList.add('hidden');
                }
            });
            
            saveColumnPreferences();
        });
    });
}

function loadColumnPreferences() {
    const preferences = JSON.parse(localStorage.getItem('appraiserTableColumns') || '{}');
    
    document.querySelectorAll('.column-toggle').forEach(toggle => {
        const column = toggle.dataset.column;
        // If preference exists, use it; otherwise default to checked
        const isVisible = preferences.hasOwnProperty(column) ? preferences[column] : true;
        
        // Set checkbox state
        toggle.checked = isVisible;
        
        // Set initial visibility
        document.querySelectorAll(`[data-column="${column}"]`).forEach(cell => {
            if (!isVisible) {
                cell.classList.add('hidden');
            }
        });
    });
}

function saveColumnPreferences() {
    const preferences = {};
    document.querySelectorAll('.column-toggle').forEach(toggle => {
        preferences[toggle.dataset.column] = toggle.checked;
    });
    localStorage.setItem('appraiserTableColumns', JSON.stringify(preferences));
}

// ----- Table Sorting Functions -----

function initTableSorting() {
    // Initialize sort states for sortable columns
    const sortStates = {
        'id': { ascending: true },
        'employee': { ascending: true },
        'department': { ascending: true }
    };
    
    // Add click listeners to all sortable columns
    document.querySelectorAll('[data-sort]').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            sortTable(column);
        });
    });
    
    // Initial sort by ID
    if (document.querySelector('#sort-id')) {
        sortTable('id');
    }
    
    // Table sorting function
    function sortTable(column) {
        const tbody = document.querySelector('#appraisers-table tbody');
        if (!tbody) return;
        
        const rows = Array.from(tbody.querySelectorAll('tr:not(:last-child)'));
        
        // Get current sort state for this column
        const isAscending = sortStates[column].ascending;
        
        rows.sort((a, b) => {
            let aValue = a.querySelector(`[data-column="${column}"]`)?.textContent.trim() || '';
            let bValue = b.querySelector(`[data-column="${column}"]`)?.textContent.trim() || '';
            
            // Compare values based on sort direction
            if (isAscending) {
                return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
            } else {
                return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
            }
        });

        // Clear and repopulate table
        rows.forEach(row => tbody.appendChild(row));

        // Update sort icons
        document.querySelectorAll('[data-sort]').forEach(header => {
            const icon = header.querySelector('.sort-icon');
            if (!icon) return;
            
            if (header.dataset.sort === column) {
                // Update icon for current column
                icon.style.transform = isAscending ? 'rotate(0deg)' : 'rotate(180deg)';
                icon.style.opacity = '1';
            } else {
                // Reset other columns
                icon.style.transform = 'rotate(0deg)';
                icon.style.opacity = '0.5';
            }
        });

        // Toggle sort state for next click
        sortStates[column].ascending = !isAscending;
    }
}

// ----- Roles Table Functions -----

function initRolesTable() {
    const roleSearchInput = document.getElementById('role-search-input');
    const roleDepartmentFilter = document.getElementById('role-department-filter');
    const roleTableRows = document.querySelectorAll('#roles-table tbody tr');
    
    // Add event listeners for filtering
    if (roleSearchInput) roleSearchInput.addEventListener('input', filterRoleTable);
    if (roleDepartmentFilter) roleDepartmentFilter.addEventListener('change', filterRoleTable);
    
    function filterRoleTable() {
        if (!roleSearchInput || !roleDepartmentFilter) return;
        
        const searchTerm = roleSearchInput.value.toLowerCase();
        const departmentValue = roleDepartmentFilter.value.toLowerCase();
        
        roleTableRows.forEach(row => {
            if (row.children.length === 1) return; // Skip empty state row
            
            const nameCell = row.cells[1]; // Employee name column
            const deptCell = row.cells[2]; // Department column
            
            if (!nameCell || !deptCell) return;
            
            const name = nameCell.textContent.trim().toLowerCase();
            const department = deptCell.textContent.trim().toLowerCase();
            
            const matchesSearch = searchTerm === '' || name.includes(searchTerm);
            const matchesDepartment = departmentValue === '' || department === departmentValue;
            
            row.style.display = (matchesSearch && matchesDepartment) ? '' : 'none';
        });
    }
}

// ----- Modal Functions -----

/**
 * Opens the assign modal for a specific employee
 * @param {string} employeeId - The ID of the employee
 * @param {string} employeeName - The name of the employee
 */
function openAssignModal(employeeId, employeeName) {
    console.log("Opening modal for employee:", employeeId, employeeName);
    
    // Get required elements
    const modal = document.getElementById('assignModal');
    const employeeInput = document.getElementById('selected_employee_id');
    const nameDisplay = document.getElementById('selected_employee_name');
    const errorMessage = document.getElementById('errorMessage');
    
    // Set employee data
    if (employeeInput) employeeInput.value = employeeId;
    if (nameDisplay && employeeName) nameDisplay.textContent = employeeName;
    
    // Reset form state
    const form = document.getElementById('assignForm');
    if (form) {
        form.reset();
        form.action = `/appraisals/appraisers/assign/${employeeId}/`;
        
        // Clear any previous error messages
        if (errorMessage) errorMessage.classList.add('hidden');
    }
    
    // Reset validation state for selects
    resetSelectStyles();
    
    // Initialize period dates
    updatePeriodDates();
    
    // Show the modal with animation
    if (modal) {
        modal.classList.remove('hidden');
        
        // Add transition effect
        setTimeout(() => {
            const modalContent = modal.querySelector('.transform');
            if (modalContent) {
                modalContent.classList.add('opacity-100', 'translate-y-0');
                modalContent.classList.remove('opacity-0', 'translate-y-4');
            }
        }, 10);
        
        // Focus first input for better accessibility
        setTimeout(() => {
            const firstSelect = modal.querySelector('select');
            if (firstSelect) firstSelect.focus();
        }, 100);
    }
}

/**
 * Resets validation styling on select elements
 */
function resetSelectStyles() {
    const selects = document.querySelectorAll('#assignForm select');
    selects.forEach(select => {
        select.classList.remove('border-red-500', 'ring-red-500');
        select.classList.add('border-gray-300', 'focus:ring-indigo-500', 'focus:border-indigo-500');
    });
}

/**
 * Closes any modal by ID
 * @param {string} modalId - The ID of the modal to close
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    // Add exit animation
    const modalContent = modal.querySelector('.transform');
    if (modalContent) {
        modalContent.classList.remove('opacity-100', 'translate-y-0');
        modalContent.classList.add('opacity-0', 'translate-y-4');
    }
    
    // Hide modal after animation
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

/**
 * Alias for closeModal specific to the assign modal
 */
function closeAssignModal() {
    closeModal('assignModal');
    
    // Reset form if needed
    const form = document.getElementById('assignForm');
    if (form) form.reset();
    
    // Clear error messages
    const errorMsg = document.getElementById('errorMessage');
    if (errorMsg) errorMsg.classList.add('hidden');
}

// ----- Form Functions -----

function initAssignForm() {
    const assignForm = document.getElementById('assignForm');
    const periodSelect = document.getElementById('period_select');
    
    // Add form submit handler
    if (assignForm) {
        assignForm.addEventListener('submit', submitAssignForm);
    }
    
    // Add period date update handler
    if (periodSelect) {
        periodSelect.addEventListener('change', updatePeriodDates);
        // Initialize dates
        updatePeriodDates();
    }
    
    // Set up date fields
    initDateFields();
}

function submitAssignForm(event) {
    event.preventDefault();
    
    const form = document.getElementById('assignForm');
    // Validate form
    const appraiser = document.getElementById('appraiser')?.value;
    const periodSelect = document.getElementById('period_select')?.value;

    if (!appraiser || !periodSelect) {
        alert('Please fill in all required fields');
        return false;
    }
    
    const formData = new FormData(form);
    // Get the CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
        },
        credentials: 'same-origin'
    })
    .then(response => response.json().then(data => ({status: response.status, data})))
    .then(({status, data}) => {
        if (status === 200 && data.success) {
            // Close modal
            closeModal('assignModal');
            // Show success message
            alert('Appraisal assigned successfully!');
            // Reload page to show updated data
            window.location.reload();
        } else {
            // Show error message
            const errorMessage = data.error ? 
                (typeof data.error === 'object' ? Object.values(data.error).join('\n') : data.error) : 
                'An error occurred while assigning the appraiser.';
            alert(errorMessage);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while assigning the appraiser. Please check the console for details.');
    });
}

function updatePeriodDates() {
    const periodSelect = document.getElementById('period_select');
    if (!periodSelect) return;
    
    const selectedOption = periodSelect.options[periodSelect.selectedIndex];
    const startField = document.getElementById('review_period_start');
    const endField = document.getElementById('review_period_end');
    
    if (!startField || !endField) return;
    
    if (selectedOption && selectedOption.value) {
        startField.value = selectedOption.dataset.start || '';
        endField.value = selectedOption.dataset.end || '';
    } else {
        startField.value = '';
        endField.value = '';
    }
}

function initDateFields() {
    const reviewPeriodStart = document.getElementById('review_period_start');
    const reviewPeriodEnd = document.getElementById('review_period_end');
    
    if (!reviewPeriodStart || !reviewPeriodEnd) return;
    
    // Initialize date inputs with today's date if empty
    if (!reviewPeriodStart.value || !reviewPeriodEnd.value) {
        const today = new Date().toISOString().split('T')[0];
        reviewPeriodStart.value = today;
        reviewPeriodEnd.value = today;
    }

    // Add date validation
    reviewPeriodStart.addEventListener('change', function() {
        reviewPeriodEnd.min = this.value;
    });

    reviewPeriodEnd.addEventListener('change', function() {
        reviewPeriodStart.max = this.value;
    });
}

// Set initial min/max values
if (document.getElementById('review_period_start') && document.getElementById('review_period_end')) {
    document.getElementById('review_period_end').min = document.getElementById('review_period_start').value;
    document.getElementById('review_period_start').max = document.getElementById('review_period_end').value;
}

// ----- Role Management Functions -----

function openRoleModal(employeeId) {
    // To be implemented
    console.log('Opening role modal for employee:', employeeId);
}