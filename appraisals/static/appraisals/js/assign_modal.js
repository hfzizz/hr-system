

// Validation to prevent primary and secondary appraiser from being the same
document.getElementById('appraiser').addEventListener('change', validateAppraisers);
document.getElementById('appraiser_secondary').addEventListener('change', validateAppraisers);

function validateAppraisers() {
    const employeeId = document.getElementById('selected_employee_id').value;
    const primary = document.getElementById('appraiser').value;
    const secondary = document.getElementById('appraiser_secondary').value;
    const errorMessage = document.getElementById('errorMessage');
    
    // Reset styles
    document.getElementById('appraiser').classList.remove('border-red-500');
    document.getElementById('appraiser_secondary').classList.remove('border-red-500');
    
    // Check if employee is assigned as their own appraiser (should never happen with UI filtering)
    if (primary === employeeId || secondary === employeeId) {
        // Apply error styles
        if (primary === employeeId) document.getElementById('appraiser').classList.add('border-red-500');
        if (secondary === employeeId) document.getElementById('appraiser_secondary').classList.add('border-red-500');
        
        // Show error message
        errorMessage.querySelector('span').textContent = 'An employee cannot be their own appraiser.';
        errorMessage.classList.remove('hidden');
        return false;
    }
    
    // Only validate if both are selected
    if (primary && secondary && primary === secondary) {
        // Apply error styles
        document.getElementById('appraiser').classList.add('border-red-500');
        document.getElementById('appraiser_secondary').classList.add('border-red-500');
        
        // Show error message
        errorMessage.querySelector('span').textContent = 'Primary and secondary appraisers cannot be the same person.';
        errorMessage.classList.remove('hidden');
        return false;
    } else {
        errorMessage.classList.add('hidden');
        return true;
    }
}

// Form submission handler
document.getElementById('assignForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    // Validate appraisers first
    if (!validateAppraisers()) {
        return;
    }
    
    // Disable the submit button to prevent double submission
    const submitButton = this.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = `
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Processing...
    `;
    
    // Clear previous error
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.classList.add('hidden');
    
    // Validate form
    const appraiser = document.getElementById('appraiser').value;
    const period = document.getElementById('period_select').value;
    
    const reviewStart = document.getElementById('review_period_start').value;
    const reviewEnd = document.getElementById('review_period_end').value;
    const appraisalStart = document.getElementById('appraisal_period_start').value;
    const appraisalEnd = document.getElementById('appraisal_period_end').value;

    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const reviewStartDate = new Date(reviewStart);

    if (reviewStartDate < today) {
        errorMessage.querySelector('span').textContent = 'The review period start date cannot be in the past.';
        errorMessage.classList.remove('hidden');
        submitButton.disabled = false; 
        submitButton.textContent = 'Assign Appraisal';
        return;
    }

    if (new Date(reviewStart) > new Date(reviewEnd)) {
        event.preventDefault();
        errorMessage.querySelector('span').textContent = 'The review period start date cannot be after the end date.';
        errorMessage.classList.remove('hidden');
        return;
    }

    // Show error with highlighted fields if required fields are missing
    if (!appraiser || !period) {
        if (!appraiser) document.getElementById('appraiser').classList.add('border-red-500');
        if (!period) document.getElementById('period_select').classList.add('border-red-500');
        
        errorMessage.querySelector('span').textContent = 'Please select both a primary appraiser and an appraisal period.';
        errorMessage.classList.remove('hidden');
        submitButton.disabled = false;
        submitButton.textContent = 'Assign Appraisal';
        return;
    }
    
    try {
        // Create a FormData object and log its contents for debugging
        const formData = new FormData(this);
        console.log("Form data being submitted:");
        for (let pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }
        
        // Update the form action URL with the actual employee ID
        const employeeId = document.getElementById('selected_employee_id').value;
        this.action = `/appraisals/appraisers/assign/${employeeId}/`;
        
        const response = await fetch(this.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });
        
        const data = await response.json();
        console.log("Server response:", data);
        
        if (data.success) {
            // Create a success notification with animation
            const successMessage = document.createElement('div');
            successMessage.className = 'success-notification fixed top-4 right-4 z-50';
            successMessage.innerHTML = `
                <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <span>${data.message || 'Appraiser assigned successfully!'}</span>
            `;
            document.body.appendChild(successMessage);
            
            // Close modal
            closeAssignModal();
            
            // Remove success message after a delay and reload
            setTimeout(() => {
                successMessage.style.opacity = '0';
                successMessage.style.transform = 'translateY(-20px)';
                setTimeout(() => {
                    successMessage.remove();
                    window.location.reload();
                }, 300);
            }, 2000);
        } else {
            // Show error with message
            errorMessage.querySelector('span').textContent = data.error || 'An error occurred while assigning the appraisal.';
            errorMessage.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Error:', error);
        errorMessage.querySelector('span').textContent = 'A network error occurred. Please try again.';
        errorMessage.classList.remove('hidden');
    } finally {
        // Re-enable the submit button
        submitButton.disabled = false;
        submitButton.textContent = 'Assign Appraisal';
    }
});

