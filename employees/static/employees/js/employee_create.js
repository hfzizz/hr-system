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

window.handleFileSelect = function(input) {
    if (input.files && input.files[0]) {
        const container = input.closest('tr');
        const filename = input.files[0].name;
        
        // Update filename display
        const filenameSpan = container.querySelector('.selected-filename');
        filenameSpan.textContent = filename;
        
        // Hide file input and show filename
        input.style.display = 'none';
        filenameSpan.style.display = 'inline';
        
        // Show replace button in actions column
        const replaceButton = container.querySelector('.replace-button');
        replaceButton.style.display = 'inline-flex';
    }
};

window.triggerFileInput = function(button) {
    const row = button.closest('tr');
    const fileInput = row.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.click();
    }
};

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    window.formCount = document.querySelectorAll('.qualification-form').length;
    window.maxForms = 10;
    
    initializePasswordFunctions();
    initializeQualificationFunctions();
    initializeDocumentFunctions();
    initializePublicationFunctions();
    
    
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            console.log("Form submitting with data:", new FormData(form));
            saveQualifications(); // Keep existing qualification saving
            savePublications();   // Add publication saving before submission
            return true;
        });

        // Add change event to save publications dynamically
        form.addEventListener('change', savePublications);
    }

    // Ensure the formset starts empty if no forms exist
    const initialForms = document.querySelectorAll("#publication-formset .publication-form");
    if (initialForms.length === 0) {
        addPublication(); // Add one form by default if empty
    }
});

function initializePublicationFunctions() {
    document.querySelectorAll("#publication-formset .publication-form").forEach(form => {
        initializePublicationForm(form);
    });
}

function initializePublicationForm(form) {
    const sourceTypeSelect = form.querySelector(".source-type-field");
    const nonManualFields = form.querySelector(".non-manual-fields");
    const manualFields = form.querySelector(".manual-fields");
    const publicationTypeSelect = form.querySelector(".publication-type-select");
    const dynamicFields = form.querySelector(".dynamic-fields");
    const citationPreview = form.querySelector(".citation-preview");

    // Ensure proper initial styling
    form.classList.add('mb-4', 'p-4', 'border', 'border-gray-200', 'rounded-md');

    // Hide DELETE checkbox if it exists
    const deleteCheckbox = form.querySelector('input[type="checkbox"][name$="-DELETE"]');
    if (deleteCheckbox) {
        deleteCheckbox.classList.add('hidden');
        // Set a hidden input with the same name to ensure Django receives the value
        const hiddenDelete = document.createElement('input');
        hiddenDelete.type = 'hidden';
        hiddenDelete.name = deleteCheckbox.name;
        hiddenDelete.value = 'off';
        deleteCheckbox.parentNode.appendChild(hiddenDelete);
        deleteCheckbox.remove();
    }

    // Handle source type changes
    if (sourceTypeSelect) {
        sourceTypeSelect.addEventListener("change", function(event) {
            console.log("Source Type changed to:", event.target.value);
            if (event.target.value === "manual") {
                nonManualFields.classList.add("hidden");
                manualFields.classList.remove("hidden");
                dynamicFields.innerHTML = ""; // Clear any existing fields
                updateDynamicFields(form);
            } else {
                manualFields.classList.add("hidden");
                nonManualFields.classList.remove("hidden");
                dynamicFields.innerHTML = ""; // Clear any manual fields
                citationPreview.classList.add("hidden");
            }
        });
    } else {
        console.error("Source Type select not found in form:", form);
    }

    // Handle publication type changes for manual entries
    if (publicationTypeSelect) {
        publicationTypeSelect.addEventListener("change", function(event) {
            console.log("Publication Type changed to:", event.target.value);
            updateDynamicFields(form);
        });

        // Trigger change event for initial value if it exists
        if (publicationTypeSelect.value) {
            const changeEvent = new Event('change');
            publicationTypeSelect.dispatchEvent(changeEvent);
        }
    } else {
        console.warn("Publication Type select not found in form:", form);
    }

    // Initial setup: Start with no fields, show based on source_type
    if (sourceTypeSelect) {
        sourceTypeSelect.value = sourceTypeSelect.value || ""; // Use existing value or default to empty
    }
    nonManualFields.classList.add("hidden");
    manualFields.classList.add("hidden");
    dynamicFields.innerHTML = ""; // Start with no fields
    citationPreview.classList.add("hidden"); // Hide citation preview initially

    // Initialize based on existing source_type
    if (sourceTypeSelect && sourceTypeSelect.value === "manual") {
        manualFields.classList.remove("hidden");
        updateDynamicFields(form);
    } else if (sourceTypeSelect && sourceTypeSelect.value) {
        nonManualFields.classList.remove("hidden");
    }

    // Update citation preview on input changes
    form.querySelectorAll("input").forEach(input => {
        input.addEventListener("input", () => updateCitationPreview(form));
    });

    // Trigger updates to ensure dynamic behavior
    updateDynamicFields(form);
    updateCitationPreview(form);
}

