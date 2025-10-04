let allData = [];
let projects = [];
let monthlyData = [];

// Fetch data from API - now using juan_gastos1 table
async function loadData() {
    try {
        showLoading('Loading data from juan_gastos1...', 'chart');
        showLoading('Loading data...', 'dataTableBody');
        
        // Fetch data from the updated API endpoint
        const response = await fetch('/api/gastos');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Loaded data from juan_gastos1:', data);
        
        if (!data || data.length === 0) {
            showError('No data found in juan_gastos1 table', 'chart');
            showError('No data available', 'dataTableBody');
            return;
        }
        
        allData = data;
        
        // Get unique projects
        projects = [...new Set(data.map(item => item.proyecto))].filter(Boolean).sort();
        console.log('Found projects:', projects);
        
        if (projects.length === 0) {
            showError('No projects found in the data', 'chart');
            return;
        }
        
        // Create monthly aggregated data
        createMonthlyData();
        
        // Create project filters
        createProjectFilters();
        
        // Update statistics
        updateStats();
        
        // Initial chart render with all projects selected
        updateChart();
        updateDataTable();
        
    } catch (error) {
        console.error('Error loading data from juan_gastos1:', error);
        showError(`Error loading data: ${error.message}. Please check your connection and try again.`, 'chart');
        showError('Failed to load data', 'dataTableBody');
    }
}

function createMonthlyData() {
    const monthlyMap = new Map();
    
    allData.forEach(item => {
        try {
            // Handle different date formats
            let date;
            if (item.fecha.includes('T')) {
                // ISO format with time
                date = new Date(item.fecha);
            } else {
                // Simple date format YYYY-MM-DD
                date = new Date(item.fecha + 'T00:00:00');
            }
            
            if (isNaN(date.getTime())) {
                console.warn('Invalid date found:', item.fecha);
                return;
            }
            
            const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
            const key = `${item.proyecto}_${monthKey}`;
            
            if (!monthlyMap.has(key)) {
                monthlyMap.set(key, {
                    proyecto: item.proyecto,
                    month: monthKey,
                    monthDisplay: date.toLocaleDateString('en-US', { year: 'numeric', month: 'long' }),
                    count: 0,
                    totalAmount: 0,
                    records: []
                });
            }
            
            const monthData = monthlyMap.get(key);
            monthData.count++;
            monthData.totalAmount += parseFloat(item.monto) || 0;
            monthData.records.push(item);
        } catch (error) {
            console.warn('Error processing item:', item, error);
        }
    });
    
    monthlyData = Array.from(monthlyMap.values()).map(item => ({
        ...item,
        avgAmount: item.count > 0 ? item.totalAmount / item.count : 0
    }));
    
    console.log('Created monthly data:', monthlyData);
}

function showLoading(message, elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        if (elementId === 'dataTableBody') {
            element.innerHTML = `<tr><td colspan="5" class="loading">${message}</td></tr>`;
        } else {
            element.innerHTML = `<div class="loading">${message}</div>`;
        }
    }
}

function showError(message, elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        if (elementId === 'dataTableBody') {
            element.innerHTML = `<tr><td colspan="5" class="error">${message}</td></tr>`;
        } else {
            element.innerHTML = `<div class="error">${message}</div>`;
        }
    }
}

function createProjectFilters() {
    const container = document.getElementById('projectFilters');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (projects.length === 0) {
        container.innerHTML = '<div class="loading">No projects found</div>';
        return;
    }
    
    projects.forEach((project, index) => {
        const filterDiv = document.createElement('div');
        filterDiv.className = 'project-filter';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `project_${project.replace(/[^a-zA-Z0-9]/g, '_')}`;
        checkbox.checked = true;
        checkbox.addEventListener('change', () => {
            updateChart();
            updateDataTable();
        });
        
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = project;
        
        filterDiv.appendChild(checkbox);
        filterDiv.appendChild(label);
        container.appendChild(filterDiv);
    });
}

function getSelectedProjects() {
    return projects.filter(project => {
        const checkbox = document.getElementById(`project_${project.replace(/[^a-zA-Z0-9]/g, '_')}`);
        return checkbox && checkbox.checked;
    });
}

function updateStats() {
    const totalProjects = projects.length;
    const totalRecords = allData.length;
    const validAmounts = allData.filter(item => item.monto != null && !isNaN(parseFloat(item.monto)));
    const totalAmount = validAmounts.reduce((sum, item) => sum + parseFloat(item.monto), 0);
    const avgAmount = validAmounts.length > 0 ? totalAmount / validAmounts.length : 0;
    
    const statsHTML = `
        <div class="stat-card">
            <div class="stat-value">${totalProjects}</div>
            <div class="stat-label">Total Projects</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${totalRecords}</div>
            <div class="stat-label">Total Records</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$${totalAmount.toLocaleString()}</div>
            <div class="stat-label">Total Amount</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">$${avgAmount.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
            <div class="stat-label">Average Amount</div>
        </div>
    `;
    
    const statsElement = document.getElementById('stats');
    if (statsElement) {
        statsElement.innerHTML = statsHTML;
    }
}

