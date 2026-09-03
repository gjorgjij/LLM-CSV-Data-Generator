let currentChart = null;
let currentColumns = [];

/* -----------------------------------------
   INPUT
----------------------------------------- */

function getInputType() {
  return document.querySelector('input[name="inputType"]:checked').value;
}

function getCurrentData() {
  const inputType = getInputType();

  if (inputType === "file") {
    return document.getElementById("filePicker").value;
  }

  return document.getElementById("dataInput").value;
}

/* -----------------------------------------
   FILE LIST
----------------------------------------- */

async function loadFiles() {
  const picker = document.getElementById("filePicker");

  const previousSelection = picker.value;

  try {
    const response = await fetch("/files");

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    picker.innerHTML = `
            <option value="">
                Select CSV file...
            </option>
        `;

    result.files.forEach((file) => {
      const option = document.createElement("option");

      option.value = file;
      option.textContent = file;

      picker.appendChild(option);
    });

    if (previousSelection && result.files.includes(previousSelection)) {
      picker.value = previousSelection;
    }
  } catch (error) {
    document.getElementById("error").innerText =
      "Could not read data folder: " + error.message;
  }
}

/* -----------------------------------------
   SWITCH INPUT MODE
----------------------------------------- */
document
  .getElementById("aiQuestion")
  .addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
      generateAIChart();
    }
  });

document.querySelectorAll('input[name="inputType"]').forEach((radio) => {
  radio.addEventListener("change", async () => {
    const type = getInputType();

    const rawContainer = document.getElementById("rawInputContainer");

    const fileContainer = document.getElementById("fileInputContainer");

    if (type === "file") {
      rawContainer.classList.add("hidden");

      fileContainer.classList.remove("hidden");

      await loadFiles();
    } else {
      fileContainer.classList.add("hidden");

      rawContainer.classList.remove("hidden");
    }
  });
});

/* -----------------------------------------
   AUTO ANALYZE SELECTED FILE
----------------------------------------- */

document
  .getElementById("filePicker")
  .addEventListener("change", async function () {
    if (this.value) {
      await analyzeData();
    }
  });

/* -----------------------------------------
   ANALYZE
----------------------------------------- */

async function analyzeData() {
  const data = getCurrentData();

  const inputType = getInputType();

  const error = document.getElementById("error");

  error.innerText = "";

  if (!data.trim()) {
    error.innerText =
      inputType === "file"
        ? "Please select a CSV file."
        : "Please provide some data.";

    return;
  }

  try {
    const response = await fetch("/analyze", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        data,
        inputType,
      }),
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    currentColumns = result.columns;

    document.getElementById("datasetInfo").innerHTML = `

                <span class="badge">
                    Rows: ${result.rows}
                </span>

                <span class="badge">
                    Columns:
                    ${result.columns.length}
                </span>

            `;

    let statusText = `${result.rows} rows loaded`;

    if (inputType === "file") {
      const filename = document.getElementById("filePicker").value;

      statusText = `${filename} • ${result.rows} rows`;
    }

    document.getElementById("status").innerText = statusText;

    createPreview(result.preview);

    populateColumns(result.columns);

    if (result.columns.length > 0) {
      await generateChart();
    }
  } catch (error) {
    document.getElementById("error").innerText = error.message;
  }
}

/* -----------------------------------------
   COLUMN SELECTORS
----------------------------------------- */

function populateColumns(columns) {
  const xSelect = document.getElementById("xColumn");

  const ySelect = document.getElementById("yColumn");

  xSelect.innerHTML = "";

  ySelect.innerHTML = `
        <option value="">
            None
        </option>
    `;

  columns.forEach((column) => {
    const xOption = document.createElement("option");

    xOption.value = column.name;

    xOption.textContent = column.name;

    xSelect.appendChild(xOption);

    if (column.type === "number") {
      const yOption = document.createElement("option");

      yOption.value = column.name;

      yOption.textContent = column.name;

      ySelect.appendChild(yOption);
    }
  });
}

/* -----------------------------------------
   PREVIEW TABLE
----------------------------------------- */

function createPreview(rows) {
  const preview = document.getElementById("preview");

  if (!rows.length) {
    preview.innerHTML = `
            <div
                style="
                    padding:20px;
                    color:#9ca3af;
                "
            >
                No rows found.
            </div>
        `;

    return;
  }

  const columns = Object.keys(rows[0]);

  let html = "<table>";

  html += "<thead><tr>";

  columns.forEach((column) => {
    html += `
                <th>
                    ${escapeHtml(column)}
                </th>
            `;
  });

  html += "</tr></thead>";

  html += "<tbody>";

  rows.forEach((row) => {
    html += "<tr>";

    columns.forEach((column) => {
      html += `
                        <td>
                            ${escapeHtml(String(row[column] ?? ""))}
                        </td>
                    `;
    });

    html += "</tr>";
  });

  html += "</tbody></table>";

  preview.innerHTML = html;
}

/* -----------------------------------------
   CHART
----------------------------------------- */
async function generateAIChart() {
  const question = document.getElementById("aiQuestion").value.trim();

  if (!question) {
    document.getElementById("error").innerText = "Enter a request for the AI.";

    return;
  }

  const data = getCurrentData();

  const inputType = getInputType();

  if (!data.trim()) {
    document.getElementById("error").innerText = "Load a dataset first.";

    return;
  }

  const button = document.getElementById("aiButton");

  button.disabled = true;

  button.textContent = "Thinking...";

  document.getElementById("error").innerText = "";

  try {
    const response = await fetch("/ai-chart", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        data,

        inputType,

        question,
      }),
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }

    const plan = result.plan;

    /* --------------------------------
           UPDATE MANUAL CONTROLS
           TO SHOW WHAT AI CHOSE
        -------------------------------- */

    document.getElementById("xColumn").value = plan.xColumn;

    document.getElementById("aggregation").value = plan.aggregation;

    document.getElementById("yColumn").value = plan.yColumn || "";

    document.getElementById("chartType").value = plan.chartType;

    /* --------------------------------
           DRAW RESULT
        -------------------------------- */

    renderChart(
      result.labels,

      result.values,

      plan.chartType,

      plan.title,
    );
  } catch (error) {
    document.getElementById("error").innerText = error.message;
  } finally {
    button.disabled = false;

    button.textContent = "Generate with AI";
  }
}

