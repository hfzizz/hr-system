// Example permission check in JS
document.querySelectorAll('.hr-controls button').forEach(button => {
    button.addEventListener('click', (e) => {
        // Get user role from data attribute set in HTML
        const userRole = document.body.dataset.userRole;
        
        if (userRole !== 'HR') {
            e.preventDefault();
            alert('You need HR privileges for this action');
            return false;
        }
    });
});
