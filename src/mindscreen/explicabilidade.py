"""SHAP da classe 1 com verificação de aditividade e agrupamento por variável original."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from mindscreen.artefatos import load_model, read_registry
from mindscreen.avaliacao import positive_probability
from mindscreen.dados_validados import TARGETS, load_dataset, safe_output


def transformed_groups(preprocessor):
    groups = []
    for name, transformer, columns in preprocessor.transformers_:
        if name == "remainder":
            continue
        if name == "categoricas":
            for column, categories in zip(columns, transformer.named_steps["encode"].categories_):
                groups.extend([column] * len(categories))
        else:
            groups.extend(columns)
    return groups


def class_one_values(values, bases, classes):
    values, bases = np.asarray(values), np.asarray(bases)
    classes = list(classes)
    if set(classes) != {0, 1}:
        raise ValueError("SHAP exige classe positiva 1 identificável")
    if values.ndim == 3:
        return values[:, :, classes.index(1)], bases[:, classes.index(1)]
    if values.ndim != 2 or classes[1] != 1:
        raise ValueError("Formato SHAP não permite identificar com segurança a classe 1")
    return values, bases.reshape(-1)


def explain_pipeline(pipeline, background, sample, seed=42):
    import shap
    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    preprocess, estimator = pipeline.named_steps["preprocess"], pipeline.named_steps["model"]
    if isinstance(estimator, DummyClassifier):
        raise ValueError("Baseline constante: não há contribuições de atributos a explicar")
    def dense(frame):
        array = preprocess.transform(frame)
        return np.asarray(array.toarray() if hasattr(array, "toarray") else array, dtype=float)
    Z, reference = dense(sample), dense(background)
    groups = transformed_groups(preprocess)
    if Z.shape[1] != len(groups):
        raise ValueError("Mapeamento de colunas transformadas inconsistente")
    fallback = None
    if isinstance(estimator, LogisticRegression):
        explanation = shap.LinearExplainer(estimator, reference)(Z)
        values, bases = class_one_values(explanation.values, explanation.base_values, estimator.classes_)
        expected = estimator.decision_function(Z)
        unit, method = "log-odds da classe 1", "LinearExplainer"
    else:
        try:
            explanation = shap.TreeExplainer(estimator, reference, model_output="probability", feature_perturbation="interventional")(Z)
            values, bases = class_one_values(explanation.values, explanation.base_values, estimator.classes_)
            unit, method = "score de probabilidade não calibrada da classe 1", "TreeExplainer interventional"
        except (ValueError, TypeError, NotImplementedError) as exc:
            fallback = type(exc).__name__
            explainer = shap.Explainer(lambda matrix: positive_probability(estimator, matrix), reference, algorithm="permutation", seed=seed)
            explanation = explainer(Z, max_evals=2 * Z.shape[1] + 1)
            values, bases = np.asarray(explanation.values), np.asarray(explanation.base_values).reshape(-1)
            unit, method = "score de probabilidade não calibrada da classe 1", "PermutationExplainer (fallback)"
        expected = positive_probability(pipeline, sample)
    if not np.allclose(bases + values.sum(axis=1), expected, atol=2e-5, rtol=2e-5):
        raise ValueError("SHAP falhou na verificação de aditividade para a classe 1")
    features = list(dict.fromkeys(groups))
    grouped = np.column_stack([values[:, np.array(groups) == feature].sum(axis=1) for feature in features])
    return {"values": grouped, "base_values": bases, "features": features, "expected": np.asarray(expected),
            "unidade": unit, "metodo": method, "fallback": fallback, "max_erro_aditividade": float(np.max(np.abs(bases + values.sum(axis=1) - expected)))}


def beeswarm_offsets(x):
    # Empacota pontos em faixas de valores para reduzir sobreposição, sem aleatoriedade.
    bins = np.floor((x - np.min(x)) / max(float(np.ptp(x)), 1e-12) * 30).astype(int)
    offsets = np.zeros(len(x))
    for b in np.unique(bins):
        indexes = np.flatnonzero(bins == b)
        n = len(indexes)
        positions = np.array([0 if j == 0 else ((j + 1) // 2) * (1 if j % 2 else -1) for j in range(n)])
        offsets[indexes] = positions / max(n // 2, 1) * 0.32
    return offsets


def save_figure(figure, path):
    figure.update_layout(template="plotly_white", font={"family": "Arial"}, margin={"l": 30, "r": 25, "t": 65, "b": 40})
    figure.write_html(path.with_suffix(".html"), include_plotlyjs="directory")
    path.with_suffix(".json").write_text(figure.to_json(), encoding="utf-8")


def run(manifest_path, registry_path, output, sample_size=128, background_size=64, seed=42):
    manifest, frame = load_dataset(manifest_path)
    registry, output = read_registry(registry_path), safe_output(output)
    output.mkdir(parents=True, exist_ok=True)
    summary = {"dataset_sha256": manifest["sha256"], "classe_explicada": 1, "semente": seed, "targets": {},
               "limitacoes": "SHAP explica a função do modelo e sua referência de desenvolvimento; não é causalidade, efeito de intervenção ou diagnóstico. Atribuições dependem da correlação entre atributos, agrupamento de one-hot e background. Compare rankings entre modelos; magnitudes em escalas diferentes não são diretamente comparáveis."}
    for target in TARGETS:
        key = registry["selecionados"]["A/" + target]
        model = load_model(registry_path, key, manifest["sha256"])
        features = registry["artefatos"][key]["preditores"]
        dev = frame.loc[frame.ano.lt(2024) & frame[target].notna(), features]
        test = frame.loc[frame.ano.eq(2024) & frame[target].notna(), features]
        background = dev.sample(min(background_size, len(dev)), random_state=seed)
        sample = test.sample(min(sample_size, len(test)), random_state=seed).reset_index(drop=True)
        try:
            result = explain_pipeline(model, background, sample, seed)
        except (ValueError, TypeError, NotImplementedError) as exc:
            summary["targets"][target] = {"modelo": key, "disponivel": False, "motivo": type(exc).__name__}
            continue
        values, names = result["values"], result["features"]
        importance = pd.DataFrame({"variavel": names, "media_absoluta_shap": np.abs(values).mean(axis=0)}).sort_values("media_absoluta_shap", ascending=False)
        importance.to_csv(output / f"{target}_importancia.csv", index=False, encoding="utf-8-sig")
        fig = go.Figure(go.Bar(x=importance.media_absoluta_shap, y=importance.variavel, orientation="h", marker_color="#6754bb"))
        fig.update_layout(title=f"Importância SHAP — {target}", xaxis_title=result["unidade"], yaxis={"autorange": "reversed"})
        save_figure(fig, output / f"{target}_importancia")
        swarm = go.Figure()
        ordered = importance.variavel.tolist()
        for i, name in enumerate(ordered):
            x = values[:, names.index(name)]
            colors = pd.to_numeric(sample[name], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
            low, high = np.nanmin(colors), np.nanmax(colors)
            colors = (colors - low) / max(high - low, 1e-12)
            swarm.add_trace(go.Scattergl(x=x, y=i + beeswarm_offsets(x), mode="markers", name=name,
                                         marker={"size": 7, "color": colors, "colorscale": "RdBu_r", "cmin": 0, "cmax": 1, "opacity": 0.75},
                                         text=sample[name].astype(str), hovertemplate=name + "<br>Valor: %{text}<br>SHAP: %{x:.4f}<extra></extra>", showlegend=False))
        swarm.update_layout(title=f"Beeswarm SHAP — {target} (classe 1)", yaxis={"tickvals": list(range(len(ordered))), "ticktext": ordered, "autorange": "reversed"}, xaxis_title=result["unidade"])
        save_figure(swarm, output / f"{target}_beeswarm")
        one = values[0]
        individual = go.Figure(go.Bar(x=one, y=names, orientation="h", marker_color=["#bd4963" if x > 0 else "#318391" for x in one]))
        individual.update_layout(title=f"Exemplo real da avaliação — {target}", xaxis_title=result["unidade"],
                                 annotations=[{"text": f"Base: {result['base_values'][0]:.4f} · saída explicada: {result['expected'][0]:.4f}", "xref": "paper", "yref": "paper", "x": 0, "y": 1.12, "showarrow": False}])
        save_figure(individual, output / f"{target}_individual")
        screen = pd.DataFrame({"categoria": sample["SCREENTIME"].astype("string").fillna("ausente"), "shap": values[:, names.index("SCREENTIME")]})
        screen_table = screen.groupby("categoria").agg(n=("shap", "size"), contribuicao_media=("shap", "mean")).reset_index()
        screen_table.to_csv(output / f"{target}_screentime.csv", index=False, encoding="utf-8-sig")
        summary["targets"][target] = {"modelo": key, "disponivel": True, "n_amostra": len(sample), "n_background": len(background),
                                      "unidade": result["unidade"], "metodo": result["metodo"], "max_erro_aditividade": result["max_erro_aditividade"],
                                      "importancia": importance.to_dict("records"), "screentime": screen_table.to_dict("records"),
                                      "exemplo": {"base": float(result["base_values"][0]), "saida": float(result["expected"][0]), "valores_questionario": {c: None if pd.isna(sample.iloc[0][c]) else int(sample.iloc[0][c]) for c in names}}}
    (output / "explicabilidade.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
