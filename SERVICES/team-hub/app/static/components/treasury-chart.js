/**
 * Enhanced Treasury Analytics Chart Component
 * Provides 30-day PnL trends, drawdown visualization, and risk metrics
 */

class TreasuryChart {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = {
      timeframe: '30d',
      showDrawdown: true,
      showVolume: false,
      theme: 'dark',
      ...options
    };

    this.chart = null;
    this.data = null;
    this.loading = false;

    this.init();
  }

  init() {
    this.container = document.getElementById(this.containerId);
    if (!this.container) {
      console.error(`Container ${this.containerId} not found`);
      return;
    }

    // Create canvas if not exists
    if (!this.container.querySelector('canvas')) {
      const canvas = document.createElement('canvas');
      canvas.width = this.container.offsetWidth;
      canvas.height = this.container.offsetHeight || 300;
      this.container.appendChild(canvas);
    }

    this.loadData();
  }

  async loadData() {
    if (this.loading) return;

    this.loading = true;
    this.showLoading();

    try {
      const response = await fetch(`/api/treasury/analytics?timeframe=${this.options.timeframe}`, {
        headers: {
          'Authorization': `Bearer ${this.getAuthToken()}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      this.data = await response.json();
      this.render();

    } catch (error) {
      console.error('Failed to load treasury data:', error);
      this.showError(error.message);
    } finally {
      this.loading = false;
    }
  }

  showLoading() {
    const canvas = this.container.querySelector('canvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#666';
      ctx.font = '16px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Loading treasury data...', canvas.width / 2, canvas.height / 2);
    }
  }

  showError(message) {
    const canvas = this.container.querySelector('canvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#f44336';
      ctx.font = '14px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`Error: ${message}`, canvas.width / 2, canvas.height / 2);
    }
  }

  render() {
    if (!this.data) return;

    const ctx = this.container.querySelector('canvas').getContext('2d');

    // Destroy existing chart
    if (this.chart) {
      this.chart.destroy();
    }

    // Prepare datasets
    const datasets = [];

    // Portfolio value line
    datasets.push({
      label: 'Portfolio Value ($)',
      data: this.data.portfolio_value,
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderWidth: 2,
      tension: 0.4,
      fill: false,
      yAxisID: 'y'
    });

    // Drawdown area (if enabled)
    if (this.options.showDrawdown && this.data.drawdown) {
      datasets.push({
        label: 'Drawdown (%)',
        data: this.data.drawdown,
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
        borderWidth: 1,
        tension: 0.4,
        fill: true,
        yAxisID: 'y1',
        pointRadius: 0
      });
    }

    // Trading volume (if enabled)
    if (this.options.showVolume && this.data.volume) {
      datasets.push({
        label: 'Trading Volume ($)',
        data: this.data.volume,
        type: 'bar',
        backgroundColor: 'rgba(156, 163, 175, 0.3)',
        borderColor: 'rgba(156, 163, 175, 0.5)',
        borderWidth: 1,
        yAxisID: 'y2'
      });
    }

    // Format timestamps
    const labels = this.data.timestamps.map(ts => {
      const date = new Date(ts);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      });
    });

    // Chart configuration
    const config = {
      type: 'line',
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              usePointStyle: true,
              padding: 20,
              color: '#e5e7eb'
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            callbacks: {
              afterLabel: (context) => {
                const index = context.dataIndex;
                let tooltip = [];

                if (this.data.pnl && this.data.pnl[index] !== undefined) {
                  tooltip.push(`PnL: $${this.data.pnl[index].toFixed(2)}`);
                }

                if (this.data.drawdown && this.data.drawdown[index] !== undefined) {
                  tooltip.push(`Drawdown: ${this.data.drawdown[index].toFixed(2)}%`);
                }

                return tooltip;
              }
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#9ca3af',
              maxTicksLimit: 10
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Portfolio Value ($)',
              color: '#9ca3af'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#9ca3af',
              callback: (value) => `$${(value / 1000).toFixed(0)}K`
            }
          }
        }
      }
    };

    // Add secondary Y-axis for drawdown
    if (this.options.showDrawdown) {
      config.options.scales.y1 = {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Drawdown (%)',
          color: '#ef4444'
        },
        grid: {
          drawOnChartArea: false
        },
        ticks: {
          color: '#ef4444',
          callback: (value) => `${value.toFixed(1)}%`
        },
        min: Math.min(...this.data.drawdown) - 1,
        max: 0
      };
    }

    // Add tertiary Y-axis for volume
    if (this.options.showVolume) {
      config.options.scales.y2 = {
        type: 'linear',
        display: true,
        position: 'right',
        title: {
          display: true,
          text: 'Volume ($)',
          color: '#9ca3af'
        },
        grid: {
          drawOnChartArea: false
        },
        ticks: {
          color: '#9ca3af',
          callback: (value) => `$${(value / 1000).toFixed(0)}K`
        }
      };
    }

    // Create chart
    this.chart = new Chart(ctx, config);

    // Add timeframe selector
    this.addTimeframeControls();
  }

  addTimeframeControls() {
    // Remove existing controls
    const existing = this.container.querySelector('.timeframe-controls');
    if (existing) existing.remove();

    const controls = document.createElement('div');
    controls.className = 'timeframe-controls';
    controls.style.cssText = `
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      gap: 5px;
      background: rgba(0, 0, 0, 0.7);
      padding: 5px;
      border-radius: 6px;
      z-index: 10;
    `;

    const timeframes = ['7d', '30d', '90d', '1y'];
    timeframes.forEach(tf => {
      const btn = document.createElement('button');
      btn.textContent = tf.toUpperCase();
      btn.style.cssText = `
        background: ${this.options.timeframe === tf ? '#3b82f6' : 'transparent'};
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;
      `;

      btn.addEventListener('click', () => {
        this.options.timeframe = tf;
        timeframes.forEach(t => {
          const b = controls.querySelector(`button:nth-child(${timeframes.indexOf(t) + 1})`);
          b.style.background = t === tf ? '#3b82f6' : 'transparent';
        });
        this.loadData();
      });

      controls.appendChild(btn);
    });

    this.container.style.position = 'relative';
    this.container.appendChild(controls);
  }

  getAuthToken() {
    // Get auth token from local storage or wherever it's stored
    return localStorage.getItem('authToken') || '';
  }

  updateOptions(newOptions) {
    this.options = { ...this.options, ...newOptions };
    if (this.chart) {
      this.loadData();
    }
  }

  resize() {
    if (this.chart) {
      this.chart.resize();
    }
  }

  destroy() {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  // Initialize any treasury chart containers
  document.querySelectorAll('[data-treasury-chart]').forEach(el => {
    const options = JSON.parse(el.dataset.treasuryChart || '{}');
    new TreasuryChart(el.id, options);
  });
});












