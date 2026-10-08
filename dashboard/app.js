/* Ant World dashboard: renders only state and measurements supplied by the API. */
class AntWorldDashboard {
  constructor() {
    this.endpoint = '/api/state';
    this.pollMs = 200;
    this.pollInFlight = false;
    this.state = null;
    this.lastIteration = null;
    this.samples = [];
    this.benchmarkRows = [];
    this.visibility = { ants: true, pheromone: true, obstacles: true };
    this.canvas = document.getElementById('worldCanvas');
    this.ctx = this.canvas.getContext('2d');
    this.worldLayer = document.createElement('canvas');
    this.worldLayerCtx = this.worldLayer.getContext('2d');
    this.previousAnts = new Map();
    this.antMotion = new Map();
    this.lastPollAt = null;
    this.lastAntFrameAt = 0;
    this.renderedMapKey = null;
    this.pheromoneCacheKey = null;
    this.pheromoneCanvas = document.createElement('canvas');
    this.pheromoneContext = this.pheromoneCanvas.getContext('2d');
    this.antSprites = null;
    this.startedAt = null;
    this.latestIterationDuration = null;
    this.mapPlaceholder = document.getElementById('mapPlaceholder');
    this.bindControls();
    document.getElementById('startSimulation').addEventListener('click', () => this.startSimulation());
    this.poll();
    this.loadBenchmark();
    window.setInterval(() => this.poll(), this.pollMs);
    window.addEventListener('resize', () => {
      this.renderedMapKey = null;
      this.render();
      this.renderCharts();
      this.renderBenchmarkCharts();
    });
    this.animationFrame = window.requestAnimationFrame(() => this.animateAnts());
  }

