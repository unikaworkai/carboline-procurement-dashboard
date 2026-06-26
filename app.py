import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
import io

warnings.filterwarnings("ignore")


def main():
	st.title("Procurement Engine Dashboard")
	st.write("Upload a CSV file to get started.")
	uploaded = st.file_uploader("Choose a CSV", type=["csv"]) 
	if uploaded is not None:
		# read uploaded file into dataframe
		try:
			df = pd.read_csv(uploaded)
		except Exception:
			st.error("Failed to read CSV. Please ensure the file is a valid CSV.")
			return
		st.subheader("Data preview")
		st.dataframe(df.head())
		st.subheader("Basic summary")
		st.write(df.describe(include='all'))
		# allow user to pick numeric columns to plot
		numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
		if numeric_cols:
			st.subheader("Quick plot")
			x_col = st.selectbox("X axis", options=numeric_cols, index=0)
			y_col = st.selectbox("Y axis", options=numeric_cols, index=min(1, len(numeric_cols)-1))
			fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
			st.plotly_chart(fig, use_container_width=True)
		else:
			st.info("No numeric columns found for plotting.")


if __name__ == "__main__":
	main()

 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
import io
 
warnings.filterwarnings("ignore")
 
# ── BRAND COLORS ──────────────────────────────────────────────
RED    = "#C41230"
BLUE   = "#003087"
NAVY   = "#1F3864"
STEEL  = "#2E75B6"
LBLUE  = "#D6E4F0"
AMBER  = "#B8860B"
GREY   = "#595959"
ORANGE = "#C55A11"
GREEN  = "#375623"
WHITE  = "#FFFFFF"
BG     = "#F8F9FA"
 
# ── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(
    page_title="Carboline Procurement Engine",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
st.markdown(f"""
<style>
  html, body, [class*="css"] {{ font-family: Arial, sans-serif !important; }}
  .main {{ background-color: {BG}; }}
  .block-container {{ padding-top: 0.5rem; padding-bottom: 1rem; }}
  .kpi {{
    background:{WHITE}; border-radius:10px; padding:18px 14px 12px;
    border-top:4px solid {RED}; box-shadow:0 2px 8px rgba(0,0,0,0.10);
    text-align:center; margin-bottom:6px;
  }}
  .kpi .lbl {{ font-size:11px; color:{GREY}; font-weight:700;
    text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; }}
  .kpi .val {{ font-size:26px; font-weight:800; color:{NAVY}; line-height:1.1; }}
  .kpi .sub {{ font-size:10px; color:{GREY}; margin-top:2px; }}
  .kpi-b  {{ border-top-color:{BLUE}  !important; }}
  .kpi-g  {{ border-top-color:{GREEN} !important; }}
  .kpi-a  {{ border-top-color:{AMBER} !important; }}
  .alert  {{
    background:{RED}; color:{WHITE}; border-radius:8px;
    padding:14px 20px; font-size:15px; font-weight:700;
    margin-bottom:12px; border-left:8px solid #800000;
  }}
  .fbox {{
    background:{LBLUE}; border-left:4px solid {BLUE}; border-radius:6px;
    padding:10px 16px; font-size:13px; color:{NAVY}; margin-bottom:12px;
  }}
  .foot {{ color:{GREY}; font-size:11px; text-align:center;
    margin-top:16px; padding-top:8px; border-top:1px solid #ddd; }}
  h2 {{ color:{NAVY}; }}
  h3 {{ color:{NAVY}; font-size:16px; }}
</style>
""", unsafe_allow_html=True)
 
CHART = dict(
    paper_bgcolor=WHITE, plot_bgcolor=WHITE,
    font=dict(family="Arial", color=NAVY),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
)
 
MONTH = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
         7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
 
FLAG_CLR = {
    "🔴 TOP PRIORITY — A-item understocked": RED,
    "🟡 REVIEW — B-item understocked": ORANGE,
    "🟠 MONITOR — C-item understocked": "#ED7D31",
    "🔵 REVIEW — Overstocked": STEEL,
    "✅ OK": GREEN,
    "⭐ GOOD APPLE — UNDERSTOCKED (priority stock)": AMBER,
    "⭐ GOOD APPLE — stocked OK": "#DAA520",
    "🗑 BAD APPLE — remove from LN": GREY,
    "D-tier — no SS needed": "#7F7F7F",
    "Out of scope": "#BFBFBF",
}
 
# ── HELPERS ───────────────────────────────────────────────────
def n(v, d=0):
    try: return f"{float(v):,.{d}f}"
    except: return "—"
 
def d(v, d=0):
    try: return f"${float(v):,.{d}f}"
    except: return "—"
 
def p(v, d=1):
    try: return f"{float(v):.{d}f}%"
    except: return "—"
 
def kpi(label, value, sub="", cls=""):
    st.markdown(f"""
    <div class="kpi {cls}">
      <div class="lbl">{label}</div>
      <div class="val">{value}</div>
      <div class="sub">{sub}</div>
    </div>""", unsafe_allow_html=True)
 
def empty(msg="No data for current selection"):
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper",
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=14, color=GREY))
    fig.update_layout(height=350, paper_bgcolor=WHITE,
                      plot_bgcolor=WHITE,
                      xaxis_visible=False, yaxis_visible=False)
    return fig
 
def dl_excel(df, filename):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    st.download_button(f"⬇️ Download {filename}",
                       data=buf.getvalue(), file_name=filename,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
 
# ── EXCEL READER ──────────────────────────────────────────────
def read_sheet(path, sheet, id_col, skip=3):
    try:
        df = pd.read_excel(path, sheet_name=sheet, skiprows=skip)
        df = df[df[id_col].notna()]
        df = df[df[id_col].astype(str).str.strip() != id_col]
        df = df[~df[id_col].astype(str).str.startswith("NaN")]
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"Could not read {sheet} from {path}: {e}")
        return pd.DataFrame()
 
