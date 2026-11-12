import streamlit as st
import pandas as pd


# ---------- 1. Page setup ----------
st.set_page_config(page_title="Credit Risk Analysis", layout="wide")
st.title("Credit Risk Analysis Dashboard")
st.caption("Data source: MySQL database credit_risk, table loan_data")

# ---------- 2.load csv-------------
df = pd.read_csv("loan_data.csv")


# Show the columns in a logical order (same order as the cleaned table)
ordered_cols = [
    # 1. Identity and loan type
    'SK_ID_CURR', 'NAME_CONTRACT_TYPE', 'NAME_CLIENT_TYPE', 'NAME_CASH_LOAN_PURPOSE',
    'NAME_PRODUCT_TYPE', 'NAME_PORTFOLIO', 'PRODUCT_COMBINATION', 'NAME_GOODS_CATEGORY',
    # 2. Decision
    'NAME_CONTRACT_STATUS', 'CODE_REJECT_REASON', 'DAYS_DECISION',
    # 3. Amounts
    'AMT_APPLICATION', 'AMT_CREDIT', 'AMT_ANNUITY', 'AMT_GOODS_PRICE',
    'AMT_DOWN_PAYMENT', 'RATE_DOWN_PAYMENT',
    # 4. Payment terms
    'CNT_PAYMENT', 'NAME_YIELD_GROUP', 'NAME_PAYMENT_TYPE', 'NFLAG_INSURED_ON_APPROVAL',
    # 5. Repayment timeline
    'DAYS_FIRST_DUE', 'DAYS_LAST_DUE_1ST_VERSION', 'DAYS_LAST_DUE', 'DAYS_TERMINATION',
    # 6. Application process and channel
    'WEEKDAY_APPR_PROCESS_START', 'HOUR_APPR_PROCESS_START',
    'FLAG_LAST_APPL_PER_CONTRACT', 'NFLAG_LAST_APPL_IN_DAY',
    'CHANNEL_TYPE', 'SELLERPLACE_AREA', 'NAME_SELLER_INDUSTRY', 'NAME_TYPE_SUITE',
]
df = df[[c for c in ordered_cols if c in df.columns]]
# Rows in order of the customer id (stable sort keeps the original order for the same id)
df = df.sort_values("SK_ID_CURR", kind="stable").reset_index(drop=True)

# ---------- 4. Sidebar filters ----------
st.sidebar.header("Filters")
contract_types = sorted(df["NAME_CONTRACT_TYPE"].dropna().unique())
client_types = sorted(df["NAME_CLIENT_TYPE"].dropna().unique())

sel_contract = st.sidebar.multiselect("Contract Type", contract_types, default=contract_types)
sel_client = st.sidebar.multiselect("Client Type", client_types, default=client_types)

df = df[
    df["NAME_CONTRACT_TYPE"].isin(sel_contract)
    & df["NAME_CLIENT_TYPE"].isin(sel_client)
]

# ---------- Data preview ----------
with st.expander("Data preview (first 100 rows, after filters)"):
    st.dataframe(df.head(100))

# ---------- 5. KPI cards ----------
st.header("Loan Application Overview")
status_counts = df["NAME_CONTRACT_STATUS"].value_counts()
total = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Applications", f"{total:,}")
c2.metric("Approved", f"{status_counts.get('Approved', 0):,}")
c3.metric("Refused", f"{status_counts.get('Refused', 0):,}")
c4.metric("Canceled", f"{status_counts.get('Canceled', 0):,}")

if total > 0:
    st.caption(f"Approval rate: {status_counts.get('Approved', 0) / total * 100:.1f}%")

# ---------- 6 and 7. Status chart and reject reasons (side by side) ----------
refused = df[df["NAME_CONTRACT_STATUS"] == "Refused"]
reason_counts = refused["CODE_REJECT_REASON"].value_counts()

left, right = st.columns(2)
with left:
    st.subheader("Application Status")
    st.bar_chart(status_counts)
with right:
    st.subheader("Reject Reasons")
    st.bar_chart(reason_counts)
    st.caption("Refused applications only")
st.dataframe(reason_counts.rename("applications").to_frame().T)

