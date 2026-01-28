import os
import pandas as pd
import streamlit as st

# -------------------------------------------------------------------
# APP CONFIG
# -------------------------------------------------------------------
st.set_page_config(page_title="MEIO Shop v1", layout="wide")
st.title("MEIO Shop - MEIO Dashboard (Method 5 SS Optimizer)")

# -------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------
# Expected baseline CSVs
EXPECTED_FILES = {
    "sales_history": "sales_history_24m_piacenza_enhanced.csv",
    "products_master": "products_master_enhanced.csv",
    "product_lifecycle": "product_lifecycle.csv",
    "sales_forecast": "sales_forecast_12m_piacenza.csv",
    "leadtime_history": "leadtime_history_24m_piacenza.csv",
}

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------------------------------------------------
# SESSION STATE INIT
# -------------------------------------------------------------------
if "dataframes" not in st.session_state:
    st.session_state.dataframes = {k: None for k in EXPECTED_FILES.keys()}

if "params" not in st.session_state:
    st.session_state.params = {}

# -------------------------------------------------------------------
# SIDEBAR – FILE UPLOADS & PARAMETERS
# -------------------------------------------------------------------
st.sidebar.header("Data Inputs")

uploaded_any = False

def load_default_or_uploaded(label_key: str, display_name: str):
    """
    Handles a single CSV source:
    - Tries file_uploader
    - If none uploaded, tries to load from ROOT_DIR with the expected file name
    """
    expected_fname = EXPECTED_FILES[label_key]

    uploaded_file = st.sidebar.file_uploader(
        f"{display_name} ({expected_fname})",
        type=["csv"],
        key=f"uploader_{label_key}",
    )

    df = None
    src = None

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            src = "uploaded"
        except Exception as e:
            st.sidebar.error(f"Error reading uploaded {display_name}: {e}")
    else:
        # Try loading from local baseline file in ROOT_DIR
        baseline_path = os.path.join(ROOT_DIR, expected_fname)
        if os.path.isfile(baseline_path):
            try:
                df = pd.read_csv(baseline_path)
                src = "baseline"
            except Exception as e:
                st.sidebar.error(f"Error reading baseline {display_name}: {e}")

    if df is not None:
        st.session_state.dataframes[label_key] = df
        if src == "uploaded":
            st.sidebar.success(f"{display_name}: using uploaded file")
        else:
            st.sidebar.info(f"{display_name}: using baseline file from repo")
        return True
    else:
        st.sidebar.warning(f"{display_name}: no data available")
        st.session_state.dataframes[label_key] = None
        return False


# 1) Upload / load each CSV
avail_sales_hist = load_default_or_uploaded("sales_history", "Sales History (24m)")
avail_prod_master = load_default_or_uploaded("products_master", "Products Master")
avail_prod_lifecycle = load_default_or_uploaded("product_lifecycle", "Product Lifecycle")
avail_sales_fcst = load_default_or_uploaded("sales_forecast", "Sales Forecast (12m)")
avail_lt_hist = load_default_or_uploaded("leadtime_history", "Lead Time History (24m)")

all_available = (
    avail_sales_hist
    and avail_prod_master
    and avail_prod_lifecycle
    and avail_sales_fcst
    and avail_lt_hist
)

st.sidebar.markdown("---")
st.sidebar.header("Parameters")

# PARAMETERS (you can tune ranges / defaults)
sl = st.sidebar.slider(
    "Service Level (SL, %)", min_value=80, max_value=99, value=95, step=1
)
min_ss = st.sidebar.number_input(
    "Minimum Safety Stock (units)", min_value=0, value=0, step=1
)
max_ss_mult = st.sidebar.slider(
    "Max Safety Stock Multiplier (vs. avg monthly demand)",
    min_value=1.0,
    max_value=10.0,
    value=4.0,
    step=0.5,
)
demand_var_factor = st.sidebar.slider(
    "Demand Variability Factor", min_value=0.5, max_value=3.0, value=1.0, step=0.1
)
lt_var_factor = st.sidebar.slider(
    "Lead Time Variability Factor", min_value=0.5, max_value=3.0, value=1.0, step=0.1
)

