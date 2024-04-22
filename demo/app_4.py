"""
Whispered Secrets.

Usage:
    streamlit run demo/app_4.py
"""

import subprocess
import time
from pathlib import Path

import speech_recognition as sr
import streamlit as st


def start_transcription(model, energy_threshold, record_timeout, phrase_timeout, mic_index):
    cmd = [
        "python",
        "-m",
        "demo.transcribe",
        "--model",
        model,
        "--energy-threshold",
        str(energy_threshold),
        "--record-timeout",
        str(record_timeout),
        "--phrase-timeout",
        str(phrase_timeout),
        "--mic-index",
        str(mic_index),
    ]
    subprocess.Popen(cmd)


def load_transcription():
    with Path.open("transcription_output.txt", "a+") as file:
        file.seek(0)  # Move cursor to the start of the file
        return file.read()


def summarize():
    cmd = [
        "python",
        "-m",
        "demo.summarize",
        "transcription_output.txt",
        "summary.txt",
    ]
    subprocess.Popen(cmd)
    with Path.open("summary.txt", "a+") as file:
        file.seek(0)  # Move cursor to the start of the file
        return file.read()


def app():
    st.title("Real-Time Transcription")
    last_update = st.empty()

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
            start_transcription(
                model,
                energy_threshold,
                record_timeout,
                phrase_timeout,
                mic_index,
            )
            st.rerun()

    if st.session_state.transcribing:
        if st.button("Stop Transcribing"):
            st.session_state.transcribing = False
            st.error("Transcription stopped!")
            time.sleep(2)
            st.rerun()
        st.success("Transcription starting...")

    if "initialized" not in st.session_state:
        st.session_state["initialized"] = True

    st.markdown("### Transcription")
    transcription_display = st.empty()

    some_markdown = """
## 🛠️ FIXES
We have two problems remaining:

- 1️⃣   Streamlit is loading the last used transcription file.
- 2️⃣   Streamlit is not stopping the transcriber CLI tool when we click "Stop".

```python
################################################################
# 1. Add a function to wipe the transcription file on either:
#    - Streamlit initialization, or
#    - When we start a new transcription.

def clear_transcription_file():
    '''Clear the contents of the transcription file'''
    # Opening in 'w' mode truncates the file
    with Path.open("transcription_output.txt", "w") as file:
        pass
    with Path.open("summary.txt", "w") as file:  # noqa: F841
        pass

################################################################
# 2. Create a "stop signal" using a file that our CLI tool can see.
#    If the file exists, it should stop.

def send_stop_signal():
    with Path.open("stop_signal.txt", "w") as f:
        print("Sending stop signal")
        f.write("stop")


################################################################
# 3. Hook it all up e.g. our "Stop transcribing" button now does this.
if st.button("Stop Transcribing"):
    st.session_state.transcribing = False
    send_stop_signal()
    st.error("Transcription stopped!")
    time.sleep(2)
    st.rerun()
```

We need to make one more change to our `transcribe.py` too:

```python
# Add this at the stop of the audio transcription loop.
while True:
    if check_for_stop_signal():
        print("Stop signal received. Exiting...")
        break
```
"""

    # UNCOMMENT THIS WHEN READY
    st.markdown("How can we fix this?")
    # st.markdown(some_markdown)

    while True:
        transcription_content = load_transcription()
        transcription_display.markdown(transcription_content)
        last_update.text(f"Last updated: {time.ctime()}")

        time.sleep(1)  # Refresh every second


if __name__ == "__main__":
    app()
