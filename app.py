"""Streamlit interface for ActivIQ."""

import streamlit as st

from src.pipeline import FitBuddyPipeline


st.set_page_config(page_title="ActivIQ", page_icon="💪")
st.title("ActivIQ")
st.caption("Offline fitness guidance using local data. ActivIQ is not a medical professional.")

if "pipeline" not in st.session_state:
    st.session_state.pipeline = FitBuddyPipeline()
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Session")
    if st.button("Reset profile"):
        st.session_state.pipeline.state.reset()
        st.session_state.messages = []
        st.rerun()
    st.json(st.session_state.pipeline.state.profile)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

if prompt := st.chat_input("Ask about exercise, workouts, or nutrition"):
    st.session_state.messages.append({"role": "user", "text": prompt})
    result = st.session_state.pipeline.respond(prompt)
    st.session_state.messages.append({"role": "assistant", "text": result["text"]})
    st.rerun()

