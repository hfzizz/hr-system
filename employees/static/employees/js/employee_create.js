console.log('JavaScript file loaded');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // Initialize form counts
    window.formCount = document.querySelectorAll('.qualification-form').length;
    window.maxForms = 10;
    
    initializePasswordFunctions();
    initializeQualificationFunctions();
    
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
    }
});

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