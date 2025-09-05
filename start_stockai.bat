@echo off
echo 🚀 Starting StockAI App...
cd /d "C:\Users\nisha\Desktop\Project\StockAI"
call .venv\Scripts\activate
streamlit run app_graph.py --server.address 0.0.0.0 --server.port 8501
pause