# ── DATA LOADING ──────────────────────────────────────────────
@st.cache_data(show_spinner="Loading Carboline data...")
def load():
    MASTER = "Carboline_MasterSS_Summary_v1(3).xlsx"
 
    # Check which files exist
    needed = {
        "rop_ss_moq.xlsx": "Safety stock calculations",
        "clean_consumption.xlsx": "Consumption data",
        "clean_po.xlsx": "Purchase orders",
        "clean_lead_time.xlsx": "Lead time data",
        "clean_cost.xlsx": "Standard costs",
        "clean_inventory.xlsx": "Inventory on-hand",
        "clean_supplier.xlsx": "Supplier master",
        "clean_item_master.xlsx": "Item master",
        "abc_classification.xlsx": "ABC classification",
        MASTER: "Master summary",
    }
    missing = [f for f in needed if not os.path.exists(f)]
    if missing:
        return None, missing
 
    D = {}
 
    # ── SS file ───────────────────────────────────────────────
    df_ss = read_sheet("rop_ss_moq.xlsx", "Full_SS_Results", "audit_flag_v4", skip=3)
    # Clean column names that have formula annotations
    df_ss.columns = [str(c).split("\n")[0].split("▶")[0].strip() for c in df_ss.columns]
    # Fix specific renamed formula cols
    col_map = {
        "ss_dollars F=OL": "ss_dollars",
        "rop_dollars F=PL": "rop_dollars",
        "avg_inv_ F=(O+P)/2L": "avg_inv_dollars",
        "curr_rop_ F=ML": "curr_rop_dollars",
        "ss_dollars": "ss_dollars",
        "rop_dollars": "rop_dollars",
    }
    df_ss.rename(columns=col_map, inplace=True)
 
    num_cols = ["avg_daily_usage_lbs", "lead_time_used_v4", "buffer_factor_v4",
                "standard_cost_usd", "current_rop_in_ln", "moq_order_increment",
                "new_ss_lbs_v4", "new_rop_lbs_v4", "rop_to_enter_ln",
                "rop_gap_lbs_v4", "financial_risk_v4"]
    for c in num_cols:
        if c in df_ss.columns:
            df_ss[c] = pd.to_numeric(df_ss[c], errors="coerce").fillna(0)
 
    # Always recompute dollar values cleanly
    df_ss["ss_dollars"]      = df_ss["new_ss_lbs_v4"]  * df_ss["standard_cost_usd"]
    df_ss["rop_dollars"]     = df_ss["new_rop_lbs_v4"] * df_ss["standard_cost_usd"]
    df_ss["avg_inv_dollars"] = (df_ss["new_ss_lbs_v4"] + df_ss["new_rop_lbs_v4"]) / 2 * df_ss["standard_cost_usd"]
    df_ss["curr_rop_dollars"]= df_ss["current_rop_in_ln"] * df_ss["standard_cost_usd"]
 
    # Ensure flag cols exist
    if "is_good_apple" not in df_ss.columns: df_ss["is_good_apple"] = "NO"
    if "is_bad_apple"  not in df_ss.columns: df_ss["is_bad_apple"]  = "NO"
    D["ss"] = df_ss
 
    # Good / Bad apple sheets
    df_bad = read_sheet("rop_ss_moq.xlsx", "🗑 Bad_Apple_Remove", "Site", skip=3)
    D["bad_apple"] = df_bad
 
    df_gs = read_sheet("rop_ss_moq.xlsx", "⭐ Good_Apple_Stock", "Site", skip=3)
    D["good_stock"] = df_gs
 
    # Good apple missing — header is at row 2 (0-indexed)
    df_gm = pd.read_excel("rop_ss_moq.xlsx",
                           sheet_name="⭐ Good_Apple_Missing_ROP",
                           skiprows=2, header=0)
    df_gm = df_gm[df_gm.iloc[:,0].notna()]
    df_gm.columns = ["item_code","std_cost","destination","lead_time_days","action_raw"][:len(df_gm.columns)]
    df_gm["action"] = "Add Item Ordering parameters in LN"
    D["good_missing"] = df_gm
 
    # ── Consumption ───────────────────────────────────────────
    df_c = read_sheet("clean_consumption.xlsx", "Clean_Consumption_Data", "site_group", skip=3)
    df_c.columns = [str(c).split("▶")[0].strip().replace(" ▶ FORMULA","") for c in df_c.columns]
    df_c["qty_issued"]   = pd.to_numeric(df_c.get("qty_issued",   0), errors="coerce").fillna(0)
    df_c["year"]         = pd.to_numeric(df_c.get("year",         0), errors="coerce")
    df_c["period_month"] = pd.to_numeric(df_c.get("period_month", 0), errors="coerce")
    df_c = df_c[df_c["qty_issued"] > 0]
    D["cons"] = df_c
 
    # ── PO ────────────────────────────────────────────────────
    df_po = read_sheet("clean_po.xlsx", "Clean_PO_Data", "item_code", skip=3)
    df_po.columns = [str(c).replace(" ▶ FORMULA","").replace(" ▶ F","").strip() for c in df_po.columns]
    df_po["unit_price"]  = pd.to_numeric(df_po.get("unit_price",  0), errors="coerce").fillna(0)
    df_po["ordered_qty"] = pd.to_numeric(df_po.get("ordered_qty", 0), errors="coerce").fillna(0)
    D["po"] = df_po
 
    # ── Lead time ─────────────────────────────────────────────
    df_lt = read_sheet("clean_lead_time.xlsx", "Lead_Time_Data", "po_number", skip=3)
    df_lt.columns = [str(c).replace(" ▶ FORMULA","").replace(" ▶ F","").strip() for c in df_lt.columns]
    df_lt["lead_time_days_winsorized"] = pd.to_numeric(
        df_lt.get("lead_time_days_winsorized", 0), errors="coerce").fillna(0)
    df_lt["planned_receipt_date"] = pd.to_datetime(df_lt.get("planned_receipt_date"), errors="coerce")
    df_lt["actual_receipt_date"]  = pd.to_datetime(df_lt.get("actual_receipt_date"),  errors="coerce")
    recv = df_lt[df_lt.get("po_status", pd.Series(dtype=str)) == "RECEIVED"].copy()
    recv["on_time_2day"] = (
        recv["actual_receipt_date"] <=
        recv["planned_receipt_date"] + pd.Timedelta(days=2)
    )
    D["lt"]   = df_lt
    D["recv"] = recv
 
    # ── Cost ──────────────────────────────────────────────────
    df_cost = read_sheet("clean_cost.xlsx", "Standard_Cost_Master", "item_code", skip=3)
    df_cost.columns = [str(c).replace(" ▶ FORMULA","").replace(" ▶ F","").strip() for c in df_cost.columns]
    df_cost["standard_cost_usd"] = pd.to_numeric(df_cost.get("standard_cost_usd",0), errors="coerce").fillna(0)
    D["cost"] = df_cost
 
    # ── Inventory ─────────────────────────────────────────────
    df_inv = read_sheet("clean_inventory.xlsx", "Inventory_OnHand", "item_code", skip=3)
    df_inv.columns = [str(c).replace(" ▶ FORMULA","").replace(" ▶ F","").strip() for c in df_inv.columns]
    for c in ["economic_stock","available_stock","inv_on_hand","inv_on_order","inv_allocated"]:
        if c in df_inv.columns:
            df_inv[c] = pd.to_numeric(df_inv[c], errors="coerce").fillna(0)
    D["inv"] = df_inv
 
    # ── Supplier ──────────────────────────────────────────────
    df_sup = read_sheet("clean_supplier.xlsx", "PO_Suppliers_Only", "supplier_bp_code", skip=3)
    D["sup"] = df_sup
 
    # ── Item master ───────────────────────────────────────────
    df_im = read_sheet("clean_item_master.xlsx", "3_Item_Master", "item_code", skip=3)
    df_im.columns = [str(c).replace(" ▶ FORMULA","").replace(" ▶ F","").strip() for c in df_im.columns]
    D["item_master"] = df_im
 
    # ── ABC ───────────────────────────────────────────────────
    df_abc = pd.read_excel("abc_classification.xlsx",
                           sheet_name="8003_RawMaterials_ABC", skiprows=3)
    df_abc.columns = ["rank","abc_tier","item_code","item_description","item_group",
                      "planning_signal","total_lbs_2024_2025","pct_of_total_lbs",
                      "cumulative_pct","buffer_factor","ss_eligible","notes"
                      ][:len(df_abc.columns)]
    df_abc = df_abc[df_abc["item_code"].notna()]
    D["abc"] = df_abc
 
    # ── Master summary ────────────────────────────────────────
    df_site = pd.read_excel(MASTER, sheet_name="Site_Summary", skiprows=3, nrows=6)
    df_site.columns = ["site","items","a_under","ga_under","bad_in_file",
                       "ss_dol","rop_dol","avg_inv_dol","avg_lt","otd","notes"
                       ][:len(df_site.columns)]
    df_site = df_site[df_site["site"].notna()]
    df_site = df_site[~df_site["site"].astype(str).str.contains("TOTAL|nan", na=True)]
    D["site_sum"] = df_site
 
    df_d = pd.read_excel(MASTER, sheet_name="D_Tier_Full_List", skiprows=1, header=0)
    df_d = df_d[df_d["item_code"].notna()]
    for c in ["total_lbs_all_years","lbs_2021_2023"]:
        if c in df_d.columns:
            df_d[c] = pd.to_numeric(df_d[c], errors="coerce").fillna(0)
    D["d_tier"] = df_d
 
    df_abc_site = pd.read_excel(MASTER, sheet_name="ABC_by_Site", skiprows=1, header=0)
    df_abc_site = df_abc_site[df_abc_site["site"].notna() &
                               ~df_abc_site["site"].astype(str).str.contains("SUBTOTAL|NaN|nan", na=True)]
    D["abc_site"] = df_abc_site
 
    return D, []
 
 
# ── FILTERS ───────────────────────────────────────────────────
def scope(df):
    """Remove OUT_OF_SCOPE and BAD APPLE from financial analysis."""
    return df[(df["abc_tier"] != "OUT_OF_SCOPE") & (df.get("is_bad_apple", "NO") == "NO")]
 