// Extract employee initials for avatar
function updateEmployeeInitials() {
    const nameElement = document.getElementById('selected_employee_name');
    const initialsElement = document.getElementById('employee-initials');
    
    if (nameElement && initialsElement && nameElement.textContent) {
        const name = nameElement.textContent.trim();
        const nameParts = name.split(' ');
        
        if (nameParts.length >= 2) {
            const initials = nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0);
            initialsElement.textContent = initials.toUpperCase();
        } else if (nameParts.length === 1 && nameParts[0]) {
            initialsElement.textContent = nameParts[0].charAt(0).toUpperCase();
        } else {
            initialsElement.textContent = '👤';
        }
    }
}

// Update employee initials when name is set
const originalSetText = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent').set;
Object.defineProperty(document.getElementById('selected_employee_name'), 'textContent', {
    set(text) {
        originalSetText.call(this, text);
        setTimeout(updateEmployeeInitials, 0);
    }
});

// Set minimum date for review period inputs to today
document.addEventListener('DOMContentLoaded', function() {

    // Get the date input elements
    const reviewStartField = document.getElementById('review_period_start');
    const reviewEndField = document.getElementById('review_period_end');
    
    if (!reviewStartField || !reviewEndField) {
        console.error('Review date fields not found on page load');
        return;
    }
    

    // Format today's date as YYYY-MM-DD for the min attribute
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0'); // January is 0!
    const dd = String(today.getDate()).padStart(2, '0');
    const formattedToday = `${yyyy}-${mm}-${dd}`;

      // Set minimum date constraints
    reviewStartField.min = formattedToday;
    reviewEndField.min = formattedToday;
    
    if (reviewStartField && reviewEndField) {
        // Set minimum date constraints
        reviewStartField.min = formattedToday;
        reviewEndField.min = formattedToday;
        
        // Handle review start date changes
        reviewStartField.addEventListener('change', function() {
            // When start date changes, update end date minimum
            if (this.value) {
                reviewEndField.min = this.value;
                
                // If end date is now before start date, update it
                if (reviewEndField.value && new Date(reviewEndField.value) < new Date(this.value)) {
                    reviewEndField.value = this.value;
                }
            } else {
                // If start date is cleared, reset end date min to today
                reviewEndField.min = formattedToday;
            }
        });
        
        // Handle review end date changes - this helps prevent the issue
        reviewEndField.addEventListener('change', function() {
            // If end date is before start date, update start date
            if (this.value && reviewStartField.value && new Date(this.value) < new Date(reviewStartField.value)) {
                reviewStartField.value = this.value;
            }
        });
    }

    // Handle review end date changes
    reviewEndField.addEventListener('change', function() {
        const selectedDate = new Date(this.value);
        selectedDate.setHours(0, 0, 0, 0);
        
        // Ensure end date is not before today
        if (selectedDate < today) {
            console.warn('Selected end date is before today, resetting to today');
            this.value = formattedToday;
        }
        
        // Ensure end date is not before start date
        if (reviewStartField.value && new Date(this.value) < new Date(reviewStartField.value)) {
            console.warn('Selected end date is before start date, adjusting');
            this.value = reviewStartField.value;
        }
    });

    // Add period select event handler to update dates
    document.getElementById('period_select').addEventListener('change', function() {
        const periodSelect = this;
        const selectedOption = periodSelect.options[periodSelect.selectedIndex];
        
        // Get the date fields
        const appraisalStartField = document.getElementById('appraisal_period_start');
        const appraisalEndField = document.getElementById('appraisal_period_end');
        
        if (selectedOption && selectedOption.value) {
            // Set appraisal period dates (these are read-only so just set them directly)
            appraisalStartField.value = selectedOption.dataset.start || '';
            appraisalEndField.value = selectedOption.dataset.end || '';
            
            // For review dates, make sure they're not in the past
            const periodStartDate = new Date(selectedOption.dataset.start);
            const periodEndDate = new Date(selectedOption.dataset.end);
            
            // Use the later of today or the period start date
            if (periodStartDate >= today) {
                reviewStartField.value = selectedOption.dataset.start;
            } else {
                reviewStartField.value = formattedToday;
            }
            
            reviewEndField.value = selectedOption.dataset.end;
        } else {
            // Clear all date fields if no period is selected
            appraisalStartField.value = '';
            appraisalEndField.value = '';
            reviewStartField.value = '';
            reviewEndField.value = '';
        }
    });
    
    // Initial validation of any existing values in the date fields
    if (reviewStartField.value) {
        const startDate = new Date(reviewStartField.value);
        startDate.setHours(0, 0, 0, 0);
        
        if (startDate < today) {
            reviewStartField.value = formattedToday;
        }
    }
    
    if (reviewEndField.value) {
        const endDate = new Date(reviewEndField.value);
        endDate.setHours(0, 0, 0, 0);
        
        if (endDate < today) {
            reviewEndField.value = formattedToday;
        }
    }

     // Set up rows
     document.querySelectorAll('#appraisers-table tbody tr').forEach(row => {
        const checkbox = row.querySelector('input[name="selected_employees"]');
        const idCell = row.querySelector('td[data-column="id"]');
        
        let employeeId = null;
        if (checkbox && checkbox.value) {
            employeeId = checkbox.value;
        } else if (idCell) {
            employeeId = idCell.textContent.trim();
        }
        
        if (employeeId) {
            row.setAttribute('data-employee-id', employeeId);
        }
    });
    
    // Add tabindex to selects for keyboard navigation
    document.querySelectorAll('#assignForm select').forEach((select, index) => {
        select.setAttribute('tabindex', index + 1);
    });
});
   
