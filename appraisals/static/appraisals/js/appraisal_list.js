document.addEventListener('DOMContentLoaded', function() {
    // Initialize tab functionality
    const tabs = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active classes
            tabs.forEach(t => {
                t.classList.remove('border-indigo-500', 'text-indigo-600');
                t.classList.add('border-transparent', 'text-gray-500');
            });
            tabContents.forEach(content => content.classList.add('hidden'));

            // Add active classes
            tab.classList.remove('border-transparent', 'text-gray-500');
            tab.classList.add('border-indigo-500', 'text-indigo-600');
            
            // Show selected content
            const targetId = tab.dataset.tab;
            document.getElementById(targetId).classList.remove('hidden');
        });
    });

    // Activate first tab by default
    tabs[0].click();

    // Initialize sorting functionality - Add data-direction attributes to all sortable headers
    const sortHeaders = document.querySelectorAll('[id^="sort-"]');
    sortHeaders.forEach(header => {
        // Initialize sort direction attribute if it doesn't exist
        if (!header.hasAttribute('data-direction')) {
            header.setAttribute('data-direction', 'desc');
        }
        
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            if (!column) {
                console.error('Sort column not specified in header data-sort attribute');
                return;
            }
            
            const tableId = header.closest('table')?.id;
            if (!tableId) {
                console.error('Could not find parent table or table has no ID');
                return;
            }
            
            sortTable(tableId, column);
        });
    });

    // Check if we should restore a specific tab from URL hash
    if (window.location.hash) {
        const tabId = window.location.hash.substring(1);
        const tab = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
        if (tab) {
            tab.click();
        }
    }
});
// Table sorting function with improved error handling and debugging
function sortTable(tableId, column) {
    console.log(`Attempting to sort ${tableId} by ${column}`);
    
    const table = document.getElementById(tableId);
    if (!table) {
        console.error(`Table #${tableId} not found`);
        return;
    }
    
    const tbody = table.querySelector('tbody');
    if (!tbody) {
        console.error(`No tbody found in table #${tableId}`);
        return;
    }
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    console.log(`Found ${rows.length} rows in ${tableId}`);
    
    // Skip if there's only the "no data" message row
    if (rows.length <= 1 && rows[0].querySelector('td[colspan]')) {
        console.log('Skipping sort - only found empty data message');
        return;
    }
    
    // Get the sort direction
    let header = document.querySelector(`#sort-${column}`);
    if (!header) {
        // Try with hyphens replaced
        const hyphenatedColumn = column.replace(/_/g, '-');
        const altHeader = document.querySelector(`#sort-${hyphenatedColumn}`);
        if (!altHeader) {
            console.error(`Header #sort-${column} not found`);
            return;
        }
        header = altHeader; // Now this works since header is a let variable
    }
        
    // Get current sort direction and toggle for next click
    let isAscending = header.getAttribute('data-direction') !== 'asc';
    header.setAttribute('data-direction', isAscending ? 'asc' : 'desc');
    
    console.log(`Sorting ${column} ${isAscending ? 'ascending' : 'descending'}`);
    
    // Update all headers to show default sort icon
    document.querySelectorAll('[id^="sort-"]').forEach(h => {
        const icon = h.querySelector('.sort-icon');
        if (icon) {
            icon.classList.remove('text-indigo-500');
            // Reset rotation
            icon.style.transform = '';
        }
    });
    
    // Update current header to show active sort icon
    const icon = header.querySelector('.sort-icon');
    if (icon) {
        icon.classList.add('text-indigo-500');
        // Rotate the icon based on direction
        icon.style.transform = isAscending ? 'rotate(0deg)' : 'rotate(180deg)';
    }
    
    // Identify which cells have the correct data-column
    let columnFound = false;
    rows.forEach(row => {
        const cell = row.querySelector(`td[data-column="${column}"]`);
        if (cell) columnFound = true;
    });
    
    if (!columnFound) {
        console.warn(`No cells with data-column="${column}" found. Attempting to find by position.`);
        // Try to find column by index
        const headers = Array.from(table.querySelectorAll('th'));
        const headerIndex = headers.findIndex(h => h.dataset.column === column);
        
        if (headerIndex >= 0) {
            // Sort by position instead
            sortByIndex(rows, headerIndex, isAscending);
        } else {
            console.error(`Could not determine column position for ${column}`);
            return;
        }
    } else {
        // Sort by data-column attribute
        sortByDataAttribute(rows, column, isAscending);
    }
    
    // Reinsert rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
    console.log(`${tableId} table sorted by ${column}`);
}