def apply_f(df, site, tier, apple):
    d = df.copy()
    if site != "All Sites": d = d[d["site_group"] == site]
    if tier != "All Tiers": d = d[d["abc_tier"] == tier]
    if apple == "⭐ Good Apple Only":   d = d[d.get("is_good_apple","NO") == "YES"]
    elif apple == "🗑 Bad Apple Only": d = d[d.get("is_bad_apple","NO") == "YES"]
    elif apple == "Regular Only":
        d = d[(d.get("is_good_apple","NO") == "NO") & (d.get("is_bad_apple","NO") == "NO")]
    return d
 
def sidebar(df_ss):
    st.sidebar.markdown(f"""
    <div style="background:{RED};border-radius:8px;padding:16px;text-align:center;margin-bottom:16px;">
      <div style="color:{WHITE};font-size:22px;font-weight:900;letter-spacing:2px;">CARBOLINE</div>
      <div style="color:rgba(255,255,255,0.8);font-size:11px;letter-spacing:1px;">
        Coatings · Linings · Fireproofing</div>
      <div style="color:rgba(255,255,255,0.65);font-size:10px;margin-top:3px;">
        An RPM International Company</div>
    </div>""", unsafe_allow_html=True)
 
    st.sidebar.markdown("## 🏭 Procurement Engine")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Filters")
 
    sites  = ["All Sites"] + sorted(df_ss["site_group"].dropna().unique().tolist())
    tiers  = ["All Tiers", "A", "B", "C", "D"]
    apples = ["All Items", "⭐ Good Apple Only", "🗑 Bad Apple Only", "Regular Only"]
 
    site  = st.sidebar.selectbox("📍 Site",     sites)
    tier  = st.sidebar.selectbox("📊 ABC Tier", tiers)
    apple = st.sidebar.selectbox("🍎 Category", apples)
 
    st.sidebar.markdown("---")
    ins = scope(df_ss)
    st.sidebar.markdown(f"**In-scope items:** {len(ins):,}")
    st.sidebar.markdown(f"**🔴 A-understocked:** {(ins['audit_flag_v4'].str.startswith('🔴')).sum():,}")
    st.sidebar.markdown(f"**⭐ Good Apples:** {(df_ss.get('is_good_apple','NO')=='YES').sum():,}")
    st.sidebar.markdown(f"**🗑 Bad Apples (in file):** {(df_ss.get('is_bad_apple','NO')=='YES').sum():,}")
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<div style='font-size:10px;color:{GREY};'>Data: June 2026 · SS v4 · OTD ±2 day</div>",
        unsafe_allow_html=True)
    return site, tier, apple
 
 
