document.addEventListener('DOMContentLoaded', function() {
    // Preview Modal Functions
    window.openPreviewModal = function(title, url) {
        const modal = document.getElementById('previewModal');
        const titleElement = document.getElementById('modalTitle');
        const preview = document.getElementById('documentPreview');
        
        titleElement.textContent = title;
        preview.src = url;
        modal.classList.remove('hidden');
    }

    window.closePreviewModal = function() {
        const modal = document.getElementById('previewModal');
        const preview = document.getElementById('documentPreview');
        
        preview.src = '';
        modal.classList.add('hidden');
    }

    // Document Management Functions
    window.replaceFile = function(row) {
        const fileCell = row.querySelector('td:nth-child(2)');
        const fileContainer = fileCell.querySelector('.file-container');
        const formIdx = row.dataset.formIdx;
        
        // Create file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.name = `document_set-${formIdx}-file`;
        fileInput.id = `id_document_set-${formIdx}-file`;
        fileInput.className = 'block w-full text-sm text-gray-500 ' +
                            'file:mr-4 file:py-2 file:px-4 ' +
                            'file:rounded-md file:border-0 ' +
                            'file:text-sm file:font-semibold ' +
                            'file:bg-indigo-50 file:text-indigo-700 ' +
                            'hover:file:bg-indigo-100';
        fileInput.required = true;
        
        // Replace content
        fileCell.innerHTML = '';
        fileCell.appendChild(fileInput);
        
        // Hide replace button
        const replaceBtn = row.querySelector('.replace-btn');
        if (replaceBtn) {
            replaceBtn.style.display = 'none';
        }
    }

    // Event Listeners
    document.addEventListener('click', function(event) {
        // Preview button
        if (event.target.classList.contains('preview-btn')) {
            const title = event.target.dataset.title;
            const url = event.target.dataset.url;
            openPreviewModal(title, url);
        }
        
        // Replace button
        if (event.target.classList.contains('replace-btn')) {
            const row = event.target.closest('tr');
            replaceFile(row);
        }
        
        // Delete button
        if (event.target.classList.contains('delete-btn')) {
            const row = event.target.closest('tr');
            const formIdx = row.dataset.formIdx;
            const deleteInput = document.getElementById(`id_document_set-${formIdx}-DELETE`);
            deleteInput.value = 'on';
            row.style.display = 'none';
        }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closePreviewModal();
        }
    });
});