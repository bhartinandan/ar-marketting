const uniqueLabels = JSON.parse('{{ unique_click_labels|escapejs }}');
  const uniqueClicks = JSON.parse('{{ unique_click_data|escapejs }}');
const createChart = (id, type, labels, data, labelName) => {
    const ctx = document.getElementById(id).getContext('2d');
    new Chart(ctx, {
      type,
      data: {
        labels,
        datasets: [{
          label: labelName,
          data,
          backgroundColor: '#3b82f6',
          borderColor: '#3b82f6',
          borderWidth: 2,
          fill: type !== 'bar',
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            ticks: { color: 'white' },
            grid: { color: '#374151' }
          },
          x: {
            ticks: { color: 'white' },
            grid: { color: '#374151' }
          }
        },
        plugins: {
          legend: {
            labels: {
              color: 'white'
            }
          }
        }
      }
    });
  };
  
  createChart('daysChart', 'line', Array.from({ length: 15 }, (_, i) => i + 1), [15, 13, 12, 10, 8, 6, 5, 4, 3, 2, 1], 'Days Left');
  createChart('scansChart', 'line', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], [100, 200, 300, 450, 600, 800, 900], 'Scans');
  createChart('uniqueScansChart', 'bar', uniqueLabels, uniqueClicks, 'Unique Scans');
  createChart('watchChart', 'line', ['1', '2', '3', '4', '5'], [1.2, 1.5, 1.6, 1.7, 2], 'Avg. Watch Time (mins)');
  createChart('clicksChart', 'bar', ['Week1', 'Week2', 'Week3', 'Week4'], [100, 300, 400, 847], 'Link Clicks');
  
  
  const userTrigger = document.querySelector('.user');
    const popoutBox = document.getElementById('popout');
  
    userTrigger.addEventListener('click', () => {
      if (popoutBox.style.display === 'flex') {
        popoutBox.style.display = 'none';
      } else {
        popoutBox.style.display = 'flex';
        popoutBox.style.flexDirection = 'column'; // ensure it maintains layout
      }
    });
  
    // Optional: Close when clicking outside
    document.addEventListener('click', (e) => {
      if (!popoutBox.contains(e.target) && !userTrigger.contains(e.target)) {
        popoutBox.style.display = 'none';
      }
    });