// HTMX Response Handler - New function
document.body.addEventListener('htmx:afterSwap', function(event) {
    if (event.target.id === 'appraiser-options-container') {
        console.log('HTMX swap completed for appraisers');
        console.log('Raw content received:', document.getElementById('appraiser-options-container').textContent);
        try {
            const parsedData = JSON.parse(document.getElementById('appraiser-options-container').textContent);
            console.log('Parsed data:', parsedData);
        } catch (error) {
            console.error('Error parsing JSON:', error);
        }
        updateAppraisersFromHtmx();
    }
});

// Function to process HTMX response and update dropdowns
function updateAppraisersFromHtmx() {
    const container = document.getElementById('appraiser-options-container');
    const primarySelect = document.getElementById('appraiser');
    const secondarySelect = document.getElementById('appraiser_secondary');
    
    try {
        // Parse the data from the container
        const appraisersData = JSON.parse(container.textContent);
        
        if (appraisersData && Array.isArray(appraisersData.appraisers)) {
            // Store for later use
            allAppraisers = appraisersData.appraisers;
            console.log(`Processed ${allAppraisers.length} appraisers from HTMX`);
            
            // Clear dropdowns
            primarySelect.innerHTML = '<option value="">Select a primary appraiser</option>';
            secondarySelect.innerHTML = '<option value="">Select a secondary appraiser (optional)</option>';
            
            // Group appraisers by department
            const departments = {};
            
            allAppraisers.forEach(appraiser => {
                // Add to primary dropdown
                const department = appraiser.department || 'Other';
                
                if (!departments[department]) {
                    departments[department] = {
                        primary: document.createElement('optgroup'),
                        secondary: document.createElement('optgroup')
                    };
                    departments[department].primary.label = department;
                    departments[department].secondary.label = department;
                    primarySelect.appendChild(departments[department].primary);
                    secondarySelect.appendChild(departments[department].secondary);
                }
                
                // Create option for primary dropdown
                const primaryOption = document.createElement('option');
                primaryOption.value = appraiser.id;
                primaryOption.textContent = `${appraiser.name} (${appraiser.post || 'No position'})`;
                departments[department].primary.appendChild(primaryOption);
                
                // Create option for secondary dropdown
                const secondaryOption = document.createElement('option');
                secondaryOption.value = appraiser.id;
                secondaryOption.textContent = `${appraiser.name} (${appraiser.post || 'No position'})`;
                departments[department].secondary.appendChild(secondaryOption);
            });
        }
    } catch (error) {
        console.error('Error processing HTMX response:', error);
    }
}

