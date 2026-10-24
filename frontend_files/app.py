"""SuperKart Sales Forecast — Streamlit frontend. Holds no model: it calls the Flask backend."""
import os
import requests
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:7860").rstrip("/")

STORES = {   # profiles of the four existing stores (from the training data; age = 2025 - established)
    "OUT001 — Supermarket Type1, Tier 2": dict(Store_Size="High", Store_Location_City_Type="Tier 2",
                                               Store_Type="Supermarket Type1", Store_Age_Years=38),
    "OUT002 — Food Mart, Tier 3": dict(Store_Size="Small", Store_Location_City_Type="Tier 3",
                                       Store_Type="Food Mart", Store_Age_Years=27),
    "OUT003 — Departmental Store, Tier 1": dict(Store_Size="Medium", Store_Location_City_Type="Tier 1",
                                                Store_Type="Departmental Store", Store_Age_Years=26),
    "OUT004 — Supermarket Type2, Tier 2": dict(Store_Size="Medium", Store_Location_City_Type="Tier 2",
                                               Store_Type="Supermarket Type2", Store_Age_Years=16),
}
PRODUCT_TYPES = {  # product type -> (Product_Id_char, Product_Type_Category)
    "Fruits and Vegetables": ("FD", "Perishables"), "Dairy": ("FD", "Perishables"), "Meat": ("FD", "Perishables"),
    "Breads": ("FD", "Perishables"), "Breakfast": ("FD", "Perishables"), "Seafood": ("FD", "Perishables"),
    "Snack Foods": ("FD", "Non Perishables"), "Frozen Foods": ("FD", "Non Perishables"),
    "Baking Goods": ("FD", "Non Perishables"), "Canned": ("FD", "Non Perishables"),
    "Starchy Foods": ("FD", "Non Perishables"), "Soft Drinks": ("DR", "Non Perishables"),
    "Hard Drinks": ("DR", "Non Perishables"), "Household": ("NC", "Non Perishables"),
    "Health and Hygiene": ("NC", "Non Perishables"), "Others": ("NC", "Non Perishables"),
}

st.set_page_config(page_title="SuperKart Sales Forecast", page_icon="🛒", layout="wide")
st.title("🛒 SuperKart — Quarterly Sales Forecast")
st.caption("Predicts Product_Store_Sales_Total for a product in a store. "
           f"Model served by the Flask API at `{BACKEND_URL}`.")

tab_single, tab_batch = st.tabs(["Single forecast", "Batch forecast (CSV)"])

with tab_single:
    left, right = st.columns(2)
    with left:
        st.subheader("Product")
        product_type = st.selectbox("Product type", list(PRODUCT_TYPES))
        id_char, category = PRODUCT_TYPES[product_type]
        if id_char == "NC":
            sugar = "No Sugar"
            st.text_input("Sugar content", sugar, disabled=True, help="Non-consumables are always 'No Sugar'")
        else:
            sugar = st.selectbox("Sugar content", ["Low Sugar", "Regular", "No Sugar"])
        weight = st.number_input("Product weight", min_value=1.0, max_value=30.0, value=12.66, step=0.1)
        mrp = st.number_input("Product MRP (max retail price)", min_value=10.0, max_value=400.0, value=147.0, step=1.0)
        area = st.number_input("Allocated display area (share of store display)", min_value=0.001, max_value=0.400,
                               value=0.056, step=0.001, format="%.3f")
        st.caption(f"Derived → Product_Id_char = **{id_char}**, Product_Type_Category = **{category}**")
    with right:
        st.subheader("Store")
        store_choice = st.selectbox("Store", list(STORES) + ["Custom store (what-if)"])
        if store_choice in STORES:
            store = STORES[store_choice]
            st.table(pd.DataFrame(store, index=["value"]).T)
        else:
            store = dict(
                Store_Size=st.selectbox("Store size", ["Small", "Medium", "High"]),
                Store_Location_City_Type=st.selectbox("City tier", ["Tier 1", "Tier 2", "Tier 3"]),
                Store_Type=st.selectbox("Store type", ["Departmental Store", "Supermarket Type1",
                                                       "Supermarket Type2", "Food Mart"]),
                Store_Age_Years=st.number_input("Store age (years)", min_value=0, max_value=60, value=15))
            st.warning("Custom combinations outside the 4 existing store profiles are extrapolations — treat as indicative.")

    payload = dict(Product_Weight=weight, Product_Sugar_Content=sugar, Product_Allocated_Area=area,
                   Product_MRP=mrp, Product_Id_char=id_char, Product_Type_Category=category, **store)

    if st.button("Predict sales", type="primary"):
        try:
            resp = requests.post(f"{BACKEND_URL}/v1/sales", json=payload, timeout=60)
            if resp.ok:
                st.success(f"Forecast revenue for this product in this store: **{resp.json()['Predicted_Sales']:,.2f}**")
            else:
                st.error(f"Backend returned {resp.status_code}: {resp.text}")
        except requests.RequestException as exc:
            st.error(f"Could not reach the backend: {exc}")
    with st.expander("JSON sent to the backend"):
        st.json(payload)

with tab_batch:
    st.write("Upload a CSV with the columns: Product_Weight, Product_Sugar_Content, Product_Allocated_Area, "
             "Product_MRP, Store_Size, Store_Location_City_Type, Store_Type, Product_Id_char, "
             "Store_Age_Years, Product_Type_Category.")
    upload = st.file_uploader("Batch file", type=["csv"])
    if upload is not None and st.button("Predict batch", type="primary"):
        try:
            resp = requests.post(f"{BACKEND_URL}/v1/sales/batch",
                                 files={"file": (upload.name, upload.getvalue(), "text/csv")}, timeout=120)
            if resp.ok:
                body = resp.json()
                result = pd.DataFrame(body["predictions"])
                result = result[["Predicted_Sales"] + [c for c in result.columns if c != "Predicted_Sales"]]
                c1, c2 = st.columns(2)
                c1.metric("Rows forecast", body["n_rows"])
                c2.metric("Total predicted sales", f"{body['total_predicted_sales']:,.2f}")
                st.dataframe(result, use_container_width=True)
                st.download_button("Download forecasts (CSV)", result.to_csv(index=False),
                                   "superkart_forecasts.csv", "text/csv")
            else:
                st.error(f"Backend returned {resp.status_code}: {resp.text}")
        except requests.RequestException as exc:
            st.error(f"Could not reach the backend: {exc}")
