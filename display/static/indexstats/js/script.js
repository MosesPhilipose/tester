const jsonDataUrl = "/ticker-data/";

async function fetchData() {
    try {
        const response = await fetch(jsonDataUrl);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const data = await response.json();

        if (data.status === "no_data") {
            document.getElementById("lastUpdated").textContent = data.message;
            document.querySelector("#marketTable tbody").innerHTML = "";
            document.getElementById("marketTable").classList.remove("show");
            document.getElementById("loadingSpinner").style.visibility = "hidden";
            return;
        }

        document.getElementById("lastUpdated").textContent = data["Generated on"];
        const tbody = document.querySelector("#marketTable tbody");
        tbody.innerHTML = "";
        data["Tickers"].forEach(ticker => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${ticker["Symbol"]}</td>
                <td>${ticker["Opening Scenario"]}</td>
                <td>${ticker["Trend Observed"]}</td>
                <td>${ticker["Upward Close"]}%</td>
                <td>${ticker["Downward Close"]}%</td>
                <td>${ticker["Flat Close"]}%</td>
            `;
            tbody.appendChild(row);
        });
        document.getElementById("marketTable").classList.add("show");
        document.getElementById("loadingSpinner").style.visibility = "hidden";
    } catch (error) {
        console.error("Error fetching data:", error);
        alert("Failed to load data. Please try again.");
    }
}

window.onload = () => {
    fetchData();
};

document.getElementById("refreshData").addEventListener("click", () => {
    fetch("/refresh-data/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            fetchData();  // Update table immediately
        } else {
            alert(`Error: ${data.message}`);
        }
    })
    .catch(error => {
        console.error("Error refreshing data:", error);
        alert("Failed to refresh data. Please try again.");
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function filterTable() {
    const input = document.getElementById("searchInput").value.toLowerCase();
    const rows = document.querySelectorAll("#marketTable tbody tr");
    rows.forEach(row => {
        const symbol = row.cells[0].textContent.toLowerCase();
        row.style.display = symbol.includes(input) ? "" : "none";
    });
}

function sortTable(columnIndex) {
    const table = document.getElementById("marketTable");
    const rows = Array.from(table.rows).slice(1);
    const isAscending = table.getAttribute("aria-sort") === "ascending";
    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim().replace('%', '').toLowerCase();
        const bValue = b.cells[columnIndex].textContent.trim().replace('%', '').toLowerCase();
        if (!isNaean(aValue) && !isNaN(bValue)) {
            return isAscending ? parseFloat(aValue) - parseFloat(bValue) : parseFloat(bValue) - parseFloat(aValue);
        } else {
            return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
        }
    });
    rows.forEach(row => table.tBodies[0].appendChild(row));
    table.setAttribute("aria-sort", isAscending ? "descending" : "ascending");
}

document.getElementById("themeToggle").addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
});

document.getElementById("exportCSV").addEventListener("click", () => {
    const rows = document.querySelectorAll("#marketTable tbody tr");
    let csvContent = "data:text/csv;charset=utf-8,";
    const headers = ["Symbol", "Opening Scenario", "Trend Observed", "Upward Close (%)", "Downward Close (%)", "Flat Close (%)"];
    csvContent += headers.join(",") + "\n";
    rows.forEach(row => {
        const rowData = Array.from(row.cells).map(cell => cell.textContent.replace(/%/g, ""));
        csvContent += rowData.join(",") + "\n";
    });
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "market_analysis.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});

document.getElementById("exportPDF").addEventListener("click", () => {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const rows = document.querySelectorAll("#marketTable tbody tr");
    const headers = ["Symbol", "Opening Scenario", "Trend Observed", "Upward Close (%)", "Downward Close (%)", "Flat Close (%)"];
    const data = [];
    rows.forEach(row => {
        const rowData = Array.from(row.cells).map(cell => cell.textContent.replace(/%/g, ""));
        data.push(rowData);
    });
    doc.autoTable({
        head: [headers],
        body: data,
        theme: "grid",
        styles: { fontSize: 8 },
        margin: { top: 20 },
        didDrawPage: function (dataArg) {
            doc.text("Market Analysis Report", 14, 15);
        },
    });
    doc.save("market_analysis.pdf");
});
