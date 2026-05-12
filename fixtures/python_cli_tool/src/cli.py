import click

from .cleaner import normalize_rows
from .exporter import write_json
from .reporting import summarize_rows


@click.group()
def main():
    """Data Tidy command group."""


@main.command()
@click.argument("input_path")
@click.option("--uppercase", is_flag=True)
@click.option("--output-json")
def clean(input_path: str, uppercase: bool, output_json: str | None):
    rows = normalize_rows(input_path, uppercase=uppercase)
    summary = summarize_rows(rows)
    if output_json:
        write_json(rows, output_json)
    click.echo(f"cleaned_rows={summary['row_count']}")


if __name__ == "__main__":
    main()
