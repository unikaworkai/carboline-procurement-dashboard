import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
import re
import io
import glob
from datetime import datetime, timedelta
 
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
 
# Bug 1 fix: heading was being cut off by insufficient top padding /
# overlap with Streamlit's own header bar. Force enough top padding
# on the main block container and the sidebar, and reset any
# negative/zero margin-top that was clipping the banner.
st.markdown(f"""
<style>
  .main .block-container {{
      padding-top: 2rem !important;
      margin-top: 0 !important;
  }}
  section[data-testid="stSidebar"] > div {{
      padding-top: 1rem !important;
  }}
  html, body, [class*="css"] {{ font-family: Arial, sans-serif !important; }}
  .main {{ background-color: {BG}; }}
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
  .reco {{
    background:{WHITE}; border:2px solid {STEEL}; border-radius:10px;
    padding:18px 22px; margin-top:10px;
  }}
  .foot {{ color:{GREY}; font-size:11px; text-align:center;
    margin-top:16px; padding-top:8px; border-top:1px solid #ddd; }}
  h2 {{ color:{NAVY}; }}
  h3 {{ color:{NAVY}; font-size:16px; }}
  .header-banner {{
    background:linear-gradient(135deg,{NAVY},{BLUE});
    border-radius:12px; padding:20px 30px; margin-top:10px; margin-bottom:18px;
  }}
  .header-banner .htitle {{
    color:{WHITE}; font-size:22px; font-weight:800; letter-spacing:1px;
  }}
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
 
SITE_LN_CODE = {
    "Lake Charles": "L3021",
    "Green Bay":    "L3023",
    "Dayton":       "L303T",
    "Louisa":       "L303S",
}
 
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
 
# ── NAME SCRUBBING ───────────────────────────────────────────
# Raw source files contain individual staff names in free-text fields
# (action notes, comments). UI must show role-based labels only.
_NAME_MAP = {
    "Pat":     "Procurement Lead",
    "Adrian":  "Procurement Team",
    "Cyndi":   "Procurement Team",
    "Mike":    "Procurement Team",
    "Brianna": "Procurement Team",
    "Gracie":  "Procurement Team",
    "Jessica": "Procurement Team",
    "Dillon":  "Site Buyer",
    "Unika":   "Procurement Team",
}
_NAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _NAME_MAP.keys()) + r")\b"
)
 
def scrub_names(val):
    """Replace any individual staff name with a role-based label."""
    if not isinstance(val, str):
        return val
    return _NAME_PATTERN.sub(lambda m: _NAME_MAP.get(m.group(1), "Procurement Team"), val)
 
def scrub_df(df, cols=None):
    """Apply name scrubbing to all object columns (or a given subset)."""
    if df is None or df.empty:
        return df
    df = df.copy()
    target_cols = cols if cols is not None else df.select_dtypes(include="object").columns
    for c in target_cols:
        if c in df.columns:
            df[c] = df[c].apply(scrub_names)
    return df
 
# ── HELPERS ───────────────────────────────────────────────────
def n(v, dec=0):
    try: return f"{float(v):,.{dec}f}"
    except: return "—"
 
def d(v, dec=0):
    try: return f"${float(v):,.{dec}f}"
    except: return "—"
 
def p(v, dec=1):
    try: return f"{float(v):.{dec}f}%"
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
 
def dl_excel(df, filename, key=None):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    st.download_button(f"⬇️ Download {filename}",
                       data=buf.getvalue(), file_name=filename,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key=key)
 
def find_file(*candidates):
    """Return the first matching file path, trying exact names first,
    then a glob fallback so minor filename punctuation differences
    (parentheses, underscores, spaces) don't break the load."""
    for c in candidates:
        if os.path.exists(c):
            return c
    for c in candidates:
        base = re.sub(r"[\(\)_]", "*", c)
        matches = glob.glob(base)
        if matches:
            return matches[0]
    return None
 
# ── EXCEL READER ──────────────────────────────────────────────
def clean_cols(cols):
    return [str(c).split("\n")[0].split("▶")[0].strip() for c in cols]
 
def read_sheet(path, sheet, id_col, skip=3):
    try:
        df = pd.read_excel(path, sheet_name=sheet, skiprows=skip)
        df.columns = clean_cols(df.columns)
        if id_col not in df.columns:
            # id_col may have had a formula/newline suffix originally
            return df.reset_index(drop=True)
        df = df[df[id_col].notna()]
        df = df[df[id_col].astype(str).str.strip() != id_col]
        df = df[~df[id_col].astype(str).str.startswith("NaN")]
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"Could not read '{sheet}' from {path}: {e}")
        return pd.DataFrame()
 
 
# ── DATA LOADING ──────────────────────────────────────────────
@st.cache_data(show_spinner="Loading Carboline data...")
def load():
    MASTER = find_file(
        "Carboline_MasterSS_Summary_v1(3).xlsx",
        "Carboline_MasterSS_Summary_v1_3_.xlsx",
        "Carboline_MasterSS_Summary_v1(3.xlsx",
    )
 
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
    }
    missing = [f for f in needed if not os.path.exists(f)]
    if MASTER is None:
        missing.append("Carboline_MasterSS_Summary_v1(3).xlsx")
    if missing:
        return None, missing
 
    D = {}
 
    # ── SS file ───────────────────────────────────────────────
    df_ss = read_sheet("rop_ss_moq.xlsx", "Full_SS_Results", "audit_flag_v4", skip=3)
    col_map = {
        "ss_dollars F=OL": "ss_dollars",
        "rop_dollars F=PL": "rop_dollars",
        "avg_inv_ F=(O+P)/2L": "avg_inv_dollars",
        "curr_rop_ F=ML": "curr_rop_dollars",
    }
    df_ss.rename(columns=col_map, inplace=True)
 
    num_cols = ["avg_daily_usage_lbs", "lead_time_used_v4", "buffer_factor_v4",
                "standard_cost_usd", "current_rop_in_ln", "moq_order_increment",
                "new_ss_lbs_v4", "new_rop_lbs_v4", "rop_to_enter_ln",
                "rop_gap_lbs_v4", "financial_risk_v4", "otd_pct_2day"]
    for c in num_cols:
        if c in df_ss.columns:
            df_ss[c] = pd.to_numeric(df_ss[c], errors="coerce").fillna(0)
 
    df_ss["ss_dollars"]       = df_ss["new_ss_lbs_v4"]  * df_ss["standard_cost_usd"]
    df_ss["rop_dollars"]      = df_ss["new_rop_lbs_v4"] * df_ss["standard_cost_usd"]
    df_ss["avg_inv_dollars"]  = (df_ss["new_ss_lbs_v4"] + df_ss["new_rop_lbs_v4"]) / 2 * df_ss["standard_cost_usd"]
    df_ss["curr_rop_dollars"] = df_ss["current_rop_in_ln"] * df_ss["standard_cost_usd"]
 
    # BUG 3 / BUG 4 FIX: is_good_apple / is_bad_apple actually contain
    # "⭐ YES" / "🗑 YES" (with emoji prefix) rather than a plain "YES",
    # so a naive == "YES" comparison returns zero matches. Normalize by
    # checking whether the cleaned, upper-cased string *contains* YES.
    if "is_good_apple" not in df_ss.columns: df_ss["is_good_apple"] = "NO"
    if "is_bad_apple"  not in df_ss.columns: df_ss["is_bad_apple"]  = "NO"
 
    def _flag_yn(series):
        s = series.astype(str).str.strip().str.upper()
        return np.where(s.str.contains("YES"), "YES", "NO")
 
    df_ss["is_good_apple"] = _flag_yn(df_ss["is_good_apple"])
    df_ss["is_bad_apple"]  = _flag_yn(df_ss["is_bad_apple"])
 
    D["ss"] = df_ss
 
    # Good / Bad apple detail sheets
    df_bad = read_sheet("rop_ss_moq.xlsx", "🗑 Bad_Apple_Remove", "Site", skip=3)
    df_bad = scrub_df(df_bad)
    D["bad_apple"] = df_bad
 
    df_gs = read_sheet("rop_ss_moq.xlsx", "⭐ Good_Apple_Stock", "Site", skip=3)
    D["good_stock"] = df_gs
 
    df_gm = pd.read_excel("rop_ss_moq.xlsx",
                           sheet_name="⭐ Good_Apple_Missing_ROP",
                           skiprows=2, header=0)
    df_gm = df_gm[df_gm.iloc[:, 0].notna()]
    df_gm.columns = ["item_code", "std_cost", "destination", "lead_time_days", "action_raw"][:len(df_gm.columns)]
    df_gm["action"] = "Add Item Ordering parameters in LN"
    D["good_missing"] = df_gm
 
    # ── Consumption ───────────────────────────────────────────
    df_c = read_sheet("clean_consumption.xlsx", "Clean_Consumption_Data", "site_group", skip=3)
    df_c["qty_issued"]   = pd.to_numeric(df_c.get("qty_issued",   0), errors="coerce").fillna(0)
    df_c["year"]         = pd.to_numeric(df_c.get("year",         0), errors="coerce")
    df_c["period_month"] = pd.to_numeric(df_c.get("period_month", 0), errors="coerce")
    df_c = df_c[df_c["qty_issued"] > 0]
    D["cons"] = df_c
 
    # ── PO ────────────────────────────────────────────────────
    df_po = read_sheet("clean_po.xlsx", "Clean_PO_Data", "item_code", skip=3)
    df_po["unit_price"]  = pd.to_numeric(df_po.get("unit_price",  0), errors="coerce").fillna(0)
    df_po["ordered_qty"] = pd.to_numeric(df_po.get("ordered_qty", 0), errors="coerce").fillna(0)
    df_po["received_qty"] = pd.to_numeric(df_po.get("received_qty", 0), errors="coerce").fillna(0)
    for c in ["order_date", "planned_receipt_date", "actual_receipt_date", "confirmed_receipt_date"]:
        if c in df_po.columns:
            df_po[c] = pd.to_datetime(df_po[c], errors="coerce")
    D["po"] = df_po
 
    # ── Lead time ─────────────────────────────────────────────
    df_lt = read_sheet("clean_lead_time.xlsx", "Lead_Time_Data", "po_number", skip=3)
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
    df_cost["standard_cost_usd"] = pd.to_numeric(df_cost.get("standard_cost_usd", 0), errors="coerce").fillna(0)
    D["cost"] = df_cost
 
    # ── Inventory ─────────────────────────────────────────────
    df_inv = read_sheet("clean_inventory.xlsx", "Inventory_OnHand", "item_code", skip=3)
    for c in ["economic_stock", "available_stock", "inv_on_hand", "inv_on_order", "inv_allocated"]:
        if c in df_inv.columns:
            df_inv[c] = pd.to_numeric(df_inv[c], errors="coerce").fillna(0)
    D["inv"] = df_inv
 
    # ── Supplier ──────────────────────────────────────────────
    df_sup = read_sheet("clean_supplier.xlsx", "PO_Suppliers_Only", "supplier_bp_code", skip=3)
    D["sup"] = df_sup
 
    # ── Item master ───────────────────────────────────────────
    df_im = read_sheet("clean_item_master.xlsx", "3_Item_Master", "item_code", skip=3)
    D["item_master"] = df_im
 
    # ── ABC ───────────────────────────────────────────────────
    df_abc = pd.read_excel("abc_classification.xlsx",
                           sheet_name="8003_RawMaterials_ABC", skiprows=3)
    df_abc.columns = ["rank", "abc_tier", "item_code", "item_description", "item_group",
                      "planning_signal", "total_lbs_2024_2025", "pct_of_total_lbs",
                      "cumulative_pct", "buffer_factor", "ss_eligible", "notes"
                      ][:len(df_abc.columns)]
    df_abc = df_abc[df_abc["item_code"].notna()]
    D["abc"] = df_abc
 
    # ── Master summary ────────────────────────────────────────
    df_site = pd.read_excel(MASTER, sheet_name="Site_Summary", skiprows=3, nrows=6)
    df_site.columns = ["site", "items", "a_under", "ga_under", "bad_in_file",
                       "ss_dol", "rop_dol", "avg_inv_dol", "avg_lt", "otd", "notes"
                       ][:len(df_site.columns)]
    df_site = df_site[df_site["site"].notna()]
    df_site = df_site[~df_site["site"].astype(str).str.contains("TOTAL|nan", na=True)]
    df_site = scrub_df(df_site, cols=["notes"])
    D["site_sum"] = df_site
 
    df_d = pd.read_excel(MASTER, sheet_name="D_Tier_Full_List", skiprows=1, header=0)
    df_d = df_d[df_d["item_code"].notna()]
    for c in ["total_lbs_all_years", "lbs_2021_2023"]:
        if c in df_d.columns:
            df_d[c] = pd.to_numeric(df_d[c], errors="coerce").fillna(0)
    D["d_tier"] = df_d
 
    df_abc_site = pd.read_excel(MASTER, sheet_name="ABC_by_Site", skiprows=1, header=0)
    df_abc_site = df_abc_site[df_abc_site["site"].notna() &
                               ~df_abc_site["site"].astype(str).str.contains("SUBTOTAL|NaN|nan", na=True)]
    D["abc_site"] = df_abc_site
 
    # ── Most recent transaction date (data freshness) ─────────
    freshness_dates = []
    if "order_date" in df_po.columns and df_po["order_date"].notna().any():
        freshness_dates.append(df_po["order_date"].max())
    if "actual_receipt_date" in df_po.columns and df_po["actual_receipt_date"].notna().any():
        freshness_dates.append(df_po["actual_receipt_date"].max())
    D["data_freshness"] = max(freshness_dates) if freshness_dates else None
 
    return D, []
 
 
