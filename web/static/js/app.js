/* 轴承故障智能监测与诊断系统 - 前端逻辑 */
const API = "/api";

// 图表实例
const chartWave = echarts.init(document.getElementById("chart-wave"));
const chartFreq = echarts.init(document.getElementById("chart-freq"));
const chartHealth = echarts.init(document.getElementById("chart-health"));

let currentFile = null;

/* ---------- 工具 ---------- */
async function fetchJSON(url, options = {}) {
    const resp = await fetch(url, options);
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || `请求失败 (${resp.status})`);
    }
    return resp.json();
}

function setStatus(text, cls = "bg-warning") {
    const el = document.getElementById("model-status");
    el.className = `badge ${cls}`;
    el.textContent = text;
}

function setHealth(score, warning = false) {
    const el = document.getElementById("health-score");
    el.textContent = score === null || score === undefined ? "--" : score;
    el.style.color = warning ? "#dc3545" : "#28a745";
    document.getElementById("health-msg").innerHTML = warning
        ? `<span class="badge bg-danger">⚠ 预警：健康退化风险</span>`
        : `<span class="badge bg-success">设备状态良好</span>`;
}

/* ---------- 图表渲染 ---------- */
function renderWave(time, signal) {
    chartWave.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 50, right: 15, top: 20, bottom: 30 },
        xAxis: { type: "category", data: time, name: "时间 (s)" },
        yAxis: { type: "value", name: "加速度 (g)" },
        dataZoom: [{ type: "inside" }, { type: "slider", height: 18 }],
        series: [{
            type: "line", data: signal, showSymbol: false,
            lineStyle: { width: 1, color: "#1f77b4" },
            areaStyle: { opacity: 0.1 }
        }]
    }, true);
}

function renderFreq(freq, mag) {
    chartFreq.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 55, right: 15, top: 20, bottom: 30 },
        xAxis: { type: "category", data: freq, name: "频率 (Hz)" },
        yAxis: { type: "value", name: "幅值" },
        series: [{
            type: "line", data: mag, showSymbol: false,
            lineStyle: { width: 1, color: "#ff7f0e" },
            areaStyle: { opacity: 0.15 }
        }]
    }, true);
}

function renderHealth(xh, yh, xf, yf, threshold) {
    // 历史 + 预测拼接
    const allX = xh.concat(xf);
    const histData = yh.concat(new Array(xf.length).fill(null));
    const fcData = new Array(xh.length).fill(null).concat(yf);
    const thData = allX.map(() => threshold);
    const splitIdx = xh.length - 1;

    chartHealth.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["历史健康指标", "趋势预测", "预警阈值"], top: 0 },
        grid: { left: 55, right: 15, top: 35, bottom: 30 },
        xAxis: { type: "category", data: allX, name: "窗口序号" },
        yAxis: { type: "value", name: "健康指标" },
        series: [
            { name: "历史健康指标", type: "line", data: histData, showSymbol: false, lineStyle: { color: "#1f77b4" } },
            { name: "趋势预测", type: "line", data: fcData, showSymbol: false, lineStyle: { type: "dashed", color: "#d62728" } },
            { name: "预警阈值", type: "line", data: thData, showSymbol: false, lineStyle: { type: "dotted", color: "#ff7f0e" }, markLine: { silent: true, data: [{ yAxis: threshold }] } }
        ],
        markLine: { data: [{ xAxis: splitIdx }] }
    }, true);
}

/* ---------- 诊断结果 ---------- */
function renderDiagnosis(d) {
    const box = document.getElementById("diag-result");
    const sevColor = d.severity === "重度" ? "bg-danger" : d.severity === "中度" ? "bg-warning text-dark" : "bg-success";
    box.innerHTML = `
        <div class="diag-type">${d.fault_name}</div>
        <div class="text-muted small mb-2">故障代码：${d.fault_type}</div>
        <div class="mb-2">
            <span class="badge badge-severity ${sevColor}">严重程度：${d.severity}</span>
        </div>
        <div class="confidence">置信度：${(d.confidence * 100).toFixed(1)}%</div>
        <div class="small text-muted mt-2">数据：${d.filename}</div>
    `;
}

function renderAdvice(d) {
    const box = document.getElementById("advice-box");
    const warnBanner = d.severity === "重度"
        ? `<div class="alert-banner alert-danger">⚠ 紧急：建议立即停机处理</div>`
        : d.severity === "中度"
            ? `<div class="alert-banner alert-warn">⚠ 较急：建议近期安排检修</div>`
            : `<div class="alert-banner" style="background:#d4edda;color:#155724;border:1px solid #c3e6cb;">✓ 常规：纳入例行检修计划</div>`;
    box.innerHTML = `
        ${warnBanner}
        <div class="mb-2"><strong>成因：</strong>${d.cause}</div>
        <div class="mb-2"><strong>处理建议：</strong>${d.advice}</div>
        <div><strong>检查清单：</strong>${(d.checks || []).join("、")}</div>
    `;
}