function getFormIndex(form) {
    const formIndexMatch = form.querySelector('input[name$="-id"]')?.name.match(/publication_set-(\d+)-id/);
    return formIndexMatch ? formIndexMatch[1] : '0';
}

function updateDynamicFields(form) {
    const publicationTypeSelect = form.querySelector(".publication-type-select");
    const dynamicFields = form.querySelector(".dynamic-fields");
    const formIndex = getFormIndex(form);
    
    if (publicationTypeSelect && publicationTypeSelect.value) {
        const type = publicationTypeSelect.value;
        let html = publicationTypeFields[type].replace(/__prefix__/g, formIndex); // Use the provided publicationTypeFields
        dynamicFields.innerHTML = html;
        
        // Preserve existing values from formData if available (for restored forms)
        const citationDiv = form.closest(".publication-form") || document.querySelector(`.publication-form[data-form-data]`);
        if (citationDiv && citationDiv.dataset.formData) {
            const formData = JSON.parse(decodeURIComponent(citationDiv.dataset.formData || '{}'));
            Object.keys(formData).forEach(field => {
                const input = dynamicFields.querySelector(`[name$="${field}"]`);
                if (input) {
                    input.value = formData[field] !== undefined ? formData[field] : "";
                    // Trigger input event to update citation preview if needed
                    input.dispatchEvent(new Event('input'));
                }
            });
        }
        
        updateCitationPreview(form);
    } else {
        dynamicFields.innerHTML = ""; // No fields until a publication type is selected
    }
}
function updateCitationPreview(form) {
    const citationSpan = form.querySelector(".formatted-citation");
    const inputs = form.querySelectorAll("input");
    const publicationType = form.querySelector(".publication-type-select")?.value;
    
    let citation = "";
    const data = {};
    inputs.forEach(input => {
        const name = input.name.split('-').pop();
        data[name] = input.value;
    });

    if (publicationType && data.title) {
        switch (publicationType) {
            case "journal":
                citation = `${data.authors || ""}. (${data.year || ""}). ${data.title}. ${data.journal_name || ""}, ${data.volume || ""}(${data.issue || ""}), ${data.pages || ""}. DOI: ${data.doi || ""}`;
                break;
            case "conference":
                citation = `${data.authors || ""}. (${data.year || ""}). ${data.title}. In ${data.publisher || ""}, ${data.pages || ""}. DOI: ${data.doi || ""}`;
                break;
            case "book":
                citation = `${data.authors || ""}. (${data.year || ""}). ${data.title}. ${data.publisher || ""}, ${data.pages || ""}. DOI: ${data.doi || ""}`;
                break;
            case "chapter":
                citation = `${data.authors || ""}. (${data.year || ""}). ${data.title}. In ${data.publisher || ""}, ${data.pages || ""}. DOI: ${data.doi || ""}`;
                break;
        }
    }

    if (citation.trim()) {
        citationSpan.textContent = citation.trim();
        form.querySelector(".citation-preview").classList.remove("hidden");
    } else {
        form.querySelector(".citation-preview").classList.add("hidden");
    }
}

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

