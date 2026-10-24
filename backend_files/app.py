"""SuperKart Sales Forecast API — serves the trained pipeline over HTTP."""
import os
import joblib
import pandas as pd
from flask import Flask, request, jsonify

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "superkart_model.joblib")
model = joblib.load(MODEL_PATH)            # loaded ONCE when the server starts

NUMERIC = ["Product_Weight", "Product_Allocated_Area", "Product_MRP", "Store_Age_Years"]
CATEGORICAL = ["Product_Sugar_Content", "Store_Size", "Store_Location_City_Type", "Store_Type",
               "Product_Id_char", "Product_Type_Category"]
FEATURES = NUMERIC + CATEGORICAL

app = Flask("SuperKart Sales Forecaster")
app.json.sort_keys = False                # keep columns in their original order


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the incoming columns and coerce types so the pipeline receives clean input."""
    missing = [c for c in FEATURES if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing required field(s): {missing}")
    frame = frame[FEATURES].copy()
    for c in NUMERIC:
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
    bad = frame[NUMERIC].isna().any(axis=1)
    if bad.any():
        raise ValueError(f"Non-numeric or empty values in numeric fields at row(s): {[int(r) for r in frame.index[bad]]}")
    for c in CATEGORICAL:
        frame[c] = frame[c].astype(str).str.strip()
    frame["Product_Sugar_Content"] = frame["Product_Sugar_Content"].replace({"reg": "Regular"})
    return frame


@app.get("/")
def health():
    return jsonify(status="ok", service="SuperKart Sales Forecast API",
                   endpoints={"POST /v1/sales": "JSON body with the 10 features -> one forecast",
                              "POST /v1/sales/batch": "multipart CSV upload (field 'file') -> forecast per row"},
                   required_fields=FEATURES)


@app.post("/v1/sales")
def predict_single():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Send a JSON object with the 10 feature fields."), 400
    try:
        X = prepare(pd.DataFrame([payload]))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    prediction = float(model.predict(X)[0])
    return jsonify(Predicted_Sales=round(prediction, 2))


@app.post("/v1/sales/batch")
def predict_batch():
    upload = request.files.get("file")
    if upload is None:
        return jsonify(error="Upload a CSV file in the form field 'file'."), 400
    try:
        frame = pd.read_csv(upload)
        X = prepare(frame)
    except (ValueError, pd.errors.ParserError) as exc:
        return jsonify(error=str(exc)), 400
    frame["Predicted_Sales"] = model.predict(X).round(2)
    return jsonify(n_rows=int(len(frame)),
                   total_predicted_sales=round(float(frame["Predicted_Sales"].sum()), 2),
                   predictions=frame.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)
