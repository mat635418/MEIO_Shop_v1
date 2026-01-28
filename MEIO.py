import os
import csv
import pandas as pd
import streamlit as st

# List of baseline CSV files expected in the root directory
BASELINE_CSV_FILES = [
    "sales_history_24m_piacenza_enhanced.csv",
    "products_master_enhanced.csv",
    "product_lifecycle.csv",
    "sales_forecast_12m_piacenza.csv",
    "leadtime_history_24m_piacenza.csv",
]

# Root directory where this script lives (the repo root on Streamlit Cloud)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="MEIO Shop v1", layout="wide")
st.title("MEIO Shop - CSV Preview")

# Sidebar: baseline files + upload
st.sidebar.header("CSV Files")

# Discover existing baseline CSVs
existing_files = []
for fname in BASELINE_CSV_FILES:
    path = os.path.join(ROOT_DIR, fname)
    if os.path.isfile(path):
        existing_files.append(fname)

if not existing_files:
    st.sidebar.warning("No baseline CSV files found in the app root directory.")
else:
    st.sidebar.success(f"Loaded {len(existing_files)} baseline CSV file(s) from root.")

# Keep track of an "extra" uploaded file in session state
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

uploaded = st.sidebar.file_uploader("Add CSV...", type=["csv"])
if uploaded is not None:
    st.session_state.uploaded_file = uploaded
    st.session_state.uploaded_file_name = uploaded.name

options = []
if existing_files:
    options.extend(existing_files)

if st.session_state.uploaded_file_name:
    options.append(f"[Uploaded] {st.session_state.uploaded_file_name}")

selected = st.sidebar.selectbox(
    "Select a CSV file to preview", options, index=0 if options else None
)

def load_csv_preview_from_path(path: str, max_rows: int = 100) -> pd.DataFrame:
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows + 1:  # header + up to max_rows
                    break
                rows.append(row)

        if not rows:
            st.info(f"{os.path.basename(path)}: file is empty.")
            return pd.DataFrame()

        headers = rows[0]
        data_rows = rows[1:]
        df = pd.DataFrame(data_rows, columns=headers)
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

def load_csv_preview_from_uploaded(uploaded_file, max_rows: int = 100) -> pd.DataFrame:
    try:
        # Let pandas read directly from the uploaded file-like object
        df = pd.read_csv(uploaded_file, nrows=max_rows)
        return df
    except Exception as e:
        st.error(f"Error loading uploaded CSV: {e}")
        return pd.DataFrame()

st.subheader("CSV Preview")

if not options:
    st.info("No CSV files available yet. Upload a CSV from the sidebar.")
else:
    if selected.startswith("[Uploaded]"):
        if st.session_state.uploaded_file is None:
            st.warning("Uploaded file is no longer available. Please upload again.")
        else:
            df = load_csv_preview_from_uploaded(st.session_state.uploaded_file)
            if not df.empty:
                st.write(
                    f"Showing {len(df)} row(s) from uploaded file "
                    f"`{st.session_state.uploaded_file_name}`."
                )
                st.dataframe(df, use_container_width=True)
    else:
        # Selected one of the baseline files
        path = os.path.join(ROOT_DIR, selected)
        if not os.path.isfile(path):
            st.error(f"File not found: {selected}")
        else:
            df = load_csv_preview_from_path(path)
            if not df.empty:
                st.write(
                    f"Showing up to {len(df)} row(s) "
                    f"from baseline file `{selected}`."
                )
                st.dataframe(df, use_container_width=True)
