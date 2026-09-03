# Local Data Chart AI

Here’s a cleaner, more natural version:

I built this project to make working with large CSV exports easier. In some cases, the original database query could not efficiently handle additional aggregations or calculations, or would take too long to complete. This tool makes it easier to analyze, aggregate, and visualize the exported data locally without relying on increasingly complex queries.

A local CSV and table visualization tool with optional AI-assisted chart generation.

The application runs locally using:

- Flask
- Pandas
- Chart.js
- Ollama
- Qwen3

The AI is used only to interpret chart requests such as:

- `Show the 10 most common codes`
- `Show total amount per employee`
- `Show average amount by department`
- `Show status distribution as a pie chart`

The actual calculations are performed by Pandas.

---

## Features

- Paste raw CSV or table data
- Load CSV files from the local `data/` folder
- Preview dataset rows and columns
- Automatically detect numeric and text columns
- Generate:
  - Bar charts
  - Line charts
  - Pie charts
  - Doughnut charts

- Aggregations:
  - Count
  - Sum
  - Average
  - Minimum
  - Maximum

- AI-assisted chart generation using a local Ollama model
- Runs locally without sending CSV data to an external AI API

---

## Project Structure

```text
local-data-chart-ai/
│
├── data/
│   └── sample.csv
│
├── static/
│   └── app.js
│
├── templates/
│   └── index.html
│
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Requirements

Install:

- Python 3.10+
- Git
- Ollama

Recommended Ollama model:

```text
qwen3:4b
```

---

## Clone the Repository

```bash
git clone <repository-url>
cd local-data-chart-ai
```

---

## Create a Python Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should then see something similar to:

```text
(.venv) PS C:\...\local-data-chart-ai>
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## Install Python Dependencies

```bash
python -m pip install -r requirements.txt
```

The project currently requires:

```text
flask
pandas
requests
```

---

## Install Ollama

Install Ollama from the official Ollama website.

Verify that it is available:

```bash
ollama --version
```

---

## Download the AI Model

The recommended model for this project is:

```bash
ollama pull qwen3:4b
```

Verify installed models:

```bash
ollama list
```

You should see something similar to:

```text
NAME        SIZE
qwen3:4b    ...
```

---

## Start Ollama

Run:

```bash
ollama serve
```

Keep this terminal open.

Ollama should normally run locally on:

```text
http://127.0.0.1:11434
```

The Flask application communicates with Ollama through:

```text
http://127.0.0.1:11434/v1/chat/completions
```

---

## Start the Application

Open another terminal.

Activate the virtual environment if necessary:

```powershell
.\.venv\Scripts\Activate.ps1
```

Then run:

```bash
python main.py
```

You should see:

```text
Running on http://127.0.0.1:5000
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

---

## Using CSV Files

CSV files can be placed inside:

```text
data/
```

Example:

```text
data/
├── sample.csv
├── employees.csv
├── claims.csv
└── test-data.csv
```

Inside the application select:

```text
Data folder
```

and choose the desired CSV file.

If you add a file while the application is already running, use:

```text
Refresh files
```

---

## Example CSV

```csv
employee,status,amount
Peter,OPEN,500
Peter,CLOSED,200
Ana,OPEN,350
Ana,OPEN,450
John,CLOSED,800
Peter,OPEN,400
```

---

## Manual Chart Example

Select:

```text
Group by: employee
Aggregation: Sum
Value: amount
Chart type: Bar
```

The application will calculate the total amount for each employee.

---

## AI Chart Examples

After loading a dataset, use the AI input field.

Examples:

```text
Show total amount per employee
```

```text
Show average amount per employee
```

```text
Show the 5 most common codes
```

```text
Show status distribution as a pie chart
```

```text
Show employees ordered by total amount
```

The AI converts the request into a structured plan.

For example:

```json
{
  "xColumn": "employee",
  "yColumn": "amount",
  "aggregation": "sum",
  "chartType": "bar",
  "sort": "descending",
  "limit": null,
  "title": "Total amount per employee"
}
```

Pandas then performs the actual calculation.

---

## Architecture

```text
User
 │
 ├── Paste CSV
 │
 └── Select CSV file
        │
        ▼
     Flask
        │
        ▼
     Pandas
        │
        ├──────────────► Manual chart
        │
        │
        └──► Ollama / Qwen3
                  │
                  ▼
             AI chart plan
                  │
                  ▼
               Pandas
                  │
                  ▼
              Chart.js
```

The LLM does not calculate the chart values itself.

It only determines:

- which column to group by
- which numeric column to use
- which aggregation to perform
- how to sort the result
- which chart type to display

---

## Privacy

The Flask server runs locally on:

```text
127.0.0.1:5000
```

Ollama runs locally on:

```text
127.0.0.1:11434
```

CSV calculations are performed locally using Pandas.

Real CSV files should not be committed to Git.

The recommended `.gitignore` includes:

```gitignore
data/*.csv
!data/sample.csv
```

This allows a safe example CSV to remain in the repository while ignoring real datasets.

---

## Important: Virtual Environment

Do not commit the virtual environment.

It should be ignored with:

```gitignore
.venv/
venv/
```

If it was accidentally added to Git:

```bash
git rm -r --cached .venv
```

Then commit the change:

```bash
git add .gitignore
git commit -m "Ignore local virtual environment"
```

---

## Updating Dependencies

After installing a new Python package, update the requirements file:

```bash
pip freeze > requirements.txt
```

Then commit it:

```bash
git add requirements.txt
git commit -m "Update Python dependencies"
```

---

## Stop the Application

Press:

```text
Ctrl + C
```

in the Flask terminal.

Stop Ollama the same way if it was manually started using:

```bash
ollama serve
```

---

## Development

A normal development workflow is:

```bash
git pull
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start Ollama:

```bash
ollama serve
```

Start Flask:

```bash
python main.py
```

Then open:

```text
http://127.0.0.1:5000
```

---

## Future Improvements

Possible next improvements:

- filtering through natural-language prompts
- multiple grouping columns
- multiple chart series
- date/time analysis
- export charts as PNG
- export analyzed data as CSV
- dataset statistics
- automatic chart recommendations
- local Chart.js bundle for fully offline use
- configurable Ollama model
- AI-generated dataset summaries
