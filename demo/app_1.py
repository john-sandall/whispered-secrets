"""
Whispered Secrets application - Part 1.

Usage:
    streamlit run demo/app_1.py
"""

import speech_recognition as sr
import streamlit as st


def start_transcription(model, energy_threshold, record_timeout, phrase_timeout, mic_index):
    st.write(
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

    start_transcription(
        model,
        energy_threshold,
        record_timeout,
        phrase_timeout,
        mic_index,
    )


if __name__ == "__main__":
    app()
