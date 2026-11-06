"""Converte CSVs em Parquet intermediário, sem harmonização ou validação."""

import argparse
from pathlib import Path


def plan(entrada: Path, saida: Path) -> list[tuple[Path, Path]]:
    entrada, saida = Path(entrada).resolve(), Path(saida).resolve()
    raw = Path("data/raw").resolve()
    if saida == raw or raw in saida.parents:
        raise ValueError("A saída não pode ficar em data/raw")
    if not entrada.exists():
        raise ValueError(f"Entrada não encontrada: {entrada}")
    if entrada.is_dir():
        if saida == entrada or entrada in saida.parents:
            raise ValueError("A saída não pode ficar dentro da pasta de entrada")
        arquivos = sorted(p for p in entrada.glob("*.csv") if p.is_file())
    elif entrada.is_file() and entrada.suffix.lower() == ".csv":
        if saida == entrada.parent or entrada.parent in saida.parents:
            raise ValueError("A saída não pode ficar na pasta de entrada")
        arquivos = [entrada]
    else:
        raise ValueError("Informe um CSV ou uma pasta contendo CSVs")
    if not arquivos:
        raise ValueError(f"Nenhum CSV encontrado em {entrada}")
    plano = [(p, saida / (p.stem + ".parquet")) for p in arquivos]
    if len({str(dest).casefold() for _, dest in plano}) != len(plano):
        raise ValueError("Há nomes de saída duplicados")
    existentes = [str(dest) for _, dest in plano if dest.exists()]
    if existentes:
        raise FileExistsError(f"Arquivos de saída já existem; escolha outra pasta: {', '.join(existentes)}")
    return plano


def convert(entrada: Path, saida: Path) -> list[Path]:
    plano = plan(entrada, saida)
    try:
        import pandas as pd
        import pyarrow  # noqa: F401; conferir o mecanismo antes de criar arquivos
    except ImportError as exc:
        raise RuntimeError("Instale as dependências: python -m pip install pandas pyarrow") from exc
    Path(saida).mkdir(parents=True, exist_ok=True)
    resultados = []
    for origem, destino in plano:
        # CSV não informa tipos: manter campos como texto evita inferir categorias
        # ou converter códigos como NA em valores ausentes sem documentação.
        tabela = pd.read_csv(origem, dtype=str, keep_default_na=False, skip_blank_lines=False)
        with destino.open("xb") as arquivo:
            try:
                tabela.to_parquet(arquivo, engine="pyarrow", index=False)
            except Exception:
                arquivo.close()
                destino.unlink()
                raise
        resultados.append(destino)
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path("Dados"), help="CSV ou pasta de CSVs (padrão: Dados)")
    parser.add_argument("--saida", type=Path, default=Path("data/interim/parquet"), help="Pasta de destino")
    args = parser.parse_args()
    try:
        resultados = convert(args.entrada, args.saida)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Erro: {exc}\n")
    for arquivo in resultados:
        print(f"Criado: {arquivo}")
    print("Conversão concluída. Arquivos intermediários não estão harmonizados nem validados.")


if __name__ == "__main__":
    main()