function editPublication(button, index) {
    console.log(`Attempting to edit publication at index ${index}`);
    
    try {
        // Find form elements
        const form = button.closest('.publication-form');
        const formFieldsDiv = document.getElementById(`form-fields-${index}`);
        const citationView = document.getElementById(`citation-view-${index}`);
        
        if (!form || !formFieldsDiv || !citationView) {
            console.error('Missing required elements for editing publication');
            alert('Error: Could not find required elements');
            return;
        }
        
        // Get data from hidden fields
        const hiddenTitle = document.getElementById(`hidden-title-${index}`);
        const hiddenAuthor = document.getElementById(`hidden-author-${index}`);
        const hiddenYear = document.getElementById(`hidden-year-${index}`);
        const hiddenPubType = document.getElementById(`hidden-pub_type-${index}`);
        const hiddenAdditionalFields = document.getElementById(`hidden-additional-fields-${index}`);
        
        if (!hiddenTitle || !hiddenAuthor || !hiddenYear || !hiddenPubType) {
            console.error(`Missing hidden fields for index ${index}`);
            alert(`Cannot edit publication: Missing required hidden fields`);
            return;
        }
        
        // Get values from hidden fields
        const title = hiddenTitle.value;
        const author = hiddenAuthor.value;
        const year = hiddenYear.value;
        const pubType = hiddenPubType.value;
        const additionalFieldsValue = hiddenAdditionalFields ? hiddenAdditionalFields.value : '{}';
        
        console.log(`Retrieved values for publication ${index}:`, { title, author, year, pubType });
        
        // Find form input fields
        const titleInput = formFieldsDiv.querySelector(`input[name="publication_set-${index}-title"]`);
        const authorInput = formFieldsDiv.querySelector(`input[name="publication_set-${index}-author"]`);
        const yearInput = formFieldsDiv.querySelector(`input[name="publication_set-${index}-year"]`);
        const pubTypeSelect = formFieldsDiv.querySelector(`select[name="publication_set-${index}-pub_type"]`);
        
        // Populate fields if they exist
        if (titleInput) titleInput.value = title;
        if (authorInput) authorInput.value = author;
        if (yearInput) yearInput.value = year;
        
        // Set publication type select value
        if (pubTypeSelect && pubType) {
            console.log(`Setting publication type to ${pubType}`);
            
            // Set value directly
            pubTypeSelect.value = pubType;
            
            // Verify and try alternative approach if needed
            if (pubTypeSelect.value !== pubType) {
                console.warn(`Failed to set value directly, trying option selection`);
                for (let i = 0; i < pubTypeSelect.options.length; i++) {
                    if (pubTypeSelect.options[i].value === pubType) {
                        pubTypeSelect.selectedIndex = i;
                        console.log(`Selected option index ${i}`);
                        break;
                    }
                }
            }
            
            // Trigger change event to load type-specific fields
            console.log(`Triggering change event to load type-specific fields for ${pubType}`);
            setTimeout(() => {
                const changeEvent = new Event('change', { bubbles: true });
                pubTypeSelect.dispatchEvent(changeEvent);
                
                // Wait for HTMX to load type-specific fields before filling additional fields
                setTimeout(() => {
                    try {
                        if (additionalFieldsValue && additionalFieldsValue !== '{}') {
                            console.log(`Populating additional fields: ${additionalFieldsValue}`);
                            const additionalFields = JSON.parse(additionalFieldsValue);
                            
                            // Find type fields container
                            const typeFieldsDiv = document.getElementById(`type-fields-${index}`);
                            if (typeFieldsDiv) {
                                Object.entries(additionalFields).forEach(([key, value]) => {
                                    const input = typeFieldsDiv.querySelector(`[name="additional_fields.${key}"]`);
                                    if (input && value) {
                                        console.log(`Setting ${key} to ${value}`);
                                        input.value = value;
                                    }
                                });
                            }
                        }
                    } catch (e) {
                        console.error('Error setting additional fields:', e);
                    }
                 }, 500); // Wait for HTMX to finish
            }, 50); // Small delay before triggering event
        }
        
        // Toggle visibility
        formFieldsDiv.classList.remove('hidden');
        citationView.classList.add('hidden');
        
    } catch (e) {
        console.error(`Error in editPublication function:`, e);
        alert(`An error occurred: ${e.message}`);
    }
}

