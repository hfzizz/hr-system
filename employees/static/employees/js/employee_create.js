console.log('JavaScript file loaded');

// Global function declarations
window.replaceFile = function(button) {
    console.log('Replace file function called');
    const row = button.closest('tr');
    console.log('Found row:', row);

    const fileCell = row.querySelector('.file-container').closest('td');
    console.log('Found file cell:', fileCell);

    if (!fileCell) {
        console.error('File cell not found');
        return;
    }

    const employeeInput = row.querySelector('input[name*="document_set-"][name$="-employee"]');
    if (!employeeInput) {
        console.error('Employee input not found');
        return;
    }

    const formIndex = employeeInput.name.match(/document_set-(\d+)-/)[1];
    console.log('Form index:', formIndex);
    
    // Create the replacement HTML with the original file input styling
    const replacementHTML = `
        <input type="file" 
               name="document_set-${formIndex}-file" 
               id="id_document_set-${formIndex}-file"
               class="block w-full text-sm text-gray-500
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-semibold
                      file:bg-indigo-50 file:text-indigo-700
                      hover:file:bg-indigo-100">
    `;

    // Replace the content of the file cell
    fileCell.innerHTML = replacementHTML;
    
    // Hide the replace button
    button.style.display = 'none';
    
    // Automatically trigger the file input dialog
    const fileInput = fileCell.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.click();
    }
    
    console.log('Replace file activated for form index:', formIndex);
};

window.updateFileName = function(input) {
    const fileName = input.files[0] ? input.files[0].name : 'No file chosen';
    const fileNameSpan = input.parentElement.querySelector('.selected-file-name');
    fileNameSpan.textContent = fileName;
};

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // Initialize form counts
    window.formCount = document.querySelectorAll('.qualification-form').length;
    window.maxForms = 10;
    
    initializePasswordFunctions();
    initializeQualificationFunctions();
    initializeDocumentFunctions();
    
    // Load saved qualifications if they exist
    loadSavedQualifications();
    
    // Add form submission handler directly
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // Save qualifications before submitting
            saveQualifications();
            
            // Allow the form to submit normally
            return true;
        });
    }
    
    console.log('Checking for template:', document.getElementById('empty-form-template'));
});

function initializeQualificationFunctions() {
    window.addQualification = function() {
        console.log('Adding qualification...');
        const template = document.getElementById('empty-form-template');
        
        if (!template) {
            console.error('Empty form template not found');
            return;
        }
        
        // Get the current form count from the management form
        const totalFormsInput = document.querySelector('[name="qualification_set-TOTAL_FORMS"]');
        const currentFormCount = parseInt(totalFormsInput.value);
        console.log('Current form count:', currentFormCount);
        
        if (currentFormCount >= window.maxForms) {
            alert('Maximum number of qualifications reached');
            return;
        }
        
        // Clone the template content
        const newRow = template.content.cloneNode(true).querySelector('tr');
        const tbody = document.getElementById('qualification-formset');
        
        if (!tbody) {
            console.error('Qualification formset tbody not found');
            return;
        }
        
        // Replace all instances of __prefix__ with the current form count
        newRow.innerHTML = newRow.innerHTML.replace(/__prefix__/g, currentFormCount);
        
        // Update the employee ID in the new row
        const employeeId = document.querySelector('[name="id"]')?.value;
        if (employeeId) {
            const employeeInput = newRow.querySelector(`[name="qualification_set-${currentFormCount}-employee"]`);
            if (employeeInput) {
                employeeInput.value = employeeId;
            }
        }
        
        tbody.appendChild(newRow);
        
        // Update management form
        totalFormsInput.value = currentFormCount + 1;
        
        console.log('Qualification added successfully. New total:', totalFormsInput.value);
    };
    
    window.deleteQualification = function(button) {
        const row = button.closest('tr');
        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        const visibleRows = document.querySelectorAll('.qualification-form:not(.d-none)').length;
        
        console.log('Deleting qualification row:', row);
        console.log('Delete input found:', deleteInput);
        console.log('Visible rows:', visibleRows);
        
        if (visibleRows <= 1) {
            alert('Cannot delete: minimum one qualification is required');
            return;
        }
        
        if (deleteInput) {
            // For existing qualifications, mark as deleted and hide the row
            deleteInput.value = 'on';
            row.style.display = 'none';
            row.classList.add('d-none');
            console.log('Marked for deletion:', deleteInput.value);
        } else {
            // For new qualifications, remove the row completely
            row.remove();
            updateFormIndices();
        }
        
        // Update the total forms count
        const totalFormsInput = document.querySelector('[name="qualification_set-TOTAL_FORMS"]');
        if (totalFormsInput) {
            const currentTotal = parseInt(totalFormsInput.value);
            totalFormsInput.value = currentTotal - 1;
            console.log('Updated total forms:', totalFormsInput.value);
        }
    };
    
    function updateFormIndices() {
        const tbody = document.getElementById('qualification-formset');
        if (!tbody) return;
        
        const rows = Array.from(tbody.querySelectorAll('.qualification-form:not([style*="display: none"]):not(.d-none)'));
        const totalFormsInput = document.querySelector('[name="qualification_set-TOTAL_FORMS"]');
        
        console.log('Updating indices for rows:', rows.length);
        
        rows.forEach((row, index) => {
            row.querySelectorAll('input').forEach(input => {
                const name = input.getAttribute('name');
                if (name) {
                    const newName = name.replace(/-\d+-/, `-${index}-`);
                    input.setAttribute('name', newName);
                    input.setAttribute('id', `id_${newName}`);
                    console.log(`Updated input name from ${name} to ${newName}`);
                }
            });
        });
        
        if (totalFormsInput) {
            totalFormsInput.value = rows.length;
            console.log('Updated total forms count:', rows.length);
        }
    }
}

