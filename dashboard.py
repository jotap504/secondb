import streamlit as st
import pandas as pd
import plotly.express as px
from database import supabase
import datetime

# --- Page Config ---
st.set_page_config(
    page_title="AI Life OS Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Premium Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stMetric {
        background-color: #1e2227;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
    }
    .stDataFrame {
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    /* Glassmorphism effect for sidebar */
    .css-1d391kg {
        background-color: rgba(30, 34, 39, 0.8);
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Data Fetching ---
@st.cache_data(ttl=60)
def fetch_data(table_name):
    try:
        response = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching {table_name}: {e}")
        return pd.DataFrame()

# --- Sidebar ---
st.sidebar.title("🧠 AI Life OS")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["📊 Overview", "💸 Expenses", "✅ Tasks", "📓 Notes"])

# --- Main Dashboard ---
if page == "📊 Overview":
    st.title("Welcome back, Juan!")
    st.markdown("Here's a quick look at your life assistant data.")

    col1, col2, col3 = st.columns(3)
    
    df_exp = fetch_data("expenses")
    df_tasks = fetch_data("tasks")
    df_notes = fetch_data("notes")

    with col1:
        total_spent = 0
        if not df_exp.empty:
            total_spent = df_exp['amount'].sum()
        st.metric("Total Expenses", f"${total_spent:,.2f}", delta_color="inverse")

    with col2:
        pending_tasks = 0
        if not df_tasks.empty:
            pending_tasks = len(df_tasks[df_tasks['status'] == 'pending'])
        st.metric("Pending Tasks", pending_tasks)

    with col3:
        total_notes = len(df_notes) if not df_notes.empty else 0
        st.metric("Captured Notes", total_notes)

    st.markdown("---")
    
    # Simple Chart in Overview
    if not df_exp.empty:
        st.subheader("Spending Trends")
        df_exp['created_at'] = pd.to_datetime(df_exp['created_at'])
        daily_exp = df_exp.groupby(df_exp['created_at'].dt.date)['amount'].sum().reset_index()
        fig = px.line(daily_exp, x='created_at', y='amount', title="Daily Spending", template="plotly_dark")
        fig.update_traces(line_color='#58a6ff')
        st.plotly_chart(fig, use_container_width=True)

elif page == "💸 Expenses":
    st.title("Expense Tracker")
    df = fetch_data("expenses")
    if not df.empty:
        st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)
        
        # Category Breakdown
        st.subheader("By Category")
        fig = px.pie(df, values='amount', names='description', title="Spend Distribution", template="plotly_dark")
        st.plotly_chart(fig)
    else:
        st.info("No expenses found yet. Talk to the bot to add some!")

elif page == "✅ Tasks":
    st.title("Task Management")
    df = fetch_data("tasks")
    if not df.empty:
        # Simple Task List with Status
        for index, row in df.iterrows():
            status_icon = "⏳" if row['status'] == 'pending' else "✅"
            st.checkbox(f"{status_icon} {row['description']} (Deadline: {row['deadline'] or 'N/A'})", 
                        value=(row['status'] == 'completed'), key=f"task_{row['id']}")
    else:
        st.info("Your task list is empty. Stay productive!")

elif page == "📓 Notes":
    st.title("Daily Notes")
    df = fetch_data("notes")
    if not df.empty:
        for index, row in df.sort_values("created_at", ascending=False).iterrows():
            with st.expander(f"📌 Note from {pd.to_datetime(row['created_at']).strftime('%Y-%m-%d %H:%M')}"):
                st.write(row['content'])
    else:
        st.info("Capture your first note using the Telegram bot.")

st.sidebar.markdown("---")
st.sidebar.caption("Status: All systems operational 🟢")
