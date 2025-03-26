// Fetch data from the JSON file and populate the table
async function fetchData() {
    try {
        console.log("Fetching JSON from:", jsonDataUrl);
        
        const response = await fetch(jsonDataUrl);
        console.log("Response Status:", response.status); // Check if it's 200
        console.log("Response Headers:", response.headers);

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Fetched Data:", data); // Debugging the data

        document.getElementById("lastUpdated").textContent = data["Data Generated On"];

        const tbody = document.querySelector("#marketTable tbody ");
        tbody.innerHTML = ""; // Clear existing rows

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
    } catch (error) {
        console.error("Error fetching data:", error);
        alert("Failed to load data. Please try again.");
    }
}




// Call fetchData on page load
window.onload = () => {
    fetchData();
};

// Refresh Data Button
document.getElementById("refreshData").addEventListener("click", () => {
    fetch("/refresh-data/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.status === "success") {
                // location.reload(true); // Reload the page to reflect updated data

                setTimeout(() => { 
                    // location.reload(true); 
                }, 20000); // Reload the page after 20 second

            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch((error) => {
            console.error("Error refreshing data:", error);
            alert("Failed to refresh data. Please try again.");
        });
});

// Helper function to get CSRF token
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

// Filter table based on search input
function filterTable() {
    const input = document.getElementById("searchInput").value.toLowerCase();
    const rows = document.querySelectorAll("#marketTable tbody tr");

    rows.forEach(row => {
        const symbol = row.cells[0].textContent.toLowerCase();
        row.style.display = symbol.includes(input) ? "" : "none";
    });
}

// Sort table columns
function sortTable(columnIndex) {
    const table = document.getElementById("marketTable");
    const rows = Array.from(table.rows).slice(1); // Exclude header row
    const isAscending = table.getAttribute("aria-sort") === "ascending";

    rows.sort((a, b) => {
        const aValue = a.cells[columnIndex].textContent.trim().toLowerCase();
        const bValue = b.cells[columnIndex].textContent.trim().toLowerCase();

        if (!isNaN(aValue) && !isNaN(bValue)) {
            return isAscending ? parseFloat(aValue) - parseFloat(bValue) : parseFloat(bValue) - parseFloat(aValue);
        } else {
            return isAscending ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
        }
    });

    rows.forEach(row => table.tBodies[0].appendChild(row));
    table.setAttribute("aria-sort", isAscending ? "descending" : "ascending");
}

// Dark Mode Toggle
document.getElementById("themeToggle").addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
});