  async loadBenchmark() {
    const status = document.getElementById('benchmarkStatus');
    try {
      const response = await fetch('/api/benchmark', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const text = await response.text();
      const lines = text.trim().split(/\r?\n/);
      if (lines.length < 2) throw new Error('CSV tidak memiliki baris hasil');
      const headers = lines[0].split(',').map(value => value.trim());
      const required = ['Threads', 'Processes', 'Data', 'Time', 'Speedup', 'Efficiency',
        'Throughput', 'Iterations', 'Seed', 'Run ID'];
      if (!required.every(header => headers.includes(header))) throw new Error('Format CSV tidak dikenali');
      this.benchmarkRows = lines.slice(1).filter(Boolean).map(line => {
        const values = line.split(',').map(value => value.trim());
        return Object.fromEntries(headers.map((header, index) => [
          header, header === 'Run ID' ? values[index] : Number(values[index]),
        ]));
      }).filter(row => required.filter(key => key !== 'Run ID')
        .every(key => Number.isFinite(row[key])) && Boolean(row['Run ID']));
      this.renderBenchmarkTable();
      this.renderBenchmarkCharts();
      status.textContent = `${this.benchmarkRows.length} measured configurations · run ${this.benchmarkRows[0]?.['Run ID'] || 'unknown'} · results/benchmark_results.csv`;
    } catch (error) {
      status.textContent = `Benchmark unavailable: ${error.message}`;
      document.getElementById('benchmarkRows').innerHTML =
        '<tr><td colspan="7" class="empty-row">Benchmark CSV tidak tersedia.</td></tr>';
      this.renderBenchmarkCharts();
    }
  }

  renderBenchmarkTable() {
    const tbody = document.getElementById('benchmarkRows');
    if (!this.benchmarkRows.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty-row">Tidak ada konfigurasi benchmark.</td></tr>';
      return;
    }
    const rows = this.benchmarkRows.map(row => {
      const tr = document.createElement('tr');
      const cells = [row.Threads, row.Processes, this.formatNumber(row.Data),
        `${this.formatNumber(row.Time, 4)} s`, `${this.formatNumber(row.Speedup, 3)}×`,
        `${this.formatNumber(row.Efficiency, 2)}%`, `${this.formatNumber(row.Throughput, 2)} ants/s`];
      for (const value of cells) {
        const td = document.createElement('td');
        td.textContent = value;
        tr.appendChild(td);
      }
      return tr;
    });
    tbody.replaceChildren(...rows);
  }

  renderBenchmarkCharts() {
    const hybrid = this.benchmarkRows.filter(row => row.Processes > 1);
    const comparisonSeries = field => {
      const fixedFields = field === 'Threads'
        ? ['Processes', 'Data', 'Iterations', 'Seed', 'Run ID']
        : ['Threads', 'Data', 'Iterations', 'Seed', 'Run ID'];
      const groups = new Map();
      for (const row of hybrid) {
        const key = JSON.stringify(fixedFields.map(name => row[name]));
        if (!groups.has(key)) groups.set(key, { fixedFields, rows: [] });
        groups.get(key).rows.push(row);
      }
      return [...groups.values()].filter(group => new Set(group.rows.map(row => row[field])).size > 1)
        .map(group => ({
          label: group.fixedFields.map(name => {
            const shortName = { Processes: 'P', Threads: 'T', Data: 'D', Iterations: 'I' }[name] || name;
            return `${shortName}${group.rows[0][name]}`;
          }).join('/'),
          points: group.rows.sort((left, right) => left[field] - right[field]).map(row => ({
            category: row[field], label: String(row[field]), value: row.Time,
          })),
        }));
    };
    this.drawBenchmarkChart('benchmarkThreadsChart', comparisonSeries('Threads'), '#2563eb', 's');
    this.drawBenchmarkChart('benchmarkProcessesChart', comparisonSeries('Processes'), '#38bdf8', 's');
    this.drawBenchmarkChart('benchmarkSpeedupChart', [{
      label: 'Speedup',
      points: this.benchmarkRows.map(row => ({
        category: `T${row.Threads}P${row.Processes}D${row.Data}`,
        label: `T${row.Threads}P${row.Processes}D${row.Data}`,
        value: row.Speedup,
      })),
    }], '#16a34a', '×');
  }

  drawBenchmarkChart(canvasId, series, color, unit) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const bounds = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.floor(bounds.width * dpr));
    const height = Math.max(1, Math.floor(bounds.height * dpr));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = dpr;
    for (let index = 1; index <= 3; index++) {
      const y = height * index / 4;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
    }
    const allPoints = series.flatMap(item => item.points);
    if (!allPoints.length) {
      ctx.fillStyle = '#94a3b8'; ctx.font = `${10 * dpr}px system-ui`;
      ctx.fillText('No matched configurations to compare', 8 * dpr, height / 2);
      return;
    }
    const categories = [...new Set(allPoints.map(point => point.category))]
      .sort((left, right) => typeof left === 'number' && typeof right === 'number'
        ? left - right : String(left).localeCompare(String(right)));
    const max = Math.max(...allPoints.map(point => point.value), .001);
    const insetX = 22 * dpr, insetY = 16 * dpr;
    const legendRows = Math.ceil(series.length / 2);
    const plotTop = (8 + legendRows * 11) * dpr;
    const plotBottom = height - insetY;
    const palette = ['#2563eb', '#f97316', '#16a34a', '#a855f7', '#0891b2', '#e11d48'];
    series.forEach((item, seriesIndex) => {
      const stroke = series.length === 1 ? color : palette[seriesIndex % palette.length];
      ctx.beginPath(); ctx.strokeStyle = stroke; ctx.lineWidth = 2 * dpr;
      item.points.forEach((point, pointIndex) => {
        const categoryIndex = categories.indexOf(point.category);
        const x = categories.length === 1 ? width / 2
          : insetX + categoryIndex / (categories.length - 1) * (width - 2 * insetX);
        const y = plotBottom - point.value / max * (plotBottom - plotTop);
        if (pointIndex === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        ctx.fillStyle = stroke; ctx.fillRect(x - 2 * dpr, y - 2 * dpr, 4 * dpr, 4 * dpr);
      });
      ctx.stroke();
      const legendX = (8 + (seriesIndex % 2) * Math.floor(width / (2 * dpr))) * dpr;
      const legendY = (12 + Math.floor(seriesIndex / 2) * 11) * dpr;
      ctx.fillStyle = stroke;
      ctx.fillRect(legendX, legendY - 3 * dpr, 8 * dpr, 2 * dpr);
      ctx.fillStyle = '#64748b'; ctx.font = `${8 * dpr}px system-ui`;
      ctx.fillText(item.label, legendX + 11 * dpr, legendY);
    });
    ctx.fillStyle = '#64748b'; ctx.font = `${8 * dpr}px system-ui`;
    ctx.fillText(`${this.formatNumber(max, 2)}${unit}`, 3 * dpr, 10 * dpr);
    if (categories.length > 1) {
      const first = String(categories[0]);
      const last = String(categories[categories.length - 1]);
      ctx.fillText(first, insetX, height - 1 * dpr);
      ctx.fillText(last, width - ctx.measureText(last).width - insetX, height - 1 * dpr);
    }
  }

