"""Carregamento restrito a artefatos locais gerados pelo projeto e verificados por hash."""

import json
import hashlib
import inspect
from importlib.metadata import version
from pathlib import Path

from mindscreen.harmonizacao import sha256
from mindscreen.dados_validados import PROJECT_ROOT

MODELS_ROOT = PROJECT_ROOT / "models"


def preprocessing_signature():
    from mindscreen.treinamento import categorical_text
    return hashlib.sha256(inspect.getsource(categorical_text).encode("utf-8")).hexdigest()


def read_registry(path=Path("models/experimentos/registro.json")):
    path = Path(path).resolve()
    root = MODELS_ROOT.resolve()
    if root not in path.parents:
        raise ValueError("Registro de modelos fora da pasta autorizada")
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("origem") != "mindscreen-treinamento-local-v1":
        raise ValueError("Origem do registro de modelos não reconhecida")
    return registry


def verified_path(registry_path, key, expected_dataset_sha=None):
    path = Path(registry_path).resolve()
    registry = read_registry(path)
    if expected_dataset_sha is not None and registry["dataset_sha256"] != expected_dataset_sha:
        raise ValueError("Modelos e dataset pertencem a execuções diferentes")
    entry = registry["artefatos"][key]
    artifact = (path.parent / entry["arquivo"]).resolve()
    if path.parent not in artifact.parents or artifact.suffix != ".joblib":
        raise ValueError("Caminho de artefato não autorizado")
    if sha256(artifact) != entry["sha256"]:
        raise ValueError("Integridade do modelo não confirmada")
    return artifact, entry


def load_model(registry_path, key, expected_dataset_sha=None):
    # Não oferece uploads: o registro e os arquivos devem provir da execução local
    # confiável. Hash detecta alteração, mas não autentica um autor desconhecido.
    artifact, _ = verified_path(registry_path, key, expected_dataset_sha)
    registry = read_registry(registry_path)
    if registry["preprocessamento_sha256"] != preprocessing_signature():
        raise ValueError("Código de pré-processamento diferente do registrado")
    experiment = key.split("/", 1)[0]
    for package in ("scikit-learn", "xgboost", "joblib", "numpy"):
        expected = registry["treinamento"][experiment]["versoes"][package]
        if expected != version(package):
            raise ValueError("Versões do ambiente não correspondem ao treinamento")
    import joblib
    model = joblib.load(artifact)
    expected_features = registry["artefatos"][key]["preditores"]
    if list(model.feature_names_in_) != expected_features or set(model.classes_) != {0, 1}:
        raise ValueError("Contrato do pipeline não corresponde ao registro")
    return model
