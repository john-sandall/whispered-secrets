"""
Whispered Secrets.

Usage:
    python -m demo.transcribe
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from queue import Queue
from time import sleep

import numpy as np
import speech_recognition as sr
import torch
import typer
import whisper


def check_for_stop_signal():
    return os.path.exists("stop_signal.txt")


def main(
    model: str = typer.Option(
        "medium",
        help="Model to use",
        prompt="Choose a model from ['tiny', 'base', 'small', 'medium']",
    ),
    energy_threshold: int = typer.Option(300, help="Energy level for mic to detect."),
    record_timeout: float = typer.Option(3.0, help="How real time the recording is in seconds."),
    phrase_timeout: float = typer.Option(
        15,
        help=(
            "How much empty space between recordings before we consider"
            "it a new line in the transcription."
        ),
    ),
    mic_index: int = typer.Option(0, help="Microphone device to use."),
):
    """main function"""

    # Configure microphone
    if mic_index is None:
        print("Available microphone devices are: ")
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f'{index}: Microphone with name "{name}" found')
        mic_index = int(input("Please enter the index of the microphone you want to use: "))
    source = sr.Microphone(sample_rate=16000, device_index=mic_index)

    # Load / Download model
    model = model + ".en"
    audio_model = whisper.load_model(model)

    # We use SpeechRecognizer to record our audio because it has a nice feature where it can detect
    # when speech ends.
    recorder = sr.Recognizer()
    recorder.energy_threshold = energy_threshold

    # Definitely do this, dynamic energy compensation lowers the energy threshold dramatically to
    # a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False

    # Thread safe Queue for passing data from the threaded recording callback.
    data_queue = Queue()
    transcription = [""]

    # The last time a recording was retrieved from the queue.
    phrase_time = None

    with source:
        recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio: sr.AudioData) -> None:
        """
        Threaded callback function to receive audio data when recordings finish.

        audio: An AudioData containing the recorded bytes.
        """
        data_queue.put(audio.get_raw_data())

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    stop_listening = recorder.listen_in_background(
        source,
        record_callback,
        phrase_time_limit=record_timeout,
    )

    message = (
        f"✅ Model {model} loaded & listening (energy_threshold={energy_threshold}, "
        f"record_timeout={record_timeout}, phrase_timeout={phrase_timeout})...\n"
    )
    print(message)
    with Path.open("transcription_output.txt", "w", encoding="utf-8") as file:
        file.write(message)

    try:
        while True:
            if check_for_stop_signal():
                print("Stop signal received. Exiting...")
                break

            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                now = datetime.now(tz=UTC)

                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                phrase_complete = False
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    phrase_complete = True

                # This is the last time we received new audio data from the queue.
                phrase_time = now

                # Combine audio data from queue
                audio_data = b"".join(list(data_queue.queue))
                data_queue.queue.clear()

                # Convert in-ram buffer to something the model can use directly without needing a
                # temp file. Convert data from 16 bit wide integers to floating point with a width
                # of 32 bits. Clamp the audio stream frequency to a PCM wavelength compatible
                # default of 32768hz max.
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                # Read the transcription.
                result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
                text = result["text"].strip()

                # If we detected a pause between recordings, add a new item to our transcription.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                else:
                    cleaned = transcription[-1].strip()
                    for suffix in ["...", ".", "?"]:
                        cleaned = cleaned.removesuffix(suffix)
                    cleaned_text = (cleaned + " " + text).strip()
                    transcription[-1] = cleaned_text

                # Clear the console to reprint the updated transcription.
                os.system("cls" if os.name == "nt" else "clear")
                for line in transcription:
                    print(line, end="\n\n")
                # Flush stdout.
                print("", end="", flush=True)

                with Path.open("transcription_output.txt", "w", encoding="utf-8") as file:
                    for line in transcription:
                        file.write(line + "\n\n")
            else:
                # Infinite loops are bad for processors, must sleep.
                sleep(0.1)
    except KeyboardInterrupt:
        pass

    finally:
        if os.path.exists("stop_signal.txt"):
            os.remove("stop_signal.txt")  # Clean up the signal file on exit

    stop_listening(wait_for_stop=False)  # Stop the background listener


if __name__ == "__main__":
    typer.run(main)
