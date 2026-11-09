"""WAF Arena local demonstration. All numbers come from runs or live lab probes."""

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from dashboard.data import i1_tpr_rows, load_results
from dashboard.live import run_live_session
from scripts.run_r1 import discover_sources
from wafarena.agents import load_checkpoint
from wafarena.defenders.driver import DefenderDriver
from wafarena.envs.backends.real import RealBackend
from wafarena.envs.defender_env import DefenderEnv
from wafarena.eval.real_gap import defender_plans

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results/summary"
SPEC = ROOT / "configs/eval/EXP-R1/real-validation.yaml"
VIDEO = ROOT / "report/video/EXP-I1_arms_race.mp4"

st.set_page_config(page_title="WAF Arena · Demo", page_icon="🛡️", layout="wide")
st.title("WAF Arena")
st.caption("SQL injection · defensa aprendida · laboratorio local aislado")

try:
    results = load_results(SUMMARY)
except (OSError, ValueError) as exc:
    st.error(f"No se pueden cargar los resúmenes versionados: {exc}")
    st.stop()

live_tab, curves_tab, matrix_tab, final_tab = st.tabs(
    ["Laboratorio en vivo", "Curvas", "Cruces", "Resultados finales"]
)

with live_tab:
    st.subheader("Decisiones sobre tráfico real del laboratorio")
    st.write(
        "Cada clic ejecuta una sesión `test` del plan EXP-R1 contra el laboratorio Docker. "
        "La comparación usa la decisión PL2 de ModSecurity observada para la misma solicitud. "
        "Esta muestra es una demostración; no se agrega a los resultados experimentales."
    )
    policy_name = st.selectbox("Defensor", ["DEF-REF-1", "selfplay-champion"])
    traffic = st.selectbox("Tráfico", ["Benigno", "Ataque ATK-REF-1"])
    max_requests = st.slider("Solicitudes máximas", 1, 20, 8)
    if st.button("Ejecutar sesión en vivo", type="primary"):
        backend = None
        try:
            with st.spinner("Consultando ModSecurity y el oráculo del laboratorio…"):
                spec = yaml.safe_load(SPEC.read_text())
                sources = discover_sources(spec)
                plans = defender_plans(
                    spec["defender_plan_seeds"][1], spec["defender_env_seed_starts"][1]
                )
                candidates = plans["ATK-REF-1"]
                plan = next(p for p in candidates if p.is_attack == (traffic != "Benigno"))
                backend = RealBackend()
                env = DefenderEnv(
                    backend=backend,
                    attacker={"type": "checkpoint", "path": str(sources["ATK-REF-1"]["path"])},
                    split="test",
                    attack_split="test",
                )
                policy = DefenderDriver(load_checkpoint(sources[policy_name]["path"]))
                sample = run_live_session(env, policy, plan, max_requests=max_requests)
                sample["timestamp_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
                sample["policy_source"] = sources[policy_name]["source_run_id"]
                sample["attacker_source"] = sources["ATK-REF-1"]["source_run_id"]
                st.session_state["live_sample"] = sample
        except Exception as exc:
            st.error(f"No se pudo ejecutar la sesión real: {exc}")
        finally:
            if backend is not None:
                backend.close()
    if "live_sample" in st.session_state:
        sample = st.session_state["live_sample"]
        st.dataframe(pd.DataFrame(sample["events"]), hide_index=True, width="stretch")
        st.caption(
            f"Fuente: laboratorio en vivo · {sample['timestamp_utc']} · plan EXP-R1 "
            f"s1/{sample['plan_ref']} (semilla {sample['plan_seed']}) · "
            f"defensor {sample['policy_source']} · atacante {sample['attacker_source']} · "
            f"sesión {'completa' if sample['complete'] else 'limitada por la demo'}"
        )

with curves_tab:
    st.subheader("Aprendizaje y planificación")
    reference = st.selectbox("Referencia de ataque", ["ATK-REF-0", "ATK-REF-1"])
    tpr = pd.DataFrame(i1_tpr_rows(results["EXP-I1_curve.csv"], reference))
    if tpr.empty:
        st.error("EXP-I1 no contiene la curva TPR solicitada")
    else:
        wide = tpr.pivot(index="generation", columns="condition", values="tpr").reset_index()
        st.line_chart(
            wide, x="generation", y=["naive", "pool"], x_label="Generación", y_label="TPR"
        )
        st.caption("Fuente: EXP-I1_curve.csv · entrenamiento eea6f78 · media de tres semillas")
    h1 = pd.DataFrame(results["EXP-H1.csv"])
    h1 = h1[h1["defender"] == "DEF-REF-1"].copy()
    h1["real_queries"] = pd.to_numeric(h1["real_queries"], errors="coerce")
    h1["er_mean"] = pd.to_numeric(h1["er_mean"], errors="coerce")
    h1 = h1.dropna(subset=["real_queries", "er_mean"])
    st.line_chart(
        h1,
        x="real_queries",
        y="er_mean",
        color="method",
        x_label="Consultas reales acumuladas",
        y_label="ER",
    )
    st.caption(
        "Fuente: EXP-H1.csv · runs 7714621 / 9d54cd2; los puntos con ER indefinida se excluyen"
    )
    if VIDEO.is_file():
        st.subheader("Carrera armamentista · EXP-I1")
        st.video(VIDEO)
        st.caption("Video generado de EXP-I1_curve.csv (eea6f78); no contiene datos simulados")

with matrix_tab:
    st.subheader("Matriz de cruces entre generaciones")
    matrix = pd.DataFrame(results["EXP-I2_matrix.csv"])
    for col in ("defender_generation", "attacker_generation", "mean_er"):
        matrix[col] = pd.to_numeric(matrix[col])
    pivot = matrix.pivot(
        index="defender_generation", columns="attacker_generation", values="mean_er"
    )
    st.dataframe(pivot.style.format("{:.4f}").background_gradient(cmap="Reds"), width="stretch")
    st.caption("Fuente: EXP-I2_matrix.csv · evaluación 85524f0 · 200 episodios por cruce y semilla")

with final_tab:
    st.subheader("Generalización final · RQ5")
    rq5 = pd.DataFrame(results["RQ5_final.csv"])
    st.dataframe(
        rq5[["exp_id", "attacker", "defender", "tpr", "fpr", "er_d", "eval_run_ids"]],
        hide_index=True,
        width="stretch",
    )
    st.caption("Fuente: RQ5_final.csv · evaluación bf14912; PL2 reutiliza d9d7d49")
    st.subheader("Brecha entre modo rápido y real · EXP-R1")
    gap = pd.DataFrame(results["EXP-R1_gap.csv"])
    st.dataframe(
        gap[["agent", "metric", "n_defined", "fast_mean", "real_mean", "gap_mean"]],
        hide_index=True,
        width="stretch",
    )
    st.caption("Fuente: EXP-R1_gap.csv · evaluación c1d2f4d · celdas vacías = métrica indefinida")
