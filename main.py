from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
import io
import os
import json
import re


app = Flask(__name__)

DATA_FOLDER = "data"

# ---------------------------------------------------------
# OLLAMA CONFIGURATION
# ---------------------------------------------------------

OLLAMA_URL = "http://127.0.0.1:11434/v1/chat/completions"

# Make sure you have:
# ollama pull qwen3:4b
MODEL_NAME = "qwen3:4b"


# ---------------------------------------------------------
# DATA
# ---------------------------------------------------------

def read_input(data, input_type):

    if input_type == "file":

        filename = data.strip()

        if not filename:
            raise ValueError("No CSV file selected.")

        safe_filename = os.path.basename(filename)

        path = os.path.join(
            DATA_FOLDER,
            safe_filename
        )

        if not os.path.exists(path):
            raise ValueError(
                f"File does not exist: {safe_filename}"
            )

        if not safe_filename.lower().endswith(".csv"):
            raise ValueError(
                "Only CSV files are supported."
            )

        df = pd.read_csv(path)

    else:

        text = data.strip()

        if not text:
            raise ValueError(
                "No data was provided."
            )

        try:

            df = pd.read_csv(
                io.StringIO(text)
            )

            if len(df.columns) == 1:

                df = pd.read_csv(
                    io.StringIO(text),
                    sep=None,
                    engine="python"
                )

        except Exception:

            df = pd.read_csv(
                io.StringIO(text),
                sep=None,
                engine="python"
            )

    if df.empty:
        raise ValueError(
            "Dataset is empty."
        )

    return df


# ---------------------------------------------------------
# COLUMN TYPE DETECTION
# ---------------------------------------------------------

def get_columns_info(df):

    columns = []

    for column in df.columns:

        numeric_version = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        numeric_percentage = (
            numeric_version
            .notna()
            .mean()
        )

        column_type = (
            "number"
            if numeric_percentage > 0.8
            else "text"
        )

        sample_values = (
            df[column]
            .dropna()
            .astype(str)
            .unique()[:5]
            .tolist()
        )

        columns.append({
            "name": str(column),
            "type": column_type,
            "examples": sample_values
        })

    return columns


# ---------------------------------------------------------
# OLLAMA
# ---------------------------------------------------------

def ask_ollama(messages):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0,
            "stream": False
        },
        timeout=180
    )

    response.raise_for_status()

    result = response.json()

    return (
        result["choices"][0]
        ["message"]
        ["content"]
    )


# ---------------------------------------------------------
# CLEAN JSON RETURNED BY MODEL
# ---------------------------------------------------------

def extract_json(text):

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if not match:
            raise ValueError(
                "AI did not return valid JSON."
            )

        return json.loads(
            match.group(0)
        )


# ---------------------------------------------------------
# AI CHART PLAN
# ---------------------------------------------------------

