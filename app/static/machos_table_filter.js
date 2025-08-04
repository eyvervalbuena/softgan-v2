document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchBar');
    const table = document.getElementById('machosTable');
    if (!searchInput || !table) return;

    const rows = Array.from(table.querySelectorAll('tbody tr'));
    searchInput.addEventListener('input', () => {
        const term = searchInput.value.trim().toLowerCase();
        rows.forEach(row => {
            const idText = row.cells[0]?.textContent.toLowerCase() || '';
            const nameText = row.cells[1]?.textContent.toLowerCase() || '';
            row.style.display = (idText.includes(term) || nameText.includes(term)) ? '' : 'none';
        });
    });
});