// Add to your DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', function() {
    // For debugging: Inspect all publications in the DOM
    console.log('Checking all publication forms in the DOM:');
    const publicationForms = document.querySelectorAll('.publication-form');
    console.log(`Found ${publicationForms.length} publication forms`);
    
    publicationForms.forEach((form, i) => {
        const formId = form.id;
        const index = formId ? formId.split('-').pop() : i;
        console.log(`Publication ${index}:`, {
            form: form,
            citationView: document.getElementById(`citation-view-${index}`),
            formFields: document.getElementById(`form-fields-${index}`),
            hiddenTitle: document.getElementById(`hidden-title-${index}`),
            hiddenAuthor: document.getElementById(`hidden-author-${index}`),
            hiddenYear: document.getElementById(`hidden-year-${index}`),
            hiddenPubType: document.getElementById(`hidden-pub_type-${index}`)
        });
    });
});

function finalizeCitation(button, index) {
    console.log(`Generating citation for publication ${index}`);
    const form = button.closest('.publication-form');
    const formFields = document.getElementById(`form-fields-${index}`);
    const citationView = document.getElementById(`citation-view-${index}`);
    
    if (!form || !formFields || !citationView) {
        console.error('Missing required elements for generating citation');
        alert('Error: Could not find required elements');
        return;
    }
    
    // IMPORTANT FIX: Look within formFields instead of form
    const pubTypeSelect = formFields.querySelector(`select[name="publication_set-${index}-pub_type"]`);
    const titleInput = formFields.querySelector(`input[name="publication_set-${index}-title"]`);
    const authorInput = formFields.querySelector(`input[name="publication_set-${index}-author"]`);
    const yearInput = formFields.querySelector(`input[name="publication_set-${index}-year"]`);
    
    console.log('Found form fields:', {
        pubTypeSelect,
        titleInput,
        authorInput,
        yearInput
    });
    
    if (!pubTypeSelect || !pubTypeSelect.value || !titleInput || !titleInput.value || 
        !authorInput || !authorInput.value || !yearInput || !yearInput.value) {
        alert("Please fill in all required fields (publication type, title, author, and year)");
        return;
    }
    
    const pubType = pubTypeSelect.value;
    const title = titleInput.value;
    const author = authorInput.value;
    const year = yearInput.value;
    
    // Collect additional fields - IMPORTANT FIX: Look within formFields
    let additionalFields = {};
    formFields.querySelectorAll('input[name^="additional_fields."], textarea[name^="additional_fields."]').forEach(field => {
        const fieldName = field.name.replace('additional_fields.', '');
        additionalFields[fieldName] = field.value || '';
    });
    
    console.log('Additional fields collected:', additionalFields);
    
    // Format citation
    let citation = '';
    switch(pubType) {
        case 'book':
            citation = `${author} (${year}). <i>${title}</i>. ${additionalFields.publisher || ''}.`;
            break;
        case 'article':
            citation = `${author} (${year}). ${title}. <i>${additionalFields.journal || ''}</i>, ${additionalFields.volume || ''}(${additionalFields.number || ''}), ${additionalFields.pages || ''}.`;
            break;
        case 'inproceedings':
            citation = `${author} (${year}). ${title}. In <i>${additionalFields.booktitle || ''}</i> (pp. ${additionalFields.pages || ''}). ${additionalFields.publisher || ''}.`;
            break;
        case 'phdthesis':
            citation = `${author} (${year}). <i>${title}</i> [Doctoral dissertation, ${additionalFields.school || ''}].`;
            break;
        case 'mastersthesis':
            citation = `${author} (${year}). <i>${title}</i> [Master's thesis, ${additionalFields.school || ''}].`;
            break;
        default:
            citation = `${author} (${year}). ${title}.`;
    }
    
    console.log('Generated citation:', citation);
    
    // Find or create hidden fields in the citation view
    const ensureHiddenField = (name, value) => {
        let field = document.getElementById(`hidden-${name}-${index}`);
        if (!field) {
            field = document.createElement('input');
            field.type = 'hidden';
            field.id = `hidden-${name}-${index}`;
            field.name = `publication_set-${index}-${name}`;
            citationView.appendChild(field);
        }
        field.value = value;
        return field;
    };
    
    // Update hidden fields
    ensureHiddenField('title', title);
    ensureHiddenField('author', author);
    ensureHiddenField('year', year);
    ensureHiddenField('pub_type', pubType);
    ensureHiddenField('additional_fields', JSON.stringify(additionalFields));
    
    // Update citation text and show the citation view
    const citationTextElement = document.getElementById(`citation-text-${index}`);
    if (citationTextElement) {
        citationTextElement.innerHTML = citation;
        formFields.classList.add('hidden');
        citationView.classList.remove('hidden');
    } else {
        console.error(`Could not find citation-text-${index} element`);
        alert('Error: Could not update citation text');
    }
}