st.session_state.params = {
    "SL": sl / 100.0,  # store as probability
    "min_ss": min_ss,
    "max_ss_mult": max_ss_mult,
    "demand_var_factor": demand_var_factor,
    "lt_var_factor": lt_var_factor,
}

# -------------------------------------------------------------------
# PLACEHOLDER: METHOD 5 SS CALCULATION
# -------------------------------------------------------------------
def method5_compute_ss(
    merged_df: pd.DataFrame,
    sl: float,
    min_ss: float,
    max_ss_mult: float,
    demand_var_factor: float,
    lt_var_factor: float,
) -> pd.DataFrame:
    """
    Placeholder for the real Method 5 SS calculation.

    EXPECTED INPUT:
    - merged_df: should contain, at minimum:
        - 'material_shop' (or similar key)
        - 'avg_monthly_demand'
        - 'demand_std'
        - 'avg_lead_time'
        - 'lead_time_std'
      The actual column names can be adapted once we know your model.

    CURRENT BEHAVIOR (dummy logic):
    - Calculates a simple "risk index" from demand and lead time variability.
    - Scales safety stock roughly as avg_demand * sqrt(lead_time) * risk factors.
    - Clips to [min_ss, max_ss_mult * avg_monthly_demand].
    - Returns merged_df with an added column 'SS_optimal'.
    """

    df = merged_df.copy()

    # --- PLACEHOLDER: define fallback columns if they don't yet exist ---
    # If your data already has the right measures, remove these fallbacks
    if "avg_monthly_demand" not in df.columns:
        # naive proxy: if you have a monthly fcst col, or use sales
        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            df["avg_monthly_demand"] = df[numeric_cols[0]].abs()
        else:
            df["avg_monthly_demand"] = 0.0

    if "demand_std" not in df.columns:
        df["demand_std"] = df["avg_monthly_demand"] * 0.5

    if "avg_lead_time" not in df.columns:
        df["avg_lead_time"] = 1.0

    if "lead_time_std" not in df.columns:
        df["lead_time_std"] = df["avg_lead_time"] * 0.3

    # --- Dummy "risk index" ---
    # (THIS IS NOT METHOD 5 – just a scaffold to visualize something.)
    df["risk_index"] = (
        df["demand_std"] * demand_var_factor
        + df["lead_time_std"] * lt_var_factor
    )

    # Rough proxy for a z-factor from SL; for now, map [0.8–0.99] to ~[0.85–2.33]
    # You would replace with the exact z from the normal distribution if Method 5 uses it.
    z_approx = 0.85 + (sl - 0.8) * (2.33 - 0.85) / (0.99 - 0.8)
    z_approx = max(0.0, z_approx)

    df["SS_raw"] = z_approx * df["risk_index"] * (df["avg_lead_time"] ** 0.5)

    # Clip SS to [min_ss, max_ss_mult * avg_monthly_demand]
    df["SS_optimal"] = df["SS_raw"].clip(
        lower=min_ss, upper=max_ss_mult * df["avg_monthly_demand"]
    )

    return df

# -------------------------------------------------------------------
# DATA PREPARATION (JOINING TABLES)
# -------------------------------------------------------------------
st.subheader("Data Status")

def show_df_info(label: str, df: pd.DataFrame | None):
    if df is None:
        st.markdown(f"- **{label}**: ❌ not available")
    else:
        st.markdown(
            f"- **{label}**: ✅ {df.shape[0]} rows, {df.shape[1]} columns"
        )

show_df_info("Sales History (24m)", st.session_state.dataframes["sales_history"])
show_df_info("Products Master", st.session_state.dataframes["products_master"])
show_df_info("Product Lifecycle", st.session_state.dataframes["product_lifecycle"])
show_df_info("Sales Forecast (12m)", st.session_state.dataframes["sales_forecast"])
show_df_info("Lead Time History (24m)", st.session_state.dataframes["leadtime_history"])

if not all_available:
    st.warning(
        "Not all data sources are available. "
        "Upload the missing files or add them to the repo root to proceed."
    )
    st.stop()

st.markdown("---")
st.subheader("MEIO – Method 5 SS Optimization")