# ═══════════════════════════════════════════════════
# TAB 1 — EXECUTIVE OVERVIEW
# ═══════════════════════════════════════════════════
def t1_overview(D, filt):
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,{NAVY},{BLUE});
                border-radius:12px;padding:22px 30px;margin-bottom:18px;">
      <div style="color:{WHITE};font-size:26px;font-weight:800;letter-spacing:1px;">
        🏭 Procurement Engine Dashboard</div>
      <div style="color:rgba(255,255,255,0.8);font-size:13px;margin-top:4px;">
        Carboline Company · Lake Charles · Green Bay · Dayton · Louisa</div>
      <div style="color:rgba(255,255,255,0.6);font-size:11px;margin-top:4px;">
        Safety Stock v4 · Good Apple / Bad Apple · Bulk Tank Caps Applied</div>
    </div>""", unsafe_allow_html=True)
 
    ins = scope(filt)
    a_under = (ins["audit_flag_v4"].str.startswith("🔴")).sum()
    ga_under = (ins["audit_flag_v4"].str.contains("GOOD APPLE.*UNDER", na=False)).sum()
    risk   = ins[ins["rop_gap_lbs_v4"] < 0]["financial_risk_v4"].sum()
    ss_inv = ins["ss_dollars"].sum()
 
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi("📦 In-Scope Items",    n(len(ins)),        "Excl. finished goods & bad apples")
    with c2: kpi("🔴 A-Items Underst.",  n(a_under),         "Fix LN reorder point now",   "kpi-b")
    with c3: kpi("⭐ Good Apple Underst.",n(ga_under),        "Priority stock below safe level","kpi-a")
    with c4: kpi("💰 A-Item $ Risk",     d(risk,0),          "Understocked A-item exposure", "kpi-b")
    with c5: kpi("📈 SS Investment",     d(ss_inv,0),        "Recommended SS × standard cost")
    with c6: kpi("🚚 OTD Rate",          "78.0%",             "With ±2 day tolerance", "kpi-g")
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # Row 1: Status by site | ABC donut
    c_l, c_r = st.columns([3,2])
    with c_l:
        st.markdown("### Inventory Status by Site")
        valid = ins[ins["abc_tier"] != "D"]
        grp = valid.groupby("site_group").agg(
            Understocked=("rop_gap_direction_v4", lambda x: x.str.startswith("UNDER").sum()),
            Overstocked=("rop_gap_direction_v4",  lambda x: x.str.startswith("OVER").sum()),
            OK=("rop_gap_direction_v4",            lambda x: x.str.startswith("OK").sum()),
        ).reset_index()
        if grp.empty:
            st.plotly_chart(empty(), use_container_width=True)
        else:
            fig = go.Figure()
            for col_n, col_c in [("Understocked",RED),("Overstocked",STEEL),("OK",GREEN)]:
                fig.add_trace(go.Bar(
                    name=col_n, x=grp["site_group"], y=grp[col_n],
                    marker_color=col_c,
                    text=grp[col_n], textposition="inside",
                    textfont=dict(color=WHITE, size=12)))
            fig.update_layout(barmode="stack", height=360,
                              title="Item Count by Status per Site",
                              xaxis_title=None, yaxis_title="Items", **CHART)
            st.plotly_chart(fig, use_container_width=True)
 
    with c_r:
        st.markdown("### ABC Tier Distribution")
        tc = ins[ins["abc_tier"].isin(["A","B","C","D"])]["abc_tier"].value_counts()
        if tc.empty:
            st.plotly_chart(empty(), use_container_width=True)
        else:
            fig2 = go.Figure(go.Pie(
                labels=tc.index, values=tc.values, hole=0.55,
                marker_colors=[RED, ORANGE, STEEL, GREY],
                textinfo="label+percent", textfont=dict(size=12)))
            fig2.update_layout(
                height=360, showlegend=True,
                annotations=[dict(text="ABC", x=0.5, y=0.5,
                                   font_size=14, showarrow=False, font_color=NAVY)],
                **CHART)
            st.plotly_chart(fig2, use_container_width=True)
 
    # Row 2: Top 10 risk | SS $ by site
    c_l2, c_r2 = st.columns([3,2])
    with c_l2:
        st.markdown("### Top 10 Items by Financial Risk")
        top10 = ins[ins["rop_gap_lbs_v4"] < -0.01].nlargest(10,"financial_risk_v4").copy()
        if top10.empty:
            st.plotly_chart(empty("No understocked items in selection"), use_container_width=True)
        else:
            top10["lbl"] = top10["item_code"] + " — " + top10["item_description"].str[:28]
            fig3 = px.bar(
                top10, x="financial_risk_v4", y="lbl", orientation="h",
                color="site_group",
                color_discrete_map={"Lake Charles":BLUE,"Green Bay":GREEN,"Dayton":AMBER,"Louisa":ORANGE},
                text=top10["financial_risk_v4"].apply(lambda v: d(v,0)),
                title="Highest Financial Exposure — Understocked Items")
            fig3.update_traces(textposition="outside", textfont=dict(size=10))
            fig3.update_layout(height=400, yaxis={"categoryorder":"total ascending"},
                               xaxis_tickprefix="$", xaxis_tickformat=",.0f",
                               yaxis_title=None, **CHART)
            st.plotly_chart(fig3, use_container_width=True)
 
    with c_r2:
        st.markdown("### Safety Stock $ by Site")
        sd = ins.groupby("site_group").agg(
            SS=("ss_dollars","sum"), ROP=("rop_dollars","sum")).reset_index()
        if sd.empty:
            st.plotly_chart(empty(), use_container_width=True)
        else:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(name="Safety Stock $", x=sd["site_group"], y=sd["SS"],
                                   marker_color=RED,
                                   text=[d(v,0) for v in sd["SS"]], textposition="outside",
                                   textfont=dict(size=9)))
            fig4.add_trace(go.Bar(name="ROP $", x=sd["site_group"], y=sd["ROP"],
                                   marker_color=STEEL,
                                   text=[d(v,0) for v in sd["ROP"]], textposition="outside",
                                   textfont=dict(size=9)))
            fig4.update_layout(barmode="group", height=400,
                               yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                               title="SS $ vs ROP $ by Site (excl. bad apples)", **CHART)
            st.plotly_chart(fig4, use_container_width=True)
 
    st.markdown(
        "<div class='foot'>Data as of June 2026 · Safety Stock v4 · "
        "OTD uses ±2 day tolerance · Scope: Item Groups 8003 & 8010</div>",
        unsafe_allow_html=True)
 
 
# ═══════════════════════════════════════════════════
# TAB 2 — PRIORITY AUDIT LIST
# ═══════════════════════════════════════════════════
def t2_audit(D, filt):
    st.markdown(f"## 🔴 Priority Audit List")
    st.markdown(
        "<div class='fbox'><b>Action required:</b> Items below are understocked. "
        "The <b>'Update LN To This Value'</b> column is the exact number to enter in "
        "LN Item Ordering session to fix the reorder point.</div>",
        unsafe_allow_html=True)
 
    ins   = scope(filt)
    audit = ins[ins["rop_gap_lbs_v4"] < -0.01].sort_values("financial_risk_v4", ascending=False).copy()
    audit.insert(0, "Rank", range(1, len(audit)+1))
 
    fa,fb,fc,fd = st.columns([2,2,2,2])
    with fa:
        sites_a = ["All Sites"] + sorted(audit["site_group"].unique().tolist())
        sf = st.selectbox("Site", sites_a, key="a_s")
    with fb:
        tiers_a = ["All Tiers"] + [t for t in ["A","B","C"] if t in audit["abc_tier"].unique()]
        tf = st.selectbox("Tier", tiers_a, key="a_t")
    with fc:
        ga_on = st.toggle("⭐ Good Apple Only", key="a_ga")
    with fd:
        rows = st.selectbox("Rows", [25,50,100,"All"], key="a_r")
 
    if sf != "All Sites": audit = audit[audit["site_group"] == sf]
    if tf != "All Tiers": audit = audit[audit["abc_tier"] == tf]
    if ga_on: audit = audit[audit.get("is_good_apple","NO") == "YES"]
    if rows != "All": audit = audit.head(int(rows))
 
    m1,m2,m3,m4 = st.columns(4)
    with m1: st.metric("Items Shown", n(len(audit)))
    with m2: st.metric("Total $ Risk", d(audit["financial_risk_v4"].sum(),0))
    with m3: st.metric("Avg Gap (lbs)", n(audit["rop_gap_lbs_v4"].mean(),0))
    with m4: st.metric("A-Items", n((audit["abc_tier"]=="A").sum()))
    st.markdown("---")
 
    if audit.empty:
        st.info("No understocked items match the current filters.")
        return
 
    disp = audit[[
        "Rank","site_group","item_code","item_description","abc_tier",
        "is_good_apple","current_rop_in_ln","new_ss_lbs_v4","new_rop_lbs_v4",
        "rop_to_enter_ln","rop_gap_lbs_v4","financial_risk_v4",
        "avg_daily_usage_lbs","lead_time_used_v4"
    ]].copy()
    disp.columns = [
        "Rank","Site","Item Code","Description","Tier","Good Apple",
        "Current LN ROP (lbs)","Rec. SS (lbs)","Rec. ROP (lbs)",
        "✅ UPDATE LN TO THIS VALUE","Gap (lbs)","Financial Risk ($)",
        "Daily Usage (lbs/day)","Lead Time (days)"
    ]
    for c in ["Current LN ROP (lbs)","Rec. SS (lbs)","Rec. ROP (lbs)",
              "✅ UPDATE LN TO THIS VALUE","Gap (lbs)","Daily Usage (lbs/day)"]:
        disp[c] = disp[c].apply(lambda v: n(v,1))
    disp["Financial Risk ($)"] = disp["Financial Risk ($)"].apply(lambda v: d(v,2))
    disp["Lead Time (days)"]   = disp["Lead Time (days)"].apply(lambda v: n(v,1))
 
    st.dataframe(disp, use_container_width=True, height=500, hide_index=True)
    dl_excel(disp, "Carboline_Priority_Audit_List.xlsx")
 
    # Chart
    top20 = audit.head(20).copy()
    top20["lbl"] = top20["item_code"] + " — " + top20["item_description"].str[:25]
    colors = [AMBER if r=="YES" else RED for r in top20["is_good_apple"]]
    fig = go.Figure(go.Bar(
        x=top20["financial_risk_v4"], y=top20["lbl"], orientation="h",
        marker_color=colors,
        text=[d(v,0) for v in top20["financial_risk_v4"]],
        textposition="outside"))
    fig.update_layout(
        height=max(380, len(top20)*22),
        title="Top 20 Items by Financial Risk (Gold = Good Apple priority item)",
        xaxis_tickprefix="$", xaxis_tickformat=",.0f",
        yaxis={"categoryorder":"total ascending"}, **CHART)
    st.plotly_chart(fig, use_container_width=True)
 
 
# ═══════════════════════════════════════════════════
# TAB 3 — SAFETY STOCK CALCULATOR
# ═══════════════════════════════════════════════════
def t3_calc(D, filt):
    st.markdown("## 🧮 Safety Stock Calculator")
    st.markdown("""
    <div class='fbox'>
    <b>Formula:</b> Recommended SS = Average Daily Usage × Lead Time × Buffer Factor
    &nbsp;|&nbsp; <b>ROP</b> = (Daily Usage × Lead Time) + Safety Stock
    &nbsp;|&nbsp; <b>MOQ</b> rounded UP to nearest order increment
    &nbsp;|&nbsp; <b>Buffer:</b> A=1.5× · B=1.0× · C=0.5× · D=0
    </div>""", unsafe_allow_html=True)
 
    srch = st.text_input("🔍 Search item code or description", "")
    ins  = scope(filt)
    if srch:
        mask = (ins["item_code"].str.contains(srch, case=False, na=False) |
                ins["item_description"].str.contains(srch, case=False, na=False))
        ins = ins[mask]
 
    m1,m2,m3,m4,m5 = st.columns(5)
    with m1: st.metric("Items", n(len(ins)))
    with m2: st.metric("Total SS $", d(ins["ss_dollars"].sum(),0))
    with m3: st.metric("Total ROP $", d(ins["rop_dollars"].sum(),0))
    with m4: st.metric("Avg Lead Time", f"{ins['lead_time_used_v4'].mean():.1f}d")
    with m5:
        pct = (ins["rop_gap_lbs_v4"] < -0.01).sum() / max(len(ins),1) * 100
        st.metric("% Understocked", p(pct))
 
    if ins.empty:
        st.info("No items match the current filters.")
        return
 
    cols_need = ["site_group","item_code","item_description","abc_tier","audit_flag_v4",
                 "is_good_apple","is_bad_apple","avg_daily_usage_lbs","lead_time_used_v4",
                 "buffer_factor_v4","standard_cost_usd","current_rop_in_ln",
                 "new_ss_lbs_v4","new_rop_lbs_v4","rop_to_enter_ln",
                 "rop_gap_lbs_v4","financial_risk_v4","ss_dollars","rop_dollars"]
    available = [c for c in cols_need if c in ins.columns]
    disp = ins[available].copy()
    rename = {
        "site_group":"Site","item_code":"Item Code","item_description":"Description",
        "abc_tier":"Tier","audit_flag_v4":"Status",
        "is_good_apple":"Good Apple","is_bad_apple":"Bad Apple",
        "avg_daily_usage_lbs":"Daily Usage (lbs)","lead_time_used_v4":"Lead Time (days)",
        "buffer_factor_v4":"Buffer","standard_cost_usd":"Std Cost ($)",
        "current_rop_in_ln":"Current LN ROP","new_ss_lbs_v4":"Rec. SS (lbs)",
        "new_rop_lbs_v4":"Rec. ROP (lbs)","rop_to_enter_ln":"✅ Enter in LN",
        "rop_gap_lbs_v4":"Gap (lbs)","financial_risk_v4":"$ Risk",
        "ss_dollars":"SS Value ($)","rop_dollars":"ROP Value ($)"
    }
    disp.rename(columns=rename, inplace=True)
    for c in ["Daily Usage (lbs)","Current LN ROP","Rec. SS (lbs)",
              "Rec. ROP (lbs)","✅ Enter in LN","Gap (lbs)"]:
        if c in disp.columns:
            disp[c] = disp[c].apply(lambda v: n(v,1))
    for c in ["Std Cost ($)","$ Risk","SS Value ($)","ROP Value ($)"]:
        if c in disp.columns:
            disp[c] = disp[c].apply(lambda v: d(v,2))
    if "Lead Time (days)" in disp.columns:
        disp["Lead Time (days)"] = disp["Lead Time (days)"].apply(lambda v: n(v,1))
    if "Buffer" in disp.columns:
        disp["Buffer"] = disp["Buffer"].apply(lambda v: n(v,1)+"×")
 
    st.dataframe(disp, use_container_width=True, height=520, hide_index=True)
    dl_excel(disp, "Carboline_SS_Calculator.xlsx")
 
 
# ═══════════════════════════════════════════════════
# TAB 4 — SUPPLIER PERFORMANCE
# ═══════════════════════════════════════════════════
def t4_supplier(D, filt):
    st.markdown("## 🚚 Supplier Performance Scorecard")
    recv  = D["recv"]
    sup   = D["sup"]
    po    = D["po"]
    cost  = D["cost"]
 
    if recv.empty or sup.empty:
        st.warning("Lead time or supplier file unavailable."); return
 
    # OTD per supplier
    sup_grp = (recv.groupby("supplier_bp_code")
               .agg(orders=("po_number","count"),
                    on_time=("on_time_2day","sum"),
                    avg_lt=("lead_time_days_winsorized","mean"))
               .reset_index())
    sup_grp["otd_pct"] = (sup_grp["on_time"] / sup_grp["orders"] * 100).round(1)
    sup_grp["avg_lt"]  = sup_grp["avg_lt"].round(1)
    sup_grp["late"]    = sup_grp["orders"] - sup_grp["on_time"]
    sup_grp = sup_grp.merge(
        sup[["supplier_bp_code","supplier_name","country_name","is_us_supplier"]],
        on="supplier_bp_code", how="left")
    sup_grp["supplier_name"] = sup_grp["supplier_name"].fillna(sup_grp["supplier_bp_code"])
    sup_grp["origin"] = sup_grp["is_us_supplier"].apply(
        lambda v: "Domestic (US)" if str(v)=="YES" else "International")
 
    overall_otd = 78.0
    active      = (sup_grp["orders"] >= 5).sum()
    avg_lt_all  = recv["lead_time_days_winsorized"].mean()
    late_pct    = (1 - recv["on_time_2day"].mean()) * 100
 
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("🚚 Overall OTD",    p(overall_otd), "±2 day tolerance", "kpi-g")
    with k2: kpi("🏢 Active Suppliers", n(active),   "With 5+ orders", "kpi-b")
    with k3: kpi("⏱ Avg Lead Time",   f"{avg_lt_all:.1f}d", "Winsorized @ 103 days")
    with k4: kpi("❌ Late Delivery",   p(late_pct),   "Without tolerance", "kpi-b")
 
    st.markdown("---")
    sup5 = sup_grp[sup_grp["orders"] >= 5]
 
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### Supplier Risk Map — OTD vs Volume")
        if not sup5.empty:
            fig = px.scatter(
                sup5, x="otd_pct", y="orders",
                size="orders", color="origin",
                hover_name="supplier_name",
                hover_data={"otd_pct":":.1f","orders":True,"avg_lt":":.1f"},
                color_discrete_map={"Domestic (US)":BLUE,"International":ORANGE},
                labels={"otd_pct":"OTD %","orders":"Total Orders"},
                title="OTD % vs Order Volume (bubble = # orders)")
            fig.add_vline(x=78, line_dash="dash", line_color=RED,
                          annotation_text="Target 78%")
            fig.update_layout(height=400, **CHART)
            st.plotly_chart(fig, use_container_width=True)
 
    with c_r:
        st.markdown("### Lead Time Distribution")
        lt_v = recv["lead_time_days_winsorized"].dropna()
        fig2 = px.histogram(lt_v, nbins=50, title="Lead Time Distribution (days)",
                             color_discrete_sequence=[BLUE])
        fig2.add_vline(x=lt_v.mean(),   line_dash="dash", line_color=RED,
                       annotation_text=f"Mean: {lt_v.mean():.1f}d")
        fig2.add_vline(x=lt_v.median(), line_dash="dot",  line_color=GREEN,
                       annotation_text=f"Median: {lt_v.median():.1f}d")
        fig2.update_layout(height=400, xaxis_title="Days", yaxis_title="Deliveries", **CHART)
        st.plotly_chart(fig2, use_container_width=True)
 
    st.markdown("### Bottom 20 Suppliers by On-Time Delivery")
    bot20 = sup5.nsmallest(20,"otd_pct")[
        ["supplier_name","country_name","orders","on_time","late","otd_pct","avg_lt"]
    ].copy()
    bot20.columns = ["Supplier","Country","Total Orders","On-Time","Late","OTD %","Avg LT (days)"]
    bot20["OTD %"]         = bot20["OTD %"].apply(lambda v: p(v))
    bot20["Avg LT (days)"] = bot20["Avg LT (days)"].apply(lambda v: n(v,1))
    st.dataframe(bot20, use_container_width=True, height=420, hide_index=True)
 
    # PPV
    st.markdown("### Purchase Price Variance (PPV) by Supplier")
    st.caption("PPV = (Actual Price Paid − Standard Cost) × Ordered Qty. "
               "Positive = unfavorable (paid more). Negative = favorable (paid less).")
    po2   = po.copy()
    cost2 = cost[["item_code","standard_cost_usd"]].copy()
    ppv   = po2.merge(cost2, on="item_code", how="left")
    ppv["standard_cost_usd"] = pd.to_numeric(ppv["standard_cost_usd"], errors="coerce").fillna(0)
    ppv["unit_price"]        = pd.to_numeric(ppv.get("unit_price",0),   errors="coerce").fillna(0)
    ppv["ordered_qty"]       = pd.to_numeric(ppv.get("ordered_qty",0),  errors="coerce").fillna(0)
    ppv["ppv"]               = (ppv["unit_price"] - ppv["standard_cost_usd"]) * ppv["ordered_qty"]
    ppv                       = ppv[ppv["standard_cost_usd"] > 0]
    sup_ppv = (ppv.groupby("supplier_bp_code")["ppv"].sum()
               .reset_index().rename(columns={"ppv":"total_ppv"}))
    sup_ppv = sup_ppv.merge(sup[["supplier_bp_code","supplier_name"]], on="supplier_bp_code", how="left")
    sup_ppv["supplier_name"] = sup_ppv["supplier_name"].fillna(sup_ppv["supplier_bp_code"])
 
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("**⚠ Unfavorable — Paid More Than Standard**")
        top_u = sup_ppv.nlargest(10,"total_ppv")
        fig_u = px.bar(top_u, x="total_ppv", y="supplier_name", orientation="h",
                        color_discrete_sequence=[RED],
                        text=top_u["total_ppv"].apply(lambda v: d(v,0)),
                        title="Top 10 — Highest Overpayment vs Standard")
        fig_u.update_traces(textposition="outside")
        fig_u.update_layout(height=380, yaxis={"categoryorder":"total ascending"},
                             xaxis_tickprefix="$", **CHART)
        st.plotly_chart(fig_u, use_container_width=True)
 
    with c_p2:
        st.markdown("**✅ Favorable — Paid Less Than Standard**")
        top_f = sup_ppv.nsmallest(10,"total_ppv")
        fig_f = px.bar(top_f, x="total_ppv", y="supplier_name", orientation="h",
                        color_discrete_sequence=[GREEN],
                        text=top_f["total_ppv"].apply(lambda v: d(v,0)),
                        title="Top 10 — Highest Underpayment vs Standard")
        fig_f.update_traces(textposition="outside")
        fig_f.update_layout(height=380, yaxis={"categoryorder":"total descending"},
                             xaxis_tickprefix="$", **CHART)
        st.plotly_chart(fig_f, use_container_width=True)
 
 
# ═══════════════════════════════════════════════════
# TAB 5 — INVENTORY & COVERAGE
# ═══════════════════════════════════════════════════
def t5_inventory(D, filt):
    st.markdown("## 📦 Inventory & Coverage Analysis")
    inv = D["inv"]
    ins = scope(filt)
 
    neg = inv[inv["economic_stock"] < 0] if "economic_stock" in inv.columns else pd.DataFrame()
    if not neg.empty:
        st.markdown(
            f"<div class='alert'>🚨 SUPPLY ALERT — {len(neg)} items have negative "
            f"economic stock (more committed to production than available). "
            f"Immediate review required.</div>",
            unsafe_allow_html=True)
 
    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("📦 Total On-Hand",   n(inv.get("inv_on_hand", pd.Series([0])).sum(),0)+" lbs", "All 4 sites")
    with k2: kpi("✅ Items With Stock", n((inv.get("inv_on_hand",pd.Series([0]))>0).sum()), "inv_on_hand > 0","kpi-g")
    with k3: kpi("⚠ Zero Stock",       n((inv.get("inv_on_hand",pd.Series([0]))==0).sum()), "No inventory","kpi-a")
    with k4: kpi("🚨 Negative Eco.",   n(len(neg)), "Crisis — more allocated than available","kpi-b")
    st.markdown("---")
 
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### On-Hand Inventory by Site")
        if "site_group" in inv.columns and "inv_on_hand" in inv.columns:
            site_inv = inv.groupby("site_group")["inv_on_hand"].sum().reset_index()
            fig = px.bar(site_inv, x="site_group", y="inv_on_hand",
                          color="site_group",
                          color_discrete_map={"Lake Charles":BLUE,"Green Bay":GREEN,"Dayton":AMBER,"Louisa":ORANGE},
                          text=site_inv["inv_on_hand"].apply(lambda v: n(v,0)),
                          title="On-Hand Inventory (lbs) by Site")
            fig.update_traces(textposition="outside", showlegend=False)
            fig.update_layout(height=360, yaxis_title="Pounds", xaxis_title=None, **CHART)
            st.plotly_chart(fig, use_container_width=True)
 
    with c_r:
        st.markdown("### 🚨 Negative Economic Stock — Crisis Items")
        st.caption("Economic stock = On-Hand + On-Order − Allocated. Negative = production shortage risk.")
        if not neg.empty and "item_code" in neg.columns:
            show_neg = neg.sort_values("economic_stock")[
                [c for c in ["site_group","item_code","inv_on_hand","inv_on_order",
                              "inv_allocated","economic_stock"] if c in neg.columns]
            ].head(20).copy()
            show_neg.columns = [c.replace("inv_","").replace("_"," ").title()
                                 for c in show_neg.columns]
            for c in show_neg.columns:
                if c not in ["Site Group","Item Code"]:
                    show_neg[c] = show_neg[c].apply(lambda v: n(v,0))
            st.dataframe(show_neg, use_container_width=True, height=340, hide_index=True)
        else:
            st.success("No items with negative economic stock.")
 
    # Coverage analysis
    st.markdown("### Coverage: On-Hand vs Recommended Safety Stock")
    if "item_code" in inv.columns and "inv_on_hand" in inv.columns:
        inv_grp = inv.groupby(["item_code","site_group"])["inv_on_hand"].sum().reset_index()
        ab_items = ins[ins["abc_tier"].isin(["A","B"])]
        if not ab_items.empty:
            cov = ab_items.merge(inv_grp, on=["item_code","site_group"], how="left")
            cov["inv_on_hand"]   = cov["inv_on_hand"].fillna(0)
            cov["shortfall"]     = cov["new_ss_lbs_v4"] - cov["inv_on_hand"]
            cov["days_stockout"] = np.where(
                cov["avg_daily_usage_lbs"] > 0,
                (cov["inv_on_hand"] / cov["avg_daily_usage_lbs"]).round(1), 0)
            below = cov[cov["shortfall"] > 0].sort_values("shortfall", ascending=False).head(25)
            if not below.empty:
                show_b = below[["site_group","item_code","item_description","abc_tier",
                                  "inv_on_hand","new_ss_lbs_v4","shortfall","days_stockout"]].copy()
                show_b.columns = ["Site","Item","Description","Tier",
                                   "On Hand (lbs)","Rec. SS (lbs)","Shortfall (lbs)","Days to Stockout"]
                for c in ["On Hand (lbs)","Rec. SS (lbs)","Shortfall (lbs)"]:
                    show_b[c] = show_b[c].apply(lambda v: n(v,1))
                show_b["Days to Stockout"] = show_b["Days to Stockout"].apply(lambda v: n(v,1))
                st.dataframe(show_b, use_container_width=True, height=400, hide_index=True)
            else:
                st.success("✅ All A/B-tier items meet recommended safety stock levels.")
 
    # Bulk tank utilization
    st.markdown("### 🛢 Bulk Tank Utilization (Lake Charles)")
    LC_TANKS = {
        "T25":40212,"T15":43388,"CM847":51478,"CM969":52138,"CM1115":95933,
        "P10":47942,"T10":73309,"O50":43148,"RS266":51298,"RS883":51598,
        "AP30":52437,"T11":89652,"T18":54225,"RS280":55767,"RS977":103057,
        "RS825":72000,"RS820":71432,"Z86":6000
    }
    if "site_group" in inv.columns and "inv_on_hand" in inv.columns:
        lc_inv = inv[inv["site_group"]=="Lake Charles"].set_index("item_code")["inv_on_hand"].to_dict()
        tank_rows = []
        for item, cap in LC_TANKS.items():
            oh  = float(lc_inv.get(item, 0))
            uti = min(oh/cap*100, 100) if cap > 0 else 0
            tank_rows.append({"Item":item,"On Hand (lbs)":oh,"Tank Cap 80% (lbs)":cap,"Utilization %":uti})
        df_tk = pd.DataFrame(tank_rows)
        fig_tk = px.bar(
            df_tk.sort_values("Utilization %"), x="Utilization %", y="Item",
            orientation="h", color="Utilization %",
            color_continuous_scale=[[0,GREEN],[0.5,"#FFF2CC"],[1.0,RED]],
            range_color=[0,100],
            text=df_tk.sort_values("Utilization %")["Utilization %"].apply(lambda v: f"{v:.0f}%"),
            title="LC Bulk Tank Utilization (% of 80% safety capacity)")
        fig_tk.update_traces(textposition="outside")
        fig_tk.update_layout(height=480, coloraxis_showscale=False, **CHART)
        st.plotly_chart(fig_tk, use_container_width=True)
 
 
# ═══════════════════════════════════════════════════
# TAB 6 — CONSUMPTION & SEASONALITY
# ═══════════════════════════════════════════════════
def t6_seasonality(D, filt):
    st.markdown("## 📈 Consumption & Seasonality Analysis")
    st.markdown("""
    <div class='fbox'>
    <b>Seasonality Index</b> = Average consumption in that month ÷ Overall monthly average.
    Index > 1.2 = peak demand month (stock up early).
    Index < 0.8 = low demand month.
    Helps procurement know WHEN to build inventory ahead of demand spikes.
    </div>""", unsafe_allow_html=True)
 
    cons = D["cons"]
 
    f1,f2,f3 = st.columns(3)
    with f1:
        site_s = st.selectbox("Site", ["All Sites"]+sorted(cons["site_group"].unique().tolist()), key="s_s")
    with f2:
        grp_s  = st.selectbox("Item Group", ["All","Raw Materials (LB)","Packaging (EA)"], key="s_g")
    with f3:
        yrs    = st.multiselect("Years", [2021,2022,2023,2024,2025,2026],
                                 default=[2024,2025], key="s_y")
 
    cf = cons.copy()
    if site_s != "All Sites": cf = cf[cf["site_group"] == site_s]
    if grp_s == "Raw Materials (LB)":  cf = cf[cf.get("unit_of_measure","LB") == "LB"]
    elif grp_s == "Packaging (EA)":    cf = cf[cf.get("unit_of_measure","EA") == "EA"]
    if yrs: cf = cf[cf["year"].isin(yrs)]
 
    # Monthly trend
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### Monthly Consumption Trend (All Sites)")
        monthly = (cons.groupby(["year","period_month"])["qty_issued"].sum().reset_index())
        monthly["date_str"] = (monthly["year"].astype(int).astype(str) + "-" +
                                monthly["period_month"].astype(int).astype(str).str.zfill(2))
        monthly = monthly.sort_values("date_str")
        fig = px.line(monthly, x="date_str", y="qty_issued",
                       title="Total Consumption by Month",
                       labels={"date_str":"Month","qty_issued":"Qty Consumed"},
                       color_discrete_sequence=[BLUE])
        fig.update_traces(line=dict(width=2))
        if len(monthly) > 2:
            xn = list(range(len(monthly)))
            z  = np.polyfit(xn, monthly["qty_issued"].fillna(0), 1)
            tr = np.poly1d(z)(xn)
            fig.add_trace(go.Scatter(x=monthly["date_str"], y=tr,
                                      name="Trend", line=dict(color=RED, dash="dash", width=2)))
        fig.update_layout(height=360, xaxis_tickangle=-45, **CHART)
        st.plotly_chart(fig, use_container_width=True)
 
    with c_r:
        st.markdown("### Seasonality Index by Month")
        if not cf.empty:
            ma = cf.groupby("period_month")["qty_issued"].mean().reset_index()
            oa = ma["qty_issued"].mean()
            ma["idx"] = (ma["qty_issued"] / oa).round(2) if oa > 0 else 1
            ma["mname"] = ma["period_month"].map(MONTH)
            colors_bar  = [RED if v>1.2 else (STEEL if v<0.8 else GREY) for v in ma["idx"]]
            fig2 = go.Figure(go.Bar(
                x=ma["mname"], y=ma["idx"], marker_color=colors_bar,
                text=ma["idx"].apply(lambda v: f"{v:.2f}"), textposition="outside"))
            fig2.add_hline(y=1.2, line_dash="dash", line_color=RED,   annotation_text="Peak (1.2)")
            fig2.add_hline(y=0.8, line_dash="dash", line_color=STEEL, annotation_text="Low (0.8)")
            fig2.update_layout(height=360,
                               title="Seasonality Index (Red=Peak · Blue=Low · Grey=Normal)",
                               yaxis_title="Index", **CHART)
            st.plotly_chart(fig2, use_container_width=True)
 
    # Heatmap
    st.markdown("### Seasonality Heatmap — Top 20 A-Items")
    st.caption("Red = peak demand. Blue = low demand. Green = normal. "
               "Use this to plan inventory build-up before demand spikes.")
    cons_lb = cons[cons["year"].isin([2024,2025])]
    if "unit_of_measure" in cons_lb.columns:
        cons_lb = cons_lb[cons_lb["unit_of_measure"] == "LB"]
    a_items = filt[(filt["abc_tier"]=="A") & (filt.get("is_bad_apple","NO")=="NO")]["item_code"].unique()[:20]
    heat = (cons_lb[cons_lb["item_code"].isin(a_items)]
            .groupby(["item_code","period_month"])["qty_issued"].mean().reset_index())
 
    if not heat.empty:
        piv = heat.pivot(index="item_code", columns="period_month", values="qty_issued").fillna(0)
        rm  = piv.mean(axis=1).replace(0, 1)
        for c in piv.columns:
            piv[c] = piv[c] / rm
        piv.columns = [MONTH.get(c, str(c)) for c in piv.columns]
        fig_h = px.imshow(
            piv,
            color_continuous_scale=[[0,BLUE],[0.35,LBLUE],[0.6,BG],[0.8,AMBER],[1,RED]],
            zmin=0.4, zmax=1.8, text_auto=".2f",
            title="Seasonality Index — Top 20 A-Items (2024-2025)",
            labels=dict(x="Month", y="Item Code", color="Index"))
        fig_h.update_layout(height=max(380, len(a_items)*26), **CHART)
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.info("Not enough data for the heatmap with current selection.")
 
    # Seasonal items
    st.markdown("### Items Flagged as Seasonal — Peak Months")
    cons24 = cons[cons["year"].isin([2024,2025])]
    if not cons24.empty:
        am = cons24.groupby(["item_code","period_month"])["qty_issued"].mean().reset_index()
        ov = am.groupby("item_code")["qty_issued"].mean()
        am = am.merge(ov.rename("overall"), on="item_code")
        am["idx"] = (am["qty_issued"] / am["overall"].replace(0,1)).round(2)
        seasonal = (am[am["idx"] > 1.2]
                    .groupby("item_code")
                    .agg(peak_months=("period_month",
                                      lambda x: ", ".join(MONTH.get(m,"?") for m in sorted(x))),
                         max_idx=("idx","max"))
                    .reset_index().sort_values("max_idx", ascending=False).head(30))
        seasonal.columns = ["Item Code","Peak Months","Max Seasonality Index"]
        seasonal["Max Seasonality Index"] = seasonal["Max Seasonality Index"].apply(lambda v: f"{v:.2f}")
        st.dataframe(seasonal, use_container_width=True, height=380, hide_index=True)
 
    # Growth
    st.markdown("### Top 20 Fastest-Growing Items (2023 vs 2024-2025)")
    c23   = cons[cons["year"]==2023].groupby("item_code")["qty_issued"].sum()
    c2425 = cons[cons["year"].isin([2024,2025])].groupby("item_code")["qty_issued"].sum()
    grw   = pd.concat([c23.rename("y2023"), c2425.rename("y2425")], axis=1).dropna()
    grw   = grw[grw["y2023"] > 1000].copy()
    grw["growth_pct"] = ((grw["y2425"] - grw["y2023"]) / grw["y2023"] * 100).round(1)
    grw   = grw.nlargest(20,"growth_pct").reset_index()
    grw.columns = ["Item Code","Lbs 2023","Lbs 2024-25","Growth %"]
    grw["Lbs 2023"]    = grw["Lbs 2023"].apply(lambda v: n(v,0))
    grw["Lbs 2024-25"] = grw["Lbs 2024-25"].apply(lambda v: n(v,0))
    grw["Growth %"]    = grw["Growth %"].apply(lambda v: f"{v:+.1f}%")
    st.dataframe(grw, use_container_width=True, height=380, hide_index=True)
 
 
# ═══════════════════════════════════════════════════
# TAB 7 — D-TIER & MTO STRATEGY
# ═══════════════════════════════════════════════════
def t7_dtier(D):
    st.markdown("## 🗑 D-Tier Items & MTO Powerhouse Strategy")
 
    df_d  = D["d_tier"]
    df_gm = D["good_missing"]
    df_gs = D["good_stock"]
    df_ba = D["bad_apple"]
    df_ss = D["ss"]
 
    ga_under = (df_ss["audit_flag_v4"].str.contains("GOOD APPLE.*UNDER", na=False)).sum()
 
    c_ga, c_ba = st.columns(2)
    with c_ga:
        st.markdown(f"""
        <div style="background:{AMBER};border-radius:10px;padding:20px;color:{WHITE};">
          <div style="font-size:17px;font-weight:800;">⭐ Good Apple — Always Stock</div>
          <div style="font-size:13px;margin-top:8px;line-height:1.7;">
            Total on priority list: <b>146 items</b><br>
            In LN with parameters: <b>59 items</b><br>
            Missing LN parameters: <b>93 items</b> — action needed<br>
            Currently understocked: <b>{ga_under} items</b>
          </div>
          <div style="font-size:11px;margin-top:8px;opacity:0.9;">
            These raws feed ~90% of Carboline's make-to-order portfolio.
            Always maintain safety stock for these items.
          </div>
        </div>""", unsafe_allow_html=True)
 
    with c_ba:
        st.markdown(f"""
        <div style="background:{GREY};border-radius:10px;padding:20px;color:{WHITE};">
          <div style="font-size:17px;font-weight:800;">🗑 Bad Apple — Phase Out</div>
          <div style="font-size:13px;margin-top:8px;line-height:1.7;">
            Total on phase-out list: <b>1,144 items</b><br>
            Still have LN parameters: <b>94 items</b> — needs removal<br>
            Already inactive in LN: <b>1,050 items</b><br>
            Safety Stock forced to: <b>Zero for all 94</b>
          </div>
          <div style="font-size:11px;margin-top:8px;opacity:0.9;">
            LN ordering parameters should be removed to eliminate
            phantom planned purchase orders.
          </div>
        </div>""", unsafe_allow_html=True)
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### D-Tier Breakdown")
        never = (df_d["total_lbs_all_years"] == 0).sum()
        slow  = (df_d["lbs_2021_2023"] > 0).sum()
        rop_f = df_d.get("has_rop_in_ln", pd.Series(dtype=str)).astype(str).str.startswith("YES").sum()
        fig = go.Figure(go.Pie(
            labels=["Never Consumed","Slow Movers\n(zero since 2024)","Have ROP in LN"],
            values=[max(never-slow,0), slow, rop_f],
            hole=0.5, marker_colors=[GREY, AMBER, RED],
            textinfo="label+value+percent", textfont=dict(size=12)))
        fig.update_layout(
            height=360,
            annotations=[dict(text="1,760\nD-Tier", x=0.5, y=0.5,
                               font_size=13, showarrow=False, font_color=NAVY)],
            **CHART)
        st.plotly_chart(fig, use_container_width=True)
 
    with c_r:
        st.markdown("### ⚠ Items With ROP Still Active (13 items)")
        st.caption("Zero consumption but still have ordering parameters — "
                   "may generate unnecessary planned purchase orders.")
        if "has_rop_in_ln" in df_d.columns:
            rop_items = df_d[df_d["has_rop_in_ln"].astype(str).str.startswith("YES")][
                ["item_code","item_description","item_group","total_lbs_all_years"]
            ].copy()
            rop_items.columns = ["Item Code","Description","Group","Total LBS All Years"]
            rop_items["Total LBS All Years"] = rop_items["Total LBS All Years"].apply(lambda v: n(v,0))
            st.dataframe(rop_items, use_container_width=True, height=320, hide_index=True)
 
    # Full D-tier
    st.markdown("### Full D-Tier Item List (1,760 items)")
    filt_d = st.radio("Show:", ["All D-Tier","Never Consumed","Slow Movers"], horizontal=True)
    show_d = df_d.copy()
    if filt_d == "Never Consumed":     show_d = df_d[df_d["total_lbs_all_years"] == 0]
    elif filt_d == "Slow Movers":      show_d = df_d[df_d["lbs_2021_2023"] > 0]
 
    cols_d = [c for c in ["item_code","item_description","item_group","item_group_label",
                           "planning_signal","standard_cost_usd","total_lbs_all_years",
                           "lbs_2021_2023","last_year_consumed","has_rop_in_ln","d_tier_reason"]
              if c in show_d.columns]
    disp_d = show_d[cols_d].copy()
    rename_d = {
        "item_code":"Item Code","item_description":"Description",
        "item_group":"Group","item_group_label":"Group Label",
        "planning_signal":"Signal","standard_cost_usd":"Std Cost ($)",
        "total_lbs_all_years":"Total LBS","lbs_2021_2023":"LBS 2021-23",
        "last_year_consumed":"Last Year","has_rop_in_ln":"ROP in LN?",
        "d_tier_reason":"Reason"
    }
    disp_d.rename(columns=rename_d, inplace=True)
    for c in ["Total LBS","LBS 2021-23"]:
        if c in disp_d.columns:
            disp_d[c] = disp_d[c].apply(lambda v: n(v,0))
    if "Std Cost ($)" in disp_d.columns:
        disp_d["Std Cost ($)"] = disp_d["Std Cost ($)"].apply(lambda v: d(v,4))
    st.dataframe(disp_d, use_container_width=True, height=400, hide_index=True)
    dl_excel(disp_d, "Carboline_D_Tier_List.xlsx")
 
    # Good Apple missing
    st.markdown(f"### ⭐ Good Apple Items Missing LN Parameters (93 items)")
    st.caption("On the priority list but have no ordering parameters in LN. "
               "LN will never auto-generate purchase orders for these.")
    if not df_gm.empty:
        gm2 = df_gm[["item_code","std_cost","destination","lead_time_days"]].copy()
        gm2.columns = ["Item Code","Std Cost ($)","Destination Site","Manager Lead Time (days)"]
        gm2["Std Cost ($)"] = gm2["Std Cost ($)"].apply(lambda v: d(v,4))
        gm2["Manager Lead Time (days)"] = gm2["Manager Lead Time (days)"].apply(lambda v: n(v,1))
        gm2["Action"] = "Add Item Ordering parameters in LN"
        st.dataframe(gm2, use_container_width=True, height=320, hide_index=True)
        dl_excel(gm2, "Carboline_Good_Apple_Missing_LN.xlsx")
 
    # Bad Apple removal
    st.markdown("### 🗑 Bad Apple Items — Remove From LN (94 items)")
    st.caption("Safety stock forced to zero. LN ordering parameters should be removed "
               "by the procurement team to eliminate phantom planned orders.")
    if not df_ba.empty:
        ba_cols = [c for c in ["Site","Item Code","Description","ABC Tier",
                                "Current LN ROP\n(was active)","MOQ","Old $ Risk"]
                   if c in df_ba.columns]
        ba2 = df_ba[ba_cols].copy() if ba_cols else df_ba.copy()
        # Clean col names
        ba2.columns = [c.replace("\n"," ") for c in ba2.columns]
        if "Old $ Risk" in ba2.columns:
            ba2["Old $ Risk"] = ba2["Old $ Risk"].apply(lambda v: d(v,2))
        st.dataframe(ba2, use_container_width=True, height=320, hide_index=True)
        dl_excel(ba2, "Carboline_Bad_Apple_Remove.xlsx")
 
 
# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    data, missing = load()
 
    if missing:
        st.error(
            "❌ **Missing Excel files.** Please copy these into the same folder as app.py:\n\n" +
            "\n".join(f"• **{f}**" for f in missing)
        )
        st.info(
            "📁 Your folder should contain:\n"
            "- rop_ss_moq.xlsx\n"
            "- clean_consumption.xlsx\n"
            "- clean_po.xlsx\n"
            "- clean_lead_time.xlsx\n"
            "- clean_cost.xlsx\n"
            "- clean_inventory.xlsx\n"
            "- clean_supplier.xlsx\n"
            "- clean_item_master.xlsx\n"
            "- abc_classification.xlsx\n"
            "- Carboline_MasterSS_Summary_v1(3).xlsx"
        )
        st.stop()
 
    df_ss = data["ss"]
    site, tier, apple = sidebar(df_ss)
    filt = apply_f(df_ss, site, tier, apple)
 
    tabs = st.tabs([
        "📊 Executive Overview",
        "🔴 Priority Audit List",
        "🧮 Safety Stock Calculator",
        "🚚 Supplier Performance",
        "📦 Inventory & Coverage",
        "📈 Consumption & Seasonality",
        "🗑 D-Tier & MTO Strategy",
    ])
 
    with tabs[0]: t1_overview(data, filt)
    with tabs[1]: t2_audit(data, filt)
    with tabs[2]: t3_calc(data, filt)
    with tabs[3]: t4_supplier(data, filt)
    with tabs[4]: t5_inventory(data, filt)
    with tabs[5]: t6_seasonality(data, filt)
    with tabs[6]: t7_dtier(data)
 
 
if __name__ == "__main__":
    main()

