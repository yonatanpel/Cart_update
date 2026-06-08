import streamlit as st
st.title("בדיקה 123")
import streamlit as st
import pandas as pd
from pathlib import Path
import sqlite3
import pulp
import time
import threading
from datetime import datetime
from fetch_prices import fetch_all_chains


# --- Scheduler: עדכון אוטומטי כל יום ב-06:00 ---
def _scheduler_loop():
    """רץ ב-background thread, מפעיל עדכון מחירים בשעה 06:00 מדי יום."""
    import schedule
    schedule.every().day.at("06:00").do(fetch_all_chains)
    while True:
        schedule.run_pending()
        time.sleep(60)

if "scheduler_started" not in st.session_state:
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    st.session_state["scheduler_started"] = True

# הגדרת תצורת עמוד ראשונית
st.set_page_config(page_title="CartIQ | סל קניות חכם", page_icon="C", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

/* ===== GLOBAL — DARK BACKGROUND ===== */
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="stHeader"],
[data-testid="stVerticalBlock"],
section.main,
section.main > div,
.block-container,
.main .block-container {
    font-family: 'Heebo', sans-serif !important;
    direction: rtl;
    text-align: right;
    background-color: #0b0f1a !important;
    color: #cbd5e1 !important;
}

/* override any white backgrounds left over */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="column"],
.element-container {
    background: transparent !important;
}

[data-testid="stSidebar"] { display: none; }
#MainMenu, footer, header { visibility: hidden; }

