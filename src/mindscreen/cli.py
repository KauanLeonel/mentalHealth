"""Interface mínima de linha de comando."""

import argparse

from mindscreen import __version__


def main() -> None:
    """Verifica se o pacote pode ser executado."""
    parser = argparse.ArgumentParser(description="CLI do MindScreen AI")
    parser.add_argument("--version", action="version", version=f"MindScreen AI {__version__}")
    parser.parse_args()
    print(f"MindScreen AI {__version__}: instalação funcionando.")


if __name__ == "__main__":
    main()