def create_ai_plan(df, question):

    columns_info = get_columns_info(df)

    prompt = f"""
You control a local data visualization application.

The user has loaded a CSV dataset.

Dataset information:

Rows:
{len(df)}

Columns:
{json.dumps(columns_info, indent=2)}

User request:

{question}

Your job is ONLY to choose how the data should be analyzed
and visualized.

Return exactly ONE JSON object.

Allowed fields:

{{
    "xColumn": "column name",
    "yColumn": "column name or null",
    "aggregation": "count | sum | average | min | max",
    "chartType": "bar | line | pie | doughnut",
    "sort": "descending | ascending | none",
    "limit": number or null,
    "title": "short chart title"
}}

Rules:

1. Use "count" only when the user wants:
   frequency, occurrences, repeated values,
   most common, least common, or record counts.

2. For count:
   yColumn must be null.

3. If the user asks for a numeric measure such as:
   amount, value, price, cost, revenue, salary, total,
   quantity, score, duration, or another numeric measure
   per category, DO NOT use count.

4. For a numeric measure per category:
   - xColumn = category column
   - yColumn = numeric measure column
   - aggregation = sum by default

5. If the user explicitly asks for:
   average -> aggregation = average
   minimum -> aggregation = min
   maximum -> aggregation = max

6. For sum, average, min or max,
   yColumn MUST contain the exact name of a numeric column.

7. Use bar charts for comparisons.

8. Use pie or doughnut only for small category distributions.

9. Use line charts mainly for ordered or time-based data.

10. "Top 10" means:
    sort = descending
    limit = 10

11. "Most common" means:
    aggregation = count
    sort = descending

12. "Least common" means:
    aggregation = count
    sort = ascending

13. Never invent column names.
    Use column names exactly as provided in Dataset information.

14. Return JSON only.
No markdown.
No explanation.

Examples:

User:
Show total amount per employee

Response:
{{
    "xColumn": "employee",
    "yColumn": "amount",
    "aggregation": "sum",
    "chartType": "bar",
    "sort": "descending",
    "limit": null,
    "title": "Total amount per employee"
}}

User:
Show average amount per employee

Response:
{{
    "xColumn": "employee",
    "yColumn": "amount",
    "aggregation": "average",
    "chartType": "bar",
    "sort": "descending",
    "limit": null,
    "title": "Average amount per employee"
}}

User:
Show the 5 most common codes

Response:
{{
    "xColumn": "code",
    "yColumn": null,
    "aggregation": "count",
    "chartType": "bar",
    "sort": "descending",
    "limit": 5,
    "title": "Top 5 codes"
}}
"""

    answer = ask_ollama([
        {
            "role": "system",
            "content":
                "You are a precise data-analysis routing engine. "
                "Always return valid JSON and always select a yColumn "
                "for numeric aggregations."
        },
        {
            "role": "user",
            "content": prompt
        }
    ])

    plan = extract_json(answer)

    print("\nRAW AI RESPONSE:")
    print(answer)

    print("\nPARSED AI PLAN:")
    print(
        json.dumps(
            plan,
            indent=2
        )
    )

    return validate_ai_plan(
        df,
        plan,
        question
    )


# ---------------------------------------------------------
# VALIDATE + REPAIR AI OUTPUT
# ---------------------------------------------------------

def validate_ai_plan(
    df,
    plan,
    question=""
):

    allowed_aggregations = {
        "count",
        "sum",
        "average",
        "min",
        "max"
    }

    allowed_charts = {
        "bar",
        "line",
        "pie",
        "doughnut"
    }

    allowed_sort = {
        "ascending",
        "descending",
        "none"
    }

    question_lower = (
        question
        .lower()
        .strip()
    )

    # -------------------------------------------------
    # X COLUMN
    # -------------------------------------------------

    x_column = plan.get(
        "xColumn"
    )

    if x_column not in df.columns:
        raise ValueError(
            f"AI selected invalid column: {x_column}"
        )

    # -------------------------------------------------
    # AGGREGATION
    # -------------------------------------------------

    aggregation = plan.get(
        "aggregation",
        "count"
    )

    if aggregation not in allowed_aggregations:
        aggregation = "count"

    # -------------------------------------------------
    # IDENTIFY NUMERIC COLUMNS
    # -------------------------------------------------

    numeric_columns = []

    for column in df.columns:

        numeric_data = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        if (
            numeric_data
            .notna()
            .mean()
            > 0.8
        ):
            numeric_columns.append(
                column
            )

    # -------------------------------------------------
    # Y COLUMN
    # -------------------------------------------------

    y_column = plan.get(
        "yColumn"
    )

    if aggregation == "count":

        y_column = None

    else:

        # AI supplied a value column,
        # but verify that it actually exists.

        if (
            y_column
            and
            y_column not in df.columns
        ):
            y_column = None

        # ---------------------------------------------
        # REPAIR MISSING Y COLUMN
        # ---------------------------------------------

        if not y_column:

            # First:
            # match an actual numeric column
            # explicitly mentioned in the question.

            for column in numeric_columns:

                if (
                    column.lower()
                    in question_lower
                ):
                    y_column = column
                    break

        if not y_column:

            # Second:
            # try semantic hints in common column names.

            hints = [
                "amount",
                "value",
                "price",
                "cost",
                "revenue",
                "salary",
                "total",
                "quantity",
                "score",
                "duration"
            ]

            for hint in hints:

                if hint in question_lower:

                    for column in numeric_columns:

                        if (
                            hint
                            in column.lower()
                        ):
                            y_column = column
                            break

                if y_column:
                    break

        if not y_column:

            # Third:
            # if there is only one usable numeric column,
            # use it automatically.

            candidates = [
                column
                for column in numeric_columns
                if column != x_column
            ]

            if len(candidates) == 1:
                y_column = candidates[0]

        if not y_column:

            raise ValueError(
                "AI selected a numeric aggregation "
                "but no value column could be determined. "
                f"Numeric columns found: {numeric_columns}"
            )

        if y_column not in df.columns:

            raise ValueError(
                f"AI selected invalid value column: {y_column}"
            )

    # -------------------------------------------------
    # CHART TYPE
    # -------------------------------------------------

    chart_type = plan.get(
        "chartType",
        "bar"
    )

    if chart_type not in allowed_charts:
        chart_type = "bar"

    # -------------------------------------------------
    # SORT
    # -------------------------------------------------

    sort = plan.get(
        "sort",
        "descending"
    )

    if sort not in allowed_sort:
        sort = "descending"

    # -------------------------------------------------
    # LIMIT
    # -------------------------------------------------

    limit = plan.get(
        "limit"
    )

    if limit is not None:

        try:
            limit = int(
                limit
            )

        except Exception:
            limit = None

        if limit is not None:

            limit = max(
                1,
                min(
                    limit,
                    100
                )
            )

    # -------------------------------------------------
    # TITLE
    # -------------------------------------------------

    title = plan.get(
        "title",
        "AI generated chart"
    )

    return {
        "xColumn": x_column,
        "yColumn": y_column,
        "aggregation": aggregation,
        "chartType": chart_type,
        "sort": sort,
        "limit": limit,
        "title": title
    }