::-webkit-scrollbar { width: 7px; }
::-webkit-scrollbar-track { background: #0b0f1a; }
::-webkit-scrollbar-thumb { background: #00c896; border-radius: 4px; }

/* ===== 3D HERO ===== */
.hero {
    perspective: 1200px;
    margin-bottom: 28px;
}
.hero-inner {
    background: linear-gradient(160deg, #0d2137 0%, #0a3d2e 50%, #061c14 100%);
    border-radius: 24px;
    padding: 60px 40px 52px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transform: perspective(900px) rotateX(3deg);
    transform-style: preserve-3d;
    box-shadow:
    0 2px 0 rgba(0,200,150,0.15),
    0 6px 0 rgba(0,160,120,0.1),
    0 14px 0 rgba(0,100,80,0.07),
    0 30px 60px rgba(0,0,0,0.6),
    0 60px 120px rgba(0,0,0,0.4),
    inset 0 1px 0 rgba(0,255,180,0.15),
    inset 0 -1px 0 rgba(0,0,0,0.4);
    border: 1px solid rgba(0,200,150,0.2);
    transition: transform 0.4s ease, box-shadow 0.4s ease;
}
.hero-inner:hover {
    transform: perspective(900px) rotateX(1deg) translateY(-4px);
    box-shadow:
    0 2px 0 rgba(0,200,150,0.2),
    0 8px 0 rgba(0,160,120,0.12),
    0 20px 0 rgba(0,100,80,0.08),
    0 40px 80px rgba(0,0,0,0.65),
    0 80px 140px rgba(0,0,0,0.45),
    inset 0 1px 0 rgba(0,255,180,0.2);
}
.hero-inner::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(0,255,180,0.6) 50%, transparent 100%);
}
.hero-inner::after {
    content: '';
    position: absolute;
    top: -100px; left: 50%;
    transform: translateX(-50%);
    width: 600px; height: 200px;
    background: radial-gradient(ellipse, rgba(0,200,150,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.hero-wordmark {
    font-size: 80px;
    font-weight: 900;
    letter-spacing: -5px;
    line-height: 1;
    margin: 0 0 10px 0;
    background: linear-gradient(135deg, #ffffff 0%, #a7f3d0 50%, #00c896 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 2px 8px rgba(0,200,150,0.4));
}
.hero-sub {
    font-size: 17px;
    color: #6ee7b7;
    font-weight: 400;
    margin: 0;
    letter-spacing: 0.3px;
}

/* ===== STATUS BAR ===== */
.status-bar {
    background: linear-gradient(135deg, #111827 0%, #0f1f2e 100%);
    border-radius: 16px;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    border: 1px solid rgba(0,200,150,0.15);
    box-shadow:
    0 4px 0 rgba(0,0,0,0.3),
    0 8px 24px rgba(0,0,0,0.4),
    inset 0 1px 0 rgba(255,255,255,0.05);
}
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(0,200,150,0.08);
    border: 1px solid rgba(0,200,150,0.2);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 13px;
    color: #6ee7b7;
    font-weight: 500;
}

/* ===== TABS ===== */
.stTabs [data-baseweb="tab-list"] {
    background: #111827 !important;
    border-radius: 16px !important;
    padding: 6px !important;
    gap: 4px !important;
    border: 1px solid rgba(0,200,150,0.12) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 12px !important;
    padding: 10px 28px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    color: #6b7280 !important;
    transition: all 0.25s !important;
    border: none !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #007a5e, #00c896) !important;
    color: #ffffff !important;
    box-shadow:
    0 2px 0 rgba(0,100,80,0.8),
    0 5px 15px rgba(0,200,150,0.4),
    inset 0 1px 0 rgba(255,255,255,0.2) !important;
    transform: translateY(-1px) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #111827 !important;
    border-radius: 20px !important;
    padding: 28px !important;
    margin-top: 12px !important;
    border: 1px solid rgba(0,200,150,0.1) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}

/* ===== SECTION TITLE ===== */
.section-title {
    font-size: 20px;
    font-weight: 700;
    color: #f0fdf4;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid rgba(0,200,150,0.35);
    display: inline-block;
}

/* ===== INPUTS ===== */
.stTextInput > div > div > input,
.stSelectbox > div > div,
[data-testid="stNumberInput"] input {
    background: #0d1520 !important;
    border-radius: 12px !important;
    border: 1px solid rgba(0,200,150,0.2) !important;
    color: #e2e8f0 !important;
    font-family: 'Heebo', sans-serif !important;
    font-size: 15px !important;
    transition: all 0.2s !important;
    direction: rtl !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3) !important;
}
.stTextInput > div > div > input:focus {
    border-color: #00c896 !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3), 0 0 0 3px rgba(0,200,150,0.15) !important;
}
.stSelectbox > div > div > div { color: #e2e8f0 !important; }

/* ===== CHECKBOXES ===== */
[data-testid="stCheckbox"] label {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: #cbd5e1 !important;
}
[data-testid="stCheckbox"] div[role="checkbox"] {
    border-color: rgba(0,200,150,0.4) !important;
    background: #0d1520 !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
}

/* ===== 3D KPI CARDS ===== */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 24px 0;
}
.kpi-card {
    background: linear-gradient(145deg, #1a2744, #111827);
    border-radius: 20px;
    padding: 26px 18px 22px;
    text-align: center;
    position: relative;
    border: 1px solid rgba(0,200,150,0.15);
    box-shadow:
    0 2px 0 rgba(0,0,0,0.4),
    0 6px 0 rgba(0,0,0,0.3),
    0 12px 0 rgba(0,0,0,0.15),
    0 20px 40px rgba(0,0,0,0.5),
    inset 0 1px 0 rgba(255,255,255,0.06);
    transform: perspective(600px) rotateX(2deg);
    transition: all 0.3s ease;
}
.kpi-card:hover {
    transform: perspective(600px) rotateX(0deg) translateY(-6px);
    box-shadow:
    0 2px 0 rgba(0,0,0,0.4),
    0 10px 0 rgba(0,0,0,0.2),
    0 30px 60px rgba(0,0,0,0.55),
    inset 0 1px 0 rgba(255,255,255,0.08);
    border-color: rgba(0,200,150,0.35);
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,200,150,0.4), transparent);
    border-radius: 50%;
}
.kpi-card.savings {
    background: linear-gradient(145deg, #1f1a0a, #2a1f06);
    border-color: rgba(245,158,11,0.2);
}
.kpi-card.savings::before { background: linear-gradient(90deg, transparent, rgba(245,158,11,0.4), transparent); }
.kpi-card.time {
    background: linear-gradient(145deg, #1a1030, #110d22);
    border-color: rgba(139,92,246,0.2);
}
.kpi-card.time::before { background: linear-gradient(90deg, transparent, rgba(139,92,246,0.5), transparent); }
.kpi-card.single {
    background: linear-gradient(145deg, #141e2e, #0e1624);
    border-color: rgba(100,116,139,0.2);
}
.kpi-label {
    font-size: 11px;
    font-weight: 700;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
}
.kpi-value { font-size: 30px; font-weight: 900; color: #f1f5f9; line-height: 1; }
.kpi-value.green { color: #00c896; text-shadow: 0 0 20px rgba(0,200,150,0.4); }
.kpi-value.amber { color: #f59e0b; text-shadow: 0 0 20px rgba(245,158,11,0.3); }
.kpi-value.purple { color: #a78bfa; text-shadow: 0 0 20px rgba(167,139,250,0.3); }

/* ===== 3D CHAIN BARS ===== */
.chain-bar-wrap { margin: 10px 0; }
.chain-bar-label {
    font-size: 14px; font-weight: 600; color: #9ca3af;
    margin-bottom: 5px; display: flex; justify-content: space-between;
}
.chain-bar-bg {
    background: #0d1520;
    border-radius: 8px; height: 16px; overflow: hidden;
    box-shadow: inset 0 3px 8px rgba(0,0,0,0.5), inset 0 -1px 0 rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
}
.chain-bar-fill {
    height: 100%; border-radius: 8px;
    box-shadow: 0 0 10px rgba(0,200,150,0.5), inset 0 1px 0 rgba(255,255,255,0.2);
    background: linear-gradient(90deg, #007a5e, #00c896);
    transition: width 0.8s cubic-bezier(0.25,0.46,0.45,0.94);
}

/* ===== 3D DETAIL TABLE ===== */
.detail-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.detail-table th {
    background: #0d1520;
    color: #4b5563;
    font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
    padding: 12px 16px; text-align: right;
    border-bottom: 1px solid rgba(0,200,150,0.15);
}
.detail-table td {
    padding: 13px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 14px; color: #cbd5e1; vertical-align: middle;
}
.detail-table tr:hover td {
    background: rgba(0,200,150,0.04);
    color: #f1f5f9;
}
.chain-badge {
    display: inline-block; padding: 3px 12px;
    border-radius: 20px; font-size: 12px; font-weight: 700;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1);
}
.badge-1 { background: rgba(0,200,150,0.15); color: #00c896; border: 1px solid rgba(0,200,150,0.25); }
.badge-2 { background: rgba(239,68,68,0.12); color: #f87171; border: 1px solid rgba(239,68,68,0.2); }
.badge-3 { background: rgba(59,130,246,0.12); color: #60a5fa; border: 1px solid rgba(59,130,246,0.2); }
.badge-4 { background: rgba(245,158,11,0.12); color: #fbbf24; border: 1px solid rgba(245,158,11,0.2); }

/* ===== 3D CART ITEMS ===== */
.cart-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 13px 18px; margin-bottom: 7px;
    background: linear-gradient(135deg, #131f30, #0f1824);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 2px 0 rgba(0,0,0,0.4), 0 6px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: all 0.2s;
}
.cart-item:hover {
    transform: translateX(-3px) translateY(-1px);
    border-color: rgba(0,200,150,0.2);
    box-shadow: 0 4px 0 rgba(0,0,0,0.4), 0 12px 24px rgba(0,0,0,0.35);
}
.cart-item-name { font-weight: 600; color: #e2e8f0; font-size: 14px; }
.cart-item-qty {
    background: linear-gradient(135deg, #007a5e, #00c896);
    color: white; border-radius: 20px; padding: 3px 14px;
    font-size: 13px; font-weight: 700;
    box-shadow: 0 2px 0 #005240, 0 4px 12px rgba(0,200,150,0.3), inset 0 1px 0 rgba(255,255,255,0.2);
}
.cat-header {
    font-size: 11px; font-weight: 700; color: #00c896;
    text-transform: uppercase; letter-spacing: 1.2px;
    padding: 14px 0 7px;
    border-bottom: 1px solid rgba(0,200,150,0.2);
    margin-bottom: 10px; margin-top: 18px;
}

/* ===== 3D BUTTONS ===== */
.stButton > button {
    border-radius: 12px !important;
    font-family: 'Heebo', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    padding: 10px 24px !important;
    transition: all 0.18s ease !important;
    border: none !important;
    background: linear-gradient(135deg, #0f1a24, #1a2744) !important;
    color: #6ee7b7 !important;
    box-shadow:
    0 4px 0 rgba(0,0,0,0.5),
    0 8px 20px rgba(0,0,0,0.4),
    inset 0 1px 0 rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(0,200,150,0.15) !important;
}
.stButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow:
    0 7px 0 rgba(0,0,0,0.5),
    0 14px 30px rgba(0,0,0,0.45),
    inset 0 1px 0 rgba(255,255,255,0.1) !important;
    color: #a7f3d0 !important;
}
.stButton > button:active {
    transform: translateY(2px) !important;
    box-shadow: 0 1px 0 rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #007a5e, #00c896) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow:
    0 4px 0 #004d3a,
    0 8px 24px rgba(0,200,150,0.35),
    inset 0 1px 0 rgba(255,255,255,0.2) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow:
    0 7px 0 #004d3a,
    0 16px 36px rgba(0,200,150,0.4),
    inset 0 1px 0 rgba(255,255,255,0.25) !important;
}
.stButton > button[kind="primary"]:active {
    box-shadow: 0 1px 0 #004d3a, 0 4px 12px rgba(0,200,150,0.25) !important;
}

/* ===== ALERTS ===== */
[data-testid="stAlert"] {
    border-radius: 14px !important;
    background: rgba(0,200,150,0.08) !important;
    border: 1px solid rgba(0,200,150,0.2) !important;
    color: #a7f3d0 !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}

/* ===== METRIC ===== */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #131f30, #0f1824);
    border-radius: 16px; padding: 18px;
    border: 1px solid rgba(0,200,150,0.12);
    box-shadow: 0 4px 0 rgba(0,0,0,0.4), 0 10px 30px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
}
[data-testid="stMetricLabel"] { color: #4b5563 !important; font-weight: 600 !important; font-size: 13px !important; }
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 900 !important; color: #00c896 !important; }

/* ===== CAPTION ===== */
[data-testid="stCaptionContainer"] p { font-size: 13px !important; color: #4b5563 !important; }

/* ===== NUMBER INPUT ===== */
[data-testid="stNumberInput"] input {
    background: #0d1520 !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(0,200,150,0.2) !important;
    text-align: center !important;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.3) !important;
}

/* RTL */
label, p, span, div, h1, h2, h3, h4, h5 { direction: rtl !important; }
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent

@st.cache_data(ttl=60)
def load_data():
    db_path = DATA_DIR / "cartiq.db"
    if not db_path.exists():
        from init_db import load_csv_to_db
        load_csv_to_db()
    conn = sqlite3.connect(db_path)
    products = pd.read_sql_query("SELECT * FROM products", conn)
    chains = pd.read_sql_query("SELECT * FROM chains", conn)
    prices = pd.read_sql_query("SELECT * FROM prices", conn)
    promotions = pd.read_sql_query("SELECT * FROM promotions", conn)
    conn.close()
    products["product_id"] = products["product_id"].astype(str)
    prices["product_id"] = prices["product_id"].astype(str)
    prices["chain_id"] = prices["chain_id"].astype(int)
    chains["chain_id"] = chains["chain_id"].astype(int)
    return products, chains, prices, promotions


def get_discount(product_id, chain_id, base_total, promotions):
    if promotions.empty:
        return 0
    rows = promotions[(promotions["product_id"] == product_id) & (promotions["chain_id"] == chain_id)]
    discount = 0
    for _, row in rows.iterrows():
        if row["promotion_type"] == "fixed_total":
            discount += float(row["discount_value"])
        elif row["promotion_type"] == "percent":
            discount += base_total * float(row["discount_value"]) / 100
    return discount


def calculate_costs(cart, prices, chains, promotions):
    results = []
    for _, chain in chains.iterrows():
        chain_id = int(chain["chain_id"])
        chain_name = chain["chain_name"]
        total = 0
        covered = 0
        for product_id, quantity in cart.items():
            price_row = prices[(prices["product_id"] == product_id) & (prices["chain_id"] == chain_id)]
            if price_row.empty:
                continue
            covered += 1
            unit_price = float(price_row.iloc[0]["price"])
            base_total = unit_price * quantity
            discount = get_discount(product_id, chain_id, base_total, promotions)
            total += max(base_total - discount, 0)
        if covered > 0:
            results.append({
                "chain_id": chain_id,
                "רשת": chain_name,
                "עלות סל": round(total, 2),
                "מוצרים זמינים": covered,
            })
    return pd.DataFrame(results) if results else pd.DataFrame(columns=["chain_id", "רשת", "עלות סל", "מוצרים זמינים"])


def optimize_split_purchase(cart, prices, chains, promotions, budget=0):
    """
    ILP לרכישה מפוצלת.
    משתנים: x[i,j] in {0,1}
    מטרה: min sum effective_cost[i,j] * x[i,j]
    אילוצים: sum_j x[i,j] = 1 לכל i; sum <= budget אם הוגדר
    """
    product_ids = list(cart.keys())
    chain_ids = list(chains["chain_id"].astype(int))
    chain_names = dict(zip(chains["chain_id"].astype(int), chains["chain_name"]))

    effective = {}
    for pid in product_ids:
        qty = cart[pid]
        effective[pid] = {}
        for cid in chain_ids:
            row = prices[(prices["product_id"] == pid) & (prices["chain_id"] == cid)]
            if row.empty:
                continue
            unit_price = float(row.iloc[0]["price"])
            base_total = unit_price * qty
            discount = get_discount(pid, cid, base_total, promotions)
            effective[pid][cid] = max(base_total - discount, 0)

    model = pulp.LpProblem("CartIQ_Split_Purchase", pulp.LpMinimize)
    x = {
        (pid, cid): pulp.LpVariable(f"x_{pid}_{cid}", cat="Binary")
        for pid in product_ids
        for cid in effective.get(pid, {})
    }
    model += pulp.lpSum(effective[pid][cid] * x[(pid, cid)] for (pid, cid) in x)
    for pid in product_ids:
        available_chains = list(effective.get(pid, {}).keys())
        if not available_chains:
            continue
        model += pulp.lpSum(x[(pid, cid)] for cid in available_chains) == 1
    if budget > 0:
        model += pulp.lpSum(effective[pid][cid] * x[(pid, cid)] for (pid, cid) in x) <= budget

    status = model.solve(pulp.PULP_CBC_CMD(msg=False))
    optimal = pulp.LpStatus[status] == "Optimal"
    if not optimal:
        return None, False, {}
    total_cost = round(pulp.value(model.objective), 2)
    assignment = {}
    for (pid, cid), var in x.items():
        if pulp.value(var) and round(pulp.value(var)) == 1:
            assignment[pid] = {
                "chain_id": cid,
                "chain_name": chain_names[cid],
                "cost": round(effective[pid][cid], 2),
            }
    return total_cost, True, assignment


# ===== LOAD DATA =====
products, chains, prices, promotions = load_data()

if "cart" not in st.session_state:
    st.session_state.cart = {}

# ===== HERO =====
n_products = len(products)
n_chains = len(chains)
last_update = prices["last_update"].max() if "last_update" in prices.columns and not prices.empty else "—"
cart_count = len(st.session_state.cart)

st.markdown(f"""
<div class="hero">
    <div class="hero-inner">
        <div class="hero-wordmark">CartIQ</div>
        <p class="hero-sub">השוואת מחירים חכמה &nbsp;&middot;&nbsp; אופטימיזציה בזמן אמת &nbsp;&middot;&nbsp; {n_products:,} מוצרים &nbsp;&middot;&nbsp; {n_chains} רשתות</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ===== STATUS BAR =====
status_col, btn_col = st.columns([4, 1])
with status_col:
    cart_pill = f"<span class='status-pill'>{cart_count} פריטים בסל</span>" if cart_count > 0 else ""
    st.markdown(f"""
    <div class="status-bar">
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <span class="status-pill">{n_products:,} מוצרים</span>
            <span class="status-pill">{n_chains} רשתות</span>
            <span class="status-pill">עדכון אחרון: {last_update}</span>
            <span class="status-pill">עדכון אוטומטי ב-06:00</span>
            {cart_pill}
        </div>
    </div>
    """, unsafe_allow_html=True)
with btn_col:
    if st.button("עדכן מחירים", use_container_width=True):
        with st.spinner("שואב מחירים..."):
            count = fetch_all_chains()
            load_data.clear()
        st.success(f"עודכן! {count:,} רשומות.")
        st.rerun()

# ===== TABS =====
tab1, tab2, tab3 = st.tabs([
    "בחירת מוצרים",
    "סל הקניות",
    "אופטימיזציה"
])

# ===== TAB 1: PRODUCTS =====
with tab1:
    cat_icons = {
        "ירקות": "", "פירות": "", "ביצים, חלב וגבינות": "",
        "קצביה": "", "מוצרים קפואים": "", "מאפים ולחם": "",
        "טואלטיקה": "", "מוצרי ניקוי": "", "אירוח": "",
        "מזווה": "", "כללי": ""
    }

    st.markdown('<div class="section-title">חיפוש והוספת מוצרים</div>', unsafe_allow_html=True)

    col_cat, col_src = st.columns([1, 1])
    all_cats = sorted(products["category"].unique())

    with col_cat:
        category = st.selectbox("מחלקה", all_cats, format_func=lambda x: x)
    with col_src:
        search = st.text_input("חיפוש חופשי", placeholder="הקלד שם מוצר...")

    if search:
        filtered = products[products["product_name"].str.contains(search, case=False, na=False)]
    else:
        filtered = products[products["category"] == category]

    total_found = len(filtered)
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:16px 0 12px;">
        <span style="font-weight:700;color:#f0fdf4;font-size:17px">{category if not search else "תוצאות חיפוש"}</span>
        <span style="background:rgba(0,200,150,0.1);border:1px solid rgba(0,200,150,0.25);border-radius:20px;padding:2px 12px;font-size:13px;color:#00c896;font-weight:600">{total_found:,} מוצרים</span>
    </div>
    """, unsafe_allow_html=True)

    for _, product in filtered.head(50).iterrows():
        product_id = str(product["product_id"])
        is_selected = product_id in st.session_state.cart

        if is_selected:
            c_left, c_right = st.columns([5, 1])
            with c_left:
                is_checked = st.checkbox(
                    f"**{product['product_name']}**",
                    key=f"check_{product_id}",
                    value=True
                )
            with c_right:
                qty = st.number_input(
                    "כמות", min_value=1,
                    value=st.session_state.cart.get(product_id, 1),
                    step=1, key=f"qty_{product_id}",
                    label_visibility="collapsed"
                )
                st.session_state.cart[product_id] = int(qty)
            if not is_checked:
                del st.session_state.cart[product_id]
                st.rerun()
        else:
            is_checked = st.checkbox(
                product['product_name'],
                key=f"check_{product_id}",
                value=False
            )
            if is_checked:
                st.session_state.cart[product_id] = 1
                st.rerun()

# ===== TAB 2: CART =====
with tab2:
    st.markdown('<div class="section-title">סל הקניות שלי</div>', unsafe_allow_html=True)

    if not st.session_state.cart:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#4b5563;">
            <div style="font-size:13px;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;color:#374151">הסל ריק</div>
            <div style="font-size:15px;color:#6b7280">עברו לטאב <strong style="color:#00c896">בחירת מוצרים</strong> כדי להתחיל</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        cart_df = products[products["product_id"].isin(st.session_state.cart.keys())].copy()
        cart_df["quantity"] = cart_df["product_id"].map(st.session_state.cart)
        total_items = cart_df["quantity"].sum()

        st.markdown(f"""
        <div style="background:linear-gradient(135deg,rgba(0,200,150,0.08),rgba(0,200,150,0.04));border:1px solid rgba(0,200,150,0.2);border-radius:14px;padding:16px 20px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 4px 16px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.04)">
            <span style="font-weight:700;color:#6ee7b7;font-size:16px">{len(cart_df)} פריטים שונים &nbsp;&middot;&nbsp; {int(total_items)} יחידות סה"כ</span>
        </div>
        """, unsafe_allow_html=True)

        for cat in sorted(cart_df["category"].unique()):
            cat_items = cart_df[cart_df["category"] == cat]
            st.markdown(f'<div class="cat-header">{cat} &nbsp;&middot;&nbsp; {len(cat_items)} פריטים</div>', unsafe_allow_html=True)
            items_html = ""
            for _, row in cat_items.iterrows():
                items_html += f"""
                <div class="cart-item">
                    <span class="cart-item-name">{row['product_name']}</span>
                    <span class="cart-item-qty">x{row['quantity']}</span>
                </div>"""
            st.markdown(items_html, unsafe_allow_html=True)

# ===== TAB 3: OPTIMIZATION =====
with tab3:
    st.markdown('<div class="section-title">מנוע אופטימיזציה ILP</div>', unsafe_allow_html=True)

    b_col, run_col = st.columns([3, 1])
    with b_col:
        budget = st.number_input("תקציב מקסימלי (ILS) — השאר 0 ללא הגבלה", min_value=0.0, value=0.0, step=50.0)
    with run_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_btn = st.button("הרץ אופטימיזציה", use_container_width=True, type="primary")

    if run_btn:
        if not st.session_state.cart:
            st.error("הסל ריק. עבור לטאב בחירת מוצרים.")
        else:
            with st.spinner("מריץ אלגוריתם ILP..."):
                t0 = time.time()
                opt_total, opt_ok, assignment = optimize_split_purchase(
                    st.session_state.cart, prices, chains, promotions, budget
                )
                solve_time = round(time.time() - t0, 3)
                costs_df = calculate_costs(st.session_state.cart, prices, chains, promotions)
                single_best = costs_df.sort_values("עלות סל").iloc[0] if not costs_df.empty else None

            if not opt_ok or opt_total is None:
                st.error("לא נמצא פתרון אופטימלי — ייתכן שהתקציב נמוך מדי.")
            else:
                single_cost = float(single_best["עלות סל"]) if single_best is not None else opt_total
                saving = round(single_cost - opt_total, 2)
                saving_pct = round(saving / single_cost * 100, 1) if single_cost > 0 else 0

                st.markdown(f"""
                <div class="kpi-grid">
                    <div class="kpi-card">
                        <div class="kpi-label">עלות ILP מפוצל</div>
                        <div class="kpi-value green">&#8362;{opt_total:.2f}</div>
                    </div>
                    <div class="kpi-card single">
                        <div class="kpi-label">רשת זולה יחידה</div>
                        <div class="kpi-value">&#8362;{single_cost:.2f}</div>
                    </div>
                    <div class="kpi-card savings">
                        <div class="kpi-label">חיסכון בפיצול</div>
                        <div class="kpi-value amber">&#8362;{saving:.2f} <span style="font-size:16px">({saving_pct}%)</span></div>
                    </div>
                    <div class="kpi-card time">
                        <div class="kpi-label">זמן פתרון ILP</div>
                        <div class="kpi-value purple">{solve_time}s</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if budget > 0:
                    if opt_total <= budget:
                        st.success(f"עומד בתקציב — נותרו {budget - opt_total:.2f} ILS")
                    else:
                        st.error(f"חריגה מהתקציב ב-{opt_total - budget:.2f} ILS")

                # Chain comparison bars
                st.markdown('<div style="margin:28px 0 12px"><strong style="font-size:16px;color:#f0fdf4">השוואת עלות לפי רשת</strong></div>', unsafe_allow_html=True)
                if not costs_df.empty:
                    max_cost = costs_df["עלות סל"].max()
                    chain_colors = {1: "#00c896", 2: "#ef4444", 3: "#3b82f6", 4: "#f59e0b"}
                    bars_html = ""
                    for _, row in costs_df.sort_values("עלות סל").iterrows():
                        pct = (row["עלות סל"] / max_cost * 100) if max_cost > 0 else 0
                        color = chain_colors.get(int(row["chain_id"]), "#6b7280")
                        is_best = row["עלות סל"] == costs_df["עלות סל"].min()
                        best_tag = "<span style='background:rgba(0,200,150,0.15);color:#00c896;border:1px solid rgba(0,200,150,0.25);border-radius:10px;padding:2px 8px;font-size:11px;font-weight:700;margin-right:6px'>הכי זול</span>" if is_best else ""
                        bars_html += f"""
                        <div class="chain-bar-wrap">
                            <div class="chain-bar-label">
                                <span>{best_tag}{row['רשת']}</span>
                                <span style="font-weight:700;color:#f1f5f9">&#8362;{row['עלות סל']:.2f}</span>
                            </div>
                            <div class="chain-bar-bg">
                                <div class="chain-bar-fill" style="width:{pct:.1f}%;background:linear-gradient(90deg,{color}88,{color})"></div>
                            </div>
                        </div>"""
                    st.markdown(f'<div style="background:linear-gradient(135deg,#0f1824,#0d1520);border-radius:16px;padding:22px;border:1px solid rgba(0,200,150,0.1);box-shadow:0 4px 20px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.03)">{bars_html}</div>', unsafe_allow_html=True)

                # Per-product detail table
                st.markdown('<div style="margin:28px 0 12px"><strong style="font-size:16px;color:#f0fdf4">פירוט רכישה אופטימלית לפי מוצר</strong></div>', unsafe_allow_html=True)
                product_names = dict(zip(products["product_id"], products["product_name"]))
                badge_class = {1: "badge-1", 2: "badge-2", 3: "badge-3", 4: "badge-4"}

                rows_html = ""
                for pid, info in sorted(assignment.items(), key=lambda x: x[1]["chain_name"]):
                    name = product_names.get(pid, pid)
                    qty = st.session_state.cart[pid]
                    chain = info["chain_name"]
                    cid = info["chain_id"]
                    cost = info["cost"]
                    bc = badge_class.get(cid, "badge-1")
                    rows_html += f"""
                    <tr>
                        <td>{name}</td>
                        <td style="text-align:center">{qty}</td>
                        <td><span class="chain-badge {bc}">{chain}</span></td>
                        <td style="text-align:left;font-weight:700;color:#f1f5f9">&#8362;{cost:.2f}</td>
                    </tr>"""

                st.markdown(f"""
                <table class="detail-table">
                    <thead>
                        <tr>
                            <th>מוצר</th>
                            <th style="text-align:center">כמות</th>
                            <th>רשת מומלצת</th>
                            <th style="text-align:left">עלות</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
                """, unsafe_allow_html=True)

#לא עושה כלום
