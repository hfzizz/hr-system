console.log('JavaScript file loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // Initialize form counts
    window.formCount = document.querySelectorAll('.qualification-form').length;
    window.maxForms = 10;
    
    initializePasswordFunctions();
    initializeQualificationFunctions();
    
    // Load saved qualifications if they exist
    loadSavedQualifications();
    
    // Add form submission handler
    document.querySelector('form').addEventListener('submit', saveQualifications);
    
    console.log('Checking for template:', document.getElementById('empty-form-template'));
    
    function initializeQualificationFunctions() {
        window.addQualification = function() {
            console.log('Adding qualification...');
            const template = document.getElementById('empty-form-template');
            console.log('Template element:', template);
            
            if (!template) {
                console.error('Empty form template not found');
                return;
            }
            
            const formCount = document.querySelectorAll('.qualification-form').length;
            console.log('Current form count:', formCount);
            
            if (formCount >= window.maxForms) {
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
            
            // Replace all instances of __prefix__ in the new row
            const prefix = formCount;
            newRow.innerHTML = newRow.innerHTML.replace(/__prefix__/g, prefix);
            
            // Update IDs and names for all inputs in the new row
            newRow.querySelectorAll('input').forEach(input => {
                input.id = input.id.replace(/__prefix__/g, prefix);
                input.name = input.name.replace(/__prefix__/g, prefix);
            });
            
            tbody.appendChild(newRow);
            
            // Update management form count
            const totalFormsInput = document.getElementById('id_qualification_set-TOTAL_FORMS');
            if (totalFormsInput) {
                totalFormsInput.value = formCount + 1;
            }
            
            console.log('Qualification added successfully');
        };
        
        window.deleteQualification = function(button) {
            const row = button.closest('tr');
            const deleteInput = row.querySelector('input[type="hidden"][name$="-DELETE"]');
            const formCount = document.querySelectorAll('.qualification-form:not([style*="display: none"])').length;
            
            if (formCount <= 1) {
                alert('Cannot delete: minimum number of qualifications required');
                return;
            }
            
            if (deleteInput) {
                deleteInput.value = 'on';
                row.style.display = 'none';
            } else {
                row.remove();
                // Update all subsequent form indices
                updateFormIndices();
            }
        };
        
        function updateFormIndices() {
            const tbody = document.getElementById('qualification-formset');
            if (!tbody) return;
            
            const rows = tbody.children;
            let visibleCount = 0;
            
            for (let i = 0; i < rows.length; i++) {
                if (rows[i].style.display !== 'none') {
                    const inputs = rows[i].getElementsByTagName('input');
                    for (let input of inputs) {
                        input.name = input.name.replace(/-\d+-/, `-${visibleCount}-`);
                        input.id = input.id.replace(/-\d+-/, `-${visibleCount}-`);
                    }
                    visibleCount++;
                }
            }
            
            const totalFormsInput = document.getElementById('id_qualification_set-TOTAL_FORMS');
            if (totalFormsInput) {
                totalFormsInput.value = visibleCount;
            }
        }

        // Add auto-save functionality
        document.getElementById('qualification-formset').addEventListener('change', function() {
            saveQualifications();
        });
    }
});

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