# ---------- 8 and 9. Loan amount analysis ----------
st.header("Loan Amount Analysis")
approved = df[df["NAME_CONTRACT_STATUS"] == "Approved"]

if len(approved) > 0:
    a1, a2, a3 = st.columns(3)
    a1.metric("Avg Applied Amount", f"{approved['AMT_APPLICATION'].mean():,.0f}")
    a2.metric("Avg Approved Amount", f"{approved['AMT_CREDIT'].mean():,.0f}")
    a3.metric("Max Approved Amount", f"{approved['AMT_CREDIT'].max():,.0f}")

left, right = st.columns(2)
with left:
    st.subheader("Average Approved Amount by Contract Type")
    if len(approved) > 0:
        st.bar_chart(approved.groupby("NAME_CONTRACT_TYPE")["AMT_CREDIT"].mean().round(0))

with right:
    st.subheader("Approval Rate by Applied Amount")
    d = df[df["AMT_APPLICATION"] > 0].copy()
    if len(d) > 100:
        d["amount_band"], bins = pd.qcut(
            d["AMT_APPLICATION"], 4,
            labels=["Low", "Medium", "High", "Very High"],
            retbins=True,
        )
        rate = (
            d.groupby("amount_band", observed=True)["NAME_CONTRACT_STATUS"]
            .apply(lambda s: (s == "Approved").mean() * 100)
            .round(1)
        )
        st.bar_chart(rate)
        st.caption("Approval rate (%) by applied-amount band. Band cutoffs: "
                   + ", ".join(f"{round(b):,}" for b in bins))

# ---------- 10. High-risk segment analysis ----------
st.header("High-Risk Segment Analysis")
segment_cols = {
    "Client Type": "NAME_CLIENT_TYPE",
    "Contract Type": "NAME_CONTRACT_TYPE",
    "Channel Type": "CHANNEL_TYPE",
    "Goods Category": "NAME_GOODS_CATEGORY",
    "Portfolio": "NAME_PORTFOLIO",
    "Seller Industry": "NAME_SELLER_INDUSTRY",
}
seg_label = st.selectbox("Segment by", list(segment_cols.keys()), key="seg_select")
col = segment_cols[seg_label]

seg = df.groupby(col)["NAME_CONTRACT_STATUS"].agg(
    total="count",
    refused=lambda s: (s == "Refused").sum(),
)
seg["refusal_rate_%"] = (seg["refused"] / seg["total"] * 100).round(1)
seg = seg[seg["total"] >= 100].sort_values("refusal_rate_%", ascending=False)

left, right = st.columns(2)
with left:
    st.bar_chart(seg["refusal_rate_%"])
with right:
    st.dataframe(seg)
st.caption("Segments with at least 100 applications. Refusal rate = Refused / Total.")

# ---------- 11. Customer-wise check ----------
st.header("Customer-wise Application Check")
in_col, btn_col = st.columns([3, 1])
with in_col:
    cust_id = st.number_input("Enter SK_ID_CURR", min_value=0, step=1, key="cust_id")
with btn_col:
    st.write("")
    check_clicked = st.button("Check Customer", key="btn_check_customer")

if check_clicked:
    cust = pd.read_sql(
        "SELECT SK_ID_CURR, NAME_CONTRACT_TYPE, NAME_CONTRACT_STATUS, "
        "AMT_APPLICATION, AMT_CREDIT, CODE_REJECT_REASON "
        "FROM loan_data WHERE SK_ID_CURR = %(id)s",
        engine,
        params={"id": int(cust_id)},
    )
    if cust.empty:
        st.warning("No application found for this ID.")
    else:
        st.dataframe(cust)
        for _, row in cust.iterrows():
            if row["NAME_CONTRACT_STATUS"] == "Refused":
                st.error(f"Refused. Reason code: {row['CODE_REJECT_REASON']}")
            elif row["NAME_CONTRACT_STATUS"] == "Approved":
                st.success(f"Approved. Credit amount: {row['AMT_CREDIT']:,.0f}")
            else:
                st.info(f"Status: {row['NAME_CONTRACT_STATUS']}")

# ---------- 12. SQL queries (20 predefined queries, all shown with their results) ----------
st.header("SQL Queries")
st.caption("The 20 predefined queries. Each question is shown with its SQL and its result. "
           "Queries that return rows show all rows.")