  bindControls() {
    for (const key of Object.keys(this.visibility)) {
      const inputs = [document.getElementById(`toggle${key[0].toUpperCase()}${key.slice(1)}`),
        document.getElementById(`control${key[0].toUpperCase()}${key.slice(1)}`)];
      inputs.forEach(input => input.addEventListener('change', () => {
        this.visibility[key] = input.checked;
        inputs.forEach(other => { other.checked = input.checked; });
        this.renderedMapKey = null;
        this.render();
        this.renderAnts();
      }));
    }
  }

  async poll() {
    if (this.pollInFlight) return;
    this.pollInFlight = true;
    try {
      const response = await fetch(this.endpoint, { headers: { Accept: 'application/json' }, cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const state = await response.json();
      if (state.status === 'starting') {
        this.setStatus('connecting', 'INITIALIZING');
        document.getElementById('simulationStatus').className = 'simulation-status starting';
        document.getElementById('simulationStatusText').textContent = 'INITIALIZING';
        document.getElementById('sideStatus').textContent = 'INITIALIZING';
        document.getElementById('startSimulation').hidden = true;
        document.getElementById('progressMessage').textContent = 'Preparing simulation…';
        return;
      }
      if (state.error) throw new Error(state.error);
      const iteration = Number.isFinite(state.iteration) ? state.iteration : state.metrics?.iteration;
      const mapChanged = iteration !== this.lastIteration;
      this.state = state;
      if (mapChanged) this.updateMotion(state);
      this.lastPollAt = performance.now();
      this.setStatus('connected', 'SYSTEM ONLINE');
      document.getElementById('errorSection').hidden = true;
      this.updateMetrics(state);
      this.addSample(state);
      if (mapChanged) this.render();
      if (mapChanged) this.renderCharts();
    } catch (error) {
      this.setStatus('disconnected', 'DISCONNECTED');
      const simulationStatus = document.getElementById('simulationStatus');
      simulationStatus.className = 'simulation-status disconnected';
      document.getElementById('simulationStatusText').textContent = 'DISCONNECTED';
      document.getElementById('sideStatus').textContent = 'DISCONNECTED';
      document.getElementById('startSimulation').hidden = true;
      document.getElementById('progressMessage').textContent = 'Backend disconnected';
      document.getElementById('errorSection').hidden = false;
      document.getElementById('errorMessage').textContent = error.message;
    } finally {
      this.pollInFlight = false;
    }
  }

  setStatus(status, text) {
    const node = document.getElementById('statusIndicator');
    node.className = `connection-badge ${status}`;
    node.querySelector('.status-text').textContent = text;
  }

  async startSimulation() {
    const button = document.getElementById('startSimulation');
    const message = document.getElementById('controlMessage');
    button.disabled = true;
    message.textContent = 'Mengirim perintah start…';
    try {
      const response = await fetch('/api/control/start', {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
      });
      const result = await response.json();
      if (!response.ok || !result.accepted) throw new Error(result.message || `HTTP ${response.status}`);
      message.textContent = 'Start diterima. Menyiapkan simulasi hybrid…';
      document.getElementById('progressMessage').textContent = 'Initializing simulation…';
      button.hidden = true;
      this.setStatus('connecting', 'STARTING');
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false;
    }
  }

  formatNumber(value, digits = 0) {
    return Number.isFinite(value) ? value.toLocaleString('en-US', {
      minimumFractionDigits: digits, maximumFractionDigits: digits
    }) : 'N/A';
  }

  updateMetrics(state) {
    const metrics = state.metrics || {};
    const performance = state.performance || {};
    const iteration = Number.isFinite(state.iteration) ? state.iteration : metrics.iteration;
    const totalIterations = state.simulation?.total_iterations;
    const status = state.status || 'ready';
    const statusNode = document.getElementById('simulationStatus');
    const statusLabel = status.toUpperCase();
    statusNode.className = `simulation-status ${status}`;
    document.getElementById('simulationStatusText').textContent = statusLabel;
    const startButton = document.getElementById('startSimulation');
    startButton.hidden = status !== 'ready';
    startButton.disabled = false;
    const sideStatus = document.getElementById('sideStatus');
    if (sideStatus) sideStatus.textContent = status === 'ready' ? 'SYSTEM READY' : statusLabel;
    document.getElementById('progressMessage').textContent = status === 'ready'
      ? 'Waiting for simulation…'
      : status === 'running' ? 'Hybrid simulation is running.'
        : status === 'completed' ? 'Simulation complete.'
          : status === 'starting' ? 'Initializing world…' : statusLabel;
    const startMessage = status === 'ready' ? 'Ready to start.'
      : status === 'running' ? 'Simulation is running.'
        : status === 'completed' ? 'Simulation complete.' : statusLabel;
    document.getElementById('controlMessage').textContent = startMessage;
    document.getElementById('iterationTotal').textContent = Number.isFinite(totalIterations)
      ? ` / ${this.formatNumber(totalIterations)}` : ' / N/A';
    const progress = Number.isFinite(totalIterations) && totalIterations > 0 && Number.isFinite(iteration)
      ? Math.max(0, Math.min(100, iteration / totalIterations * 100)) : null;
    document.getElementById('progressFill').style.width = progress === null ? '0%' : `${progress}%`;
    if (!this.startedAt && state.performance?.started_at) this.startedAt = state.performance.started_at;
    const started = state.performance?.started_at || this.startedAt;
    document.getElementById('startedAt').textContent = started
      ? new Date(started).toLocaleTimeString() : 'N/A';
    const elapsed = state.performance?.execution_time_seconds;
    document.getElementById('elapsedClock').textContent = Number.isFinite(elapsed) ? this.formatClock(elapsed) : 'N/A';
    const iterationDuration = state.performance?.iteration_time_seconds;
    if (Number.isFinite(iterationDuration)) this.latestIterationDuration = iterationDuration;
    document.getElementById('iterationTime').textContent = Number.isFinite(this.latestIterationDuration)
      ? `${this.formatNumber(this.latestIterationDuration, 3)} s` : 'N/A';
    const ids = {
      iteration: this.formatNumber(iteration),
      statIteration: this.formatNumber(iteration),
      antCount: Array.isArray(state.ants) ? this.formatNumber(state.ants.length) : 'N/A',
      foodRemaining: this.formatNumber(metrics.food_remaining),
      foodCollected: this.formatNumber(metrics.food_collected),
      telemetryFood: this.formatNumber(metrics.food_collected),
      searchingCount: this.formatNumber((state.ants || []).filter(ant => ant.behavior === 'searching').length),
      returningCount: this.formatNumber((state.ants || []).filter(ant => ant.behavior === 'returning').length),
      atFoodCount: this.formatNumber((state.ants || []).filter(ant => ant.behavior === 'at_food').length),
      averagePath: this.formatNumber(performance.average_path_length ?? metrics.average_path_length, 1),
      bestPath: this.formatNumber(performance.best_path_length ?? metrics.best_path_length, 1),
      threads: Number.isFinite(performance.threads) ? `${performance.threads} workers` : 'N/A',
      processes: Number.isFinite(performance.processes) ? `${performance.processes} workers` : 'N/A',
      configuredAnts: Number.isFinite(state.ants?.length) ? `${this.formatNumber(state.ants.length)} ants` : 'N/A',
      seedValue: Number.isFinite(state.seed) ? this.formatNumber(state.seed) : 'N/A',
      totalTime: Number.isFinite(performance.execution_time_seconds) ? `${this.formatNumber(performance.execution_time_seconds, 2)} s` : 'N/A',
      throughput: Number.isFinite(performance.throughput) ? `${this.formatNumber(performance.throughput, 1)} ants/s` : 'N/A',
      speedup: Number.isFinite(performance.speedup) ? `${this.formatNumber(performance.speedup, 2)}×` : 'N/A',
      efficiency: Number.isFinite(performance.efficiency_percent) ? `${this.formatNumber(performance.efficiency_percent, 1)}%` : 'N/A',
      avgPheromone: this.formatNumber(metrics.avg_pheromone, 3),
      maxPheromone: this.formatNumber(metrics.max_pheromone, 3),
    };
    for (const [id, value] of Object.entries(ids)) document.getElementById(id).textContent = value;
    document.getElementById('mode').textContent = performance.mode || 'HYBRID';
    document.getElementById('headerMode').textContent = performance.mode || 'HYBRID';
    document.getElementById('perfTime').textContent = ids.totalTime;
    document.getElementById('perfSpeedup').textContent = ids.speedup;
    document.getElementById('perfEfficiency').textContent = ids.efficiency;
    document.getElementById('perfThroughput').textContent = ids.throughput;
    const completedAt = performance.completed_at;
    document.getElementById('completedAt').textContent = completedAt
      ? new Date(completedAt).toLocaleTimeString() : 'N/A';
  }

  addSample(state) {
    const iteration = Number.isFinite(state.iteration) ? state.iteration : state.metrics?.iteration;
    if (!Number.isFinite(iteration) || iteration === this.lastIteration) return;
    this.lastIteration = iteration;
    const performance = state.performance || {};
    this.samples.push({
      time: performance.execution_time_seconds,
      speedup: performance.speedup,
      food: state.metrics?.food_collected,
    });
    if (this.samples.length > 90) this.samples.shift();
  }

  formatClock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const hh = String(Math.floor(total / 3600)).padStart(2, '0');
    const mm = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
    const ss = String(total % 60).padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
  }

  updateMotion(state) {
    if (!Array.isArray(state.ants)) return;
    const now = performance.now();
    const duration = Math.max(120, Math.min(650, (now - (this.lastPollAt || now)) * 1.8));
    const next = new Map();
    for (const ant of state.ants) {
      if (!Array.isArray(ant.position)) continue;
      const [x, y] = ant.position;
      const previous = this.previousAnts.get(ant.id) || { x, y };
      const dx = x - previous.x;
      const dy = y - previous.y;
      this.antMotion.set(ant.id, {
        fromX: previous.x, fromY: previous.y, x, y,
        angle: dx || dy ? Math.atan2(dy, dx) : (this.antMotion.get(ant.id)?.angle || 0),
        start: now, duration,
        hasFood: ant.has_food,
        behavior: ant.behavior || (ant.has_food ? 'returning' : 'searching'),
      });
      next.set(ant.id, { x, y });
    }
    this.previousAnts = next;
  }

  render() {
    const state = this.state;
    const world = state?.world;
    if (!world?.width || !world?.height || !this.ctx) return;
    this.mapPlaceholder.hidden = true;
    const bounds = this.canvas.parentElement.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.floor(bounds.width * dpr));
    const height = Math.max(1, Math.floor(bounds.height * dpr));
    const dimensionsChanged = this.canvas.width !== width || this.canvas.height !== height;
    if (dimensionsChanged) {
      this.canvas.width = width;
      this.canvas.height = height;
      this.worldLayer.width = width;
      this.worldLayer.height = height;
    }
    const iteration = Number.isFinite(state.iteration) ? state.iteration : state.metrics?.iteration;
    const mapKey = `${iteration}:${width}:${height}:${this.visibility.pheromone}:${this.visibility.obstacles}`;
    if (!dimensionsChanged && mapKey === this.renderedMapKey) return;
    this.renderedMapKey = mapKey;
    const ctx = this.worldLayerCtx;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, width, height);
    const cell = Math.min(width / world.width, height / world.height);
    const offsetX = (width - cell * world.width) / 2;
    const offsetY = (height - cell * world.height) / 2;
    const xAt = x => offsetX + x * cell;
    const yAt = y => offsetY + y * cell;

