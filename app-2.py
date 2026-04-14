
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import datetime

st.set_page_config(page_title="Busy Buffet Dashboard", layout="wide")

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data
def load_data():
    FILE = "2026 Data Test1 Final - Busy Buffet Dataset.xlsx"
    sheets = {
        "133": "2026-03-13",
        "143": "2026-03-14",
        "153": "2026-03-15",
        "173": "2026-03-17",
        "183": "2026-03-18"
    }
    all_days = []
    for sheet_name, date in sheets.items():
        df = pd.read_excel(FILE, sheet_name=sheet_name, usecols=range(8))
        df.columns = ["service_no", "pax", "queue_start", "queue_end",
                      "table_no", "meal_start", "meal_end", "guest_type"]
        df["date"] = date
        df = df[df["service_no"].notna()]
        all_days.append(df)
    data = pd.concat(all_days, ignore_index=True)
    data["date"] = pd.to_datetime(data["date"])

    def parse_time(val, date):
        if pd.isna(val): return pd.NaT
        try:
            if isinstance(val, datetime.time):
                return datetime.datetime.combine(date, val)
            t = pd.to_datetime(str(val), format="%H:%M:%S").time()
            return datetime.datetime.combine(date, t)
        except:
            return pd.NaT

    for col in ["queue_start", "queue_end", "meal_start", "meal_end"]:
        data[col] = data.apply(lambda r: parse_time(r[col], r["date"]), axis=1)

    data["meal_duration"] = (data["meal_end"] - data["meal_start"]).dt.total_seconds() / 60
    data["wait_duration"] = (data["queue_end"] - data["queue_start"]).dt.total_seconds() / 60
    data["meal_duration"] = data["meal_duration"].where(data["meal_duration"] >= 0)
    data["meal_duration"] = data["meal_duration"].where(data["meal_duration"] <= 300)
    data["has_queue"] = data["queue_start"].notna()
    data["has_meal"] = data["meal_start"].notna()
    data["is_walkaways"] = data["has_queue"] & ~data["has_meal"]
    data["guest_type"] = data["guest_type"].str.strip()
    return data

data = load_data()

# ============================================================
# HEADER
# ============================================================
st.title("🍽️ Busy Buffet Dashboard")
st.markdown("**Hotel Amber 85 — Breakfast Buffet Analysis**")
st.divider()

# ============================================================
# KPI CARDS
# ============================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Pax", f"{int(data['pax'].sum())}")
col2.metric("Avg Meal Duration", f"{data['meal_duration'].mean():.0f} min")
col3.metric("Avg Wait Time", f"{data['wait_duration'].mean():.0f} min")
col4.metric("Total Walk-aways", f"{data['is_walkaways'].sum()}")
st.divider()

# ============================================================
# TASK 1
# ============================================================
st.header("Task 1: Staff Comments Analysis")

# Comment 1
st.subheader("Comment 1: In-house Wait & Walk-in Walk-away")

inhouse_wait = data[(data["guest_type"]=="In house") & (data["has_queue"]==True)]["wait_duration"].mean()
walkin_wait  = data[(data["guest_type"]=="Walk in") & (data["is_walkaways"]==True)]["wait_duration"].mean()

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(["In-house\n(waited for table)", "Walk-in\n(left without eating)"],
       [inhouse_wait, walkin_wait],
       color=["#42A5F5", "#EF5350"], width=0.4, edgecolor="white")
for bar, val in zip(ax.patches, [inhouse_wait, walkin_wait]):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f"{val:.0f} min", ha="center", fontweight="bold", fontsize=12)
ax.set_title("Comment 1: How long did guests wait?", fontweight="bold")
ax.set_ylabel("Avg Wait Time (minutes)")
ax.set_ylim(0, max(inhouse_wait, walkin_wait)*1.3)
st.pyplot(fig)
st.markdown("> จากข้อมูลพบว่าเวลารอคิวส่งผลต่อพฤติกรรมของลูกค้าโดยตรง โดยลูกค้าที่รอนานเกินไปมีแนวโน้มตัดสินใจออกจากคิวโดยไม่ใช้บริการ อย่างไรก็ตาม จำนวน walk-away โดยรวมยังไม่สูงมากนัก บ่งชี้ว่าปัญหาคิวยาวเกิดขึ้นเฉพาะช่วง peak period เท่านั้น **Verdict: TRUE ✅**")
st.divider()

# Comment 2
st.subheader("Comment 2: Busy Every Day?")
pax_by_day = data.groupby("date")["pax"].sum()
wa_by_day  = data[data["is_walkaways"]].groupby("date").size().reindex(pax_by_day.index, fill_value=0)
labels     = [d.strftime("%d %b") for d in pax_by_day.index]
colors     = ["#EF5350" if wa > 5 else "#FFA726" if wa > 0 else "#42A5F5" for wa in wa_by_day.values]

fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.bar(labels, pax_by_day.values, color=colors, width=0.5, edgecolor="white")
for i, v in enumerate(pax_by_day.values):
    ax.text(i, v+2, f"{int(v)} pax", ha="center", fontweight="bold", fontsize=10)
for i, v in enumerate(wa_by_day.values):
    label = f"🚶 {int(v)} left" if v > 0 else "✅ no queue"
    ax.text(i, 8, label, ha="center", fontsize=9, color="white", fontweight="bold")
from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(color="#42A5F5", label="Normal — no queue"),
    Patch(color="#FFA726", label="Busy — queue exists"),
    Patch(color="#EF5350", label="Critical — walk-aways"),
], loc="upper left", fontsize=9)
ax.set_title("Comment 2: Is it busy every single day?", fontweight="bold")
ax.set_ylabel("Total Pax")
ax.set_ylim(0, pax_by_day.max()*1.3)
st.pyplot(fig)
st.markdown("> จากข้อมูลพบว่าปัญหาเกิดขึ้นเฉพาะ **วันเสาร์-อาทิตย์** เท่านั้น วันธรรมดาไม่มีคิวเลย ถ้าจัดการ weekend ได้ดีขึ้น ปัญหาส่วนใหญ่น่าจะหมดไปเอง **Verdict: FALSE ❌**")
st.divider()

# Comment 3
st.subheader("Comment 3: Walk-in Sit Too Long?")
meal_by_day = data.groupby(["date","guest_type"])["meal_duration"].mean().unstack()
meal_by_day.index = [d.strftime("%d %b\n%a") for d in meal_by_day.index]
overall_avg = data["meal_duration"].mean()

fig, ax = plt.subplots(figsize=(10, 4))
x = range(len(meal_by_day))
width = 0.35
bars1 = ax.bar([i-width/2 for i in x], meal_by_day["In house"], width=width, color="#42A5F5", label="In-house", edgecolor="white")
bars2 = ax.bar([i+width/2 for i in x], meal_by_day["Walk in"],  width=width, color="#EF5350", label="Walk-in",  edgecolor="white")
for bar in list(bars1)+list(bars2):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
            f"{bar.get_height():.0f}m", ha="center", fontsize=9, fontweight="bold")
ax.axhline(overall_avg, color="gray", linestyle="--", linewidth=2)
ax.text(4.55, overall_avg+1.5, f"Overall Avg: {overall_avg:.0f} min", color="gray", fontsize=9, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(meal_by_day.index)
ax.set_ylabel("Avg Meal Duration (mins)")
ax.set_title("Comment 3: Do Walk-in customers sit longer?", fontweight="bold")
ax.legend()
st.pyplot(fig)
st.markdown("> Walk-in นั่งนานกว่า In-house จริง แต่ไม่ได้นั่งทั้งวัน เฉลี่ยประมาณ 1 ชั่วโมง ปัญหาที่แท้จริงคือจำนวนลูกค้าที่เพิ่มขึ้นใน weekend มากกว่า **Verdict: PARTIALLY TRUE ⚠️**")
st.divider()

# ============================================================
# TASK 2
# ============================================================
st.header("Task 2: Why Recommended Actions Won't Work")

# Action 1
st.subheader("Action 1: Reduce Seating Time from 5 Hours")
meal_data = data["meal_duration"].dropna()
bins = [0, 60, 120, 180, 300]
labels_bin = ["0-1 hr", "1-2 hr", "2-3 hr", "3-5 hr"]
counts = pd.cut(meal_data, bins=bins, labels=labels_bin).value_counts().sort_index()
pct = counts / counts.sum() * 100

fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(labels_bin, pct.values, color=["#42A5F5","#FFA726","#EF5350","#B71C1C"], width=0.5, edgecolor="white")
for bar, val in zip(bars, pct.values):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f"{val:.1f}%", ha="center", fontweight="bold", fontsize=11)
ax.text(0.5, 85, f"Avg Meal Duration: {meal_data.mean():.0f} min",
        ha="center", fontsize=11, fontweight="bold", color="white",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#42A5F5"))
ax.set_title("Action 1: Does the 5-hour limit actually matter?", fontweight="bold")
ax.set_xlabel("Meal Duration Range")
ax.set_ylabel("% of Customers")
ax.set_ylim(0, 100)
st.pyplot(fig)
st.markdown("> ลูกค้าเกือบทั้งหมดนั่งแค่ 0-1 ชั่วโมง ไม่มีใครแม้แต่ใกล้เคียง 5 ชั่วโมง การลดเวลาจึงไม่ได้แก้ปัญหาอะไรเลย **Verdict: Won't Work ❌**")
st.divider()

# Action 2
st.subheader("Action 2: Raise Price to ฿259 Everyday")
is_weekend = [d.weekday() >= 5 for d in pax_by_day.index]
rev_current  = sum(pax_by_day.values * [199 if w else 159 for w in is_weekend])
rev_best     = sum(pax_by_day.values * 259)
pax_real     = [p*0.7 if not w else p for p,w in zip(pax_by_day.values, is_weekend)]
rev_real     = sum([p*259 for p in pax_real])

fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.bar(["Current\n(159/199)", "259 All Days\n(Best Case)", "259 All Days\n(Weekday -30%)"],
              [rev_current, rev_best, rev_real],
              color=["#42A5F5","#66BB6A","#EF5350"], width=0.4, edgecolor="white")
for bar, val in zip(bars, [rev_current, rev_best, rev_real]):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+500,
            f"฿{val:,.0f}", ha="center", fontweight="bold", fontsize=11)
