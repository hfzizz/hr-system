const AppraisalForm = (function() {
    // Private variables
    let fieldsToSave = {};
    let saveTimer;
    const saveDelay = 800; // ms to wait before saving
    
    // Initialize the form handlers
    function init() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const appraisalId = document.querySelector('[name=appraisal_id]').value;
        const saveIndicator = document.getElementById('save-indicator');
        
        // Individual field save - for backward compatibility
        document.querySelectorAll('[data-auto-save="true"]').forEach(element => {
            if (element.tagName === 'INPUT' && (element.type === 'radio' || element.type === 'checkbox')) {
                element.addEventListener('change', function() {
                    saveField(this);
                });
            } else if (element.tagName === 'SELECT') {
                element.addEventListener('change', function() {
                    saveField(this);
                });
            } else {
                element.addEventListener('blur', function() {
                    saveField(this);
                });
            }
        });
        
        // Batch field save - for fields that support it
        document.querySelectorAll('[data-batch-save="true"]').forEach(element => {
            if (element.tagName === 'INPUT' && (element.type === 'radio' || element.type === 'checkbox')) {
                element.addEventListener('change', function() {
                    queueFieldForSave(this);
                });
            } else if (element.tagName === 'SELECT') {
                element.addEventListener('change', function() {
                    queueFieldForSave(this);
                });
            } else {
                element.addEventListener('blur', function() {
                    queueFieldForSave(this);
                });
            }
        });
        
        // Form section functionality
        document.querySelectorAll('.section-nav-button').forEach(button => {
            button.addEventListener('click', function(e) {
                if (Object.keys(fieldsToSave).length > 0) {
                    // Force save any pending changes before navigation
                    clearTimeout(saveTimer);
                    saveBatchFields();
                }
            });
        });
        
        // Individual field save function
        function saveField(element) {
            // Show save indicator
            if (saveIndicator) saveIndicator.classList.remove('hidden');
            
            // Build form data
            const formData = new FormData();
            formData.append('field', element.dataset.field);
            formData.append('section', element.dataset.section);
            formData.append('appraisal_id', appraisalId);
            
            // Get value based on element type
            if (element.type === 'checkbox') {
                formData.append('value', element.checked ? 'true' : 'false');
            } else if (element.type === 'radio') {
                formData.append('value', element.value);
            } else {
                formData.append('value', element.value);
            }
            
            // Send the request
            fetch('/appraisals/save-field/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Saved:', data);
                if (saveIndicator) {
                    setTimeout(() => {
                        saveIndicator.classList.add('hidden');
                    }, 500);
                }
            })
            .catch(error => {
                console.error('Error saving field:', error);
            });
        }
        
        // Queue field for batch saving
        function queueFieldForSave(element) {
            const field = element.dataset.field;
            const section = element.dataset.section;
            
            if (!field || !section) return; // Skip if missing required data
            
            // Get value based on element type
            let value;
            if (element.type === 'checkbox') {
                value = element.checked ? 'true' : 'false';
            } else if (element.type === 'radio') {
                if (!element.checked) return; // Only save checked radio buttons
                value = element.value;
            } else {
                value = element.value;
            }
            
            // Add to queue
            fieldsToSave[`${section}-${field}`] = {
                field: field,
                section: section,
                value: value
            };
            
            // Show save indicator
            if (saveIndicator) saveIndicator.classList.remove('hidden');
            
            // Set a delay before saving to batch multiple changes
            clearTimeout(saveTimer);
            saveTimer = setTimeout(saveBatchFields, saveDelay);
        }
        
        // Send batched fields to server
        function saveBatchFields() {
            if (Object.keys(fieldsToSave).length === 0) {
                if (saveIndicator) saveIndicator.classList.add('hidden');
                return;
            }
            
            const payload = {
                appraisal_id: appraisalId,
                fields: Object.values(fieldsToSave)
            };
            
            fetch('/appraisals/save-multiple-fields/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                console.log('Batch saved:', data);
                fieldsToSave = {}; // Clear the queue
                
                if (saveIndicator) {
                    setTimeout(() => {
                        saveIndicator.classList.add('hidden');
                    }, 500);
                }
            })
            .catch(error => {
                console.error('Error batch saving fields:', error);
            });
        }
    }
    
    // Public API
    return {
        init: init
    };
})();

// Initialize when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    AppraisalForm.init();
});