function initializeDocumentFunctions() {
    // Initialize other document-related functions
    const template = document.querySelector('#empty-document-template');
    console.log('Checking for template:', template);
    
    if (template) {
        window.addDocument = function() {
            console.log('Adding document...');
            const totalFormsInput = document.querySelector('[name="document_set-TOTAL_FORMS"]');
            const currentFormCount = parseInt(totalFormsInput.value);
            
            // Clone the template content
            const newRow = template.content.cloneNode(true).querySelector('tr');
            const tbody = document.getElementById('document-formset');
            
            if (!tbody) {
                console.error('Document formset tbody not found');
                return;
            }
            
            // Replace all instances of __prefix__ with the current form count
            newRow.innerHTML = newRow.innerHTML.replace(/__prefix__/g, currentFormCount);
            
            // Update the employee ID in the new row
            const employeeId = document.querySelector('[name="id"]')?.value;
            if (employeeId) {
                const employeeInput = newRow.querySelector(`[name="document_set-${currentFormCount}-employee"]`);
                if (employeeInput) {
                    employeeInput.value = employeeId;
                }
            }
            
            tbody.appendChild(newRow);
            
            // Update management form
            totalFormsInput.value = currentFormCount + 1;
            
            console.log('Document added successfully. New total:', totalFormsInput.value);
        };

        window.deleteDocument = function(button) {
            const row = button.closest('tr');
            const deleteInput = row.querySelector('input[name$="-DELETE"]');
            
            if (deleteInput) {
                // Mark for deletion in Django
                deleteInput.value = 'on';
                
                // Hide the row visually
                row.style.display = 'none';
                row.classList.add('d-none');
                
                console.log('Document marked for deletion:', deleteInput.value);
            } else {
                // If no DELETE input found (new unsaved row), just remove the row
                row.remove();
                
                // Update the total forms count
                const totalFormsInput = document.querySelector('[name="document_set-TOTAL_FORMS"]');
                if (totalFormsInput) {
                    const currentTotal = parseInt(totalFormsInput.value);
                    totalFormsInput.value = currentTotal - 1;
                }
            }
        };

        // Preview modal functions
        window.showPreviewModal = function(title, url) {
            console.log('Showing preview modal:', title, url);
            const modal = document.getElementById('previewModal');
            const modalTitle = document.getElementById('modalTitle');
            const preview = document.getElementById('documentPreview');
            
            if (!modal || !modalTitle || !preview) {
                console.error('Modal elements not found');
                return;
            }

            modalTitle.textContent = title;
            preview.src = url;
            modal.classList.remove('hidden');
        };

        window.closePreviewModal = function() {
            const modal = document.getElementById('previewModal');
            const preview = document.getElementById('documentPreview');
            
            if (modal && preview) {
                preview.src = '';
                modal.classList.add('hidden');
            }
        };

        // Initialize event listeners
        function initializeEventListeners() {
            console.log('Initializing document event listeners...');
            
            // Preview buttons
            document.querySelectorAll('.preview-btn').forEach(button => {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    const title = this.getAttribute('data-title');
                    const url = this.getAttribute('data-url');
                    console.log('Preview clicked:', title, url);
                    showPreviewModal(title, url);
                });
            });
        }

        // Call the initialization when the DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeEventListeners);
        } else {
            initializeEventListeners();
        }
    }
}

