document.addEventListener('DOMContentLoaded', function() {
    // Initialize all collapsible sections
    initializeSections();
    
    // Initialize inline forms
    initializeInlineForms();
    
    // Initialize tooltips
    initializeTooltips();
});

function initializeSections() {
    document.querySelectorAll('.section-card').forEach(section => {
        const header = section.querySelector('.section-header');
        const content = section.querySelector('.section-content');
        const icon = header.querySelector('.section-icon');

        header.addEventListener('click', () => {
            content.classList.toggle('hidden');
            icon.classList.toggle('rotate-180');
        });
    });
}

function initializeInlineForms() {
    // Handle inline form additions
    document.querySelectorAll('.add-inline-item').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const template = document.querySelector(this.dataset.template);
            const container = document.querySelector(this.dataset.container);
            const clone = template.content.cloneNode(true);
            
            // Update form index
            const newIndex = container.children.length;
            updateFormIndex(clone, newIndex);
            
            container.appendChild(clone);
        });
    });

    // Handle inline form deletions
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-inline-item')) {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this item?')) {
                const row = e.target.closest('.inline-item');
                row.remove();
            }
        }
    });
}

function initializeTooltips() {
    tippy('[data-tippy-content]', {
        placement: 'top',
        arrow: true,
        theme: 'light-border'
    });
}

function updateFormIndex(element, index) {
    element.querySelectorAll('[name]').forEach(input => {
        input.name = input.name.replace('__prefix__', index);
        input.id = input.id.replace('__prefix__', index);
    });
    element.querySelectorAll('[for]').forEach(label => {
        label.htmlFor = label.htmlFor.replace('__prefix__', index);
    });
}