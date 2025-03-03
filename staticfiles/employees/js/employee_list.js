document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log("Raw table config:", document.querySelector('.container').dataset.tableConfig);
        const tableConfig = JSON.parse(document.querySelector('.container').dataset.tableConfig);
        console.log("Parsed table config:", tableConfig);
        
        // Initialize your table here
        const container = document.querySelector('.dynamic-table-container');
        if (container) {
            new DynamicTable(container);
        } else {
            console.error("Could not find table container");
        }
    } catch (error) {
        console.error("Error initializing table:", error);
    }
});