ax.set_title("Action 2: Does raising price to ฿259 everyday increase revenue?", fontweight="bold")
ax.set_ylabel("Total Revenue (฿)")
ax.set_ylim(0, rev_best*1.25)
st.pyplot(fig)
st.markdown("> ขึ้นราคาทุกวันไม่ได้แก้ปัญหาคิว weekend เพราะคนที่อยากมา weekend ก็ยังมาอยู่ดี แถมยังทำให้ลูกค้าวันธรรมดาหายไปด้วย **Verdict: Won't Work ❌**")
st.divider()

# Action 3
st.subheader("Action 3: Queue Skipping for In-house")
counts_type = data["guest_type"].value_counts()

fig, ax = plt.subplots(figsize=(6, 6))
ax.pie(counts_type.values,
       labels=counts_type.index,
       colors=["#42A5F5","#EF5350"],
       autopct="%1.1f%%",
       explode=(0.03,0.03),
       startangle=90,
       textprops={"fontsize":12},
       wedgeprops={"edgecolor":"white","linewidth":2})
ax.set_title("Action 3: Who are we actually serving?", fontweight="bold")
ax.legend([f"In-house ({counts_type["In house"]} groups)",
           f"Walk-in ({counts_type["Walk in"]} groups)"],
          loc="lower center", fontsize=10, bbox_to_anchor=(0.5,-0.05))
ax.text(0, -1.4,
        "⚠️ Walk-in คือ 57% ของลูกค้าทั้งหมด\nให้ In-house ข้ามคิว = Walk-in รอนานขึ้น\nจำนวนคนเท่าเดิม ความยุ่งไม่ได้หายไปไหน",
        ha="center", fontsize=10,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF3E0", edgecolor="#EF5350"),
        color="#B71C1C")
st.pyplot(fig)
st.markdown("> Walk-in คือลูกค้าส่วนใหญ่ การให้ In-house ข้ามคิวไม่ได้ลดความยุ่งวุ่นวายลงเลย แค่ย้ายปัญหาไปให้ Walk-in รอนานขึ้นแทน **Verdict: Won't Work ❌**")
st.divider()

# ============================================================
# TASK 3
# ============================================================
st.header("Task 3: Recommended Solution")
st.subheader("Raise Weekend Price to ฿259 + 2hr Seating Limit on Weekend")

rev_proposed = sum(pax_by_day.values * [259 if w else 159 for w in is_weekend])
diff = rev_proposed - rev_current

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(["Current\n(159/199)", "Proposed\n(159 weekday / 259 weekend)"],
       [rev_current, rev_proposed],
       color=["#42A5F5","#66BB6A"], width=0.4, edgecolor="white")
for bar, val in zip(ax.patches, [rev_current, rev_proposed]):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+500,
            f"฿{val:,.0f}", ha="center", fontweight="bold", fontsize=12)
ax.text(0.5, rev_proposed*0.5,
        f"+฿{diff:,.0f}\n(+{diff/rev_current*100:.1f}%)",
        ha="center", fontsize=12, fontweight="bold", color="#2E7D32",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#E8F5E9", edgecolor="#66BB6A"))
ax.set_title("Revenue: Raise price on Weekend only", fontweight="bold")
ax.set_ylabel("Total Revenue (฿)")
ax.set_ylim(0, rev_proposed*1.3)
st.pyplot(fig)
st.markdown("> ปัญหาทั้งหมดเกิดเฉพาะ weekend ดังนั้นการแก้เฉพาะจุดนั้นสมเหตุสมผลที่สุด ขึ้นราคา weekend ช่วยเพิ่มรายได้และลด demand ที่มากเกินไป ส่วนการจำกัดเวลา 2 ชั่วโมงช่วยให้หมุนโต๊ะได้เร็วขึ้น โดยไม่กระทบวันธรรมดาเลย")
