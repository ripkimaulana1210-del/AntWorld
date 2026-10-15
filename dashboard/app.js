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
    this.pendingAction = null;
    this.activitySignature = '';
    this.lastStatus = null;
    this.mapPlaceholder = document.getElementById('mapPlaceholder');
    this.bindControls();
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
      this.bindBenchmarkTooltips();
      status.textContent = `${this.benchmarkRows.length} measured configurations · run ${this.benchmarkRows[0]?.['Run ID'] || 'unknown'} · results/benchmark_results.csv`;
    } catch (error) {
      status.textContent = `Benchmark unavailable: ${error.message}`;
      document.getElementById('benchmarkRows').innerHTML =
        '<tr><td colspan="7" class="empty-row">Benchmark CSV tidak tersedia.</td></tr>';
      this.renderBenchmarkCharts();
      this.bindBenchmarkTooltips();
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

  /**
   * Build the three benchmark comparison datasets from the measured CSV rows.
   *
   * Grouping rule: a "series" is a set of hybrid rows that share every field
   * except the one being varied. Only series that actually vary are kept, so a
   * line never connects two configurations that are not on the same experiment
   * group. This is what makes Time vs Threads and Time vs Processes honest.
   */
  buildBenchmarkModel() {
    const hybrid = this.benchmarkRows.filter(row => row.Processes > 1);
    const groupingFields = {
      Threads: ['Processes', 'Data', 'Iterations', 'Seed'],
      Processes: ['Threads', 'Data', 'Iterations', 'Seed'],
    };
    const shortName = { Threads: 'T', Processes: 'P', Data: 'ants', Seed: 'seed' };

    const seriesFor = field => {
      const fixed = groupingFields[field];
      const groups = new Map();
      for (const row of hybrid) {
        const key = JSON.stringify(fixed.map(name => row[name]));
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(row);
      }
      return [...groups.values()]
        .filter(rows => new Set(rows.map(row => row[field])).size > 1)
        .map(rows => {
          const sorted = rows.slice().sort((a, b) => a[field] - b[field]);
          const head = sorted[0];
          // Compact legend: only the fields needed to tell the lines apart.
          const detail = fixed.filter(name => name !== 'Seed' && name !== 'Iterations')
            .map(name => `${shortName[name]}=${name === 'Data' ? this.formatNumber(head[name]) : head[name]}`)
            .join(' · ');
          return {
            label: `${detail}${fixed.includes('Iterations') ? ` · it=${head.Iterations}` : ''}`,
            seed: head.Seed,
            points: sorted.map(row => ({
              category: row[field],
              value: row.Time,
              detail: { field, varied: row[field], row },
            })),
          };
        });
    };

    // Configuration axis: one bar per (threads, processes, ants) at a fixed workload.
    const configurations = [];
    const seenConfig = new Set();
    for (const row of hybrid) {
      const key = `T${row.Threads}P${row.Processes}D${row.Data}`;
      if (seenConfig.has(key)) continue;
      seenConfig.add(key);
      configurations.push({
        label: `T${row.Threads}·P${row.Processes}·${this.formatNumber(row.Data)}`,
        value: row.Speedup,
        detail: { row },
      });
    }
    configurations.sort((a, b) => a.detail.row.Data - b.detail.row.Data
      || a.detail.row.Threads - b.detail.row.Threads
      || a.detail.row.Processes - b.detail.row.Processes);

    // Baseline reference: serial rows are measured with Processes=1 and Speedup 1.0.
    const serials = this.benchmarkRows.filter(row => row.Processes === 1);
    const baseline = {
      value: 1,
      label: 'serial 1×',
      measured: serials.length > 0,
    };

    return {
      threads: seriesFor('Threads'),
      processes: seriesFor('Processes'),
      speedup: {
        bars: configurations.map((item, index) => ({ ...item, index })),
        baseline,
        slowCount: configurations.filter(item => item.value < 1).length,
        fastCount: configurations.filter(item => item.value >= 1).length,
      },
    };
  }

  renderBenchmarkCharts() {
    const model = this.buildBenchmarkModel();
    this.drawLineChart('benchmarkThreadsChart', model.threads, {
      unit: 's', axisLabel: 'threads (I/O workers)',
      empty: 'No matched configurations to compare',
    });
    this.drawLineChart('benchmarkProcessesChart', model.processes, {
      unit: 's', axisLabel: 'processes (CPU workers)',
      empty: 'No matched configurations to compare',
    });
    this.drawSpeedupChart('benchmarkSpeedupChart', model.speedup);
    // Snapshot the finished charts so tooltips can be shown/hidden without a redraw.
    for (const id of ['benchmarkThreadsChart', 'benchmarkProcessesChart', 'benchmarkSpeedupChart']) {
      const canvas = document.getElementById(id);
      if (canvas) this.captureBenchmarkBase(canvas);
    }
  }

  /** Shared canvas setup: DPR-aware sizing plus the inset reserved for axes. */
  prepareBenchmarkCanvas(canvas) {
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
    ctx.textBaseline = 'middle';
    return { ctx, dpr, width, height };
  }

  drawChartGrid(ctx, dpr, plot, ticks) {
    ctx.strokeStyle = '#eef2f7';
    ctx.lineWidth = 1 * dpr;
    ctx.fillStyle = '#94a3b8';
    ctx.font = `${8.5 * dpr}px ${getComputedStyle(document.body).fontFamily}`;
    ctx.textAlign = 'right';
    for (const tick of ticks) {
      const y = Math.round(tick.y) + .5 * dpr;
      ctx.beginPath();
      ctx.moveTo(plot.left, y);
      ctx.lineTo(plot.right, y);
      ctx.stroke();
      ctx.fillText(tick.label, plot.left - 5 * dpr, y);
    }
    ctx.textAlign = 'left';
  }

  /**
   * Time-vs-<field> line chart.
   *
   * Legend labels used to embed seed and Run ID, producing 59-character entries
   * that overflowed the 2-column legend and collided with the plot. Long
   * metadata now lives only in the tooltip.
   */
  drawLineChart(canvasId, series, options) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const { ctx, dpr, width, height } = this.prepareBenchmarkCanvas(canvas);
    const emptyMessage = options.empty || 'No data';
    const points = series.flatMap(item => item.points);

    ctx.fillStyle = '#0f172a';
    ctx.font = `600 ${10 * dpr}px ${getComputedStyle(document.body).fontFamily}`;
    ctx.textAlign = 'left';
    ctx.fillText(series.length === 1 ? series[0].label : `${series.length} experiment groups`, 8 * dpr, 10 * dpr);

    if (!points.length) {
      canvas.__antHitboxes = [];
      canvas.__antTooltip = null;
      ctx.fillStyle = '#94a3b8';
      ctx.font = `${9.5 * dpr}px ${getComputedStyle(document.body).fontFamily}`;
      ctx.textAlign = 'left';
      ctx.fillText(emptyMessage, 8 * dpr, height / 2);
      return;
    }

    const categories = [...new Set(points.map(point => point.category))]
      .sort((a, b) => a - b);
    const values = points.map(point => point.value).filter(Number.isFinite);
    const maxValue = Math.max(...values, 0.001);
    const ticks = [maxValue, maxValue / 2, 0].map(value => ({ value, label: `${this.formatNumber(value, 2)}${options.unit}` }));
    const legendLines = Math.min(series.length, 3);

    const plot = {
      left: 42 * dpr,
      right: width - 8 * dpr,
      // legend occupies 20 + n*11 px; add a 12 px gap so lines never touch it
      top: (20 + legendLines * 11 + 12) * dpr,
      bottom: height - 22 * dpr,
    };
    plot.bottom = Math.max(plot.bottom, plot.top + 24 * dpr);

    this.drawChartGrid(ctx, dpr, plot, ticks.map(tick => ({
      y: plot.bottom - tick.value / maxValue * (plot.bottom - plot.top),
      label: tick.label,
    })));

    const xAt = category => categories.length === 1
      ? (plot.left + plot.right) / 2
      : plot.left + categories.indexOf(category) / (categories.length - 1) * (plot.right - plot.left);
    const yAt = value => plot.bottom - value / maxValue * (plot.bottom - plot.top);
    const palette = ['#2563eb', '#f97316', '#16a34a', '#a855f7', '#0891b2', '#e11d48'];

    // --- legend (stacked full-width rows so long labels never collide) ---
    ctx.font = `${8.5 * dpr}px ${getComputedStyle(document.body).fontFamily}`;
    const legendTop = 20 * dpr;
    series.forEach((item, index) => {
      const color = palette[index % palette.length];
      const y = legendTop + index * 11 * dpr;
      ctx.fillStyle = color;
      ctx.fillRect(8 * dpr, y - 1.5 * dpr, 9 * dpr, 3 * dpr);
      ctx.fillStyle = '#475569';
      ctx.textAlign = 'left';
      ctx.fillText(this.ellipsize(ctx, item.label, width - 30 * dpr), 21 * dpr, y);
    });

    // --- lines + points ---
    const hitboxes = [];
    series.forEach((item, seriesIndex) => {
      const color = palette[seriesIndex % palette.length];
      ctx.strokeStyle = color;
      ctx.lineWidth = 2 * dpr;
      ctx.lineJoin = 'round';
      ctx.beginPath();
      item.points.forEach((point, pointIndex) => {
        const x = xAt(point.category);
        const y = yAt(point.value);
        if (pointIndex === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
      item.points.forEach(point => {
        const x = xAt(point.category);
        const y = yAt(point.value);
        ctx.fillStyle = '#fff';
        ctx.beginPath(); ctx.arc(x, y, 3.1 * dpr, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(x, y, 2 * dpr, 0, Math.PI * 2); ctx.fill();
        hitboxes.push({
          cx: x, cy: y, r: 7 * dpr,
          title: `T${point.detail.row.Threads} · P${point.detail.row.Processes} · ${this.formatNumber(point.detail.row.Data)} ants`,
          lines: [
            `Execution time: ${this.formatNumber(point.detail.row.Time, 4)} s`,
            `Speedup: ${this.formatNumber(point.detail.row.Speedup, 4)}×`,
            `Efficiency: ${this.formatNumber(point.detail.row.Efficiency, 2)}%`,
            `Throughput: ${this.formatNumber(point.detail.row.Throughput, 2)} ants/s`,
            `Seed ${point.detail.row.Seed} · ${point.detail.row.Iterations} it`,
            `Run ${point.detail.row['Run ID']}`,
          ],
        });
      });
    });

    // --- axes ---
    ctx.fillStyle = '#64748b';
    ctx.font = `${8.5 * dpr}px ${getComputedStyle(document.body).fontFamily}`;
    ctx.textAlign = 'center';
    categories.forEach(category => {
      ctx.fillText(String(category), xAt(category), height - 12 * dpr);
    });
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(options.axisLabel, (plot.left + plot.right) / 2, height - 2 * dpr);

    // --- x axis rules (kept off the text baseline zone) ---
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1 * dpr;
    ctx.beginPath();
    ctx.moveTo(plot.left, plot.bottom + .5 * dpr);
    ctx.lineTo(plot.right, plot.bottom + .5 * dpr);
    ctx.stroke();

    canvas.__antHitboxes = hitboxes;
  }

  /**
   * Speedup-vs-configuration bar chart.
   *
   * Previously this was a line chart over 36 configurations in CSV order, which
   * connected serial (Processes=1, speedup 1.0) and hybrid rows into one
   * zig-zag and made the comparison unreadable. Bars keyed on
   * threads/processes/ants with a 1× baseline make it legible.
   */
  drawSpeedupChart(canvasId, model) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const { ctx, dpr, width, height } = this.prepareBenchmarkCanvas(canvas);
    const bars = model.bars || [];
    canvas.__antHitboxes = [];
    canvas.__antTooltip = null;

    const font = getComputedStyle(document.body).fontFamily;
    ctx.textAlign = 'left';
    ctx.fillStyle = '#0f172a';
    ctx.font = `600 ${10 * dpr}px ${font}`;
    ctx.fillText('Speedup vs configuration', 8 * dpr, 10 * dpr);
    if (model.baseline.measured) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = `${8 * dpr}px ${font}`;
      ctx.fillText('measured hybrid runs · dashed line = measured serial baseline', 8 * dpr, 22 * dpr);
    }

    if (!bars.length) {
      ctx.fillStyle = '#94a3b8';
      ctx.font = `${9.5 * dpr}px ${font}`;
      ctx.fillText('No hybrid configurations measured', 8 * dpr, height / 2);
      return;
    }

    const plot = { left: 42 * dpr, right: width - 8 * dpr, top: 36 * dpr, bottom: height - 26 * dpr };
    plot.bottom = Math.max(plot.bottom, plot.top + 30 * dpr);

    const maxValue = Math.max(...bars.map(bar => bar.value), model.baseline.value + 0.2);
    const minValue = Math.min(...bars.map(bar => bar.value), 0);
    const span = Math.max(maxValue - minValue, 0.2);
    const yAt = value => plot.bottom - (value - minValue) / span * (plot.bottom - plot.top);

    const ticks = [maxValue, (maxValue + minValue) / 2, minValue];
    this.drawChartGrid(ctx, dpr, plot, ticks.map(value => ({ y: yAt(value), label: `${this.formatNumber(value, 2)}×` })));

    // --- bars ---
    const slot = (plot.right - plot.left) / bars.length;
    const barWidth = Math.max(4 * dpr, Math.min(slot * 0.62, 26 * dpr));
    const baselineY = yAt(model.baseline.value);
    const hitboxes = [];
    bars.forEach(bar => {
      const center = plot.left + slot * (bar.index + 0.5);
      const valueY = yAt(bar.value);
      const top = Math.min(valueY, baselineY);
      const bottom = Math.max(valueY, baselineY);
      const heightPx = Math.max(1.5 * dpr, bottom - top);
      const slow = bar.value < model.baseline.value;
      ctx.fillStyle = slow ? '#dc2626' : '#2563eb';
      ctx.globalAlpha = slow ? 0.9 : 0.86;
      ctx.fillRect(center - barWidth / 2, top, barWidth, heightPx);
      ctx.globalAlpha = 1;
      // value label above fast bars, below slow bars, so it never sits on the baseline;
      // clamped inside the plot so the outermost bar cannot push text off the canvas
      ctx.fillStyle = slow ? '#b91c1c' : '#1d4ed8';
      ctx.font = `${8 * dpr}px ${font}`;
      ctx.textAlign = 'center';
      const halfLabel = ctx.measureText(`${this.formatNumber(bar.value, 3)}×`).width / 2;
      const labelX = Math.max(plot.left + halfLabel, Math.min(plot.right - halfLabel, center));
      const labelY = slow
        ? Math.min(plot.bottom - 3 * dpr, valueY + 7 * dpr)
        : Math.max(plot.top + 6 * dpr, top - 6 * dpr);
      ctx.fillText(`${this.formatNumber(bar.value, 3)}×`, labelX, labelY);
      hitboxes.push({
        cx: labelX, cy: (top + bottom) / 2, r: Math.max(9 * dpr, barWidth * 0.75),
        rect: { x: Math.max(plot.left, center - slot / 2), y: plot.top, w: Math.min(slot, plot.right - plot.left), h: plot.bottom - plot.top },
        title: `T${bar.detail.row.Threads} · P${bar.detail.row.Processes} · ${this.formatNumber(bar.detail.row.Data)} ants`,
        lines: [
          `Speedup: ${this.formatNumber(bar.value, 4)}×`,
          `Execution time: ${this.formatNumber(bar.detail.row.Time, 4)} s`,
          `Baseline serial: ${this.formatNumber(bar.detail.row.Time / (bar.value || 1), 4)} s`,
          `Efficiency: ${this.formatNumber(bar.detail.row.Efficiency, 2)}%`,
          `Throughput: ${this.formatNumber(bar.detail.row.Throughput, 2)} ants/s`,
          `Seed ${bar.detail.row.Seed} · ${bar.detail.row.Iterations} it`,
        ],
      });
    });

    // --- 1× baseline reference (measured serial runs, Speedup = 1.0) ---
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1.4 * dpr;
    ctx.setLineDash([5 * dpr, 4 * dpr]);
    ctx.beginPath();
    ctx.moveTo(plot.left, Math.round(baselineY) + .5 * dpr);
    ctx.lineTo(plot.right, Math.round(baselineY) + .5 * dpr);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#0f172a';
    ctx.font = `600 ${8 * dpr}px ${font}`;
    ctx.textAlign = 'right';
    ctx.fillText(model.baseline.measured ? '1× serial' : '1× (speedup = 1)', plot.right - 2 * dpr, baselineY - 6 * dpr);

    // --- x labels: compact T/P/ants, rotated only if crowded ---
    const labels = bars.map(bar => bar.label);
    ctx.font = `${7.5 * dpr}px ${font}`;
    const widest = Math.max(...labels.map(label => ctx.measureText(label).width));
    const rotate = widest > slot * 0.98;
    ctx.fillStyle = '#64748b';
    if (rotate) {
      ctx.textAlign = 'right';
      bars.forEach(bar => {
        const center = plot.left + slot * (bar.index + 0.5);
        ctx.save();
        ctx.translate(center + 3 * dpr, plot.bottom + 4 * dpr);
        ctx.rotate(-Math.PI / 3.4);
        ctx.fillText(bar.label, 0, 0);
        ctx.restore();
      });
    } else {
      ctx.textAlign = 'center';
      bars.forEach(bar => {
        const center = plot.left + slot * (bar.index + 0.5);
        ctx.fillText(bar.label, center, plot.bottom + 10 * dpr);
      });
    }
    ctx.textAlign = 'left';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(`bars: ${bars.length} hybrid configs · ${model.slowCount} below 1× (slowdown)`, 8 * dpr, height - 3 * dpr);

    canvas.__antHitboxes = hitboxes;
  }

  ellipsize(ctx, text, maxWidth) {
    if (ctx.measureText(text).width <= maxWidth) return text;
    let truncated = text;
    while (truncated.length > 4 && ctx.measureText(`${truncated}…`).width > maxWidth) {
      truncated = truncated.slice(0, -1);
    }
    return `${truncated}…`;
  }

  /**
   * Tooltip binding.
   *
   * Tooltips are drawn onto the same canvas, so the previous implementation had
   * no way to erase one without redrawing the whole chart. Each canvas now keeps
   * a base bitmap captured right after a chart draw; showing and hiding a tooltip
   * is a bitmap blit plus an overlay, which cannot accumulate artifacts.
   */
  bindBenchmarkTooltips() {
    for (const id of ['benchmarkThreadsChart', 'benchmarkProcessesChart', 'benchmarkSpeedupChart']) {
      const canvas = document.getElementById(id);
      if (!canvas || canvas.__antTooltipBound) continue;
      canvas.__antTooltipBound = true;
      canvas.style.cursor = 'default';
      canvas.addEventListener('pointermove', event => this.handleBenchmarkPointer(canvas, event));
      canvas.addEventListener('pointerleave', () => this.clearBenchmarkTooltip(canvas));
    }
  }

  captureBenchmarkBase(canvas) {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const buffer = document.createElement('canvas');
    buffer.width = canvas.width;
    buffer.height = canvas.height;
    buffer.getContext('2d').drawImage(canvas, 0, 0);
    canvas.__antBase = buffer;
    canvas.__antBaseDpr = dpr;
    canvas.__antCursor = null;
  }

  clearBenchmarkTooltip(canvas) {
    canvas.__antCursor = null;
    canvas.style.cursor = 'default';
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (canvas.__antBase) {
      canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
      canvas.getContext('2d').drawImage(canvas.__antBase, 0, 0);
    } else {
      this.renderBenchmarkCharts();
      return;
    }
    this.paintBenchmarkCursor(canvas, dpr, null);
  }

  handleBenchmarkPointer(canvas, event) {
    if (!canvas.__antBase) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const bounds = canvas.getBoundingClientRect();
    const px = (event.clientX - bounds.left) * dpr;
    const py = (event.clientY - bounds.top) * dpr;
    const hit = (canvas.__antHitboxes || []).find(box => box.rect
      ? px >= box.rect.x && px <= box.rect.x + box.rect.w && py >= box.rect.y && py <= box.rect.y + box.rect.h
      : Math.hypot(px - box.cx, py - box.cy) <= box.r) || null;
    const signature = hit ? `${Math.round(px)}:${Math.round(py)}:${hit.title}` : null;
    if (signature === canvas.__antCursor) return;
    canvas.__antCursor = signature;
    canvas.style.cursor = hit ? 'pointer' : 'default';

    // restore the pristine chart, then draw the crosshair and tooltip on top
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(canvas.__antBase, 0, 0);
    this.paintBenchmarkCursor(canvas, dpr, hit ? { px, py } : null);
    if (hit) this.drawBenchmarkTooltip(ctx, dpr, canvas.width, canvas.height, { px, py, hit });
  }

  paintBenchmarkCursor(canvas, dpr, cursor) {
    if (!cursor) return;
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.strokeStyle = 'rgba(37,99,235,.35)';
    ctx.lineWidth = 1 * dpr;
    ctx.setLineDash([3 * dpr, 3 * dpr]);
    ctx.beginPath();
    ctx.moveTo(0, Math.round(cursor.py) + .5 * dpr);
    ctx.lineTo(canvas.width, Math.round(cursor.py) + .5 * dpr);
    ctx.stroke();
    ctx.restore();
  }

  drawBenchmarkTooltip(ctx, dpr, width, height, payload) {
    const font = getComputedStyle(document.body).fontFamily;
    const hit = payload.hit;
    ctx.save();
    ctx.font = `${9 * dpr}px ${font}`;
    const titleWidth = ctx.measureText(hit.title).width;
    ctx.font = `${8.5 * dpr}px ${font}`;
    const rowWidths = hit.lines.map(line => ctx.measureText(line).width);
    const boxWidth = Math.min(width - 8 * dpr, Math.max(titleWidth, ...rowWidths) + 16 * dpr);
    const boxHeight = (16 + hit.lines.length * 12) * dpr;
    let x = payload.px + 12 * dpr;
    let y = payload.py + 12 * dpr;
    if (x + boxWidth > width - 4 * dpr) x = payload.px - boxWidth - 12 * dpr;
    if (y + boxHeight > height - 4 * dpr) y = height - boxHeight - 4 * dpr;
    x = Math.max(4 * dpr, x);
    y = Math.max(4 * dpr, y);

    ctx.fillStyle = 'rgba(255,255,255,0.97)';
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1 * dpr;
    ctx.beginPath();
    ctx.roundRect(x, y, boxWidth, boxHeight, 5 * dpr);
    ctx.fill();
    ctx.stroke();

    ctx.textAlign = 'left';
    ctx.fillStyle = '#0f172a';
    ctx.font = `700 ${9 * dpr}px ${font}`;
    ctx.fillText(hit.title, x + 8 * dpr, y + 10 * dpr, boxWidth - 16 * dpr);
    ctx.fillStyle = '#475569';
    ctx.font = `${8.5 * dpr}px ${font}`;
    hit.lines.forEach((line, index) => {
      ctx.fillText(line, x + 8 * dpr, y + (23 + index * 12) * dpr, boxWidth - 16 * dpr);
    });
    ctx.restore();
  }

  bindControls() {
    document.getElementById('btnStart').addEventListener('click', () => this.sendControl('start'));
    document.getElementById('btnPause').addEventListener('click', () => this.sendControl('pause'));
    document.getElementById('btnResume').addEventListener('click', () => this.sendControl('resume'));
    document.getElementById('btnQuickResume').addEventListener('click', () => this.sendControl('resume'));
    document.getElementById('btnRestart').addEventListener('click', () => this.showRestartModal(true));
    document.getElementById('btnCancelRestart').addEventListener('click', () => this.showRestartModal(false));
    document.getElementById('btnConfirmRestart').addEventListener('click', () => {
      this.showRestartModal(false);
      this.sendControl('restart');
    });
    document.getElementById('restartModal').addEventListener('click', event => {
      if (event.target.id === 'restartModal') this.showRestartModal(false);
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') this.showRestartModal(false);
    });

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
      const iteration = Number.isFinite(state.iteration) ? state.iteration : state.metrics?.iteration;
      if (state.status === 'ready' && iteration === 0 && this.lastStatus && this.lastStatus !== 'ready') {
        this.samples = [];
        this.lastIteration = null;
        this.startedAt = null;
        this.latestIterationDuration = null;
      }
      const mapChanged = iteration !== this.lastIteration;
      this.state = state;
      this.lastStatus = state.status;
      if (mapChanged) this.updateMotion(state);
      this.lastPollAt = performance.now();
      this.setStatus(state.status === 'error' ? 'error' : 'connected',
        state.status === 'error' ? 'SYSTEM ERROR' : 'SYSTEM ONLINE');
      document.getElementById('errorSection').hidden = state.status !== 'error';
      if (state.status === 'error') document.getElementById('errorMessage').textContent = state.error || 'Simulation error';
      this.updateMetrics(state);
      this.renderActivities(state.activities || []);
      this.addSample(state);
      if (mapChanged) this.render();
      if (mapChanged) this.renderCharts();
    } catch (error) {
      this.setStatus('disconnected', 'DISCONNECTED');
      const simulationStatus = document.getElementById('simulationStatus');
      simulationStatus.className = 'simulation-status disconnected';
      document.getElementById('simulationStatusText').textContent = 'DISCONNECTED';
      document.getElementById('sideStatus').textContent = 'DISCONNECTED';
      this.state = null;
      this.lastStatus = 'disconnected';
      this.updateControls('disconnected');
      document.getElementById('pauseOverlay').hidden = true;
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

  showRestartModal(show) {
    document.getElementById('restartModal').hidden = !show;
    if (show) document.getElementById('btnCancelRestart').focus();
  }

  async sendControl(action) {
    if (this.pendingAction || !this.state) return;
    this.pendingAction = action;
    this.updateControls(this.state.status);
    const message = document.getElementById('controlMessage');
    const labels = { start: 'Starting…', pause: 'Pausing…', resume: 'Resuming…', restart: 'Restarting…' };
    message.textContent = labels[action];
    try {
      const response = await fetch(`/api/control/${action}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
      });
      const result = await response.json();
      if (!response.ok || !result.accepted) throw new Error(result.message || `HTTP ${response.status}`);
      message.textContent = result.message || labels[action];
    } catch (error) {
      message.textContent = error.message || `Tidak dapat ${action} simulasi.`;
    } finally {
      this.pendingAction = null;
      if (this.state) this.updateControls(this.state.status);
    }
  }

  updateControls(status) {
    const connected = status !== 'disconnected' && status !== 'error';
    const pending = Boolean(this.pendingAction);
    const visible = (id, show) => { document.getElementById(id).hidden = !show; };
    visible('btnStart', connected && status === 'ready');
    visible('btnPause', connected && status === 'running');
    visible('btnResume', connected && status === 'paused');
    visible('btnRestart', connected && ['running', 'paused', 'completed', 'starting'].includes(status));
    document.getElementById('btnQuickResume').disabled = pending || !connected;
    for (const id of ['btnStart', 'btnPause', 'btnResume', 'btnRestart', 'btnConfirmRestart']) {
      document.getElementById(id).disabled = pending || !connected;
    }
    document.getElementById('pauseOverlay').hidden = status !== 'paused';
  }

  renderActivities(activities) {
    const feed = document.getElementById('activityFeed');
    const latest = Array.isArray(activities) ? activities.slice(-10).reverse() : [];
    const signature = latest.map(item => `${item.id}:${item.message}`).join('|');
    if (signature === this.activitySignature) return;
    this.activitySignature = signature;
    document.getElementById('activityCount').textContent = `${latest.length} event${latest.length === 1 ? '' : 's'}`;
    feed.replaceChildren();
    if (!latest.length) {
      const empty = document.createElement('p');
      empty.className = 'activity-empty';
      empty.textContent = 'Belum ada aktivitas simulasi.';
      feed.appendChild(empty);
      return;
    }
    for (const event of latest) {
      const row = document.createElement('div');
      row.className = `activity-item ${String(event.type || 'info').replace(/[^a-z0-9_-]/gi, '')}`;
      const message = document.createElement('span');
      message.className = 'activity-msg';
      const marker = document.createElement('i');
      marker.setAttribute('aria-hidden', 'true');
      message.append(marker, document.createTextNode(String(event.message || 'Simulation event')));
      const time = document.createElement('time');
      time.className = 'activity-time';
      time.textContent = String(event.time || '');
      row.append(message, time);
      feed.appendChild(row);
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
    this.updateControls(status);
    const sideStatus = document.getElementById('sideStatus');
    if (sideStatus) sideStatus.textContent = status === 'ready' ? 'READY' : statusLabel;
    document.getElementById('progressMessage').textContent = status === 'ready'
      ? 'Ready to start.'
      : status === 'running' ? 'Hybrid simulation is running.'
        : status === 'paused' ? 'Simulation paused. State is preserved.'
        : status === 'completed' ? 'Simulation complete.'
          : status === 'starting' ? 'Initializing world…'
            : status === 'restarting' ? 'Resetting simulation…' : statusLabel;
    const startMessage = status === 'ready' ? 'Ready to start.'
      : status === 'running' ? 'Simulation is running.'
        : status === 'paused' ? 'Simulation paused. Choose Resume to continue.'
          : status === 'completed' ? 'Simulation complete. Restart to run again.'
            : status === 'starting' ? 'Preparing simulation…'
              : status === 'restarting' ? 'Resetting simulation…' : statusLabel;
    if (!this.pendingAction) document.getElementById('controlMessage').textContent = startMessage;
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
          this.drawRock(ctx, xAt(x) + cell / 2, yAt(y) + cell / 2, cell * .48);
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
    ctx.lineWidth = Math.max(.6, radius * .12);
    ctx.lineJoin = 'round';
    ctx.fillStyle = '#64748b'; ctx.strokeStyle = '#475569';
    ctx.beginPath();
    ctx.moveTo(x - radius * .96, y - radius * .18);
    ctx.lineTo(x - radius * .72, y - radius * .73);
    ctx.lineTo(x - radius * .22, y - radius * .91);
    ctx.lineTo(x + radius * .18, y - radius * .68);
    ctx.lineTo(x + radius * .78, y - radius * .61);
    ctx.lineTo(x + radius * .98, y - radius * .08);
    ctx.lineTo(x + radius * .66, y + radius * .61);
    ctx.lineTo(x + radius * .12, y + radius * .87);
    ctx.lineTo(x - radius * .51, y + radius * .72);
    ctx.closePath(); ctx.fill(); ctx.stroke();

    ctx.fillStyle = '#cbd5e1';
    ctx.beginPath();
    ctx.moveTo(x - radius * .68, y - radius * .56);
    ctx.lineTo(x - radius * .2, y - radius * .78);
    ctx.lineTo(x + radius * .18, y - radius * .56);
    ctx.lineTo(x - radius * .08, y - radius * .1);
    ctx.lineTo(x - radius * .75, y + radius * .02);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#475569';
    ctx.beginPath();
    ctx.moveTo(x - radius * .08, y - radius * .1);
    ctx.lineTo(x + radius * .18, y - radius * .56);
    ctx.lineTo(x + radius * .78, y - radius * .48);
    ctx.lineTo(x + radius * .86, y - radius * .04);
    ctx.lineTo(x + radius * .55, y + radius * .5);
    ctx.lineTo(x + radius * .12, y + radius * .7);
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }

  drawFoodCluster(ctx, x, y, cell, amount) {
    ctx.save();
    const offsets = [[0, 0], [-.24, -.18], [.24, -.17], [-.2, .2], [.22, .2], [0, -.31], [0, .31]];
    offsets.slice(0, Math.min(offsets.length, amount)).forEach(([dx, dy], index) => {
      const cx = x + dx * cell;
      const cy = y + dy * cell;
      const size = cell * (index ? .24 : .29);
      ctx.save(); ctx.translate(cx, cy); ctx.rotate((index % 2 ? -1 : 1) * .42);
      ctx.fillStyle = index % 2 ? '#15803d' : '#22c55e';
      ctx.beginPath();
      ctx.moveTo(-size, 0);
      ctx.quadraticCurveTo(-size * .18, -size * .8, size, -size * .12);
      ctx.quadraticCurveTo(size * .12, size * .8, -size, 0);
      ctx.fill();
      ctx.strokeStyle = '#bbf7d0'; ctx.lineWidth = Math.max(.45, cell * .035);
      ctx.beginPath(); ctx.moveTo(-size * .72, size * .02); ctx.lineTo(size * .68, -size * .04); ctx.stroke();
      ctx.fillStyle = '#166534';
      ctx.beginPath(); ctx.arc(size * .42, -size * .03, size * .25, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    });
    ctx.restore();
  }

  drawNest(ctx, x, y, cell) {
    ctx.save();
    ctx.fillStyle = '#eab308'; ctx.strokeStyle = '#a16207'; ctx.lineWidth = Math.max(1, cell * .12);
    ctx.beginPath();
    ctx.moveTo(x - cell * 1.65, y + cell * .42);
    ctx.quadraticCurveTo(x - cell * 1.25, y - cell * .48, x - cell * .35, y - cell * .68);
    ctx.quadraticCurveTo(x + cell * .72, y - cell * .94, x + cell * 1.55, y - cell * .14);
    ctx.quadraticCurveTo(x + cell * 1.86, y + cell * .2, x + cell * 1.48, y + cell * .56);
    ctx.quadraticCurveTo(x, y + cell * .98, x - cell * 1.65, y + cell * .42);
    ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#fef08a';
    ctx.beginPath(); ctx.ellipse(x - cell * .42, y - cell * .2, cell * .68, cell * .24, -.28, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#713f12';
    ctx.beginPath(); ctx.ellipse(x + cell * .12, y + cell * .38, cell * .43, cell * .3, 0, Math.PI, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#422006';
    ctx.beginPath(); ctx.ellipse(x + cell * .12, y + cell * .42, cell * .3, cell * .2, 0, Math.PI, Math.PI * 2); ctx.fill();
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
      const gait = Math.sin(now / 55 + Number(ant.id) * .7) > 0;
      const frame = Array.isArray(sprite) ? sprite[Number(gait)] : sprite;
      ctx.drawImage(frame, -frame.width / 2, -frame.height / 2);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  renderAnts() {
    if (!this.state?.world) return;
    this.drawAntLayer(1, window.devicePixelRatio || 1, 0, 0, this.state.world);
  }

  createAntSprites() {
    const create = (headColor, gait) => {
      const sprite = document.createElement('canvas');
      sprite.width = 34;
      sprite.height = 24;
      const ctx = sprite.getContext('2d');
      ctx.lineWidth = 1.2;
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#713f12';
      // Pre-render 6 articulated legs in two gait poses; one inexpensive sprite draw per ant/frame.
      for (let pair = 0; pair < 3; pair++) {
        const legX = 8 + pair * 5;
        const stride = gait * (pair === 1 ? -1 : 1);
        for (const side of [-1, 1]) {
          ctx.beginPath();
          ctx.moveTo(legX, 12 + side);
          ctx.lineTo(legX - 1 + stride * 1.5, 12 + side * 5);
          ctx.lineTo(legX - 2 + stride * 3, 12 + side * 8);
          ctx.stroke();
        }
      }
      ctx.lineWidth = 1;
      // Antennae point toward the head (+X).
      ctx.beginPath();
      ctx.moveTo(22, 10); ctx.quadraticCurveTo(27, 3, 32, 4);
      ctx.moveTo(22, 14); ctx.quadraticCurveTo(27, 21, 32, 20);
      ctx.stroke();
      // Abdomen, narrow thorax, then head: visible segmented ant anatomy.
      ctx.fillStyle = '#9a3412';
      ctx.beginPath(); ctx.ellipse(8, 12, 5.8, 4.1, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#c2410c';
      ctx.beginPath(); ctx.arc(16, 12, 2.7, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = headColor;
      ctx.beginPath(); ctx.arc(21, 12, 3.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#fff7ed';
      ctx.beginPath(); ctx.arc(22, 11, .65, 0, Math.PI * 2); ctx.fill();
      return sprite;
    };
    return {
      searching: [create('#f97316', -1), create('#f97316', 1)],
      returning: [create('#ea580c', -1), create('#ea580c', 1)],
    };
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
    this.drawChart('timeChart', 'time', '#2563eb', 's');
    this.drawChart('speedChart', 'speedup', '#16a34a', '×');
    this.drawChart('foodChart', 'food', '#f97316', '');
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
