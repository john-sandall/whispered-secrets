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
from pathlib import Path

import typer
from langchain_ollama import OllamaLLM

MAX_PREVIEW_LENGTH = 200

# Translation client (loaded lazily)
_translator = None

def get_translator():
    """Lazy load the DeepL translator."""
    global _translator
    if _translator is None:
        api_key = os.getenv("DEEPL_API_KEY")
        if api_key:
            try:
                import deepl
                typer.echo("Initializing DeepL translator...")
                _translator = deepl.Translator(api_key)
                # Test the API key
                usage = _translator.get_usage()
                if usage.character.limit:
                    chars_used = usage.character.count
                    chars_limit = usage.character.limit
                    typer.echo(f"DeepL API connected! ({chars_used:,}/{chars_limit:,} characters used)")
                else:
                    typer.echo("DeepL API connected!")
            except ImportError:
                typer.echo("Warning: deepl library not installed. Translation disabled.")
                typer.echo("Install with: pip install deepl")
                _translator = False
            except Exception as e:
                typer.echo(f"DeepL initialization error: {e}")
                typer.echo("Please check your DEEPL_API_KEY environment variable")
                _translator = False
        else:
            typer.echo("Note: Set DEEPL_API_KEY environment variable for Japanese translation")
            _translator = False
    return _translator


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
                    raise ValueError(f"Missing required field: {field}")

            # Ensure items is a list with at least some content
            if not isinstance(summary["items"], list):
                summary["items"] = ["No items", "No items", "No items"]
            elif len(summary["items"]) < 3:
                while len(summary["items"]) < 3:
                    summary["items"].append("")

        except (json.JSONDecodeError, ValueError) as e:
            typer.echo(f"Error parsing JSON: {e}")

            # Try to extract any useful content from partial JSON
            fallback_title = "Parse Error"
            fallback_tldr = "Failed to parse LLM response"

            # Look for partial title/tldr in the response
            if '"title"' in json_str:
                try:
                    import re
                    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', json_str)
                    if title_match and title_match.group(1).strip():
                        fallback_title = title_match.group(1)
                except:
                    pass

            summary = {
                "title": fallback_title,
                "tldr": fallback_tldr,
                "items": ["JSON parse error", "Check LLM response", "Using fallback"],
                "details": "The LLM response could not be parsed as valid JSON.",
            }

    # Translate to Japanese if available
    translator = get_translator()
    japanese_summary = {}

    if translator and translator is not False:
        try:
            typer.echo("Translating summary to Japanese...")

            # Translate each field using DeepL
            japanese_summary["title"] = translator.translate_text(
                summary["title"], target_lang="JA"
            ).text

            japanese_summary["tldr"] = translator.translate_text(
                summary["tldr"], target_lang="JA"
            ).text

            # Translate items list
            japanese_summary["items"] = []
            for item in summary["items"]:
                if item:  # Skip empty items
                    translated = translator.translate_text(item, target_lang="JA").text
                    japanese_summary["items"].append(translated)

            japanese_summary["details"] = translator.translate_text(
                summary["details"], target_lang="JA"
            ).text

            typer.echo("Translation complete!")
        except Exception as e:
            typer.echo(f"Translation error: {e}")
            japanese_summary = None
    else:
        japanese_summary = None

    # Create side-by-side markdown format
    markdown = f"""# Summary / 要約

## English Version

### {summary["title"]}

_**tldr:** {summary["tldr"]}_

"""
    for bullet in summary["items"]:
        if bullet:  # Skip empty items
            markdown += f"- {bullet}\n"

    markdown += f"""
{summary["details"]}

---

## Japanese Version / 日本語版

"""

    if japanese_summary:
        markdown += f"""### {japanese_summary["title"]}

_**tldr:** {japanese_summary["tldr"]}_

"""
        for bullet in japanese_summary["items"]:
            if bullet:  # Skip empty items
                markdown += f"- {bullet}\n"

        markdown += f"""
{japanese_summary["details"]}
"""
    else:
        markdown += "_Translation not available / 翻訳は利用できません_\n"

    typer.echo(markdown)
    with Path(output_filepath).open("w") as f:
        f.write(markdown)


if __name__ == "__main__":
    typer.run(main)
