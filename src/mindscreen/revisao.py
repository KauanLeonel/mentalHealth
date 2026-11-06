"""Verificação integrada dos dados e artefatos, sem refazer treinamentos."""

import argparse
from datetime import datetime
import gc
import json
import inspect
from pathlib import Path
from time import perf_counter

import pandas as pd

from mindscreen.ambiente import peak_memory_mb
from mindscreen.artefatos import load_model, read_registry
from mindscreen.auditoria import audit, write_reports
from mindscreen.dados_validados import load_dataset, safe_output
from mindscreen.harmonizacao import run as harmonize, sha256, snapshot
from mindscreen.inferencia import predict_profile


def run(output=Path("reports/revisao")):
    output = safe_output(output)
    source = Path("Dados").resolve()
    if output == source or source in output.parents:
        raise ValueError("Relatórios devem ficar fora da pasta de origem")
    output.mkdir(parents=True, exist_ok=True)
    temporary = Path(".tmp") / ("revisao-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    before = {**snapshot("Dados"), **snapshot("data/raw")}
    start = perf_counter()
    result = {"inicio": datetime.now().isoformat(), "checagens": {}}
    manifest, original = load_dataset("data/processed/manifesto.json")
    key = {"fontes_sha256": before, "dataset_sha256": manifest["sha256"],
           "config_sha256": sha256("configs/harmonizacao.json"), "codigo_harmonizacao_sha256": sha256(inspect.getsourcefile(harmonize))}
    previous_path = output / "integracao.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
    if previous.get("chave_revisao_dados") == key:
        result["validacao_dados_reutilizada_apos_conferir_hashes"] = True
        result["checagens"].update({"auditoria_cinco_edicoes": True, "harmonizacao_reproduz_dataset": True})
    else:
        inventory = audit(Path("Dados"))
        write_reports(inventory, output / "auditoria")
        if inventory["erros"] or len(inventory["arquivos"]) != 5:
            raise ValueError("Inventário de cinco edições não confirmado")
        result["checagens"]["auditoria_cinco_edicoes"] = True
        result["tempo_auditoria_s"] = perf_counter() - start
        check_start = perf_counter()
        harmonize(Path("Dados"), temporary / "processed", temporary / "reports", Path("configs/harmonizacao.json"))
        _, regenerated = load_dataset(temporary / "processed/manifesto.json")
        pd.testing.assert_frame_equal(original, regenerated)
        result["checagens"]["harmonizacao_reproduz_dataset"] = True
        result["tempo_harmonizacao_s"] = perf_counter() - check_start
    result["chave_revisao_dados"] = key
    registry_path = Path("models/experimentos/registro.json")
    if registry_path.exists():
        registry = read_registry(registry_path)
        for artifact_key in registry["artefatos"]:
            model = load_model(registry_path, artifact_key, manifest["sha256"])
            del model
            gc.collect()
        result["modelos_verificados"] = len(registry["artefatos"])
        result["checagens"]["integridade_contrato_versoes_modelos"] = True
        rules = json.loads(Path("configs/harmonizacao.json").read_text(encoding="utf-8"))
        profile = {"SC_AGE_YEARS": 12, "SCREENTIME": 3, "SC_SEX": 1, "HOURSLEEP": 4, "PHYSACTIV": 2, "MAKEFRIEND": 1}
        predictions = predict_profile(profile, manifest, rules, registry_path)
        result["checagens"]["inferencia_compartilhada_funciona"] = len(predictions) == 2
        result["status"] = "concluida"
    else:
        result["status"] = "dados_concluidos_modelos_pendentes"
    result["checagens"]["originais_inalterados"] = before == {**snapshot("Dados"), **snapshot("data/raw")}
    if not all(result["checagens"].values()):
        raise ValueError("Falha nas verificações de integração")
    result["tempo_total_s"] = perf_counter() - start
    result["pico_memoria_processo_revisao_mb"] = peak_memory_mb()
    result["tamanho_modelos_mb"] = round(sum(p.stat().st_size for p in Path("models/experimentos").rglob("*.joblib")) / 1024**2, 2)
    result["tamanho_dataset_mb"] = round(Path("data/processed/dataset.parquet").stat().st_size / 1024**2, 2)
    (output / "integracao.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/revisao"))
    print(json.dumps(run(parser.parse_args().output), indent=2, ensure_ascii=False))
