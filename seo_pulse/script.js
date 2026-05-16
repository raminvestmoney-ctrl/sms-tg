document.addEventListener('DOMContentLoaded', () => {
    // Initialize Pulse Chart
    const ctx = document.getElementById('pulseChart').getContext('2d');
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 209, 255, 0.2)');
    gradient.addColorStop(1, 'rgba(0, 209, 255, 0)');

    const pulseChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(10).fill(''),
            datasets: [{
                label: 'Response Time (ms)',
                data: [120, 150, 130, 170, 140, 160, 145, 155, 140, 150],
                borderColor: '#00d1ff',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                backgroundColor: gradient,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#bbc9cf' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // Simulate Real-time data
    setInterval(() => {
        pulseChart.data.datasets[0].data.shift();
        pulseChart.data.datasets[0].data.push(Math.floor(Math.random() * (180 - 120 + 1)) + 120);
        pulseChart.update('none');
    }, 2000);

    // Sidebar active state toggle
    const navLinks = document.querySelectorAll('.sidebar nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        });
    });

    // Connect Backend to Frontend
    const analyzeBtn = document.querySelector('.primary-btn');
    const searchInput = document.querySelector('.search-bar input');

    analyzeBtn.addEventListener('click', async () => {
        const url = searchInput.value;
        if (!url) return alert('Please enter a domain URL');

        analyzeBtn.innerText = 'Analyzing...';
        analyzeBtn.disabled = true;

        try {
            const response = await fetch(`http://localhost:8000/audit?url=${encodeURIComponent(url)}`);
            const data = await response.json();

            if (data.detail) throw new Error(data.detail);

            // Update UI
            updateDashboard(data);
        } catch (err) {
            alert('Audit failed: ' + err.message);
        } finally {
            analyzeBtn.innerText = 'Analyze New Site';
            analyzeBtn.disabled = false;
        }
    });

    function updateDashboard(data) {
        // Update Score Gauge
        const scoreCircle = document.querySelector('.circle');
        const scoreText = document.querySelector('.percentage');
        scoreCircle.style.strokeDasharray = `${data.score}, 100`;
        scoreText.textContent = data.score;

        // Update Vitals
        const vitalValues = document.querySelectorAll('.vital-item .value');
        vitalValues[0].textContent = data.vitals.lcp;
        vitalValues[1].textContent = data.vitals.fid;
        vitalValues[2].textContent = data.vitals.cls;

        // Update Issues List
        const issuesContainer = document.querySelector('.issues-list');
        issuesContainer.innerHTML = data.issues.map(issue => `
            <div class="issue-item">
                <div class="issue-icon ${issue.priority.toLowerCase()}">${issue.priority === 'High' ? '⚠️' : '⚙️'}</div>
                <div class="issue-details">
                    <span class="title">${issue.title}</span>
                    <span class="path">${issue.path}</span>
                </div>
                <span class="priority ${issue.priority.toLowerCase()}">${issue.priority}</span>
            </div>
        `).join('') || '<p>No issues found! Great job.</p>';

        // Update Screenshots
        document.getElementById('desktop-img').src = data.screenshots.desktop;
        document.getElementById('mobile-img').src = data.screenshots.mobile;

        // Update PDF Link
        const pdfLink = document.getElementById('download-pdf');
        pdfLink.href = data.pdf_report;
        pdfLink.style.display = 'inline-block';
    }
});