async function generateChart() {
  const data = getCurrentData();

  const inputType = getInputType();

  if (!data.trim()) {
    return;
  }

  const xColumn = document.getElementById("xColumn").value;

  const yColumn = document.getElementById("yColumn").value;

  const aggregation = document.getElementById("aggregation").value;

  const chartType = document.getElementById("chartType").value;

  if (!xColumn) {
    return;
  }

  document.getElementById("error").innerText = "";

  try {
    const response = await fetch("/chart", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        data,
        inputType,
        xColumn,
        yColumn,
        aggregation,
      }),
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error);
    }
    renderChart(
      result.labels,
      result.values,
      chartType,
      `${capitalize(aggregation)} by ${xColumn}`,
    );
    if (currentChart) {
      currentChart.destroy();
    }

    const canvas = document.getElementById("chart");

    const ctx = canvas.getContext("2d");

    document.getElementById("chartPlaceholder").classList.add("hidden");

    const colors = createColors(result.labels.length);

    currentChart = new Chart(ctx, {
      type: chartType,

      data: {
        labels: result.labels,

        datasets: [
          {
            label: `${capitalize(aggregation)} by ${xColumn}`,

            data: result.values,

            backgroundColor: chartType === "line" ? undefined : colors,

            borderColor: chartType === "line" ? "#111827" : undefined,

            borderWidth: chartType === "line" ? 2 : 1,

            tension: 0.25,

            fill: false,
          },
        ],
      },

      options: {
        responsive: true,

        maintainAspectRatio: false,

        interaction: {
          mode: "nearest",

          intersect: false,
        },

        plugins: {
          legend: {
            display: chartType === "pie" || chartType === "doughnut",
          },

          tooltip: {
            enabled: true,
          },
        },

        scales:
          chartType === "pie" || chartType === "doughnut"
            ? {}
            : {
                x: {
                  grid: {
                    display: false,
                  },

                  ticks: {
                    autoSkip: true,

                    maxRotation: 45,

                    minRotation: 0,
                  },
                },

                y: {
                  beginAtZero: true,

                  grid: {
                    color: "#f0f1f3",
                  },
                },
              },
      },
    });
  } catch (error) {
    document.getElementById("error").innerText = error.message;
  }
}

/* -----------------------------------------
   CLEAR
----------------------------------------- */

function clearData() {
  document.getElementById("dataInput").value = "";

  document.getElementById("filePicker").value = "";

  document.getElementById("preview").innerHTML = "";

  document.getElementById("datasetInfo").innerHTML = `

            <span class="badge">
                Rows: —
            </span>

            <span class="badge">
                Columns: —
            </span>

        `;

  document.getElementById("status").innerText = "No dataset loaded";

  document.getElementById("error").innerText = "";

  if (currentChart) {
    currentChart.destroy();

    currentChart = null;
  }

  document.getElementById("chartPlaceholder").classList.remove("hidden");
}

/* -----------------------------------------
   HELPERS
----------------------------------------- */

function createColors(count) {
  const palette = [
    "#111827",
    "#374151",
    "#6b7280",
    "#9ca3af",
    "#4b5563",
    "#1f2937",
    "#71717a",
    "#52525b",
  ];

  return Array.from(
    {
      length: count,
    },

    (_, i) => palette[i % palette.length],
  );
}

function capitalize(value) {
  if (!value) {
    return "";
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
}

function renderChart(labels, values, chartType, title) {
  if (currentChart) {
    currentChart.destroy();
  }

  const canvas = document.getElementById("chart");

  const ctx = canvas.getContext("2d");

  document.getElementById("chartPlaceholder").classList.add("hidden");

  const colors = createColors(labels.length);

  currentChart = new Chart(ctx, {
    type: chartType,

    data: {
      labels,

      datasets: [
        {
          label: title,

          data: values,

          backgroundColor: chartType === "line" ? undefined : colors,

          borderColor: chartType === "line" ? "#111827" : undefined,

          borderWidth: chartType === "line" ? 2 : 1,

          tension: 0.25,

          fill: false,
        },
      ],
    },

    options: {
      responsive: true,

      maintainAspectRatio: false,

      plugins: {
        title: {
          display: true,

          text: title,

          font: {
            size: 15,
          },
        },

        legend: {
          display: chartType === "pie" || chartType === "doughnut",
        },
      },

      scales:
        chartType === "pie" || chartType === "doughnut"
          ? {}
          : {
              x: {
                grid: {
                  display: false,
                },
              },

              y: {
                beginAtZero: true,

                grid: {
                  color: "#f0f1f3",
                },
              },
            },
    },
  });
}

function escapeHtml(value) {
  return value

    .replaceAll("&", "&amp;")

    .replaceAll("<", "&lt;")

    .replaceAll(">", "&gt;")

    .replaceAll('"', "&quot;")

    .replaceAll("'", "&#039;");
}

/* -----------------------------------------
   STARTUP
----------------------------------------- */

window.addEventListener("DOMContentLoaded", async () => {
  await loadFiles();
});