// Update openAssignModal function
window.openAssignModal = function(employeeId, employeeName) {
    // Set the employee details
    document.getElementById('selected_employee_id').value = employeeId;
    document.getElementById('selected_employee_name').textContent = employeeName;

    // Reset form fields
    document.getElementById('appraiser').value = '';
    document.getElementById('appraiser_secondary').value = '';
    document.getElementById('period_select').value = '';
    document.getElementById('review_period_start').value = '';
    document.getElementById('review_period_end').value = '';
    document.getElementById('errorMessage').classList.add('hidden');
    
    // Show the modal
    document.getElementById('assignModal').classList.remove('hidden');
    
    // Add animation class after a small delay to ensure proper rendering
    setTimeout(() => {
        const modalPanel = document.querySelector('#assignModal .transform');
        if (modalPanel) {
            modalPanel.classList.add('opacity-100');
            modalPanel.classList.remove('opacity-0', 'translate-y-4');
        }
    }, 10);
    
    // Update employee initials
    updateEmployeeInitials();
};

// Primary appraiser change handler
document.getElementById('appraiser').addEventListener('change', function() {
    const primaryValue = this.value;
    const secondarySelect = document.getElementById('appraiser_secondary');
    
    // Enable all options in secondary
    Array.from(secondarySelect.options).forEach(option => {
        option.disabled = false;
    });
    
    // Disable the selected primary in secondary dropdown
    if (primaryValue) {
        const matchingOption = secondarySelect.querySelector(`option[value="${primaryValue}"]`);
        if (matchingOption) {
            matchingOption.disabled = true;
        }
    }
    
    // Validate
    validateAppraisers();
});

// Close modal function
function closeAssignModal() {
    // Hide the modal
    const modal = document.getElementById('assignModal');
    const modalPanel = modal.querySelector('.transform');
    
    // Animate out
    if (modalPanel) {
        modalPanel.classList.add('opacity-0', 'translate-y-4');
        modalPanel.classList.remove('opacity-100');
    }
    
    // Wait for animation to finish
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
    
    // Clear form fields
    document.getElementById('appraiser').value = '';
    document.getElementById('appraiser_secondary').value = '';
    document.getElementById('period_select').value = '';
    document.getElementById('review_period_start').value = '';
    document.getElementById('review_period_end').value = '';
    document.getElementById('errorMessage').classList.add('hidden');
}