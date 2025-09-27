"""
Whispered Secrets.

Usage:
    ollama serve
    python -m demo.summarize 'transcription_output.txt' "summary.txt"
    python -m demo.summarize --help
"""

import json
from pathlib import Path

import typer
from langchain_ollama import OllamaLLM

MAX_PREVIEW_LENGTH = 200


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
        summary_text = llm.invoke(
            """
            You must output EVERYTHING in Japanese.

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
        if "{" in summary_text and "}" in summary_text:
            # Find the last closing brace to handle nested objects
            start = summary_text.find("{")
            end = summary_text.rfind("}") + 1
            summary_text = summary_text[start:end]
        else:
            summary_text = ""

        typer.echo(
            f"JSON length: {len(summary_text)}, content: '{summary_text[:MAX_PREVIEW_LENGTH]}...'"
            if len(summary_text) > MAX_PREVIEW_LENGTH
            else f"JSON length: {len(summary_text)}, content: '{summary_text}'"
        )

        try:
            summary = json.loads(summary_text)
        except Exception as e:
            typer.echo(f"Error parsing JSON: {e}")
            # Fallback to default values if JSON parsing fails
            summary = {
                "title": "Parse Error",
                "tldr": "Failed to parse LLM response",
                "items": ["JSON parse error", "Check LLM response", "Using fallback"],
                "details": "The LLM response could not be parsed as valid JSON.",
            }

    markdown = f"""
# {summary["title"]}

_**tldr:** {summary["tldr"]}_

"""
    for bullet in summary["items"]:
        markdown += f"""- {bullet}
"""
    markdown += f"""
{summary["details"]}
"""

    typer.echo(markdown)
    with Path(output_filepath).open("w") as f:
        f.write(markdown)


if __name__ == "__main__":
    typer.run(main)