@st.cache_data
def run_query(sql):
    return pd.read_sql(sql, engine)


def show_query(num, question, sql):
    st.markdown(f"**Q{num}. {question}**")
    with st.expander("Show SQL"):
        st.code(sql.strip(), language="sql")

    result = run_query(sql)
    # Queries that return all columns (SELECT *) are shown in the same logical order
    result = result[[c for c in ordered_cols if c in result.columns]
                    + [c for c in result.columns if c not in ordered_cols]]

    if result.shape == (1, 1):
        # a single number is shown as a big value
        value = pd.to_numeric(result.iloc[0, 0], errors="coerce")
        if pd.isna(value):
            st.write(result)
        else:
            text = f"{int(value):,}" if float(value).is_integer() else f"{float(value):,.2f}"
            st.metric(result.columns[0], text)
    else:
        second = pd.to_numeric(result.iloc[:, 1], errors="coerce") if result.shape[1] == 2 else None
        if second is not None and 2 <= len(result) <= 10 and second.notna().all():
            # a small summary table: table on the left, chart on the right
            left, right = st.columns(2)
            left.dataframe(result)
            right.bar_chart(pd.Series(second.values, index=result.iloc[:, 0].astype(str)))
        else:
            st.dataframe(result)
        st.caption(f"{len(result):,} rows")
    st.divider()

basic = [
    ("Retrieve all records from the loan_data table.",
     "SELECT * FROM loan_data ORDER BY SK_ID_CURR"),
    ("Display all loan applications with their contract type and contract status.",
     "SELECT SK_ID_CURR, NAME_CONTRACT_TYPE, NAME_CONTRACT_STATUS\nFROM loan_data ORDER BY SK_ID_CURR"),
    ("Retrieve all applications where the contract status is 'Approved'.",
     "SELECT * FROM loan_data\nWHERE NAME_CONTRACT_STATUS = 'Approved' ORDER BY SK_ID_CURR"),
    ("Display all applications where the contract status is 'Refused'.",
     "SELECT * FROM loan_data\nWHERE NAME_CONTRACT_STATUS = 'Refused' ORDER BY SK_ID_CURR"),
    ("Retrieve all applications belonging to the 'Repeater' client type.",
     "SELECT * FROM loan_data\nWHERE NAME_CLIENT_TYPE = 'Repeater' ORDER BY SK_ID_CURR"),
]

aggregation = [
    ("Calculate the total number of loan applications.",
     "SELECT COUNT(*) AS total_applications FROM loan_data"),
    ("Calculate the total credit amount across all applications.",
     "SELECT SUM(AMT_CREDIT) AS total_credit FROM loan_data"),
    ("Calculate the average loan application amount.",
     "SELECT ROUND(AVG(AMT_APPLICATION), 2) AS avg_application FROM loan_data"),
    ("Count the number of applications for each contract status.",
     "SELECT NAME_CONTRACT_STATUS, COUNT(*) AS total\nFROM loan_data GROUP BY NAME_CONTRACT_STATUS"),
    ("Calculate the average annuity amount for each contract type.",
     "SELECT NAME_CONTRACT_TYPE, ROUND(AVG(AMT_ANNUITY), 2) AS avg_annuity\nFROM loan_data GROUP BY NAME_CONTRACT_TYPE"),
]

join_based = [
    ("Retrieve loan applications where the credit amount is greater than 500,000.",
     "SELECT * FROM loan_data WHERE AMT_CREDIT > 500000 ORDER BY SK_ID_CURR"),
    ("Find applications where the down payment amount is greater than 50,000.",
     "SELECT * FROM loan_data WHERE AMT_DOWN_PAYMENT > 50000 ORDER BY SK_ID_CURR"),
    ("Count the number of applications for each client type.",
     "SELECT NAME_CLIENT_TYPE, COUNT(*) AS total\nFROM loan_data GROUP BY NAME_CLIENT_TYPE"),
    ("Calculate the average credit amount for each loan contract status.",
     "SELECT NAME_CONTRACT_STATUS, ROUND(AVG(AMT_CREDIT), 2) AS avg_credit\nFROM loan_data GROUP BY NAME_CONTRACT_STATUS"),
    ("Find the top 5 product combinations with the highest number of applications.",
     "SELECT PRODUCT_COMBINATION, COUNT(*) AS total\nFROM loan_data GROUP BY PRODUCT_COMBINATION\nORDER BY total DESC LIMIT 5"),
]