# ---------------------------------------------------------
# CALCULATE CHART DATA
# ---------------------------------------------------------

def calculate_chart(
    df,
    x_column,
    y_column,
    aggregation,
    sort="descending",
    limit=None
):

    if x_column not in df.columns:

        raise ValueError(
            f"Column '{x_column}' does not exist."
        )

    # -------------------------------------------------
    # COUNT
    # -------------------------------------------------

    if aggregation == "count":

        result = (
            df.groupby(
                x_column,
                dropna=False
            )
            .size()
            .reset_index(
                name="value"
            )
        )

    # -------------------------------------------------
    # NUMERIC AGGREGATION
    # -------------------------------------------------

    else:

        if not y_column:

            raise ValueError(
                "Select a numeric Value column."
            )

        if y_column not in df.columns:

            raise ValueError(
                f"Column '{y_column}' does not exist."
            )

        working_df = df.copy()

        working_df[y_column] = (
            pd.to_numeric(
                working_df[y_column],
                errors="coerce"
            )
        )

        grouped = (
            working_df
            .groupby(
                x_column,
                dropna=False
            )[y_column]
        )

        if aggregation == "sum":

            result = (
                grouped
                .sum()
                .reset_index(
                    name="value"
                )
            )

        elif aggregation == "average":

            result = (
                grouped
                .mean()
                .reset_index(
                    name="value"
                )
            )

        elif aggregation == "min":

            result = (
                grouped
                .min()
                .reset_index(
                    name="value"
                )
            )

        elif aggregation == "max":

            result = (
                grouped
                .max()
                .reset_index(
                    name="value"
                )
            )

        else:

            raise ValueError(
                "Unsupported aggregation."
            )

    result = (
        result
        .dropna(
            subset=["value"]
        )
    )

    # -------------------------------------------------
    # SORT
    # -------------------------------------------------

    if sort == "descending":

        result = (
            result
            .sort_values(
                "value",
                ascending=False
            )
        )

    elif sort == "ascending":

        result = (
            result
            .sort_values(
                "value",
                ascending=True
            )
        )

    # -------------------------------------------------
    # LIMIT
    # -------------------------------------------------

    if limit:

        result = (
            result
            .head(limit)
        )

    labels = (
        result[x_column]
        .fillna("(empty)")
        .astype(str)
        .tolist()
    )

    values = (
        result["value"]
        .round(2)
        .tolist()
    )

    return (
        labels,
        values
    )


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


