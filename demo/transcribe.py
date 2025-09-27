"""
Whispered Secrets.

Usage:
    python -m demo.transcribe

Set DEEPL_API_KEY environment variable for translation.
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


def get_translator():
    """Initialize DeepL translator if API key is available."""
    api_key = os.getenv("DEEPL_API_KEY")
    if api_key:
        try:
            import deepl
            translator = deepl.Translator(api_key)
            # Test the connection
            usage = translator.get_usage()
            if usage.character.limit:
                print(f"DeepL connected! ({usage.character.count:,}/{usage.character.limit:,} chars used)")
            else:
                print("DeepL connected!")
            return translator
        except ImportError:
            print("Warning: deepl library not installed. Translation disabled.")
            print("Install with: pip install deepl")
            return None
        except Exception as e:
            print(f"DeepL initialization error: {e}")
            return None
    else:
        print("Note: Set DEEPL_API_KEY environment variable for real-time translation")
        return None


def main(
    model: str = typer.Option(
        "medium",
        help="Model to use. Choose from: tiny, base, small, medium, or with language suffix like small.en or small.ja",
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
    # Store original model name for language detection and display
    original_model = model

    # Check if model already has a language suffix (.en, .ja, .multi, etc.) or is a multilingual model
    if "." not in model:
        # If no suffix, default to English-only model for backward compatibility
        # unless it's "large" which doesn't have .en variant
        if model != "large":
            model = model + ".en"
    elif ".multi" in model:
        # For multilingual models, remove the .multi suffix as Whisper uses base names for multilingual
        model = model.replace(".multi", "")
    elif ".ja" in model:
        # For Japanese, we use the multilingual model but will force Japanese language
        model = model.replace(".ja", "")

    audio_model = whisper.load_model(model)

    # Initialize DeepL translator if available
    translator = get_translator()

    # Determine source and target languages based on model
    is_japanese_model = ".ja" in original_model
    if is_japanese_model:
        source_lang = "JA"
        target_lang = "EN-US"  # English US
        print("Japanese → English translation enabled" if translator else "")
    else:
        source_lang = "EN"
        target_lang = "JA"
        print("English → Japanese translation enabled" if translator else "")

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
    translations = [""]  # Store translations separately

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
        f"✅ Model {original_model} (using {model}) loaded & listening (energy_threshold={energy_threshold}, "
        f"record_timeout={record_timeout}, phrase_timeout={phrase_timeout})...\n"
    )
    print(message)
    with open("transcription_output.txt", "w", encoding="utf-8") as file:
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
                # Determine language based on original model name
                if ".ja" in original_model:
                    # Force Japanese language for Japanese models
                    result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available(), language="ja")
                else:
                    # Let Whisper auto-detect or use default (English for .en models, auto for .multi)
                    result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
                text = result["text"].strip()

                # If we detected a pause between recordings, add a new item to our transcription.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                    # Translate the new phrase
                    if translator and text:
                        try:
                            translation = translator.translate_text(text, target_lang=target_lang)
                            translations.append(translation.text)
                        except Exception as e:
                            print(f"Translation error: {e}")
                            translations.append("")
                    else:
                        translations.append("")
                else:
                    cleaned = transcription[-1].strip()
                    for suffix in ["...", ".", "?"]:
                        cleaned = cleaned.removesuffix(suffix)
                    cleaned_text = (cleaned + " " + text).strip()
                    transcription[-1] = cleaned_text

                    # Translate the ENTIRE combined text, not just the increment
                    if translator and cleaned_text:
                        try:
                            translation = translator.translate_text(cleaned_text, target_lang=target_lang)
                            translations[-1] = translation.text
                        except Exception as e:
                            print(f"Translation error: {e}")
                            if len(translations) > 0:
                                translations[-1] = ""
                    elif len(translations) > 0:
                        translations[-1] = ""

                # Clear the console to reprint the updated transcription.
                os.system("cls" if os.name == "nt" else "clear")

                # Display both original and translated text
                for i, line in enumerate(transcription):
                    if line:  # Skip empty lines
                        print(f"[Original] {line}")
                        if translator and i < len(translations) and translations[i]:
                            print(f"[{target_lang}] {translations[i]}")
                        print()  # Add spacing between segments

                # Flush stdout.
                print("", end="", flush=True)

                # Write both versions to file in a structured format
                with open("transcription_output.txt", "w", encoding="utf-8") as file:
                    if translator:
                        file.write("=== BILINGUAL TRANSCRIPTION ===\n\n")
                        if is_japanese_model:
                            file.write("【日本語 / Original Japanese】\n")
                        else:
                            file.write("【English / Original】\n")
                        file.write("-" * 40 + "\n")

                    for line in transcription:
                        if line:
                            file.write(line + "\n\n")

                    # Add translations section if available
                    if translator and any(translations):
                        file.write("\n" + "=" * 40 + "\n\n")
                        if is_japanese_model:
                            file.write("【English Translation / 英訳】\n")
                        else:
                            file.write("【Japanese Translation / 日本語訳】\n")
                        file.write("-" * 40 + "\n")

                        for trans in translations:
                            if trans:
                                file.write(trans + "\n\n")
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