function updateChart() {
    const selectedProjects = getSelectedProjects();
    
    if (selectedProjects.length === 0) {
        document.getElementById('chart').innerHTML = '<div class="loading">Please select at least one project to display the chart</div>';
        return;
    }
    
    const filteredMonthlyData = monthlyData.filter(item => 
        selectedProjects.includes(item.proyecto)
    );
    
    if (filteredMonthlyData.length === 0) {
        document.getElementById('chart').innerHTML = '<div class="loading">No data found for selected projects</div>';
        return;
    }
    
    // Group data by project
    const traces = [];
    const colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
    ];
    
    selectedProjects.forEach((project, index) => {
        const projectData = filteredMonthlyData
            .filter(item => item.proyecto === project)
            .sort((a, b) => a.month.localeCompare(b.month));
        
        if (projectData.length === 0) return;
        
        traces.push({
            x: projectData.map(item => item.month + '-01'), // Add day for proper date parsing
            y: projectData.map(item => item.totalAmount),
            name: project,
            type: 'scatter',
            mode: 'lines+markers',
            marker: {
                color: colors[index % colors.length],
                size: 10,
                line: {
                    color: 'white',
                    width: 2
                }
            },
            line: {
                width: 4,
                shape: 'spline'
            },
            hovertemplate: 
                '<b>%{fullData.name}</b><br>' +
                'Month: %{x|%B %Y}<br>' +
                'Total Amount: $%{y:,.2f}<br>' +
                'Records: ' + projectData.map(item => item.count).join(', ') + '<br>' +
                '<extra></extra>'
        });
    });
    
    if (traces.length === 0) {
        document.getElementById('chart').innerHTML = '<div class="loading">No valid data points found for the selected projects.</div>';
        return;
    }
    
    const layout = {
        title: {
            text: 'Monthly Expenses from juan_gastos1 Table',
            font: { 
                size: 24,
                color: '#2c3e50',
                family: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif'
            }
        },
        xaxis: {
            title: {
                text: 'Month',
                font: { size: 14, color: '#666' }
            },
            type: 'date',
            gridcolor: '#f0f0f0',
            tickfont: { color: '#666' },
            tickformat: '%b %Y'
        },
        yaxis: {
            title: {
                text: 'Monthly Total Amount ($)',
                font: { size: 14, color: '#666' }
            },
            tickformat: '$,.0f',
            gridcolor: '#f0f0f0',
            tickfont: { color: '#666' }
        },
        hovermode: 'closest',
        showlegend: true,
        legend: {
            x: 1,
            xanchor: 'right',
            y: 1,
            bgcolor: 'rgba(255,255,255,0.9)',
            bordercolor: '#ddd',
            borderwidth: 1
        },
        margin: {
            l: 80,
            r: 80,
            t: 80,
            b: 80
        },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
        displaylogo: false,
        toImageButtonOptions: {
            format: 'png',
            filename: 'juan_gastos_monthly_chart',
            height: 600,
            width: 1200,
            scale: 1
        }
    };
    
    Plotly.newPlot('chart', traces, layout, config);
}

function updateDataTable() {
    const selectedProjects = getSelectedProjects();
    const filteredMonthlyData = monthlyData.filter(item => 
        selectedProjects.includes(item.proyecto)
    ).sort((a, b) => {
        if (a.proyecto !== b.proyecto) {
            return a.proyecto.localeCompare(b.proyecto);
        }
        return a.month.localeCompare(b.month);
    });
    
    const tbody = document.getElementById('dataTableBody');
    const summaryInfo = document.getElementById('summaryInfo');
    
    if (!tbody) return;
    
    if (filteredMonthlyData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No data available for selected projects</td></tr>';
        if (summaryInfo) summaryInfo.style.display = 'none';
        return;
    }
    
    // Update summary info
    const totalRecords = filteredMonthlyData.reduce((sum, item) => sum + item.count, 0);
    const totalAmount = filteredMonthlyData.reduce((sum, item) => sum + item.totalAmount, 0);
    
    if (summaryInfo) {
        summaryInfo.innerHTML = `
            <strong>Summary:</strong> Showing ${filteredMonthlyData.length} monthly aggregations 
            from ${selectedProjects.length} project(s), representing ${totalRecords} individual records 
            with a total value of $${totalAmount.toLocaleString()}.
        `;
        summaryInfo.style.display = 'block';
    }
    
    // Populate table
    tbody.innerHTML = filteredMonthlyData.map(item => `
        <tr>
            <td><strong>${item.proyecto}</strong></td>
            <td>${item.monthDisplay}</td>
            <td>${item.count}</td>
            <td>$${item.totalAmount.toLocaleString()}</td>
            <td>$${item.avgAmount.toLocaleString(undefined, {maximumFractionDigits: 2})}</td>
        </tr>
    `).join('');
}

function selectAllProjects() {
    projects.forEach(project => {
        const checkbox = document.getElementById(`project_${project.replace(/[^a-zA-Z0-9]/g, '_')}`);
        if (checkbox) checkbox.checked = true;
    });
    updateChart();
    updateDataTable();
}

function deselectAllProjects() {
    projects.forEach(project => {
        const checkbox = document.getElementById(`project_${project.replace(/[^a-zA-Z0-9]/g, '_')}`);
        if (checkbox) checkbox.checked = false;
    });
    updateChart();
    updateDataTable();
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'a') {
            e.preventDefault();
            selectAllProjects();
        } else if (e.ctrlKey && e.key === 'd') {
            e.preventDefault();
            deselectAllProjects();
        }
    });
});

// Add error handling for network issues
window.addEventListener('online', function() {
    console.log('Connection restored');
    loadData();
});

window.addEventListener('offline', function() {
    showError('Connection lost. Please check your internet connection.', 'chart');
});