@app.route("/files")
def list_files():

    os.makedirs(
        DATA_FOLDER,
        exist_ok=True
    )

    files = [

        filename

        for filename
        in os.listdir(
            DATA_FOLDER
        )

        if (
            filename
            .lower()
            .endswith(".csv")

            and

            os.path.isfile(
                os.path.join(
                    DATA_FOLDER,
                    filename
                )
            )
        )
    ]

    return jsonify({
        "success": True,
        "files": sorted(files)
    })


# ---------------------------------------------------------
# ANALYZE
# ---------------------------------------------------------

@app.route(
    "/analyze",
    methods=["POST"]
)
def analyze():

    try:

        payload = (
            request.get_json()
            or {}
        )

        data = payload.get(
            "data",
            ""
        )

        input_type = payload.get(
            "inputType",
            "raw"
        )

        df = read_input(
            data,
            input_type
        )

        columns = (
            get_columns_info(
                df
            )
        )

        frontend_columns = [
            {
                "name": c["name"],
                "type": c["type"]
            }
            for c in columns
        ]

        preview = (
            df.head(50)
            .fillna("")
            .astype(str)
            .to_dict(
                orient="records"
            )
        )

        return jsonify({
            "success": True,
            "rows": len(df),
            "columns": frontend_columns,
            "preview": preview
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


# ---------------------------------------------------------
# MANUAL CHART
# ---------------------------------------------------------

@app.route(
    "/chart",
    methods=["POST"]
)
def chart():

    try:

        payload = (
            request.get_json()
            or {}
        )

        df = read_input(
            payload.get(
                "data",
                ""
            ),
            payload.get(
                "inputType",
                "raw"
            )
        )

        labels, values = (
            calculate_chart(

                df,

                payload.get(
                    "xColumn"
                ),

                payload.get(
                    "yColumn"
                ),

                payload.get(
                    "aggregation",
                    "count"
                ),

                sort="descending",

                limit=None
            )
        )

        return jsonify({
            "success": True,
            "labels": labels,
            "values": values
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


# ---------------------------------------------------------
# AI CHART
# ---------------------------------------------------------

@app.route(
    "/ai-chart",
    methods=["POST"]
)
def ai_chart():

    try:

        payload = (
            request.get_json()
            or {}
        )

        data = payload.get(
            "data",
            ""
        )

        input_type = payload.get(
            "inputType",
            "raw"
        )

        question = (
            payload.get(
                "question",
                ""
            )
            .strip()
        )

        if not question:

            raise ValueError(
                "Enter a request for the AI."
            )

        df = read_input(
            data,
            input_type
        )

        plan = create_ai_plan(
            df,
            question
        )

        print("\nFINAL VALIDATED PLAN:")
        print(
            json.dumps(
                plan,
                indent=2
            )
        )

        labels, values = (
            calculate_chart(

                df,

                plan[
                    "xColumn"
                ],

                plan[
                    "yColumn"
                ],

                plan[
                    "aggregation"
                ],

                sort=plan[
                    "sort"
                ],

                limit=plan[
                    "limit"
                ]
            )
        )

        return jsonify({
            "success": True,
            "plan": plan,
            "labels": labels,
            "values": values
        })

    except requests.exceptions.ConnectionError:

        return jsonify({
            "success": False,
            "error":
                "Could not connect to Ollama. "
                "Make sure 'ollama serve' is running."
        }), 503

    except requests.exceptions.Timeout:

        return jsonify({
            "success": False,
            "error":
                "Ollama took too long to respond."
        }), 504

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 400


# ---------------------------------------------------------
# START
# ---------------------------------------------------------

if __name__ == "__main__":

    os.makedirs(
        DATA_FOLDER,
        exist_ok=True
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )