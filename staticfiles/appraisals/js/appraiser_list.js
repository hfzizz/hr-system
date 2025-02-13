function openAssignModal(employeeId) {
    document.getElementById('selected_employee_id').value = employeeId;
    document.getElementById('assignModal').classList.remove('hidden');
}

function submitAssignForm(event) {
    event.preventDefault();
    
    const form = document.getElementById('assignForm');
    const formData = new FormData(form);

    // Get the CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

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
            document.getElementById('assignModal').classList.add('hidden');
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
    const selectedOption = periodSelect.options[periodSelect.selectedIndex];
    
    if (selectedOption.value) {
        document.getElementById('review_period_start').value = selectedOption.dataset.start;
        document.getElementById('review_period_end').value = selectedOption.dataset.end;
    } else {
        document.getElementById('review_period_start').value = '';
        document.getElementById('review_period_end').value = '';
    }
}

// Form validation
document.addEventListener('DOMContentLoaded', function() {
    const assignForm = document.getElementById('assignForm');
    if (assignForm) {
        assignForm.addEventListener('submit', function(event) {
            const appraiser = document.getElementById('appraiser').value;
            const periodSelect = document.getElementById('period_select').value;

            if (!appraiser || !periodSelect) {
                event.preventDefault();
                alert('Please fill in all required fields');
                return false;
            }
        });
    }

    // Initialize date inputs with today's date
    const today = new Date().toISOString().split('T')[0];
    const reviewPeriodStart = document.getElementById('review_period_start');
    const reviewPeriodEnd = document.getElementById('review_period_end');
    
    if (reviewPeriodStart && reviewPeriodEnd) {
        reviewPeriodStart.value = today;
        reviewPeriodEnd.value = today;

        // Add date validation
        reviewPeriodStart.addEventListener('change', function() {
            reviewPeriodEnd.min = this.value;
        });

        reviewPeriodEnd.addEventListener('change', function() {
            reviewPeriodStart.max = this.value;
        });
    }

    // Add click handlers to all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            showTab(this.dataset.tab);
        });
    });

    // Initialize the first tab
    showTab('assign-tab');
});

function showTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Show selected tab content
    document.getElementById(tabId).classList.remove('hidden');
    
    // Update tab button styles
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('border-indigo-500', 'text-indigo-600');
        button.classList.add('border-transparent', 'text-gray-500');
    });
    
    // Highlight active tab
    const activeButton = document.querySelector(`[data-tab="${tabId}"]`);
    activeButton.classList.remove('border-transparent', 'text-gray-500');
    activeButton.classList.add('border-indigo-500', 'text-indigo-600');
}

// Role management functions
function openRoleModal(employeeId) {
    // To be implemented
    console.log('Opening role modal for employee:', employeeId);
}