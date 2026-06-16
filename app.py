import streamlit as st
import pandas as pd
from pathlib import Path
import sqlite3
import pulp
import time
import threading
from datetime import datetime
from fetch_prices import fetch_all_chains

# הגדרת תצורת עמוד ראשונית
st.set_page_config(page_title="CartIQ | סל קניות חכם", page_icon="C", layout="wide")

# --- Scheduler ---
def _scheduler_loop():
    import schedule
    schedule.every().day.at("06:00").do(fetch_all_chains)
    while True:
        schedule.run_pending()
        time.sleep(60)

if "scheduler_started" not in st.session_state:
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()
    st.session_state["scheduler_started"] = True

# --- העיצוב ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Heebo', sans-serif !important; direction: rtl; text-align: right; background-color: #F8FAFC !important; color: #1E293B !important;
}
.section-title { font-size: 20px; font-weight: 700; color: #10B981 !important; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid rgba(16,185,129,0.35); display: inline-block; }
.kpi-card { background: #FFFFFF; border-radius: 20px; padding: 26px 18px; text-align: center; border: 1px solid #E2E8F0; box-shadow: 0 4px 10px rgba(0,0,0,0.03); }
.kpi-label { font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; margin-bottom: 10px; }
.kpi-value { font-size: 30px; font-weight: 900; color: #1E293B; }
.green { color: #10B981; }
.amber { color: #F59E0B; }
.stButton > button { border-radius: 12px !important; font-weight: 700 !important; background: #10B981 !important; color: #FFFFFF !important; border: none !important; }
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
    conn.execute("DELETE FROM chains WHERE chain_id IN (4, 5)")
    conn.execute("INSERT INTO chains (chain_id, chain_name) VALUES (4, 'ויקטורי'), (5, 'אושר עד')")
    conn.commit()
    products = pd.read_sql_query("SELECT * FROM products", conn)
    chains = pd.read_sql_query("SELECT * FROM chains", conn)
    prices = pd.read_sql_query("SELECT * FROM prices", conn)
    promotions = pd.read_sql_query("SELECT * FROM promotions", conn)
    conn.close()
    return products, chains, prices, promotions

def get_discount(product_id, chain_id, base_total, promotions):
    rows = promotions[(promotions["product_id"] == product_id) & (promotions["chain_id"] == chain_id)]
    discount = 0
    for _, row in rows.iterrows():
        if row["promotion_type"] == "fixed_total": discount += float(row["discount_value"])
        elif row["promotion_type"] == "percent": discount += base_total * float(row["discount_value"]) / 100
    return discount

def calculate_costs(cart, prices, chains, promotions):
    results = []
    for _, chain in chains.iterrows():
        chain_id = int(chain["chain_id"])
        total = 0
        covered = 0
        for product_id, quantity in cart.items():
            price_row = prices[(prices["product_id"] == product_id) & (prices["chain_id"] == chain_id)]
            if price_row.empty: continue
            covered += 1
            unit_price = float(price_row.iloc[0]["price"])
            total += max((unit_price * quantity) - get_discount(product_id, chain_id, unit_price * quantity, promotions), 0)
        if covered > 0: results.append({"chain_id": chain_id, "רשת": chain["chain_name"], "עלות סל": round(total, 2)})
    return pd.DataFrame(results) if not results == [] else pd.DataFrame(columns=["chain_id", "רשת", "עלות סל"])

def optimize_split_purchase(cart, prices, chains, promotions, budget=0):
    product_ids = list(cart.keys())
    chain_ids = list(chains["chain_id"].astype(int))
    chain_names = dict(zip(chains["chain_id"].astype(int), chains["chain_name"]))
    effective = {pid: {cid: max(float(prices[(prices["product_id"] == pid) & (prices["chain_id"] == cid)].iloc[0]["price"]) * cart[pid] - get_discount(pid, cid, float(prices[(prices["product_id"] == pid) & (prices["chain_id"] == cid)].iloc[0]["price"]) * cart[pid], promotions), 0) for cid in chain_ids if not prices[(prices["product_id"] == pid) & (prices["chain_id"] == cid)].empty} for pid in product_ids}
    model = pulp.LpProblem("CartIQ", pulp.LpMinimize)
    x = {(pid, cid): pulp.LpVariable(f"x_{pid}_{cid}", cat="Binary") for pid in product_ids for cid in effective[pid]}
    model += pulp.lpSum(effective[pid][cid] * x[(pid, cid)] for pid in product_ids for cid in effective[pid])
    for pid in product_ids: model += pulp.lpSum(x[(pid, cid)] for cid in effective[pid]) == 1
    if budget > 0: model += pulp.lpSum(effective[pid][cid] * x[(pid, cid)] for pid in product_ids for cid in effective[pid]) <= budget
    model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[model.status] != "Optimal": return None, False, {}
    assignment = {pid: {"chain_id": cid, "chain_name": chain_names[cid], "cost": round(effective[pid][cid], 2)} for pid in product_ids for cid in effective[pid] if pulp.value(x[(pid, cid)]) == 1}
    return round(pulp.value(model.objective), 2), True, assignment

products, chains, prices, promotions = load_data()
if "cart" not in st.session_state: st.session_state.cart = {}

st.markdown('<div class="hero"><div class="hero-inner"><div class="hero-wordmark">CartIQ</div></div></div>', unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["בחירת מוצרים", "סל הקניות", "אופטימיזציה"])

with tab1:
    category = st.selectbox("מחלקה", sorted(products["category"].unique()))
    for _, product in products[products["category"] == category].iterrows():
        pid = str(product["product_id"])
        if st.checkbox(product["product_name"], key=f"check_{pid}", value=(pid in st.session_state.cart)):
            st.session_state.cart[pid] = st.number_input("כמות", 1, 10, st.session_state.cart.get(pid, 1), key=f"qty_{pid}")
        elif pid in st.session_state.cart:
            del st.session_state.cart[pid]
            st.rerun()

with tab3:
    if st.button("הרץ אופטימיזציה", type="primary"):
        if not st.session_state.cart: st.error("הסל ריק.")
        else:
            opt_total, opt_ok, assignment = optimize_split_purchase(st.session_state.cart, prices, chains, promotions, budget if budget > 0 else 0)
            
            if budget > 0 and opt_total and opt_total > budget:
                st.error(f"חריגה של {opt_total - budget:.2f} ₪.")
                if st.button("בצע התאמה אוטומטית לתקציב"):
                    def get_max_price(pid):
                        p_rows = prices[prices['product_id'] == pid]
                        return p_rows['price'].max() if not p_rows.empty else 0
                    sorted_cart = sorted(st.session_state.cart.items(), key=lambda x: get_max_price(x[0]), reverse=True)
                    for pid, qty in sorted_cart:
                        if opt_total <= budget: break
                        del st.session_state.cart[pid]
                        new_total, _, _ = optimize_split_purchase(st.session_state.cart, prices, chains, promotions, budget)
                        if new_total: opt_total = new_total
                    st.rerun()

            if opt_total:
                costs_df = calculate_costs(st.session_state.cart, prices, chains, promotions)
                single_cost = costs_df["עלות סל"].min() if not costs_df.empty else opt_total
                saving = round(single_cost - opt_total, 2)
                saving_pct = round(saving / single_cost * 100, 1) if single_cost > 0 else 0
                st.markdown(f"""
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 24px 0;">
                    <div class="kpi-card"><div class="kpi-label">עלות מפוצלת (ILP)</div><div class="kpi-value green">&#8362;{opt_total:.2f}</div></div>
                    <div class="kpi-card"><div class="kpi-label">רשת זולה יחידה</div><div class="kpi-value">&#8362;{single_cost:.2f}</div></div>
                    <div class="kpi-card"><div class="kpi-label">חיסכון בפיצול</div><div class="kpi-value amber">&#8362;{saving:.2f} <span style="font-size:16px">({saving_pct}%)</span></div></div>
                </div>
                """, unsafe_allow_html=True)
