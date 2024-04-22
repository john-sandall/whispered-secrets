"""
Whispered Secrets.

Usage:
    streamlit run demo/app_3.py
"""

import subprocess
import time

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

    st.markdown("### Transcription")
    transcription_display = st.empty()

    some_markdown = """
The transcription is working! But Streamlit isn't accessing the output. Let's add the following to our `transcribe.py`:

```python
with Path.open("transcription_output.txt", "w", encoding="utf-8") as file:
    file.write(message)

...

# Inside the audio processing loop...
while True:

    # Read audio bytes from Queue()
    # Transcribe with Whisper
    # Add to the list `transcription`

    ...

    with Path.open("transcription_output.txt", "w", encoding="utf-8") as file:
        for line in transcription:
            file.write(line + "\\n\\n")
```

We will also need to add some bits to our Streamlit application. We will need:

```python
################################################################
# 1. A container to hold the transcription.

st.markdown("### Transcription")
transcription_display = st.empty()

################################################################
# 2. A transcription loader.

def load_transcription():
    with Path.open("transcription_output.txt", "a+") as file:
        file.seek(0)  # Move cursor to the start of the file
        return file.read()

################################################################
# 3. A loop to put the transcription into the Streamlit container (and a clock, for fun!).
while True:
    transcription_content = load_transcription()
    transcription_display.markdown(transcription_content)
    last_update.text(f"Last updated: {time.ctime()}")

    time.sleep(1)  # Refresh every second
```
"""

    transcription_display.markdown(some_markdown)


if __name__ == "__main__":
    app()