function removePublication(button) {
    const form = button.closest('.publication-form');
    if (!form) {
        console.error('Could not find publication form to remove');
        return;
    }
    
    const index = form.id.split('-').pop();
    const deleteInput = document.getElementById(`delete-${index}`);
    
    if (deleteInput) {
        // For existing publications, mark for deletion
        deleteInput.value = 'on';
        form.style.display = 'none';
        console.log(`Marked publication ${index} for deletion`);
    } else {
        // For new publications, remove from DOM
        form.remove();
        console.log(`Removed new publication ${index}`);
    }
    
    // Update total forms count
    const totalFormsInput = document.querySelector('#id_publication_set-TOTAL_FORMS');
    if (totalFormsInput) {
        const newTotal = parseInt(totalFormsInput.value) - 1;
        totalFormsInput.value = newTotal;
        console.log(`Updated publications total to ${newTotal}`);
    }
}

// Add a utility function for debugging
function inspectDOM(startIndex, endIndex) {
    console.log('--- Publication DOM Inspection ---');
    for (let i = startIndex; i <= endIndex; i++) {
        console.log(`--- Publication ${i} DOM Structure ---`);
        console.log(`#publication-form-${i}:`, document.getElementById(`publication-form-${i}`));
        console.log(`#citation-view-${i}:`, document.getElementById(`citation-view-${i}`));
        console.log(`#form-fields-${i}:`, document.getElementById(`form-fields-${i}`));
        console.log(`#hidden-title-${i}:`, document.getElementById(`hidden-title-${i}`));
        console.log(`#hidden-pub_type-${i}:`, document.getElementById(`hidden-pub_type-${i}`));
        console.log(`#type-fields-${i}:`, document.getElementById(`type-fields-${i}`));
    }
}

// Add HTMX event monitoring
document.addEventListener('DOMContentLoaded', function() {
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        console.log('HTMX Request Details:', {
            target: evt.detail.target,
            path: evt.detail.path,
            params: evt.detail.parameters,
            headers: evt.detail.headers
        });
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        console.log('HTMX Response Details:', {
            target: evt.detail.target,
            status: evt.detail.xhr.status,
            path: evt.detail.pathInfo ? evt.detail.pathInfo.requestPath : 'unknown'
        });
    });
    
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX Error Response:', {
            error: evt.detail.error,
            status: evt.detail.xhr.status,
            response: evt.detail.xhr.responseText
        });
    });
    
    // For debugging - uncomment when needed
    // setTimeout(() => inspectDOM(0, 5), 1000);
});

// Make sure the functions are globally available
window.editPublication = editPublication;
window.finalizeCitation = finalizeCitation;
window.removePublication = removePublication;
window.populateAdditionalFields = populateAdditionalFields;
window.inspectDOM = inspectDOM;