import streamlit as st
from graph_agent import crew

st.set_page_config(page_title="Stock Agent Crew", layout="wide")

st.title("📈 Stock Agent Crew (LangGraph)")

query = st.text_input("Enter your query:", "Fundamentals and valuation for Infosys")
symbols = st.text_input("Stock symbols (comma separated):", "INFY.NS,TCS.NS")

if st.button("Run Analysis"):
    state = {"query": query, "symbols": [s.strip() for s in symbols.split(",")]}
    with st.spinner("Agents working..."):
        result = crew.invoke(state)
    st.subheader("Answer")
    st.write(result["answer"])

    st.subheader("Raw Data")
    st.json(result)
