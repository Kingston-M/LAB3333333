import streamlit as st

st.set_page_config(
    page_title="NBAStat: Beyond the Box Score",
    page_icon="🏀",
    layout="wide"
)

# Title of App
st.title("Web Development Labs 03 & 04")

# Assignment Data
st.header("CS 1301")
st.subheader("NBAStat: Beyond the Box Score — Web Development - Section A")
st.subheader("Audrey Bewley, Kingston Morgan")

st.markdown("---")

# Introduction
st.write("""
Welcome to our Streamlit Web Development app! You can navigate between the pages using the sidebar to the left. The following pages are:

1. **Basketball Data**: Want to compare NBA teams or players with interactive NBA 2K-style visual cards, radar/bar graphs, team logos, and player headshots, or see where players are from? Go here!
2. **Basketball Chat**: Want to talk to a friendly AI basketball analyst that knows the ins and outs of the NBA? Go here!
3. **Basketball Agent**: Want to ask an AI data agent real analytical questions backed directly by live NBA stats tools (efficiency, team ratings, roster leaders, and player comparisons)? Go here!
""")

st.info("💡 **Project Focus — Beyond the Box Score:** Instead of looking only at Points Per Game, use the **Basketball Data** and **Basketball Agent** pages to explore True Shooting % (TS%), Offensive/Defensive Ratings, Assists, Rebounds, Steals, Blocks, and Plus/Minus.")