    if (this.visibility.pheromone && Array.isArray(world.pheromone_grid)) {
      this.drawPheromoneTrail(ctx, world.pheromone_grid, width, height, cell, offsetX, offsetY, world);
    }

    // A subtle grid makes cell scale legible without overpowering trails and ants.
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = Math.max(.45, dpr * .28);
    for (let x = 0; x <= world.width; x += 10) {
      ctx.beginPath(); ctx.moveTo(xAt(x), offsetY); ctx.lineTo(xAt(x), offsetY + cell * world.height); ctx.stroke();
    }
    for (let y = 0; y <= world.height; y += 10) {
      ctx.beginPath(); ctx.moveTo(offsetX, yAt(y)); ctx.lineTo(offsetX + cell * world.width, yAt(y)); ctx.stroke();
    }

    if (this.visibility.obstacles && Array.isArray(world.obstacle_grid)) {
      for (let y = 0; y < world.height; y++) for (let x = 0; x < world.width; x++) {
        if (world.obstacle_grid[y]?.[x]) {
          this.drawRock(ctx, xAt(x) + cell / 2, yAt(y) + cell / 2, cell * .42);
        }
      }
    }

    if (Array.isArray(world.food_grid)) {
      for (let y = 0; y < world.height; y++) for (let x = 0; x < world.width; x++) {
        const amount = world.food_grid[y]?.[x] || 0;
        if (amount <= 0) continue;
        this.drawFoodCluster(ctx, xAt(x) + cell / 2, yAt(y) + cell / 2, cell,
          Math.max(1, Math.ceil(amount / 30)));
      }
    }

