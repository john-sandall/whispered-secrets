"""
Whispered Secrets.

Usage:
    streamlit run demo/app_2.py
"""
import time

import speech_recognition as sr
import streamlit as st

time.sleep(0.1)


def start_transcription(model, energy_threshold, record_timeout, phrase_timeout, mic_index):
    return (
        f"Model {model} loaded & listening (energy_threshold={energy_threshold}, "
        f"record_timeout={record_timeout}, phrase_timeout={phrase_timeout}, mic_index={mic_index})",
    )


def app():
    st.title("Real-Time Transcription")

    # Sidebar
    model = st.sidebar.selectbox("Choose a model", ["tiny", "base", "small", "medium"])
    mic_index = st.sidebar.selectbox(
        "Select the microphone",
        options=[(i, name) for i, name in enumerate(sr.Microphone.list_microphone_names())],
        format_func=lambda x: x[1],  # Display the name of the microphone
    )[0]  # we want the index
    energy_threshold = st.sidebar.slider(
        "Energy Threshold",
        min_value=100,
        max_value=500,
        value=300,
    )
    record_timeout = st.sidebar.slider(
        "Record Timeout (s)",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
    )
    phrase_timeout = st.sidebar.slider(
        "Phrase Timeout (s)",
        min_value=5.0,
        max_value=30.0,
        value=15.0,
    )

    # Start/stop transcription
    if "transcribing" not in st.session_state:
        st.session_state.transcribing = False

    if not st.session_state.transcribing:
        if st.button("Start Transcribing"):
            st.session_state.transcribing = True
            st.write(
                start_transcription(
                    model,
                    energy_threshold,
                    record_timeout,
                    phrase_timeout,
                    mic_index,
                ),
            )
            # st.rerun()

    if st.session_state.transcribing:
        if st.button("Stop Transcribing"):
            st.session_state.transcribing = False
            st.error("Transcription stopped!")
            # time.sleep(2)
            # st.rerun()
        st.success("Transcription starting...")


if __name__ == "__main__":
    app()