# -------------------------------------------------------------------
# BUILD A WORKING DATASET
# -------------------------------------------------------------------
# For now, we assume there is a common key like 'material_shop'.
# If your actual join keys are different (e.g., material + shop columns),
# we can adjust the merging logic.

sales_hist = st.session_state.dataframes["sales_history"]
prod_master = st.session_state.dataframes["products_master"]
prod_lifecycle = st.session_state.dataframes["product_lifecycle"]
sales_fcst = st.session_state.dataframes["sales_forecast"]
lt_hist = st.session_state.dataframes["leadtime_history"]

# Guess a join key – adapt here once we know the real schema
POTENTIAL_KEYS = ["material_shop", "Material_Shop", "materialShop", "SKU_Shop"]

join_key = None
for k in POTENTIAL_KEYS:
    if k in sales_hist.columns:
        join_key = k
        break

if join_key is None:
    st.error(
        "Could not find a common 'material_shop' key in Sales History. "
        "Please share your schema so we can configure the joins correctly."
    )
    st.stop()

st.info(f"Using `{join_key}` as the primary key for the MEIO aggregation.")

# Merge everything step by step on the chosen key.
df_working = sales_hist.copy()

def safe_merge(left, right, key, how="left", suffix):
    common_cols = list(set(left.columns).intersection(set(right.columns)) - {key})
    right_renamed = right.rename(
        columns={c: f"{c}{suffix}" for c in common_cols}
    )
    return left.merge(right_renamed, on=key, how=how)

df_working = safe_merge(df_working, sales_fcst, join_key, how="left", suffix="_fcst")
df_working = safe_merge(df_working, prod_master, join_key, how="left", suffix="_pm")
df_working = safe_merge(df_working, prod_lifecycle, join_key, how="left", suffix="_pl")
df_working = safe_merge(df_working, lt_hist, join_key, how="left", suffix="_lt")

st.write(f"Working dataset size after merges: {df_working.shape[0]} rows, {df_working.shape[1]} columns")

# Optional: let user quickly preview a few rows
with st.expander("Preview merged dataset (first 50 rows)"):
    st.dataframe(df_working.head(50), use_container_width=True)

# -------------------------------------------------------------------
# COMPUTE SS (METHOD 5 PLACEHOLDER)
# -------------------------------------------------------------------
compute_btn = st.button("Compute Optimal SS by Material_Shop")

if compute_btn:
    params = st.session_state.params
    result_df = method5_compute_ss(
        df_working,
        sl=params["SL"],
        min_ss=params["min_ss"],
        max_ss_mult=params["max_ss_mult"],
        demand_var_factor=params["demand_var_factor"],
        lt_var_factor=params["lt_var_factor"],
    )

    # Extract only a few key columns for display
    display_cols = [join_key, "SS_optimal"]
    for c in ["avg_monthly_demand", "demand_std", "avg_lead_time", "lead_time_std"]:
        if c in result_df.columns:
            display_cols.append(c)

    result_view = result_df[display_cols].copy()

    st.success("Safety Stock (SS) computed successfully (placeholder Method 5).")
    st.write(
        "Below is the SS per material-shop combination. "
        "Once we plug in the actual Method 5 formula, these values will reflect the true optimization."
    )

    # Simple filters
    col1, col2 = st.columns(2)
    with col1:
        unique_keys = sorted(result_view[join_key].dropna().astype(str).unique())
        search_term = st.text_input("Filter material_shop (contains):", "")
    with col2:
        min_ss_filter = st.number_input(
            "Show only rows with SS_optimal ≥", min_value=0.0, value=0.0, step=1.0
        )

    filtered = result_view.copy()
    if search_term:
        filtered = filtered[filtered[join_key].astype(str).str.contains(search_term, case=False)]
    filtered = filtered[filtered["SS_optimal"] >= min_ss_filter]

    st.dataframe(filtered, use_container_width=True)

    # Optional: allow user to download the result
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download SS results as CSV",
        data=csv_bytes,
        file_name="meio_ss_optimal_results.csv",
        mime="text/csv",
    )
else:
    st.info("Set parameters in the sidebar and click **Compute Optimal SS by Material_Shop** to run the MEIO calculation.")