financial = [
    ("Calculate the total credit amount for approved and refused applications separately.",
     "SELECT NAME_CONTRACT_STATUS, SUM(AMT_CREDIT) AS total_credit\nFROM loan_data\nWHERE NAME_CONTRACT_STATUS IN ('Approved', 'Refused')\nGROUP BY NAME_CONTRACT_STATUS"),
    ("Find the top 3 contract types with the highest average credit amount.",
     "SELECT NAME_CONTRACT_TYPE, ROUND(AVG(AMT_CREDIT), 2) AS avg_credit\nFROM loan_data GROUP BY NAME_CONTRACT_TYPE\nORDER BY avg_credit DESC LIMIT 3"),
    ("Calculate the total application amount for each payment type.",
     "SELECT NAME_PAYMENT_TYPE, SUM(AMT_APPLICATION) AS total_application\nFROM loan_data GROUP BY NAME_PAYMENT_TYPE"),
    ("Identify the top 5 seller industries based on total credit amount.",
     "SELECT NAME_SELLER_INDUSTRY, SUM(AMT_CREDIT) AS total_credit\nFROM loan_data GROUP BY NAME_SELLER_INDUSTRY\nORDER BY total_credit DESC LIMIT 5"),
    ("Calculate the approval percentage for each contract type.",
     "SELECT NAME_CONTRACT_TYPE,\n       ROUND(SUM(NAME_CONTRACT_STATUS = 'Approved') * 100.0 / COUNT(*), 2) AS approval_pct\nFROM loan_data GROUP BY NAME_CONTRACT_TYPE"),
]



 

tab1, tab2, tab3, tab4 = st.tabs([
    "Basic Queries (1-5)",
    "Aggregation Queries (6-10)",
    "Join-Based Queries (11-15)",
    "Financial Tracking Queries (16-20)",
])

number = 1
for tab, group in [(tab1, basic), (tab2, aggregation), (tab3, join_based), (tab4, financial)]:
    with tab:
        for question, sql in group:
            show_query(number, question, sql)
            number += 1

# ---------- 13. Key insights (fixed text, not changed by the sidebar filters) ----------
st.header("Key Insights")

st.markdown("""
### 1. Overall Status
- Total applications: **49,896**
- Approved: **31,885 (63.9%)**
- Refused: **8,650 (17.3%)**
- Canceled: **8,503 (17.0%)**
- Unused offer: **858 (1.7%)**
- Canceled applications are almost as many as refused ones. These were not rejected by the bank, so they are reported separately.

### 2. Reject Reasons
- **HC** is the top reason (5,076 applications, about 59% of refusals).
- Next are **LIMIT** (1,780) and **SCO** (1,135).
- **SCOFR** (360), **VERIF** (116) and **SYSTEM** (16) are small.
- **XNA** (reason not recorded): 167 refused applications.
- Total: 8,650 refused applications.

### 3. Loan Amount
- Average applied amount (approved): **174,910**
- Average approved amount: **194,728**
- Maximum approved amount: **2,565,842**
- On average, the credit amount is higher than the amount applied for.

### 4. Approval Rate by Applied Amount
| Band | Applied amount | Approval rate |
|---|---|---|
| Low | 6,120 - 49,697 | 85.0% |
| Medium | 49,697 - 104,908 | 84.9% |
| High | 104,908 - 225,000 | 77.8% |
| Very High | above 225,000 | 65.9% |

- Approval rate stays near 85% up to about 105,000 and then falls as the requested amount grows.
- This is a trend in the data, not a fixed bank rule.

### 5. Approval Rate by Contract Type
- Consumer loans: **85.7%** (20,149 of 23,507)
- Revolving loans: **50.6%** (2,837 of 5,611)
- Cash loans: **42.8%** (8,899 of 20,770)
- Rates are Approved divided by all applications, including canceled ones.