# ── FILTERS ───────────────────────────────────────────────────
def scope(df):
    """Remove OUT_OF_SCOPE and BAD APPLE from financial analysis."""
    return df[(df["abc_tier"] != "OUT_OF_SCOPE") & (df.get("is_bad_apple", "NO") == "NO")]
 
def apply_f(df, site, tier, apple):
    dd = df.copy()
    if site != "All Sites": dd = dd[dd["site_group"] == site]
    if tier != "All Tiers": dd = dd[dd["abc_tier"] == tier]
    if apple == "⭐ Good Apple Only":   dd = dd[dd.get("is_good_apple", "NO") == "YES"]
    elif apple == "🗑 Bad Apple Only": dd = dd[dd.get("is_bad_apple", "NO") == "YES"]
    elif apple == "Regular Only":
        dd = dd[(dd.get("is_good_apple", "NO") == "NO") & (dd.get("is_bad_apple", "NO") == "NO")]
    return dd
 
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
    good_n = (df_ss.get("is_good_apple", "NO") == "YES").sum()
    bad_n  = (df_ss.get("is_bad_apple",  "NO") == "YES").sum()
    st.sidebar.markdown(f"**In-scope items:** {len(ins):,}")
    st.sidebar.markdown(f"**🔴 A-understocked:** {(ins['audit_flag_v4'].str.startswith('🔴')).sum():,}")
    st.sidebar.markdown(f"**⭐ Good Apples:** {good_n:,}")
    st.sidebar.markdown(f"**🗑 Bad Apples (in file):** {bad_n:,}")
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
    <div class="header-banner">
      <div class="htitle">🏭 Procurement Engine Dashboard</div>
      <div style="color:rgba(255,255,255,0.8);font-size:13px;margin-top:4px;">
        Carboline Company · Lake Charles · Green Bay · Dayton · Louisa</div>
      <div style="color:rgba(255,255,255,0.6);font-size:11px;margin-top:4px;">
        Safety Stock v4 · Good Apple / Bad Apple · Bulk Tank Caps Applied</div>
    </div>""", unsafe_allow_html=True)
 
    ins = scope(filt)
    a_under  = (ins["audit_flag_v4"].str.startswith("🔴")).sum()
    ga_under = (ins["audit_flag_v4"].str.contains("GOOD APPLE.*UNDER", na=False)).sum()
    risk     = ins[ins["rop_gap_lbs_v4"] < 0]["financial_risk_v4"].sum()
    ss_inv   = ins["ss_dollars"].sum()
 
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: kpi("📦 In-Scope Items",     n(len(ins)), "Excl. finished goods & bad apples")
    with c2: kpi("🔴 A-Items Underst.",   n(a_under),  "Fix LN reorder point now",        "kpi-b")
    with c3: kpi("⭐ Good Apple Underst.", n(ga_under), "Priority stock below safe level", "kpi-a")
    with c4: kpi("💰 A-Item $ Risk",      d(risk, 0),  "Understocked A-item exposure",    "kpi-b")
    with c5: kpi("📈 SS Investment",      d(ss_inv, 0),"Recommended SS × standard cost")
    with c6: kpi("🚚 OTD Rate",           "78.0%",     "With ±2 day tolerance",            "kpi-g")
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # NEW: Site Summary mini-table (pulled from the master file's Site_Summary
    # sheet for speed rather than recomputed on the fly)
    st.markdown("### Site Summary")
    site_sum = D.get("site_sum", pd.DataFrame())
    if not site_sum.empty:
        ss_disp = site_sum[["site", "items", "a_under", "ss_dol", "rop_dol", "avg_lt", "otd"]].copy()
        ss_disp.columns = ["Site Name", "Items", "A-Understocked", "SS $", "ROP $", "Avg Lead Time", "OTD %"]
        ss_disp["SS $"]  = ss_disp["SS $"].apply(lambda v: d(v, 0))
        ss_disp["ROP $"] = ss_disp["ROP $"].apply(lambda v: d(v, 0))
        ss_disp["Avg Lead Time"] = ss_disp["Avg Lead Time"].apply(lambda v: f"{float(v):.1f} days" if pd.notna(v) else "—")
        ss_disp["OTD %"] = ss_disp["OTD %"].apply(lambda v: p(v))
        ss_disp["Items"] = ss_disp["Items"].apply(lambda v: n(v))
        ss_disp["A-Understocked"] = ss_disp["A-Understocked"].apply(lambda v: n(v))
        st.dataframe(ss_disp, use_container_width=True, height=215, hide_index=True)
    else:
        st.info("Site Summary not available.")
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # Row 1: Status by site | ABC donut
    c_l, c_r = st.columns([3, 2])
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
            for col_n, col_c in [("Understocked", RED), ("Overstocked", STEEL), ("OK", GREEN)]:
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
        tc = ins[ins["abc_tier"].isin(["A", "B", "C", "D"])]["abc_tier"].value_counts()
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
    c_l2, c_r2 = st.columns([3, 2])
    with c_l2:
        st.markdown("### Top 10 Items by Financial Risk")
        top10 = ins[ins["rop_gap_lbs_v4"] < -0.01].nlargest(10, "financial_risk_v4").copy()
        if top10.empty:
            st.plotly_chart(empty("No understocked items in selection"), use_container_width=True)
        else:
            top10["lbl"] = top10["item_code"] + " — " + top10["item_description"].str[:28]
            fig3 = px.bar(
                top10, x="financial_risk_v4", y="lbl", orientation="h",
                color="site_group",
                color_discrete_map={"Lake Charles": BLUE, "Green Bay": GREEN, "Dayton": AMBER, "Louisa": ORANGE},
                text=top10["financial_risk_v4"].apply(lambda v: d(v, 0)),
                title="Highest Financial Exposure — Understocked Items")
            fig3.update_traces(textposition="outside", textfont=dict(size=10))
            fig3.update_layout(height=400, yaxis={"categoryorder": "total ascending"},
                               xaxis_tickprefix="$", xaxis_tickformat=",.0f",
                               yaxis_title=None, **CHART)
            st.plotly_chart(fig3, use_container_width=True)
 
    with c_r2:
        st.markdown("### Safety Stock $ by Site")
        sd = ins.groupby("site_group").agg(
            SS=("ss_dollars", "sum"), ROP=("rop_dollars", "sum")).reset_index()
        if sd.empty:
            st.plotly_chart(empty(), use_container_width=True)
        else:
            fig4 = go.Figure()
            fig4.add_trace(go.Bar(name="Safety Stock $", x=sd["site_group"], y=sd["SS"],
                                   marker_color=RED,
                                   text=[d(v, 0) for v in sd["SS"]], textposition="outside",
                                   textfont=dict(size=9)))
            fig4.add_trace(go.Bar(name="ROP $", x=sd["site_group"], y=sd["ROP"],
                                   marker_color=STEEL,
                                   text=[d(v, 0) for v in sd["ROP"]], textposition="outside",
                                   textfont=dict(size=9)))
            fig4.update_layout(barmode="group", height=400,
                               yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                               title="SS $ vs ROP $ by Site (excl. bad apples)", **CHART)
            st.plotly_chart(fig4, use_container_width=True)
 
    # NEW: data freshness indicator
    freshness = D.get("data_freshness")
    fresh_str = freshness.strftime("%B %d, %Y") if pd.notna(freshness) else "Unavailable"
    st.markdown(
        f"<div class='foot'>Data as of June 2026 · Safety Stock v4 · "
        f"OTD uses ±2 day tolerance · Scope: Item Groups 8003 & 8010<br>"
        f"📅 Most recent purchase order transaction on file: <b>{fresh_str}</b></div>",
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
    audit.insert(0, "Rank", range(1, len(audit) + 1))
 
    fa, fb, fc, fd = st.columns([2, 2, 2, 2])
    with fa:
        sites_a = ["All Sites"] + sorted(audit["site_group"].unique().tolist())
        sf = st.selectbox("Site", sites_a, key="a_s")
    with fb:
        tiers_a = ["All Tiers"] + [t for t in ["A", "B", "C"] if t in audit["abc_tier"].unique()]
        tf = st.selectbox("Tier", tiers_a, key="a_t")
    with fc:
        ga_on = st.toggle("⭐ Good Apple Only", key="a_ga")
    with fd:
        rows = st.selectbox("Rows", [25, 50, 100, "All"], key="a_r")
 
    if sf != "All Sites": audit = audit[audit["site_group"] == sf]
    if tf != "All Tiers": audit = audit[audit["abc_tier"] == tf]
    if ga_on: audit = audit[audit.get("is_good_apple", "NO") == "YES"]
    if rows != "All": audit = audit.head(int(rows))
 
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Items Shown", n(len(audit)))
    with m2: st.metric("Total $ Risk", d(audit["financial_risk_v4"].sum(), 0))
    with m3: st.metric("Avg Gap (lbs)", n(audit["rop_gap_lbs_v4"].mean(), 0))
    with m4: st.metric("A-Items", n((audit["abc_tier"] == "A").sum()))
    st.markdown("---")
 
    if audit.empty:
        st.info("No understocked items match the current filters.")
        return
 
    disp = audit[[
        "Rank", "site_group", "item_code", "item_description", "abc_tier",
        "is_good_apple", "current_rop_in_ln", "new_ss_lbs_v4", "new_rop_lbs_v4",
        "rop_to_enter_ln", "rop_gap_lbs_v4", "financial_risk_v4",
        "avg_daily_usage_lbs", "lead_time_used_v4"
    ]].copy()
    disp.columns = [
        "Rank", "Site", "Item Code", "Description", "Tier", "Good Apple",
        "Current LN ROP (lbs)", "Rec. SS (lbs)", "Rec. ROP (lbs)",
        "✅ UPDATE LN TO THIS VALUE", "Gap (lbs)", "Financial Risk ($)",
        "Daily Usage (lbs/day)", "Lead Time (days)"
    ]
    for c in ["Current LN ROP (lbs)", "Rec. SS (lbs)", "Rec. ROP (lbs)",
              "✅ UPDATE LN TO THIS VALUE", "Gap (lbs)", "Daily Usage (lbs/day)"]:
        disp[c] = disp[c].apply(lambda v: n(v, 1))
    disp["Financial Risk ($)"] = disp["Financial Risk ($)"].apply(lambda v: d(v, 2))
    disp["Lead Time (days)"]   = disp["Lead Time (days)"].apply(lambda v: n(v, 1))
 
    st.dataframe(disp, use_container_width=True, height=500, hide_index=True)
 
    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        dl_excel(disp, "Carboline_Priority_Audit_List.xlsx", key="dl_audit_std")
    with c_dl2:
        # NEW: Export for LN — formatted exactly for LN import
        ln_export = audit[["site_group", "item_code", "rop_to_enter_ln", "moq_order_increment"]].copy()
        ln_export.rename(columns={"item_code": "Item"}, inplace=True)
        ln_export["Company"] = 3000
        ln_export["Site"] = ln_export["site_group"].map(SITE_LN_CODE).fillna(ln_export["site_group"])
        ln_export["Order Method"] = audit.get("lt_source_v4", "Order Point")
        ln_export["Safety Stock"] = ln_export["rop_to_enter_ln"]
        ln_export["Order Qty Increment"] = audit["moq_order_increment"]
        ln_export = ln_export[["Company", "Site", "Item", "Order Method",
                                "Safety Stock", "Order Qty Increment"]]
        dl_excel(ln_export, "Carboline_LN_Import_Export.xlsx", key="dl_audit_ln")
 
    # Chart
    top20 = audit.head(20).copy()
    top20["lbl"] = top20["item_code"] + " — " + top20["item_description"].str[:25]
    colors = [AMBER if r == "YES" else RED for r in top20["is_good_apple"]]
    fig = go.Figure(go.Bar(
        x=top20["financial_risk_v4"], y=top20["lbl"], orientation="h",
        marker_color=colors,
        text=[d(v, 0) for v in top20["financial_risk_v4"]],
        textposition="outside"))
    fig.update_layout(
        height=max(380, len(top20) * 22),
        title="Top 20 Items by Financial Risk (Gold = Good Apple priority item)",
        xaxis_tickprefix="$", xaxis_tickformat=",.0f",
        yaxis={"categoryorder": "total ascending"}, **CHART)
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
 
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Items", n(len(ins)))
    with m2: st.metric("Total SS $", d(ins["ss_dollars"].sum(), 0))
    with m3: st.metric("Total ROP $", d(ins["rop_dollars"].sum(), 0))
    with m4: st.metric("Avg Lead Time", f"{ins['lead_time_used_v4'].mean():.1f}d")
    with m5:
        pct = (ins["rop_gap_lbs_v4"] < -0.01).sum() / max(len(ins), 1) * 100
        st.metric("% Understocked", p(pct))
 
    if ins.empty:
        st.info("No items match the current filters.")
        return
 
    cols_need = ["site_group", "item_code", "item_description", "abc_tier", "audit_flag_v4",
                 "is_good_apple", "is_bad_apple", "avg_daily_usage_lbs", "lead_time_used_v4",
                 "buffer_factor_v4", "standard_cost_usd", "current_rop_in_ln",
                 "new_ss_lbs_v4", "new_rop_lbs_v4", "rop_to_enter_ln",
                 "rop_gap_lbs_v4", "financial_risk_v4", "ss_dollars", "rop_dollars"]
    available = [c for c in cols_need if c in ins.columns]
    disp = ins[available].copy()
    rename = {
        "site_group": "Site", "item_code": "Item Code", "item_description": "Description",
        "abc_tier": "Tier", "audit_flag_v4": "Status",
        "is_good_apple": "Good Apple", "is_bad_apple": "Bad Apple",
        "avg_daily_usage_lbs": "Daily Usage (lbs)", "lead_time_used_v4": "Lead Time (days)",
        "buffer_factor_v4": "Buffer", "standard_cost_usd": "Std Cost ($)",
        "current_rop_in_ln": "Current LN ROP", "new_ss_lbs_v4": "Rec. SS (lbs)",
        "new_rop_lbs_v4": "Rec. ROP (lbs)", "rop_to_enter_ln": "✅ Enter in LN",
        "rop_gap_lbs_v4": "Gap (lbs)", "financial_risk_v4": "$ Risk",
        "ss_dollars": "SS Value ($)", "rop_dollars": "ROP Value ($)"
    }
    disp.rename(columns=rename, inplace=True)
    for c in ["Daily Usage (lbs)", "Current LN ROP", "Rec. SS (lbs)",
              "Rec. ROP (lbs)", "✅ Enter in LN", "Gap (lbs)"]:
        if c in disp.columns:
            disp[c] = disp[c].apply(lambda v: n(v, 1))
    for c in ["Std Cost ($)", "$ Risk", "SS Value ($)", "ROP Value ($)"]:
        if c in disp.columns:
            disp[c] = disp[c].apply(lambda v: d(v, 2))
    if "Lead Time (days)" in disp.columns:
        disp["Lead Time (days)"] = disp["Lead Time (days)"].apply(lambda v: n(v, 1))
    if "Buffer" in disp.columns:
        disp["Buffer"] = disp["Buffer"].apply(lambda v: n(v, 1) + "×")
 
    st.dataframe(disp, use_container_width=True, height=520, hide_index=True)
    dl_excel(disp, "Carboline_SS_Calculator.xlsx", key="dl_calc")
 
 
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
        st.warning("Lead time or supplier file unavailable.")
        return
 
    dnu_set = set(sup.loc[sup.get("is_do_not_use", "NO").astype(str).str.upper() == "YES",
                          "supplier_bp_code"].astype(str))
 
    # OTD per supplier
    sup_grp = (recv.groupby("supplier_bp_code")
               .agg(orders=("po_number", "count"),
                    on_time=("on_time_2day", "sum"),
                    avg_lt=("lead_time_days_winsorized", "mean"))
               .reset_index())
    sup_grp["otd_pct"] = (sup_grp["on_time"] / sup_grp["orders"] * 100).round(1)
    sup_grp["avg_lt"]  = sup_grp["avg_lt"].round(1)
    sup_grp["late"]    = sup_grp["orders"] - sup_grp["on_time"]
    sup_grp = sup_grp.merge(
        sup[["supplier_bp_code", "supplier_name", "country_name", "is_us_supplier"]],
        on="supplier_bp_code", how="left")
    sup_grp["supplier_name"] = sup_grp["supplier_name"].fillna(sup_grp["supplier_bp_code"])
    sup_grp["origin"] = sup_grp["is_us_supplier"].apply(
        lambda v: "Domestic (US)" if str(v) == "YES" else "International")
    sup_grp["is_dnu"] = sup_grp["supplier_bp_code"].astype(str).isin(dnu_set)
 
    overall_otd = 78.0
    active      = (sup_grp["orders"] >= 5).sum()
    avg_lt_all  = recv["lead_time_days_winsorized"].mean()
    late_pct    = (1 - recv["on_time_2day"].mean()) * 100
 
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("🚚 Overall OTD",      p(overall_otd), "±2 day tolerance", "kpi-g")
    with k2: kpi("🏢 Active Suppliers", n(active),      "With 5+ orders",   "kpi-b")
    with k3: kpi("⏱ Avg Lead Time",    f"{avg_lt_all:.1f}d", "Winsorized @ 103 days")
    with k4: kpi("❌ Late Delivery",    p(late_pct),    "Without tolerance", "kpi-b")
 
    if dnu_set:
        st.markdown(
            f"<div class='alert'>🚫 {len(dnu_set)} supplier(s) flagged Do-Not-Use — "
            f"highlighted in red throughout this tab.</div>", unsafe_allow_html=True)
 
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
                hover_data={"otd_pct": ":.1f", "orders": True, "avg_lt": ":.1f"},
                color_discrete_map={"Domestic (US)": BLUE, "International": ORANGE},
                labels={"otd_pct": "OTD %", "orders": "Total Orders"},
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
    bot20 = sup5.nsmallest(20, "otd_pct")[
        ["supplier_name", "country_name", "orders", "on_time", "late", "otd_pct", "avg_lt", "is_dnu"]
    ].copy()
    bot20.columns = ["Supplier", "Country", "Total Orders", "On-Time", "Late", "OTD %", "Avg LT (days)", "_dnu"]
    bot20["OTD %"]         = bot20["OTD %"].apply(lambda v: p(v))
    bot20["Avg LT (days)"] = bot20["Avg LT (days)"].apply(lambda v: n(v, 1))
 
    def _style_dnu(row):
        return [f"background-color:{RED};color:white" if row["_dnu"] else "" for _ in row]
 
    bot20_show = bot20.drop(columns=["_dnu"])
    if bot20["_dnu"].any():
        st.dataframe(bot20.style.apply(_style_dnu, axis=1).hide(axis="columns", subset=["_dnu"]),
                     use_container_width=True, height=420)
    else:
        st.dataframe(bot20_show, use_container_width=True, height=420, hide_index=True)
 
    # PPV
    st.markdown("### Purchase Price Variance (PPV) by Supplier")
    st.caption("PPV = (Actual Price Paid − Standard Cost) × Ordered Qty. "
               "Positive = unfavorable (paid more). Negative = favorable (paid less).")
    po2   = po.copy()
    cost2 = cost[["item_code", "standard_cost_usd"]].copy()
    ppv   = po2.merge(cost2, on="item_code", how="left")
    ppv["standard_cost_usd"] = pd.to_numeric(ppv["standard_cost_usd"], errors="coerce").fillna(0)
    ppv["unit_price"]        = pd.to_numeric(ppv.get("unit_price", 0),  errors="coerce").fillna(0)
    ppv["ordered_qty"]       = pd.to_numeric(ppv.get("ordered_qty", 0), errors="coerce").fillna(0)
    ppv["ppv"]               = (ppv["unit_price"] - ppv["standard_cost_usd"]) * ppv["ordered_qty"]
    ppv                      = ppv[ppv["standard_cost_usd"] > 0]
    sup_ppv = (ppv.groupby("supplier_bp_code")["ppv"].sum()
               .reset_index().rename(columns={"ppv": "total_ppv"}))
    sup_ppv = sup_ppv.merge(sup[["supplier_bp_code", "supplier_name"]], on="supplier_bp_code", how="left")
    sup_ppv["supplier_name"] = sup_ppv["supplier_name"].fillna(sup_ppv["supplier_bp_code"])
 
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("**⚠ Unfavorable — Paid More Than Standard**")
        top_u = sup_ppv.nlargest(10, "total_ppv")
        fig_u = px.bar(top_u, x="total_ppv", y="supplier_name", orientation="h",
                        color_discrete_sequence=[RED],
                        text=top_u["total_ppv"].apply(lambda v: d(v, 0)),
                        title="Top 10 — Highest Overpayment vs Standard")
        fig_u.update_traces(textposition="outside")
        fig_u.update_layout(height=380, yaxis={"categoryorder": "total ascending"},
                             xaxis_tickprefix="$", **CHART)
        st.plotly_chart(fig_u, use_container_width=True)
 
    with c_p2:
        st.markdown("**✅ Favorable — Paid Less Than Standard**")
        top_f = sup_ppv.nsmallest(10, "total_ppv")
        fig_f = px.bar(top_f, x="total_ppv", y="supplier_name", orientation="h",
                        color_discrete_sequence=[GREEN],
                        text=top_f["total_ppv"].apply(lambda v: d(v, 0)),
                        title="Top 10 — Highest Underpayment vs Standard")
        fig_f.update_traces(textposition="outside")
        fig_f.update_layout(height=380, yaxis={"categoryorder": "total descending"},
                             xaxis_tickprefix="$", **CHART)
        st.plotly_chart(fig_f, use_container_width=True)
 
    # NEW: PPV trend over time (quarterly)
    st.markdown("### PPV Trend Over Time — Is Overpayment Getting Better or Worse?")
    ppv_t = ppv.copy()
    if "order_date" in ppv_t.columns:
        ppv_t["order_date"] = pd.to_datetime(ppv_t["order_date"], errors="coerce")
        ppv_t = ppv_t[ppv_t["order_date"].notna()]
        ppv_t["quarter"] = ppv_t["order_date"].dt.to_period("Q").astype(str)
        q_trend = ppv_t.groupby("quarter")["ppv"].sum().reset_index().sort_values("quarter")
        if not q_trend.empty:
            fig_t = go.Figure()
            colors_q = [RED if v > 0 else GREEN for v in q_trend["ppv"]]
            fig_t.add_trace(go.Bar(x=q_trend["quarter"], y=q_trend["ppv"],
                                    marker_color=colors_q,
                                    text=[d(v, 0) for v in q_trend["ppv"]],
                                    textposition="outside", name="Quarterly PPV"))
            fig_t.add_trace(go.Scatter(x=q_trend["quarter"], y=q_trend["ppv"],
                                        mode="lines", line=dict(color=NAVY, width=2, dash="dot"),
                                        name="Trend line"))
            fig_t.update_layout(height=380,
                                 title="Quarterly Total PPV (Red = net overpayment, Green = net savings)",
                                 yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                                 xaxis_tickangle=-45, **CHART)
            st.plotly_chart(fig_t, use_container_width=True)
        else:
            st.plotly_chart(empty("No dated PO data available for PPV trend"), use_container_width=True)
    else:
        st.plotly_chart(empty("Order date not available for PPV trend"), use_container_width=True)
 
    # NEW: Vendor Scorecard out of 100
    st.markdown("### 📋 Vendor Scorecard (0–100)")
    st.caption("OTD % (40 pts) + Lead Time Score (30 pts, best near 30-day target) "
               "+ PPV Score (30 pts, favorable pricing scores higher).")
    score_base = sup5.merge(sup_ppv[["supplier_bp_code", "total_ppv"]], on="supplier_bp_code", how="left")
    score_base["total_ppv"] = score_base["total_ppv"].fillna(0)
 
    score_base["otd_score"] = (score_base["otd_pct"] / 100 * 40).clip(0, 40)
    lt_dev = (score_base["avg_lt"] - 30).abs()
    max_dev = lt_dev.max() if lt_dev.max() > 0 else 1
    score_base["lt_score"] = (30 * (1 - lt_dev / max_dev)).clip(0, 30)
    ppv_abs = score_base["total_ppv"].clip(upper=0).abs()  # only reward favorable (negative) ppv fully
    ppv_range = score_base["total_ppv"].max() - score_base["total_ppv"].min()
    ppv_range = ppv_range if ppv_range != 0 else 1
    score_base["ppv_score"] = (30 * (1 - (score_base["total_ppv"] - score_base["total_ppv"].min()) / ppv_range)).clip(0, 30)
    score_base["scorecard"] = (score_base["otd_score"] + score_base["lt_score"] + score_base["ppv_score"]).round(1)
 
    sc_disp_cols = ["supplier_name", "country_name", "otd_pct", "avg_lt", "total_ppv", "scorecard", "is_dnu"]
    sc = score_base[sc_disp_cols].copy()
    sc.columns = ["Supplier", "Country", "OTD %", "Avg LT (days)", "Total PPV ($)", "Scorecard /100", "_dnu"]
 
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.markdown("**🏆 Top 20 Suppliers**")
        top_sc = sc.nlargest(20, "Scorecard /100").copy()
        top_sc["OTD %"] = top_sc["OTD %"].apply(lambda v: p(v))
        top_sc["Avg LT (days)"] = top_sc["Avg LT (days)"].apply(lambda v: n(v, 1))
        top_sc["Total PPV ($)"] = top_sc["Total PPV ($)"].apply(lambda v: d(v, 0))
        if top_sc["_dnu"].any():
            st.dataframe(top_sc.style.apply(_style_dnu, axis=1).hide(axis="columns", subset=["_dnu"]),
                         use_container_width=True, height=420)
        else:
            st.dataframe(top_sc.drop(columns=["_dnu"]), use_container_width=True, height=420, hide_index=True)
    with c_s2:
        st.markdown("**⚠ Bottom 20 Suppliers**")
        bot_sc = sc.nsmallest(20, "Scorecard /100").copy()
        bot_sc["OTD %"] = bot_sc["OTD %"].apply(lambda v: p(v))
        bot_sc["Avg LT (days)"] = bot_sc["Avg LT (days)"].apply(lambda v: n(v, 1))
        bot_sc["Total PPV ($)"] = bot_sc["Total PPV ($)"].apply(lambda v: d(v, 0))
        if bot_sc["_dnu"].any():
            st.dataframe(bot_sc.style.apply(_style_dnu, axis=1).hide(axis="columns", subset=["_dnu"]),
                         use_container_width=True, height=420)
        else:
            st.dataframe(bot_sc.drop(columns=["_dnu"]), use_container_width=True, height=420, hide_index=True)
 
 
# ═══════════════════════════════════════════════════
# TAB 5 — INVENTORY & COVERAGE
# ═══════════════════════════════════════════════════
def t5_inventory(D, filt):
    st.markdown("## 📦 Inventory & Coverage Analysis")
    inv = D["inv"]
    ins = scope(filt)
 
    # Emergency alert always shows if negative economic stock exists,
    # regardless of any filter selection — never hidden.
    neg_all = inv[inv["economic_stock"] < 0] if "economic_stock" in inv.columns else pd.DataFrame()
    if not neg_all.empty:
        st.markdown(
            f"<div class='alert'>🚨 SUPPLY ALERT — {len(neg_all)} items have negative "
            f"economic stock (more committed to production than available). "
            f"Immediate review required.</div>",
            unsafe_allow_html=True)
 
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("📦 Total On-Hand",    n(inv.get("inv_on_hand", pd.Series([0])).sum(), 0) + " lbs", "All 4 sites")
    with k2: kpi("✅ Items With Stock", n((inv.get("inv_on_hand", pd.Series([0])) > 0).sum()), "inv_on_hand > 0", "kpi-g")
    with k3: kpi("⚠ Zero Stock",        n((inv.get("inv_on_hand", pd.Series([0])) == 0).sum()), "No inventory", "kpi-a")
    with k4: kpi("🚨 Negative Eco.",     n(len(neg_all)), "Crisis — more allocated than available", "kpi-b")
    st.markdown("---")
 
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### On-Hand Inventory by Site")
        if "site_group" in inv.columns and "inv_on_hand" in inv.columns:
            site_inv = inv.groupby("site_group")["inv_on_hand"].sum().reset_index()
            fig = px.bar(site_inv, x="site_group", y="inv_on_hand",
                          color="site_group",
                          color_discrete_map={"Lake Charles": BLUE, "Green Bay": GREEN, "Dayton": AMBER, "Louisa": ORANGE},
                          text=site_inv["inv_on_hand"].apply(lambda v: n(v, 0)),
                          title="On-Hand Inventory (lbs) by Site")
            fig.update_traces(textposition="outside", showlegend=False)
            fig.update_layout(height=360, yaxis_title="Pounds", xaxis_title=None, **CHART)
            st.plotly_chart(fig, use_container_width=True)
 
    with c_r:
        st.markdown("### 🚨 Negative Economic Stock — Crisis Items")
        st.caption("Economic stock = On-Hand + On-Order − Allocated. Negative = production shortage risk.")
        if not neg_all.empty and "item_code" in neg_all.columns:
            show_neg = neg_all.sort_values("economic_stock")[
                [c for c in ["site_group", "item_code", "inv_on_hand", "inv_on_order",
                              "inv_allocated", "economic_stock"] if c in neg_all.columns]
            ].head(20).copy()
            show_neg.columns = [c.replace("inv_", "").replace("_", " ").title()
                                 for c in show_neg.columns]
            for c in show_neg.columns:
                if c not in ["Site Group", "Item Code"]:
                    show_neg[c] = show_neg[c].apply(lambda v: n(v, 0))
            st.dataframe(show_neg, use_container_width=True, height=340, hide_index=True)
        else:
            st.success("No items with negative economic stock.")
 
    # Coverage analysis
    st.markdown("### Coverage: On-Hand vs Recommended Safety Stock")
    if "item_code" in inv.columns and "inv_on_hand" in inv.columns:
        inv_grp = inv.groupby(["item_code", "site_group"])["inv_on_hand"].sum().reset_index()
        ab_items = ins[ins["abc_tier"].isin(["A", "B"])]
        if not ab_items.empty:
            cov = ab_items.merge(inv_grp, on=["item_code", "site_group"], how="left")
            cov["inv_on_hand"]   = cov["inv_on_hand"].fillna(0)
            cov["shortfall"]     = cov["new_ss_lbs_v4"] - cov["inv_on_hand"]
            cov["days_stockout"] = np.where(
                cov["avg_daily_usage_lbs"] > 0,
                (cov["inv_on_hand"] / cov["avg_daily_usage_lbs"]).round(1), 0)
            below = cov[cov["shortfall"] > 0].sort_values("shortfall", ascending=False).head(25)
            if not below.empty:
                show_b = below[["site_group", "item_code", "item_description", "abc_tier",
                                  "inv_on_hand", "new_ss_lbs_v4", "shortfall", "days_stockout"]].copy()
                show_b.columns = ["Site", "Item", "Description", "Tier",
                                   "On Hand (lbs)", "Rec. SS (lbs)", "Shortfall (lbs)", "Days to Stockout"]
                for c in ["On Hand (lbs)", "Rec. SS (lbs)", "Shortfall (lbs)"]:
                    show_b[c] = show_b[c].apply(lambda v: n(v, 1))
                show_b["Days to Stockout"] = show_b["Days to Stockout"].apply(lambda v: n(v, 1))
                st.dataframe(show_b, use_container_width=True, height=400, hide_index=True)
            else:
                st.success("✅ All A/B-tier items meet recommended safety stock levels.")
 
    # Bulk tank utilization
    st.markdown("### 🛢 Bulk Tank Utilization (Lake Charles)")
    LC_TANKS = {
        "T25": 40212, "T15": 43388, "CM847": 51478, "CM969": 52138, "CM1115": 95933,
        "P10": 47942, "T10": 73309, "O50": 43148, "RS266": 51298, "RS883": 51598,
        "AP30": 52437, "T11": 89652, "T18": 54225, "RS280": 55767, "RS977": 103057,
        "RS825": 72000, "RS820": 71432, "Z86": 6000
    }
    if "site_group" in inv.columns and "inv_on_hand" in inv.columns:
        lc_inv = inv[inv["site_group"] == "Lake Charles"].set_index("item_code")["inv_on_hand"].to_dict()
        tank_rows = []
        for item, cap in LC_TANKS.items():
            oh  = float(lc_inv.get(item, 0))
            uti = min(oh / cap * 100, 100) if cap > 0 else 0
            tank_rows.append({"Item": item, "On Hand (lbs)": oh, "Tank Cap 80% (lbs)": cap, "Utilization %": uti})
        df_tk = pd.DataFrame(tank_rows)
        fig_tk = px.bar(
            df_tk.sort_values("Utilization %"), x="Utilization %", y="Item",
            orientation="h", color="Utilization %",
            color_continuous_scale=[[0, GREEN], [0.5, "#FFF2CC"], [1.0, RED]],
            range_color=[0, 100],
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
 
    f1, f2, f3 = st.columns(3)
    with f1:
        site_s = st.selectbox("Site", ["All Sites"] + sorted(cons["site_group"].unique().tolist()), key="s_s")
    with f2:
        grp_s  = st.selectbox("Item Group", ["All", "Raw Materials (LB)", "Packaging (EA)"], key="s_g")
    with f3:
        yrs    = st.multiselect("Years", [2021, 2022, 2023, 2024, 2025, 2026],
                                 default=[2024, 2025], key="s_y")
 
    cf = cons.copy()
    if site_s != "All Sites": cf = cf[cf["site_group"] == site_s]
    if grp_s == "Raw Materials (LB)":  cf = cf[cf.get("unit_of_measure", "LB") == "LB"]
    elif grp_s == "Packaging (EA)":    cf = cf[cf.get("unit_of_measure", "EA") == "EA"]
    if yrs: cf = cf[cf["year"].isin(yrs)]
 
    # Monthly trend
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### Monthly Consumption Trend (All Sites)")
        monthly = (cons.groupby(["year", "period_month"])["qty_issued"].sum().reset_index())
        monthly["date_str"] = (monthly["year"].astype(int).astype(str) + "-" +
                                monthly["period_month"].astype(int).astype(str).str.zfill(2))
        monthly = monthly.sort_values("date_str")
        fig = px.line(monthly, x="date_str", y="qty_issued",
                       title="Total Consumption by Month",
                       labels={"date_str": "Month", "qty_issued": "Qty Consumed"},
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
            colors_bar  = [RED if v > 1.2 else (STEEL if v < 0.8 else GREY) for v in ma["idx"]]
            fig2 = go.Figure(go.Bar(
                x=ma["mname"], y=ma["idx"], marker_color=colors_bar,
                text=ma["idx"].apply(lambda v: f"{v:.2f}"), textposition="outside"))
            fig2.add_hline(y=1.2, line_dash="dash", line_color=RED,   annotation_text="Peak (1.2)")
            fig2.add_hline(y=0.8, line_dash="dash", line_color=STEEL, annotation_text="Low (0.8)")
            fig2.update_layout(height=360,
                               title="Seasonality Index (Red=Peak · Blue=Low · Grey=Normal)",
                               yaxis_title="Index", **CHART)
            st.plotly_chart(fig2, use_container_width=True)
 
    # NEW: Year-over-year comparison chart — 2023 vs 2024-2025 by month
    st.markdown("### Year-over-Year Comparison — 2023 vs 2024-2025")
    yoy_src = cons[cons["year"].isin([2023, 2024, 2025])].copy()
    if not yoy_src.empty:
        yoy = yoy_src.groupby(["year", "period_month"])["qty_issued"].sum().reset_index()
        yoy["mname"] = yoy["period_month"].map(MONTH)
        fig_yoy = go.Figure()
        yoy_colors = {2023: GREY, 2024: STEEL, 2025: RED}
        for yr in [2023, 2024, 2025]:
            yr_df = yoy[yoy["year"] == yr].sort_values("period_month")
            if not yr_df.empty:
                fig_yoy.add_trace(go.Scatter(
                    x=yr_df["mname"], y=yr_df["qty_issued"], mode="lines+markers",
                    name=str(yr), line=dict(color=yoy_colors.get(yr, NAVY), width=2)))
        fig_yoy.update_layout(height=380, title="Monthly Consumption — 2023 vs 2024 vs 2025 (Overlaid)",
                               xaxis_title="Month", yaxis_title="Qty Consumed", **CHART)
        st.plotly_chart(fig_yoy, use_container_width=True)
    else:
        st.plotly_chart(empty("No 2023-2025 data available"), use_container_width=True)
 
    # Heatmap
    st.markdown("### Seasonality Heatmap — Top 20 A-Items")
    st.caption("Red = peak demand. Blue = low demand. Green = normal. "
               "Use this to plan inventory build-up before demand spikes.")
    cons_lb = cons[cons["year"].isin([2024, 2025])]
    if "unit_of_measure" in cons_lb.columns:
        cons_lb = cons_lb[cons_lb["unit_of_measure"] == "LB"]
    a_items = filt[(filt["abc_tier"] == "A") & (filt.get("is_bad_apple", "NO") == "NO")]["item_code"].unique()[:20]
    heat = (cons_lb[cons_lb["item_code"].isin(a_items)]
            .groupby(["item_code", "period_month"])["qty_issued"].mean().reset_index())
 
    if not heat.empty:
        piv = heat.pivot(index="item_code", columns="period_month", values="qty_issued").fillna(0)
        rm  = piv.mean(axis=1).replace(0, 1)
        for c in piv.columns:
            piv[c] = piv[c] / rm
        piv.columns = [MONTH.get(c, str(c)) for c in piv.columns]
        fig_h = px.imshow(
            piv,
            color_continuous_scale=[[0, BLUE], [0.35, LBLUE], [0.6, BG], [0.8, AMBER], [1, RED]],
            zmin=0.4, zmax=1.8, text_auto=".2f",
            title="Seasonality Index — Top 20 A-Items (2024-2025)",
            labels=dict(x="Month", y="Item Code", color="Index"))
        fig_h.update_layout(height=max(380, len(a_items) * 26), **CHART)
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.info("Not enough data for the heatmap with current selection.")
 
    # Seasonal items
    st.markdown("### Items Flagged as Seasonal — Peak Months")
    cons24 = cons[cons["year"].isin([2024, 2025])]
    am = pd.DataFrame()
    if not cons24.empty:
        am = cons24.groupby(["item_code", "period_month"])["qty_issued"].mean().reset_index()
        ov = am.groupby("item_code")["qty_issued"].mean()
        am = am.merge(ov.rename("overall"), on="item_code")
        am["idx"] = (am["qty_issued"] / am["overall"].replace(0, 1)).round(2)
        seasonal = (am[am["idx"] > 1.2]
                    .groupby("item_code")
                    .agg(peak_months=("period_month",
                                      lambda x: ", ".join(MONTH.get(m, "?") for m in sorted(x))),
                         max_idx=("idx", "max"))
                    .reset_index().sort_values("max_idx", ascending=False).head(30))
        seasonal.columns = ["Item Code", "Peak Months", "Max Seasonality Index"]
        seasonal["Max Seasonality Index"] = seasonal["Max Seasonality Index"].apply(lambda v: f"{v:.2f}")
        st.dataframe(seasonal, use_container_width=True, height=380, hide_index=True)
 
    # NEW: Buying Calendar — order_date = peak_month_start - lead_time_days
    st.markdown("### 📅 Buying Calendar — When to Place Orders for A-Items")
    st.caption("For each A-item with a peak demand month, the order-by date is calculated as "
               "Peak Month Start − Lead Time (days). Sorted soonest-first so buyers know what's due this month.")
    if not am.empty:
        peak_per_item = (am[am["idx"] > 1.0]
                          .sort_values("idx", ascending=False)
                          .groupby("item_code")
                          .first()
                          .reset_index()[["item_code", "period_month", "idx"]])
        peak_per_item.columns = ["item_code", "peak_month", "peak_index"]
 
        a_tier_items = filt[(filt["abc_tier"] == "A") & (filt.get("is_bad_apple", "NO") == "NO")][
            ["item_code", "item_description", "site_group", "lead_time_used_v4"]
        ].drop_duplicates("item_code")
 
        cal = a_tier_items.merge(peak_per_item, on="item_code", how="inner")
        if not cal.empty:
            current_year = datetime.now().year
            def _order_by(row):
                try:
                    peak_start = datetime(current_year, int(row["peak_month"]), 1)
                    lt = float(row["lead_time_used_v4"]) if pd.notna(row["lead_time_used_v4"]) else 30
                    order_date = peak_start - timedelta(days=lt)
                    # if that date has already passed this year, roll to next year's peak
                    if order_date < datetime.now():
                        peak_start = datetime(current_year + 1, int(row["peak_month"]), 1)
                        order_date = peak_start - timedelta(days=lt)
                    return order_date
                except Exception:
                    return pd.NaT
            cal["order_by_date"] = cal.apply(_order_by, axis=1)
            cal = cal.dropna(subset=["order_by_date"]).sort_values("order_by_date")
            cal_disp = cal[["order_by_date", "item_code", "item_description", "site_group",
                             "peak_month", "lead_time_used_v4", "peak_index"]].copy()
            cal_disp["Peak Month"] = cal_disp["peak_month"].map(MONTH)
            cal_disp["Order By Date"] = cal_disp["order_by_date"].dt.strftime("%b %d, %Y")
            cal_disp["Lead Time (days)"] = cal_disp["lead_time_used_v4"].apply(lambda v: n(v, 1))
            cal_disp["Seasonality Index"] = cal_disp["peak_index"].apply(lambda v: f"{v:.2f}")
            cal_disp = cal_disp[["Order By Date", "item_code", "item_description", "site_group",
                                  "Peak Month", "Lead Time (days)", "Seasonality Index"]]
            cal_disp.columns = ["Order By Date", "Item Code", "Description", "Site",
                                 "Peak Month", "Lead Time (days)", "Seasonality Index"]
            st.dataframe(cal_disp, use_container_width=True, height=420, hide_index=True)
            dl_excel(cal_disp, "Carboline_Buying_Calendar.xlsx", key="dl_buycal")
        else:
            st.info("No A-tier items with a clear peak month under current filters.")
    else:
        st.info("Not enough consumption data to build a buying calendar.")
 
    # Growth
    st.markdown("### Top 20 Fastest-Growing Items (2023 vs 2024-2025)")
    c23   = cons[cons["year"] == 2023].groupby("item_code")["qty_issued"].sum()
    c2425 = cons[cons["year"].isin([2024, 2025])].groupby("item_code")["qty_issued"].sum()
    grw   = pd.concat([c23.rename("y2023"), c2425.rename("y2425")], axis=1).dropna()
    grw   = grw[grw["y2023"] > 1000].copy()
    grw["growth_pct"] = ((grw["y2425"] - grw["y2023"]) / grw["y2023"] * 100).round(1)
    grw   = grw.nlargest(20, "growth_pct").reset_index()
    grw.columns = ["Item Code", "Lbs 2023", "Lbs 2024-25", "Growth %"]
    grw["Lbs 2023"]    = grw["Lbs 2023"].apply(lambda v: n(v, 0))
    grw["Lbs 2024-25"] = grw["Lbs 2024-25"].apply(lambda v: n(v, 0))
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
            labels=["Never Consumed", "Slow Movers\n(zero since 2024)", "Have ROP in LN"],
            values=[max(never - slow, 0), slow, rop_f],
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
                ["item_code", "item_description", "item_group", "total_lbs_all_years"]
            ].copy()
            rop_items.columns = ["Item Code", "Description", "Group", "Total LBS All Years"]
            rop_items["Total LBS All Years"] = rop_items["Total LBS All Years"].apply(lambda v: n(v, 0))
            st.dataframe(rop_items, use_container_width=True, height=320, hide_index=True)
 
    # Full D-tier
    st.markdown("### Full D-Tier Item List (1,760 items)")
    filt_d = st.radio("Show:", ["All D-Tier", "Never Consumed", "Slow Movers"], horizontal=True)
    show_d = df_d.copy()
    if filt_d == "Never Consumed":     show_d = df_d[df_d["total_lbs_all_years"] == 0]
    elif filt_d == "Slow Movers":      show_d = df_d[df_d["lbs_2021_2023"] > 0]
 
    cols_d = [c for c in ["item_code", "item_description", "item_group", "item_group_label",
                           "planning_signal", "standard_cost_usd", "total_lbs_all_years",
                           "lbs_2021_2023", "last_year_consumed", "has_rop_in_ln", "d_tier_reason"]
              if c in show_d.columns]
    disp_d = show_d[cols_d].copy()
    rename_d = {
        "item_code": "Item Code", "item_description": "Description",
        "item_group": "Group", "item_group_label": "Group Label",
        "planning_signal": "Signal", "standard_cost_usd": "Std Cost ($)",
        "total_lbs_all_years": "Total LBS", "lbs_2021_2023": "LBS 2021-23",
        "last_year_consumed": "Last Year", "has_rop_in_ln": "ROP in LN?",
        "d_tier_reason": "Reason"
    }
    disp_d.rename(columns=rename_d, inplace=True)
    for c in ["Total LBS", "LBS 2021-23"]:
        if c in disp_d.columns:
            disp_d[c] = disp_d[c].apply(lambda v: n(v, 0))
    if "Std Cost ($)" in disp_d.columns:
        disp_d["Std Cost ($)"] = disp_d["Std Cost ($)"].apply(lambda v: d(v, 4))
    if "Last Year" in disp_d.columns:
        disp_d["Last Year"] = disp_d["Last Year"].astype(str)
    disp_d = scrub_df(disp_d, cols=["Reason"])
    st.dataframe(disp_d, use_container_width=True, height=400, hide_index=True)
    dl_excel(disp_d, "Carboline_D_Tier_List.xlsx", key="dl_dtier")
 
    # Good Apple missing
    st.markdown(f"### ⭐ Good Apple Items Missing LN Parameters (93 items)")
    st.caption("On the priority list but have no ordering parameters in LN. "
               "LN will never auto-generate purchase orders for these.")
    if not df_gm.empty:
        gm2 = df_gm[["item_code", "std_cost", "destination", "lead_time_days"]].copy()
        gm2.columns = ["Item Code", "Std Cost ($)", "Destination Site", "Manager Lead Time (days)"]
        gm2["Std Cost ($)"] = gm2["Std Cost ($)"].apply(lambda v: d(v, 4))
        gm2["Manager Lead Time (days)"] = gm2["Manager Lead Time (days)"].apply(lambda v: n(v, 1))
        gm2["Action"] = "Add Item Ordering parameters in LN"
        st.dataframe(gm2, use_container_width=True, height=320, hide_index=True)
        dl_excel(gm2, "Carboline_Good_Apple_Missing_LN.xlsx", key="dl_gm")
 
    # Bad Apple removal
    st.markdown("### 🗑 Bad Apple Items — Remove From LN (94 items)")
    st.caption("Safety stock forced to zero. LN ordering parameters should be removed "
               "by the procurement team to eliminate phantom planned orders.")
    if not df_ba.empty:
        ba_cols = [c for c in ["Site", "Item Code", "Description", "ABC Tier",
                                "Current LN ROP\n(was active)", "MOQ", "Old $ Risk"]
                   if c in df_ba.columns]
        ba2 = df_ba[ba_cols].copy() if ba_cols else df_ba.copy()
        ba2.columns = [c.replace("\n", " ") for c in ba2.columns]
        if "Old $ Risk" in ba2.columns:
            ba2["Old $ Risk"] = ba2["Old $ Risk"].apply(lambda v: d(v, 2))
        st.dataframe(ba2, use_container_width=True, height=320, hide_index=True)
        dl_excel(ba2, "Carboline_Bad_Apple_Remove.xlsx", key="dl_ba")
 
 
# ═══════════════════════════════════════════════════
# TAB 8 — DEMAND FORECASTING (PROPHET)
# ═══════════════════════════════════════════════════
def _prepare_monthly_series(df, date_col, qty_col):
    """Aggregate to monthly totals and fill missing months with 0."""
    s = df[[date_col, qty_col]].dropna(subset=[date_col]).copy()
    s[qty_col] = pd.to_numeric(s[qty_col], errors="coerce").fillna(0)
    s["ds"] = pd.to_datetime(s[date_col]).dt.to_period("M").dt.to_timestamp()
    monthly = s.groupby("ds")[qty_col].sum().reset_index()
    monthly.columns = ["ds", "y"]
    if monthly.empty:
        return monthly
    full_range = pd.date_range(monthly["ds"].min(), monthly["ds"].max(), freq="MS")
    monthly = monthly.set_index("ds").reindex(full_range, fill_value=0).rename_axis("ds").reset_index()
    return monthly
 
 
@st.cache_resource(show_spinner=False)
def _fit_prophet(monthly_json, horizon_months):
    """Fit a Prophet model. Cached on the serialized data + horizon so we
    don't refit every time the user just changes an unrelated widget."""
    from prophet import Prophet
    monthly = pd.read_json(io.StringIO(monthly_json))
    monthly["ds"] = pd.to_datetime(monthly["ds"])
 
    model = Prophet(
        seasonality_mode='multiplicative',
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        changepoint_prior_scale=0.1,
        seasonality_prior_scale=10,
        interval_width=0.95
    )
    model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
    model.fit(monthly)
 
    future = model.make_future_dataframe(periods=horizon_months, freq="MS")
    forecast = model.predict(future)
    return forecast.to_json(date_format="iso"), model.params
 
 