// Helper function to sort by data-column attribute
function sortByDataAttribute(rows, column, isAscending) {
    rows.sort((a, b) => {
        const cellA = a.querySelector(`td[data-column="${column}"]`);
        const cellB = b.querySelector(`td[data-column="${column}"]`);
        
        if (!cellA || !cellB) return 0;
        
        return compareValues(
            extractTextContent(cellA), 
            extractTextContent(cellB), 
            isAscending
        );
    });
}

// Helper function to sort by column index
function sortByIndex(rows, columnIndex, isAscending) {
    rows.sort((a, b) => {
        const cellsA = a.querySelectorAll('td');
        const cellsB = b.querySelectorAll('td');
        
        if (columnIndex >= cellsA.length || columnIndex >= cellsB.length) return 0;
        
        return compareValues(
            extractTextContent(cellsA[columnIndex]), 
            extractTextContent(cellsB[columnIndex]), 
            isAscending
        );
    });
}

// Helper function to extract text content, handling nested elements
function extractTextContent(cell) {
    // First try to get text from a status badge if present
    const statusBadge = cell.querySelector('.rounded-full');
    if (statusBadge) {
        return statusBadge.textContent.trim();
    }
    
    // Try to get from common text containers
    const textDiv = cell.querySelector('.text-sm, .text-xs');
    if (textDiv) {
        return textDiv.textContent.trim();
    }
    
    // Fallback to cell's text content
    return cell.textContent.trim();
}

// Helper function to compare values with appropriate type conversion
function compareValues(valA, valB, isAscending) {
    // Check if values are dates
    const dateA = new Date(valA);
    const dateB = new Date(valB);
    
    if (!isNaN(dateA) && !isNaN(dateB)) {
        return isAscending ? dateA - dateB : dateB - dateA;
    }
    
    // Check if values are numbers
    const numA = parseFloat(valA);
    const numB = parseFloat(valB);
    
    if (!isNaN(numA) && !isNaN(numB)) {
        return isAscending ? numA - numB : numB - numA;
    }
    
    // Default to string comparison
    return isAscending ? valA.localeCompare(valB) : valB.localeCompare(valA);
}

// Action functions
function deleteAppraisal(appraisalId) {
    if (!appraisalId) {
        console.error('No appraisal ID provided');
        return;
    }
    
    if (confirm('Are you sure you want to delete this appraisal? This action cannot be undone.')) {
        // Create a form and submit it
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = "/appraisals/forms/delete/"; // Ensure this matches your URL pattern
        
        // Add CSRF token from the page
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        // Add appraisal ID
        const appraisalIdInput = document.createElement('input');
        appraisalIdInput.type = 'hidden';
        appraisalIdInput.name = 'appraisal_id';
        appraisalIdInput.value = appraisalId;
        form.appendChild(appraisalIdInput);
        
        // Submit the form
        document.body.appendChild(form);
        form.submit();
    }
}
// Action functions
function sendReminder(id) {
    // TODO: Implement reminder functionality
    console.log('Sending reminder for form:', id);
}

function requestAmendment(id) {
    // TODO: Implement amendment request functionality
    console.log('Requesting amendment for form:', id);
}

function downloadPDF(id) {
    // TODO: Implement PDF download functionality
    console.log('Downloading PDF for form:', id);
} 