"""Allow `python -m src` to invoke the CLI."""

from src.cli import app

if __name__ == "__main__":
    app()