def _mape(actual, predicted):
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    mask = actual != 0
    if mask.sum() == 0:
        return None
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)
 
 
def _run_forecast_pipeline(monthly, horizon_months, item_label, site_label):
    """Runs the full Prophet pipeline (fit, validation holdout, seasonality
    index, charts, recommendation) given a prepared monthly series."""
    try:
        from prophet import Prophet  # noqa: F401  (import check only)
    except ImportError:
        st.error("⚠ Prophet is not installed in this environment. "
                  "Install it with: `pip install prophet==1.3.0`")
        return
 
    if len(monthly) < 12:
        st.warning("⚠ Not enough history for reliable forecast. Need at least 12 months of data.")
        return
 
    with st.spinner("🔮 Building forecast model — this takes about 10 seconds..."):
        # Validation: hold out the last 3 months
        mape_value = None
        if len(monthly) >= 15:
            train = monthly.iloc[:-3].copy()
            holdout = monthly.iloc[-3:].copy()
            try:
                fc_json, _ = _fit_prophet(train.to_json(date_format="iso"), 3)
                fc_val = pd.read_json(io.StringIO(fc_json))
                fc_val["ds"] = pd.to_datetime(fc_val["ds"])
                merged = holdout.merge(fc_val[["ds", "yhat"]], on="ds", how="left")
                mape_value = _mape(merged["y"], merged["yhat"])
            except Exception:
                mape_value = None
 
        # Full fit for the actual forecast
        fc_json, _ = _fit_prophet(monthly.to_json(date_format="iso"), horizon_months)
        forecast = pd.read_json(io.StringIO(fc_json))
        forecast["ds"] = pd.to_datetime(forecast["ds"])
 
    today = pd.Timestamp(datetime.now().date())
    hist = monthly.copy()
    last_hist_date = hist["ds"].max()
 
    # ── Chart 1: Main Forecast ──────────────────────────────
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=hist["ds"], y=hist["y"], mode="lines+markers",
        name="Historical", line=dict(color="black", width=1.5),
        marker=dict(size=5, color="black")))
 
    future_part = forecast[forecast["ds"] > last_hist_date]
    fig1.add_trace(go.Scatter(
        x=future_part["ds"], y=future_part["yhat"], mode="lines",
        name="Forecast", line=dict(color=STEEL, width=2.5),
        hovertemplate="Date: %{x}<br>Forecasted Qty (lbs): %{y:,.0f}<extra></extra>"))
    fig1.add_trace(go.Scatter(
        x=pd.concat([future_part["ds"], future_part["ds"][::-1]]),
        y=pd.concat([future_part["yhat_upper"], future_part["yhat_lower"][::-1]]),
        fill="toself", fillcolor="rgba(46,117,182,0.18)",
        line=dict(color="rgba(255,255,255,0)"), name="95% Confidence",
        hoverinfo="skip"))
    today_str = last_hist_date.strftime("%Y-%m-%d")
    fig1.add_shape(type="line", x0=today_str, x1=today_str, y0=0, y1=1,
                   xref="x", yref="paper",
                   line=dict(color=RED, dash="dash", width=1.5))
    fig1.add_annotation(x=today_str, y=1.02, xref="x", yref="paper",
                        text="Today", showarrow=False, font=dict(color=RED, size=11))
    fig1.update_layout(
        height=440,
        title=f"Demand Forecast — {item_label} at {site_label} — Next {horizon_months} Months",
        yaxis_title="Quantity (lbs)", xaxis_title=None, **CHART)
    st.plotly_chart(fig1, use_container_width=True)
 
    # MAPE / accuracy
    if mape_value is not None:
        if mape_value < 15:
            badge_color, badge_label = GREEN, "Excellent"
        elif mape_value <= 30:
            badge_color, badge_label = AMBER, "Good"
        else:
            badge_color, badge_label = RED, "Use with caution"
        st.markdown(
            f"<div class='fbox' style='border-left-color:{badge_color};'>"
            f"<b>Model Accuracy: {mape_value:.1f}% MAPE</b> (lower is better). "
            f"Last 3 months validation. "
            f"<span style='color:{badge_color};font-weight:800;'>{badge_label}</span></div>",
            unsafe_allow_html=True)
    else:
        st.caption("Not enough history to compute a 3-month holdout validation score.")
 
    # ── Chart 2: Trend ───────────────────────────────────────
    trend_series = forecast[["ds", "trend"]].copy()
    first_t, last_t = trend_series["trend"].iloc[0], trend_series["trend"].iloc[-1]
    if last_t > first_t * 1.03:
        trend_dir, trend_color = "GROWING", GREEN
    elif last_t < first_t * 0.97:
        trend_dir, trend_color = "DECLINING", RED
    else:
        trend_dir, trend_color = "STABLE", GREY
 
    fig2 = go.Figure(go.Scatter(
        x=trend_series["ds"], y=trend_series["trend"], mode="lines",
        line=dict(color=trend_color, width=2.5), name="Trend"))
    fig2.update_layout(height=320,
                        title=f"Underlying Demand Trend — {trend_dir}",
                        yaxis_title="Trend (lbs)", xaxis_title=None, **CHART)
    st.plotly_chart(fig2, use_container_width=True)
 
    # ── Chart 3: Seasonality Index by Month ─────────────────
    monthly_seas = forecast[["ds", "yearly"]].copy()
    monthly_seas["month"] = monthly_seas["ds"].dt.month
    seas_idx = monthly_seas.groupby("month")["yearly"].mean().reset_index()
    seas_idx["index"] = 1 + seas_idx["yearly"]  # multiplicative seasonality, centered at 1
    seas_idx["mname"] = seas_idx["month"].map(MONTH)
    seas_colors = [RED if v > 1.2 else (STEEL if v < 0.8 else GREY) for v in seas_idx["index"]]
    fig3 = go.Figure(go.Bar(
        x=seas_idx["mname"], y=seas_idx["index"], marker_color=seas_colors,
        text=seas_idx["index"].apply(lambda v: f"{v:.2f}"), textposition="outside"))
    fig3.add_hline(y=1.2, line_dash="dash", line_color=RED, annotation_text="Peak (buy ahead)")
    fig3.add_hline(y=0.8, line_dash="dash", line_color=STEEL, annotation_text="Low (safe to defer)")
    fig3.update_layout(height=360, title="Seasonal Pattern — When Demand Is High vs Low",
                        yaxis_title="Seasonality Index", **CHART)
    st.plotly_chart(fig3, use_container_width=True)
 
    # ── Procurement recommendation ──────────────────────────
    next6 = future_part.head(6)
    avg_monthly_6mo = next6["yhat"].mean() if not next6.empty else future_part["yhat"].mean()
    peak_row = future_part.loc[future_part["yhat"].idxmax()] if not future_part.empty else None
 
    st.markdown("### 📦 Procurement Recommendation")
    if peak_row is not None:
        peak_month_name = peak_row["ds"].strftime("%B %Y")
        peak_qty = peak_row["yhat"]
        buffer_factor = 1.5  # default A-tier buffer as a planning placeholder
        lead_time_days_assumed = 30
        rec_ss_peak = peak_qty * buffer_factor * (lead_time_days_assumed / 30)
        action = ("INCREASE ORDER FREQUENCY" if peak_qty > avg_monthly_6mo * 1.3
                  else "REDUCE ORDER QTY" if peak_qty < avg_monthly_6mo * 0.7
                  else "STOCK IS SUFFICIENT")
        rec_html = f"""
        <div class='reco'>
        <b>Forecasted avg monthly demand (next 6 months):</b> {n(avg_monthly_6mo,0)} lbs<br>
        <b>Peak demand month:</b> {peak_month_name} — {n(peak_qty,0)} lbs<br>
        <b>Recommended safety stock for peak period:</b> {n(rec_ss_peak,0)} lbs
        (= peak × {buffer_factor}× buffer × lead time adjustment)<br>
        <b>Action:</b> <span style="font-weight:800;color:{RED if action=='INCREASE ORDER FREQUENCY' else (STEEL if action=='REDUCE ORDER QTY' else GREEN)};">{action}</span>
        </div>"""
        st.markdown(rec_html, unsafe_allow_html=True)
    else:
        st.info("Not enough forecast data to generate a procurement recommendation.")
 
    # ── Download ─────────────────────────────────────────────
    export_df = future_part[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    export_df.columns = ["Date", "Forecasted Qty (lbs)", "Lower Bound (95%)", "Upper Bound (95%)"]
    export_df["Date"] = export_df["Date"].dt.strftime("%Y-%m-%d")
    export_df["Seasonality Index"] = export_df["Date"].apply(
        lambda dstr: seas_idx.set_index("mname")["index"].get(MONTH[pd.Timestamp(dstr).month], 1.0))
    dl_excel(export_df, "Carboline_Demand_Forecast.xlsx", key="dl_forecast")
 
 
@st.cache_data(show_spinner=False)
def _item_list_for_forecast(_cons):
    return sorted(_cons["item_code"].dropna().unique().tolist())
 
 
def t8_forecast(D):
    st.markdown("## 🔮 Demand Forecasting")
    st.markdown("""
    <div class='fbox'>
    Forecasts use Facebook Prophet with multiplicative seasonality, tuned for
    business demand data. Build a forecast from existing consumption history,
    or upload your own dataset.
    </div>""", unsafe_allow_html=True)
 
    try:
        import prophet  # noqa: F401
    except ImportError:
        st.error("⚠ Prophet is not installed. Install it with: `pip install prophet==1.3.0`")
        return
 
    cons = D["cons"]
    mode = st.radio("Forecasting Mode", ["📊 Use Existing Consumption Data", "📁 Upload My Own Data"],
                     horizontal=True)
 
    if mode == "📊 Use Existing Consumption Data":
        items = _item_list_for_forecast(cons)
        c1, c2, c3 = st.columns(3)
        with c1:
            item_sel = st.selectbox("Item Code", items, key="fc_item")
        with c2:
            site_sel = st.selectbox("Site", ["All Sites", "Lake Charles", "Green Bay", "Dayton", "Louisa"], key="fc_site")
        with c3:
            horizon = st.selectbox("Forecast Horizon (months)", [3, 6, 12, 18, 24], index=1, key="fc_horizon")
 
        if st.button("🔮 Build Forecast", key="fc_build_btn"):
            df_item = cons[cons["item_code"] == item_sel].copy()
            if site_sel != "All Sites":
                df_item = df_item[df_item["site_group"] == site_sel]
 
            df_item["ds_raw"] = pd.to_datetime(
                df_item["year"].astype(int).astype(str) + "-" +
                df_item["period_month"].astype(int).astype(str).str.zfill(2) + "-01",
                errors="coerce")
            monthly = _prepare_monthly_series(df_item, "ds_raw", "qty_issued")
 
            if monthly.empty:
                st.warning("No consumption history found for this item/site combination.")
            else:
                site_label = site_sel if site_sel != "All Sites" else "All Sites"
                _run_forecast_pipeline(monthly, horizon, item_sel, site_label)
 
    else:
        st.markdown("#### Upload Your Own Data")
        st.caption("Accepts CSV or Excel files. No row limit — supports 70,000+ rows.")
        uploaded = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xls"], key="fc_upload")
 
        if uploaded is not None:
            try:
                if uploaded.name.endswith(".csv"):
                    udf = pd.read_csv(uploaded)
                else:
                    udf = pd.read_excel(uploaded)
            except Exception as e:
                st.error(f"Could not read the uploaded file: {e}")
                return
 
            st.success(f"Loaded {len(udf):,} rows.")
            cols = udf.columns.tolist()
            c1, c2 = st.columns(2)
            with c1:
                date_col_sel = st.selectbox("Which column is the date?", cols, key="fc_datecol")
            with c2:
                qty_col_sel = st.selectbox("Which column is the quantity?", cols, key="fc_qtycol")
 
            horizon_u = st.selectbox("Forecast Horizon (months)", [3, 6, 12, 18, 24], index=1, key="fc_horizon_u")
 
            udf["_ds_parsed"] = pd.to_datetime(udf[date_col_sel], errors="coerce")
            udf["_y_parsed"]  = pd.to_numeric(udf[qty_col_sel], errors="coerce")
            valid = udf.dropna(subset=["_ds_parsed"])
 
            if not valid.empty:
                st.info(f"📅 Date range: {valid['_ds_parsed'].min().date()} to "
                        f"{valid['_ds_parsed'].max().date()} · {len(valid):,} valid rows")
 
            if st.button("🔮 Build Forecast", key="fc_build_btn_upload"):
                monthly = _prepare_monthly_series(udf, "_ds_parsed", "_y_parsed")
                if monthly.empty:
                    st.warning("Could not build a monthly series from the selected columns. "
                               "Check that the date column parses correctly.")
                else:
                    _run_forecast_pipeline(monthly, horizon_u, "Uploaded Dataset", "Custom Data")
 
 
# ═══════════════════════════════════════════════════
# TAB 9 — COUNTRY OF ORIGIN & TARIFF TRACKER
# ═══════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _build_country_spend(_po, _sup, _cost):
    po2 = _po.copy()
    po2["spend"] = pd.to_numeric(po2.get("unit_price", 0), errors="coerce").fillna(0) * \
                   pd.to_numeric(po2.get("ordered_qty", 0), errors="coerce").fillna(0)
    merged = po2.merge(
        _sup[["supplier_bp_code", "supplier_name", "country_name", "country_code"]],
        on="supplier_bp_code", how="left")
    merged["country_name"] = merged["country_name"].fillna("Unknown")
    merged["country_code"] = merged["country_code"].fillna("UNK")
    return merged
 
 
def t9_tariff(D):
    st.markdown("## 🌍 Country of Origin & Tariff Tracker")
 
    po, sup, cost = D["po"], D["sup"], D["cost"]
    merged = _build_country_spend(po, sup, cost)
 
    total_spend = merged["spend"].sum()
    country_grp = merged.groupby(["country_name", "country_code"]).agg(
        suppliers=("supplier_bp_code", "nunique"),
        items=("item_code", "nunique"),
        spend=("spend", "sum"),
    ).reset_index()
    country_grp["pct_of_total"] = (country_grp["spend"] / total_spend * 100) if total_spend > 0 else 0
 
    def _risk(row):
        if row["suppliers"] == 1:
            return "HIGH (single-source)"
        if row["pct_of_total"] >= 30:
            return "HIGH"
        if row["pct_of_total"] >= 10:
            return "MEDIUM"
        return "LOW"
    country_grp["risk"] = country_grp.apply(_risk, axis=1)
 
    # World map
    st.markdown("### Global Spend by Country of Origin")
    map_df = country_grp[country_grp["country_name"] != "Unknown"].copy()
    if not map_df.empty:
        fig_map = px.choropleth(
            map_df, locations="country_name", locationmode="country names",
            color="spend", hover_name="country_name",
            color_continuous_scale=["#FFF0F0", "#C41230"],
            labels={"spend": "Total Spend ($)"},
            title="Total Spend by Country of Origin (2024-2025)")
        fig_map.update_layout(height=480, **CHART)
        fig_map.update_geos(showframe=False, showcoastlines=True)
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.plotly_chart(empty("No country-mapped spend data available"), use_container_width=True)
 
    # Spend table
    st.markdown("### Spend by Country")
    tbl = country_grp.sort_values("spend", ascending=False).copy()
    tbl_disp = tbl[["country_name", "suppliers", "items", "spend", "pct_of_total", "risk"]].copy()
    tbl_disp.columns = ["Country", "Suppliers", "Items Sourced", "Total Spend 2024-25 ($)", "% of Total Spend", "Risk Level"]
    tbl_disp["Total Spend 2024-25 ($)"] = tbl_disp["Total Spend 2024-25 ($)"].apply(lambda v: d(v, 0))
    tbl_disp["% of Total Spend"] = tbl_disp["% of Total Spend"].apply(lambda v: p(v))
 
    def _style_risk(row):
        color = RED if "HIGH" in row["Risk Level"] else (AMBER if row["Risk Level"] == "MEDIUM" else "")
        return [f"color:{color};font-weight:700" if color else "" for _ in row]
 
    st.dataframe(tbl_disp.style.apply(_style_risk, axis=1), use_container_width=True, height=420)
 
    st.markdown("---")
 
    # Tariff scenario calculator
    st.markdown("### 🧮 Tariff Scenario Calculator")
    countries_avail = sorted(tbl["country_name"].unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
        tariff_country = st.selectbox("Select a country", countries_avail, key="tariff_country")
    with c2:
        tariff_pct = st.number_input("Tariff percentage (%)", min_value=0.0, max_value=200.0,
                                      value=25.0, step=1.0, key="tariff_pct")
 
    c_sub = merged[merged["country_name"] == tariff_country]
    impacted_spend = c_sub["spend"].sum()
    cost_increase = impacted_spend * (tariff_pct / 100)
    n_items = c_sub["item_code"].nunique()
    n_suppliers = c_sub["supplier_bp_code"].nunique()
 
    st.markdown(
        f"<div class='fbox'>A <b>{tariff_pct:.0f}%</b> tariff on <b>{tariff_country}</b> would increase "
        f"annual raw material costs by <b>{d(cost_increase,0)}</b>, affecting "
        f"<b>{n_items}</b> items and <b>{n_suppliers}</b> suppliers.</div>",
        unsafe_allow_html=True)
 
    st.markdown("#### Top 10 Items Most Impacted")
    item_impact = (c_sub.groupby(["item_code"])["spend"].sum() * (tariff_pct / 100)).reset_index()
    item_impact.columns = ["Item Code", "Est. Cost Impact ($)"]
    item_impact = item_impact.sort_values("Est. Cost Impact ($)", ascending=False).head(10)
    item_impact["Est. Cost Impact ($)"] = item_impact["Est. Cost Impact ($)"].apply(lambda v: d(v, 0))
    st.dataframe(item_impact, use_container_width=True, height=380, hide_index=True)
 
    # Export
    export_tbl = tbl[["country_name", "suppliers", "items", "spend", "pct_of_total", "risk"]].copy()
    export_tbl.columns = ["Country", "Suppliers", "Items Sourced", "Total Spend ($)", "% of Total Spend", "Risk Level"]
    dl_excel(export_tbl, "Carboline_Tariff_Risk_Report.xlsx", key="dl_tariff")
 
 
# ═══════════════════════════════════════════════════
# TAB 10 — OPEN PO MONITOR
# ═══════════════════════════════════════════════════
def t10_openpo(D):
    st.markdown("## 📬 Open PO Monitor")
 
    po = D["po"].copy()
    sup = D["sup"]
    today = pd.Timestamp(datetime.now().date())
 
    open_po = po[po.get("po_status", "") == "OPEN"].copy()
    if open_po.empty:
        st.info("No open purchase orders found.")
        return
 
    open_po["planned_receipt_date"] = pd.to_datetime(open_po["planned_receipt_date"], errors="coerce")
    open_po["days_overdue"] = (today - open_po["planned_receipt_date"]).dt.days
    open_po["days_overdue"] = open_po["days_overdue"].fillna(0).clip(lower=0)
 
    def _status(row):
        if pd.isna(row["planned_receipt_date"]) or row["planned_receipt_date"] >= today:
            return "🟢 GREEN"
        elif row["days_overdue"] <= 30:
            return "🟡 AMBER"
        else:
            return "🔴 RED"
    open_po["status_light"] = open_po.apply(_status, axis=1)
    open_po["est_value"] = pd.to_numeric(open_po.get("unit_price", 0), errors="coerce").fillna(0) * \
                            pd.to_numeric(open_po.get("ordered_qty", 0), errors="coerce").fillna(0)
 
    open_po = open_po.merge(sup[["supplier_bp_code", "supplier_name"]], on="supplier_bp_code", how="left")
    open_po["supplier_name"] = open_po["supplier_name"].fillna(open_po["supplier_bp_code"])
 
    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        site_f = st.selectbox("Site", ["All Sites"] + sorted(open_po["site_group"].dropna().unique().tolist()), key="po_site")
    with f2:
        status_f = st.selectbox("Status", ["All", "Overdue Only", "On Track"], key="po_status_f")
    with f3:
        date_range = st.date_input("Order Date Range",
                                    value=(open_po["order_date"].min().date() if open_po["order_date"].notna().any() else datetime.now().date(),
                                           open_po["order_date"].max().date() if open_po["order_date"].notna().any() else datetime.now().date()),
                                    key="po_date_range")
 
    f_po = open_po.copy()
    if site_f != "All Sites":
        f_po = f_po[f_po["site_group"] == site_f]
    if status_f == "Overdue Only":
        f_po = f_po[f_po["status_light"].isin(["🟡 AMBER", "🔴 RED"])]
    elif status_f == "On Track":
        f_po = f_po[f_po["status_light"] == "🟢 GREEN"]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        f_po = f_po[(f_po["order_date"] >= start_d) & (f_po["order_date"] <= end_d)]
 
    total_open = len(f_po)
    total_overdue = f_po["status_light"].isin(["🟡 AMBER", "🔴 RED"]).sum()
    total_value = f_po["est_value"].sum()
    avg_days_overdue = f_po.loc[f_po["days_overdue"] > 0, "days_overdue"].mean()
 
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("📬 Total Open POs",      n(total_open),    "Placed, not yet received")
    with k2: kpi("⏰ Total Overdue",       n(total_overdue), "Amber + Red",          "kpi-b")
    with k3: kpi("💰 Total Open Value",    d(total_value,0), "Unreceived PO $")
    with k4: kpi("📅 Avg Days Overdue",    f"{avg_days_overdue:.1f}d" if pd.notna(avg_days_overdue) else "—", "Among overdue POs", "kpi-a")
 
    st.markdown("---")
 
    c_l, c_r = st.columns(2)
    with c_l:
        st.markdown("### Open PO Count by Site")
        site_counts = f_po.groupby("site_group").size().reset_index(name="count")
        fig_s = px.bar(site_counts, x="site_group", y="count",
                        color="site_group",
                        color_discrete_map={"Lake Charles": BLUE, "Green Bay": GREEN, "Dayton": AMBER, "Louisa": ORANGE},
                        text="count", title="Open POs by Site")
        fig_s.update_traces(textposition="outside", showlegend=False)
        fig_s.update_layout(height=360, xaxis_title=None, yaxis_title="Open POs", **CHART)
        st.plotly_chart(fig_s, use_container_width=True)
 
    with c_r:
        st.markdown("### Open PO Count by Supplier (Top 15)")
        sup_counts = f_po.groupby("supplier_name").size().reset_index(name="count").nlargest(15, "count")
        fig_sup = px.bar(sup_counts.sort_values("count"), x="count", y="supplier_name", orientation="h",
                          color_discrete_sequence=[STEEL],
                          text="count", title="Suppliers With Most Open POs")
        fig_sup.update_traces(textposition="outside")
        fig_sup.update_layout(height=420, yaxis_title=None, xaxis_title="Open POs", **CHART)
        st.plotly_chart(fig_sup, use_container_width=True)
 
    st.markdown("### Open PO Detail")
    detail = f_po[["status_light", "po_number", "item_code", "item_description", "site_group",
                   "supplier_name", "ordered_qty", "order_date", "planned_receipt_date",
                   "days_overdue", "est_value"]].copy() if "item_description" in f_po.columns else \
             f_po[["status_light", "po_number", "item_code", "site_group",
                   "supplier_name", "ordered_qty", "order_date", "planned_receipt_date",
                   "days_overdue", "est_value"]].copy()
    detail.sort_values("days_overdue", ascending=False, inplace=True)
    rename_cols = {
        "status_light": "Status Light", "po_number": "PO Number", "item_code": "Item Code",
        "item_description": "Description", "site_group": "Site", "supplier_name": "Supplier Name",
        "ordered_qty": "Ordered Qty", "order_date": "Order Date",
        "planned_receipt_date": "Planned Receipt Date", "days_overdue": "Days Overdue",
        "est_value": "Estimated Value ($)"
    }
    detail.rename(columns=rename_cols, inplace=True)
    for c in ["Order Date", "Planned Receipt Date"]:
        if c in detail.columns:
            detail[c] = pd.to_datetime(detail[c], errors="coerce").dt.strftime("%Y-%m-%d")
    detail["Ordered Qty"] = detail["Ordered Qty"].apply(lambda v: n(v, 1))
    detail["Days Overdue"] = detail["Days Overdue"].apply(lambda v: n(v, 0))
    detail["Estimated Value ($)"] = detail["Estimated Value ($)"].apply(lambda v: d(v, 2))
 
    st.dataframe(detail, use_container_width=True, height=480, hide_index=True)
    dl_excel(detail, "Carboline_Open_PO_List.xlsx", key="dl_openpo")
 
 
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
        "🔮 Demand Forecasting",
        "🌍 Country & Tariff Tracker",
        "📬 Open PO Monitor",
    ])
 
    with tabs[0]: t1_overview(data, filt)
    with tabs[1]: t2_audit(data, filt)
    with tabs[2]: t3_calc(data, filt)
    with tabs[3]: t4_supplier(data, filt)
    with tabs[4]: t5_inventory(data, filt)
    with tabs[5]: t6_seasonality(data, filt)
    with tabs[6]: t7_dtier(data)
    with tabs[7]: t8_forecast(data)
    with tabs[8]: t9_tariff(data)
    with tabs[9]: t10_openpo(data)
 
 
if __name__ == "__main__":
    main()
