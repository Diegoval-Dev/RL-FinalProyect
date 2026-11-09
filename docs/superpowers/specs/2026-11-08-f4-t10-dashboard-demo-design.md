# F4-T10 Dashboard and Demo Design

## Goal

Provide a local Streamlit demo that shows live WAF decisions and the project's recorded experiment results, with every displayed observation traceable to either the running lab or a saved run.

## Data and interaction

- Run Streamlit through a separate Compose overlay (`dashboard/docker-compose.yml`) attached to the isolated lab network and a UI bridge, needed for Docker's host port publishing. The base lab Compose file retains only internal networks and no published ports. Only the dashboard joins the UI bridge, and only `127.0.0.1:8501` is published on the host. `make demo` starts the lab and service and prints the local URL.
- The live tab generates a deterministic `test` session from the frozen EXP-R1 plan. A user chooses `DEF-REF-1` or the F4-T08 champion and benign or `ATK-REF-1` traffic. `DefenderEnv(backend="real")` probes the live lab; the dashboard records each defender action and the PL2 ModSecurity decision for the same request. It labels run/source identities and never presents this as a new experiment result.
- The results tab reads only versioned summary CSVs: EXP-I1 TPR curves, EXP-H1 query curve, EXP-I2 cross-play matrix, RQ5 summary, and EXP-R1 gaps. Missing or malformed files produce a clear error instead of example values.
- The video is a short MP4 generated deterministically from EXP-I1's versioned TPR curve. It is labeled with the source experiment and SHA, embedded in Streamlit, and regenerable with a command. No fabricated frames or metrics.

## Boundaries

- No training, checkpoint selection, or writes to experiment summaries.
- Live samples are bounded to one session and a maximum number of displayed requests. They use real backend calls and show source, seed, session ID, and timestamp. They are not added to EXP-R1's statistical results.
- The dashboard's result loaders validate required columns and source SHA. The video script uses the same loader.
- Streamlit is a `demo` dependency group; the lab runner's existing dependencies remain unchanged. Docker builds a dashboard image from the runner base plus that group.

## Acceptance

`make demo` starts healthy lab containers and a reachable Streamlit page at localhost. A live sample shows defender and ModSecurity decisions sourced from real lab responses. Charts, matrix, and video read saved run data. Unit tests cover data validation and live sample boundaries; lint and the full suite pass.