/* ---------- 数据加载 ---------- */
async function loadDatasets() {
    const items = await fetchJSON(`${API}/datasets`);
    const sel = document.getElementById("dataset-select");
    sel.innerHTML = "";
    items.forEach(it => {
        const opt = document.createElement("option");
        opt.value = it.filename;
        opt.textContent = `${it.filename}  [${it.label_cn}${it.diameter ? "·φ" + it.diameter : ""}]`;
        sel.appendChild(opt);
    });
    sel.disabled = false;
    document.getElementById("btn-load").disabled = false;
}

async function loadSignal(filename) {
    const d = await fetchJSON(`${API}/signal/${encodeURIComponent(filename)}`);
    renderWave(d.time, d.signal);
    renderFreq(d.freq, d.mag);
    document.getElementById("load-info").innerHTML =
        `${d.meta.label_cn} · 长度 ${d.meta.length} 点 · ${d.meta.rpm} rpm · ${d.meta.load} HP`;
    return d;
}

async function diagnose(filename) {
    const d = await fetchJSON(`${API}/diagnose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename })
    });
    renderDiagnosis(d);
    renderAdvice(d);
    setHealth(null);
    loadRecords();
}

async function predictHealth(filename) {
    const d = await fetchJSON(`${API}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename, metric: "rms" })
    });
    renderHealth(d.x_history, d.y_history, d.x_forecast, d.y_forecast, d.threshold);
    setHealth(d.forecast_health, d.warning);
    document.getElementById("predict-info").innerHTML =
        `当前健康度 ${d.current_health} → 预测末端 ${d.forecast_health}，` +
        `当前值 ${d.current_value} / 阈值 ${d.threshold}，` +
        (d.warning ? `<span class="text-danger fw-bold">⚠ 已触发预警</span>` : `<span class="text-success">未预警</span>`);
}

async function loadRecords() {
    const d = await fetchJSON(`${API}/records`);
    const rb = document.getElementById("record-body");
    const ab = document.getElementById("alarm-body");
    rb.innerHTML = d.samples.length
        ? d.samples.map(s => `<tr><td>${s.sample_time}</td><td>${s.fault_type}</td><td>${(s.confidence * 100).toFixed(1)}%</td></tr>`).join("")
        : `<tr><td colspan="3" class="text-muted">暂无记录</td></tr>`;
    ab.innerHTML = d.alarms.length
        ? d.alarms.map(a => `<tr><td>${a.timestamp}</td><td>${a.alarm_type}</td><td>${a.description}</td></tr>`).join("")
        : `<tr><td colspan="3" class="text-muted">暂无告警</td></tr>`;
}

/* ---------- 事件绑定 ---------- */
document.getElementById("btn-load").addEventListener("click", async () => {
    currentFile = document.getElementById("dataset-select").value;
    if (!currentFile) return;
    document.getElementById("btn-load").disabled = true;
    document.getElementById("btn-diagnose").disabled = false;
    document.getElementById("btn-predict").disabled = false;
    try {
        await loadSignal(currentFile);
        setStatus("数据已加载", "bg-success");
    } catch (e) {
        setStatus("加载失败", "bg-danger");
        alert(e.message);
    } finally {
        document.getElementById("btn-load").disabled = false;
    }
});

document.getElementById("btn-diagnose").addEventListener("click", async () => {
    if (!currentFile) return;
    setStatus("诊断中...", "bg-info");
    document.getElementById("btn-diagnose").disabled = true;
    try {
        await diagnose(currentFile);
        setStatus("诊断完成", "bg-success");
    } catch (e) {
        setStatus("诊断失败", "bg-danger");
        alert(e.message);
    } finally {
        document.getElementById("btn-diagnose").disabled = false;
    }
});

document.getElementById("btn-predict").addEventListener("click", async () => {
    if (!currentFile) return;
    setStatus("预测中...", "bg-info");
    document.getElementById("btn-predict").disabled = true;
    try {
        await predictHealth(currentFile);
        setStatus("预测完成", "bg-success");
    } catch (e) {
        setStatus("预测失败", "bg-danger");
        alert(e.message);
    } finally {
        document.getElementById("btn-predict").disabled = false;
    }
});

window.addEventListener("resize", () => {
    chartWave.resize();
    chartFreq.resize();
    chartHealth.resize();
});

/* ---------- 初始化 ---------- */
(async function init() {
    try {
        const h = await fetchJSON(`${API}/health`);
        setStatus(h.model_loaded ? "模型已就绪" : "模型未加载", h.model_loaded ? "bg-success" : "bg-danger");
        await loadDatasets();
        await loadRecords();
    } catch (e) {
        setStatus("后端连接失败", "bg-danger");
        alert("无法连接后端服务：" + e.message);
    }
})();
