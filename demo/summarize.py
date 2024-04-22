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
from langchain_community.llms import Ollama


def main(input_filepath: str, output_filepath: str):
    """Reads a text file and summarizes its contents using Ollama."""
    # Initialize the Ollama model
    llm = Ollama(model="llama3")

    # Read the contents of the file
    try:
        with Path.open(input_filepath, "r") as file:
            content = file.read()
    except Exception as e:
        typer.echo(f"Error reading file: {e}")
        raise typer.Exit()

    # Generate a summary using Ollama
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
    summary_text = summary_text[summary_text.find("{") : summary_text.find("}") + 1]

    typer.echo(summary_text)
    try:
        summary = json.loads(summary_text)
    except Exception as e:
        typer.echo(f"Error reading file: {e}")
        raise typer.Exit()

    markdown = f"""
# {summary['title']}

_**tldr:** {summary['tldr']}_

"""
    for bullet in summary["items"]:
        markdown += f"""- {bullet}
"""
    markdown += f"""
{summary['details']}
"""

    typer.echo(markdown)
    with Path.open(output_filepath, "w") as f:
        f.write(markdown)


if __name__ == "__main__":
    typer.run(main)
