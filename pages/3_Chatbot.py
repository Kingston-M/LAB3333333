import os
import streamlit as st
from pydantic_ai import Agent

st.set_page_config(page_title="NBAStat | Basketball Chat", page_icon="💬", layout="wide")

st.title("💬 Basketball Chat — NBA Analytics Assistant")
st.caption("Ask about basketball strategy, advanced analytics concepts (TS%, PER, Offensive/Defensive Rating), or NBA history.")

# Load Gemini API key into environment for Pydantic AI
if "GOOGLE_API_KEY" in st.secrets and st.secrets["GOOGLE_API_KEY"]:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

@st.cache_resource
def get_chat_agent():
    return Agent(
        "google-gla:gemini-2.5-flash",
        instructions=(
            "You are an enthusiastic, knowledgeable NBA analytics assistant for the 'NBAStat: Beyond the Box Score' "
            "CS 1301 project created by Audrey Bewley and Kingston Morgan. Stay strictly on the theme of basketball, "
            "NBA analytics, and explaining statistics like True Shooting Percentage (TS%), Usage Rate (USG%), "
            "Offensive/Defensive Rating, and player roles. Do not claim to look up live scores on this page; "
            "remind users they can visit the 'Basketball Agent' page for live dataset queries."
        ),
    )

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask a question about NBA analytics or basketball..."):
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            if not os.environ.get("GOOGLE_API_KEY"):
                st.warning("⚠️ Please add your `GOOGLE_API_KEY` to `.streamlit/secrets.toml` to activate the chatbot.")
            else:
                agent = get_chat_agent()
                with st.spinner("Analyzing basketball concepts..."):
                    result = agent.run_sync(prompt, message_history=st.session_state.chat_history)
                st.markdown(result.output)
                st.session_state.chat_messages.append({"role": "assistant", "content": result.output})
                st.session_state.chat_history = result.all_messages()
        except Exception as e:
            st.error(f"An error occurred while generating a response: {e}")
