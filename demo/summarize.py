"""
Whispered Secrets.

Usage:
    ollama serve
    python -m demo.summarize 'transcription_output.txt' "summary.txt"
    python -m demo.summarize --help

Set DEEPL_API_KEY environment variable for Japanese translation.
"""

import json
import os
import re
from pathlib import Path

import typer
from langchain_ollama import OllamaLLM

try:
    import deepl
except ImportError:
    deepl = None

MAX_PREVIEW_LENGTH = 200
MIN_ITEMS_COUNT = 3


class TranslatorManager:
    """Manages DeepL translator instance."""

    def __init__(self):
        """Initialize the translator manager."""
        self._translator = None
        self._initialized = False

    def get_translator(self):
        """Lazy load the DeepL translator."""
        if self._initialized:
            return self._translator

        self._initialized = True
        api_key = os.getenv("DEEPL_API_KEY")
        if api_key:
            if deepl is None:
                typer.echo("Warning: deepl library not installed. Translation disabled.")
                typer.echo("Install with: pip install deepl")
                self._translator = False
                return self._translator

            try:
                typer.echo("Initializing DeepL translator...")
                self._translator = deepl.Translator(api_key)
                # Test the API key
                usage = self._translator.get_usage()
                if usage.character.limit:
                    chars_used = usage.character.count
                    chars_limit = usage.character.limit
                    typer.echo(
                        f"DeepL API connected! ({chars_used:,}/{chars_limit:,} characters used)"
                    )
                else:
                    typer.echo("DeepL API connected!")
            except Exception as e:
                typer.echo(f"DeepL initialization error: {e}")
                typer.echo("Please check your DEEPL_API_KEY environment variable")
                self._translator = False
        else:
            typer.echo("Note: Set DEEPL_API_KEY environment variable for Japanese translation")
            self._translator = False
        return self._translator


# Global instance
translator_manager = TranslatorManager()


def _validate_summary_field(field_name: str) -> None:
    """Helper to raise missing field error."""
    msg = f"Missing required field: {field_name}"
    raise ValueError(msg)


def main(input_filepath: str, output_filepath: str):
    """Reads a text file and summarizes its contents using Ollama."""
    # Initialize the Ollama model
    llm = OllamaLLM(model="llama3")

    # Read the contents of the file
    try:
        with Path(input_filepath).open() as file:
            content = file.read()
    except Exception as e:
        typer.echo(f"Error reading file: {e}")
        raise typer.Exit()

    # Generate a summary using Ollama
    if not content.strip():
        typer.echo("No content to summarize")
        summary = {
            "title": "No Content",
            "tldr": "No transcript available",
            "items": ["No content", "No content", "No content"],
            "details": "No transcript content was provided for summarization.",
        }
    else:
        # Generate English summary first
        summary_text = llm.invoke(
            """
            Summarize the following transcription giving a JSON output containing
                - "title": Catchy title to summarise the entire transcript
                - "tldr": tldr-style "tagline"
                - "items": A JSON array of three strings representing the need-to-know most interesting bits of information
                - "details": A single paragraph elaborating or going into a little more detail as required
            """
            + f"""Here's the transcript:

            {content}

            Your JSON MUST be valid! You must ONLY provide the raw JSON. JSON file:

            """
        )

        # Try to find JSON in the response
        json_str = ""
        if "{" in summary_text and "}" in summary_text:
            # Find the last closing brace to handle nested objects
            start = summary_text.find("{")
            end = summary_text.rfind("}") + 1
            json_str = summary_text[start:end]
        else:
            json_str = summary_text.strip()

        typer.echo(
            f"JSON length: {len(json_str)}, content: '{json_str[:MAX_PREVIEW_LENGTH]}...'"
            if len(json_str) > MAX_PREVIEW_LENGTH
            else f"JSON length: {len(json_str)}, content: '{json_str}'"
        )

        try:
            summary = json.loads(json_str)
            # Validate required fields
            required_fields = ["title", "tldr", "items", "details"]
            for field in required_fields:
                if field not in summary:
                    _validate_summary_field(field)

            # Ensure items is a list with at least some content
            if not isinstance(summary["items"], list):
                summary["items"] = ["No items", "No items", "No items"]
            elif len(summary["items"]) < MIN_ITEMS_COUNT:
                while len(summary["items"]) < MIN_ITEMS_COUNT:
                    summary["items"].append("")

        except (json.JSONDecodeError, ValueError) as e:
            typer.echo(f"Error parsing JSON: {e}")

            # Try to extract any useful content from partial JSON
            fallback_title = "Parse Error"
            fallback_tldr = "Failed to parse LLM response"

            # Look for partial title/tldr in the response
            if '"title"' in json_str:
                try:
                    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', json_str)
                    if title_match and title_match.group(1).strip():
                        fallback_title = title_match.group(1)
                except Exception:
                    pass

            summary = {
                "title": fallback_title,
                "tldr": fallback_tldr,
                "items": ["JSON parse error", "Check LLM response", "Using fallback"],
                "details": "The LLM response could not be parsed as valid JSON.",
            }

    # Build English-only markdown summary
    english_markdown = f"""# Summary

### {summary["title"]}

_**tldr:** {summary["tldr"]}_

"""
    for bullet in summary["items"]:
        if bullet:
            english_markdown += f"- {bullet}\n"

    english_markdown += f"""
{summary["details"]}
"""

    # Always write English summary to output_filepath
    typer.echo(english_markdown)
    with Path(output_filepath).open("w") as f:
        f.write(english_markdown)

    # Optionally write translated summary to translated_summary.txt
    translator = translator_manager.get_translator()
    translated_summary_path = Path("translated_summary.txt")
    japanese_markdown = None

    if translator and translator is not False:
        try:
            typer.echo("Translating summary to Japanese...")
            title_ja = translator.translate_text(summary["title"], target_lang="JA").text
            tldr_ja = translator.translate_text(summary["tldr"], target_lang="JA").text
            items_ja = [
                translator.translate_text(item, target_lang="JA").text
                for item in summary["items"]
                if item
            ]
            details_ja = translator.translate_text(summary["details"], target_lang="JA").text

            japanese_markdown = f"""# 要約(日本語)

### {title_ja}

_**tldr:** {tldr_ja}_

"""
            for bullet in items_ja:
                if bullet:
                    japanese_markdown += f"- {bullet}\n"

            japanese_markdown += f"""
{details_ja}
"""
            typer.echo("Translation complete!")
        except Exception as e:
            typer.echo(f"Translation error: {e}")
            japanese_markdown = ""
    else:
        japanese_markdown = ""

    # Always write file, even if empty, so UI can read it safely
    with translated_summary_path.open("w") as f:
        f.write(japanese_markdown)


if __name__ == "__main__":
    typer.run(main)