    const nest = world.nest_position;
    if (Array.isArray(nest)) {
      const cx = xAt(nest[0]) + cell / 2;
      const cy = yAt(nest[1]) + cell / 2;
      this.drawNest(ctx, cx, cy, cell);
    }

    this.ctx.clearRect(0, 0, width, height);
    this.ctx.drawImage(this.worldLayer, 0, 0);
    this.renderAnts();
  }

  drawPheromoneTrail(ctx, grid, width, height, cell, offsetX, offsetY, world) {
    const iteration = Number.isFinite(this.state?.iteration) ? this.state.iteration : this.state?.metrics?.iteration;
    const cacheKey = `${iteration}:${world.width}:${world.height}`;
    if (cacheKey !== this.pheromoneCacheKey) {
      const field = this.pheromoneCanvas;
      field.width = world.width;
      field.height = world.height;
      const fctx = this.pheromoneContext;
      const image = fctx.createImageData(world.width, world.height);
      let max = 0;
      for (const row of grid) for (const value of row) if (value > max) max = value;
      if (max > 0) {
        for (let y = 0; y < world.height; y++) for (let x = 0; x < world.width; x++) {
          const value = grid[y]?.[x] || 0;
          if (value <= 0) continue;
          const intensity = Math.pow(Math.min(1, value / max), .58);
          const index = (y * world.width + x) * 4;
          const color = intensity < .3 ? [219, 234, 254]
            : intensity < .65 ? [96, 165, 250]
              : intensity < .9 ? [37, 99, 235] : [29, 78, 216];
          image.data[index] = color[0];
          image.data[index + 1] = color[1];
          image.data[index + 2] = color[2];
          image.data[index + 3] = Math.round(20 + intensity * 150);
        }
      }
      fctx.putImageData(image, 0, 0);
      this.pheromoneCacheKey = cacheKey;
    }
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.drawImage(this.pheromoneCanvas, offsetX, offsetY, cell * world.width, cell * world.height);
    ctx.restore();
  }

  drawRock(ctx, x, y, radius) {
    ctx.save();
    const gradient = ctx.createLinearGradient(x - radius, y - radius, x + radius, y + radius);
    gradient.addColorStop(0, '#cbd5e1'); gradient.addColorStop(.5, '#94a3b8'); gradient.addColorStop(1, '#64748b');
    ctx.fillStyle = gradient; ctx.strokeStyle = '#64748b'; ctx.lineWidth = Math.max(.6, radius * .12);
    ctx.beginPath(); ctx.moveTo(x - radius, y - radius * .25); ctx.lineTo(x - radius * .45, y - radius * .9);
    ctx.lineTo(x + radius * .42, y - radius * .78); ctx.lineTo(x + radius, y - radius * .1);
    ctx.lineTo(x + radius * .69, y + radius * .73); ctx.lineTo(x - radius * .4, y + radius * .84);
    ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.restore();
  }

  drawFoodCluster(ctx, x, y, cell, amount) {
    const radius = cell * .16;
    ctx.save();
    const offsets = [[0, 0], [-.22, -.14], [.23, -.16], [-.19, .2], [.22, .2], [0, -.3], [0, .31]];
    offsets.slice(0, Math.min(offsets.length, amount)).forEach(([dx, dy], index) => {
      ctx.beginPath(); ctx.fillStyle = index % 2 ? '#16a34a' : '#4ade80';
      ctx.arc(x + dx * cell, y + dy * cell, radius * (index ? .84 : 1.12), 0, Math.PI * 2); ctx.fill();
    });
    ctx.restore();
  }

  drawNest(ctx, x, y, cell) {
    ctx.save();
    ctx.fillStyle = 'rgba(234,179,8,.14)'; ctx.beginPath(); ctx.arc(x, y, cell * 2, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#facc15'; ctx.strokeStyle = '#ca8a04'; ctx.lineWidth = Math.max(1, cell * .12);
    ctx.beginPath(); ctx.ellipse(x, y + cell * .12, cell * 1.7, cell * .9, 0, Math.PI, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#eab308'; ctx.beginPath(); ctx.arc(x, y - cell * .13, cell * .34, 0, Math.PI * 2); ctx.fill();
    ctx.font = `600 ${Math.max(8, cell * .8)}px Manrope, sans-serif`; ctx.textAlign = 'center';
    ctx.fillStyle = '#854d0e'; ctx.fillText('NEST', x, y + cell * 1.65);
    ctx.restore();
  }

  drawAntLayer(cell, dpr, offsetX, offsetY, world) {
    const ctx = this.ctx;
    if (!ctx) return;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.drawImage(this.worldLayer, 0, 0);
    if (!this.visibility.ants) return;
    if (!this.antSprites) this.antSprites = this.createAntSprites();
    const cellPx = Math.min(this.canvas.width / world.width, this.canvas.height / world.height);
    const ox = (this.canvas.width - cellPx * world.width) / 2;
    const oy = (this.canvas.height - cellPx * world.height) / 2;
    const now = performance.now();
    for (const ant of (this.state?.ants || [])) {
      const motion = this.antMotion.get(ant.id);
      if (!motion) continue;
      const t = Math.min(1, (now - motion.start) / motion.duration);
      const eased = t * t * (3 - 2 * t);
      const x = motion.fromX + (motion.x - motion.fromX) * eased;
      const y = motion.fromY + (motion.y - motion.fromY) * eased;
      const cx = ox + (x + .5) * cellPx;
      const cy = oy + (y + .5) * cellPx;
      const bob = Math.sin(now / 230 + Number(ant.id) * .37) * cellPx * .018;
      const sprite = motion.hasFood ? this.antSprites.returning : this.antSprites.searching;
      const spriteScale = Math.max(.34, Math.min(.58, cellPx / 19));
      const cos = Math.cos(motion.angle) * spriteScale;
      const sin = Math.sin(motion.angle) * spriteScale;
      ctx.setTransform(cos, sin, -sin, cos, cx, cy + bob);
      ctx.drawImage(sprite, -sprite.width / 2, -sprite.height / 2);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  renderAnts() {
    if (!this.state?.world) return;
    this.drawAntLayer(1, window.devicePixelRatio || 1, 0, 0, this.state.world);
  }

  createAntSprites() {
    const create = (headColor) => {
      const sprite = document.createElement('canvas');
      sprite.width = 28;
      sprite.height = 18;
      const ctx = sprite.getContext('2d');
      ctx.lineWidth = 1.35;
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#c2410c';
      // Bake anatomy once; each live ant frame only draws and rotates one image.
      for (let pair = 0; pair < 3; pair++) {
        const legX = 7 + pair * 5;
        for (const side of [-1, 1]) {
          ctx.beginPath();
          ctx.moveTo(legX, 9 + side);
          ctx.lineTo(legX - 2, 9 + side * 5);
          ctx.lineTo(legX - 4, 9 + side * 7);
          ctx.stroke();
        }
      }
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(20, 7); ctx.quadraticCurveTo(24, 2, 27, 3);
      ctx.moveTo(20, 11); ctx.quadraticCurveTo(24, 16, 27, 15);
      ctx.stroke();
      ctx.fillStyle = '#f97316';
      ctx.beginPath(); ctx.ellipse(8, 9, 5, 3.7, 0, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(15, 9, 2.6, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = headColor;
      ctx.beginPath(); ctx.arc(20, 9, 3.3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff0dc';
      ctx.beginPath(); ctx.arc(21, 8, .65, 0, Math.PI * 2); ctx.fill();
      return sprite;
    };
    return { searching: create('#f97316'), returning: create('#38bdf8') };
  }

  drawAnt(ctx, x, y, angle, scale, hasFood, phase, behavior) {
    const size = scale;
    const legSwing = Math.sin(phase * 2.1) * 1.4 * size;
    ctx.save(); ctx.translate(x, y); ctx.rotate(angle);
    ctx.shadowColor = hasFood ? 'rgba(65,216,237,.55)' : 'rgba(255,140,92,.38)';
    ctx.shadowBlur = 4 * size;
    ctx.strokeStyle = '#ffd0aa'; ctx.lineWidth = Math.max(.8, 1.05 * size); ctx.lineCap = 'round';
    // Three pairs of articulated legs, gently stepping while the ant advances.
    for (let i = 0; i < 3; i++) {
      const lx = (i - 1) * 2.2 * size;
      const swing = legSwing * (i % 2 ? -1 : 1);
      for (const side of [-1, 1]) {
        ctx.beginPath(); ctx.moveTo(lx, side * .7 * size);
        ctx.lineTo(lx + swing, side * 2.0 * size);
        ctx.lineTo(lx + swing * 1.8, side * 3.0 * size); ctx.stroke();
      }
    }
    // Antennae point from the head (front is +X).
    ctx.beginPath(); ctx.moveTo(3.7 * size, -.6 * size); ctx.quadraticCurveTo(5.2 * size, -2.3 * size, 6.0 * size, -2.0 * size);
    ctx.moveTo(3.7 * size, .6 * size); ctx.quadraticCurveTo(5.2 * size, 2.3 * size, 6.0 * size, 2.0 * size); ctx.stroke();
    ctx.fillStyle = '#46252b';
    ctx.beginPath(); ctx.ellipse(-2.3 * size, 0, 2.7 * size, 2.05 * size, 0, 0, Math.PI * 2); ctx.fill(); // abdomen
    ctx.beginPath(); ctx.arc(0.7 * size, 0, 1.45 * size, 0, Math.PI * 2); ctx.fill(); // thorax
    const headColor = behavior === 'at_food' ? '#79e4a5'
      : behavior === 'at_nest' ? '#63a8ff'
        : behavior === 'following_pheromone' ? '#ffc75c'
          : hasFood ? '#58d9e5' : '#ff9867';
    ctx.fillStyle = headColor;
    ctx.beginPath(); ctx.arc(3.4 * size, 0, 1.75 * size, 0, Math.PI * 2); ctx.fill(); // head
    ctx.fillStyle = '#fff0dc'; ctx.beginPath(); ctx.arc(4.05 * size, -.55 * size, .33 * size, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  animateAnts() {
    const now = performance.now();
    // 12.5 fps is enough for interpolation, while keeping the 1,390-agent layer light.
    if (document.visibilityState === 'visible' && this.state?.world && now - this.lastAntFrameAt >= 50) {
      this.lastAntFrameAt = now;
      this.drawAntLayer(1, window.devicePixelRatio || 1, 0, 0, this.state.world);
    }
    this.animationFrame = window.requestAnimationFrame(() => this.animateAnts());
  }

  renderCharts() {
    this.drawChart('timeChart', 'time', '#41d8ed', 's');
    this.drawChart('speedChart', 'speedup', '#b48aff', '×');
    this.drawChart('foodChart', 'food', '#79e4a5', '');
  }

  drawChart(canvasId, key, color, unit) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const box = canvas.getBoundingClientRect();
    const chartWidth = Math.max(1, Math.floor(box.width * dpr));
    const chartHeight = Math.max(1, Math.floor(box.height * dpr));
    if (canvas.width !== chartWidth || canvas.height !== chartHeight) {
      canvas.width = chartWidth;
      canvas.height = chartHeight;
    }
    const width = canvas.width, height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(158,178,205,.11)'; ctx.lineWidth = 1;
    for (let i = 1; i <= 3; i++) { const y = height * i / 4; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke(); }
    if (this.samples.length < 2) {
      ctx.fillStyle = '#8493a7'; ctx.font = `${12 * dpr}px Manrope, sans-serif`;
      ctx.fillText('Menunggu data historis…', 10 * dpr, height / 2);
      return;
    }
    const values = this.samples.map(sample => sample[key]);
    const finite = values.filter(Number.isFinite);
    if (finite.length < 2) {
      ctx.fillStyle = '#8493a7'; ctx.font = `${11 * dpr}px Manrope, sans-serif`;
      ctx.fillText(`Data ${key} belum tersedia`, 10 * dpr, height / 2); return;
    }
    const min = Math.min(0, ...finite), max = Math.max(...finite, min + .0001);
    ctx.fillStyle = '#7c8da3'; ctx.font = `${8 * dpr}px "DM Mono", monospace`;
    ctx.fillText(`${max.toFixed(2)}${unit}`, 2 * dpr, 10 * dpr);
    ctx.fillText(`${min.toFixed(2)}${unit}`, 2 * dpr, height - 2 * dpr);
    ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = 2 * dpr; ctx.lineJoin = 'round';
    let started = false;
    values.forEach((value, index) => {
      if (!Number.isFinite(value)) { started = false; return; }
      const x = index / Math.max(1, values.length - 1) * width;
      const y = height - 10 * dpr - ((value - min) / (max - min)) * (height - 22 * dpr);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

document.addEventListener('DOMContentLoaded', () => { window.antWorldDashboard = new AntWorldDashboard(); });