function loadSavedQualifications() {
    const savedData = localStorage.getItem('draft_qualifications');
    if (!savedData) return;

    try {
        const qualifications = JSON.parse(savedData);
        const tbody = document.getElementById('qualification-formset');
        
        // Clear existing forms except the first one if it's empty
        const existingForms = tbody.querySelectorAll('.qualification-form');
        if (existingForms.length > 0) {
            const firstForm = existingForms[0];
            const isEmpty = Array.from(firstForm.querySelectorAll('input[type="text"], input[type="date"]'))
                .every(input => !input.value);
            
            if (isEmpty) {
                while (tbody.children.length > 0) {
                    tbody.removeChild(tbody.lastChild);
                }
            }
        }

        // Add saved qualifications
        qualifications.forEach(qual => {
            window.addQualification();
            const newRow = tbody.lastElementChild;
            
            newRow.querySelector('[name$="-degree_diploma"]').value = qual.degree_diploma || '';
            newRow.querySelector('[name$="-university_college"]').value = qual.university_college || '';
            newRow.querySelector('[name$="-from_date"]').value = qual.from_date || '';
            newRow.querySelector('[name$="-to_date"]').value = qual.to_date || '';
        });

        // Update total forms count
        const totalFormsInput = document.getElementById('id_qualification_set-TOTAL_FORMS');
        if (totalFormsInput) {
            totalFormsInput.value = qualifications.length;
        }
    } catch (error) {
        console.error('Error loading saved qualifications:', error);
        localStorage.removeItem('draft_qualifications');
    }
}

function saveQualifications() {
    const qualifications = [];
    document.querySelectorAll('.qualification-form').forEach(row => {
        if (row.style.display !== 'none') {
            const qualification = {
                degree_diploma: row.querySelector('[name$="-degree_diploma"]').value,
                university_college: row.querySelector('[name$="-university_college"]').value,
                from_date: row.querySelector('[name$="-from_date"]').value,
                to_date: row.querySelector('[name$="-to_date"]').value
            };
            
            // Only save if at least one field is filled
            if (Object.values(qualification).some(value => value)) {
                qualifications.push(qualification);
            }
        }
    });

    if (qualifications.length > 0) {
        localStorage.setItem('draft_qualifications', JSON.stringify(qualifications));
    } else {
        localStorage.removeItem('draft_qualifications');
    }
}

function initializePasswordFunctions() {
    window.generatePassword = function() {
        const length = 12;
        const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*";
        let password = "";
        for (let i = 0; i < length; i++) {
            password += charset.charAt(Math.floor(Math.random() * charset.length));
        }
        document.getElementById('id_password').value = password;
    };

    window.togglePasswordVisibility = function() {
        const passwordInput = document.getElementById('id_password');
        const toggleButton = document.getElementById('toggle_password');
        
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            toggleButton.textContent = 'Hide';
        } else {
            passwordInput.type = 'password';
            toggleButton.textContent = 'Show';
        }
    };

    window.copyPassword = function() {
        const passwordInput = document.getElementById('id_password');
        
        const tempInput = document.createElement('input');
        tempInput.value = passwordInput.value;
        document.body.appendChild(tempInput);
        
        tempInput.select();
        document.execCommand('copy');
        
        document.body.removeChild(tempInput);
        
        const copyButton = document.getElementById('copy_password');
        const originalText = copyButton.textContent;
        copyButton.textContent = 'Copied!';
        setTimeout(() => {
            copyButton.textContent = originalText;
        }, 2000);
    };
}