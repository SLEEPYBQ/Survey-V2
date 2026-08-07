#!/usr/bin/env python3
"""A document-first Streamlit workspace for the PaperQA CLI pipeline."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from question_loader import QuestionLoaderError, load_questions


ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / ".paperqa_runs"
QUESTION_DIR = ROOT / "questions"


@dataclass(frozen=True)
class PipelineRun:
    """Files and process state produced by one isolated pipeline run."""

    returncode: int
    output_dir: Path
    log_text: str


def _question_configs() -> list[Path]:
    return sorted([*QUESTION_DIR.glob("*.yaml"), *QUESTION_DIR.glob("*.yml")])


def _save_uploads(files, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for uploaded_file in files:
        safe_name = Path(uploaded_file.name).name
        (destination / safe_name).write_bytes(uploaded_file.getbuffer())


def _run_pipeline(
    files,
    input_kind: str,
    question_path: Path,
    api_key: str,
    api_base: str,
    model: str,
    max_workers: int,
    on_output: Callable[[str], None] | None = None,
) -> PipelineRun:
    """Run the CLI in an isolated folder and optionally stream each log line."""
    run_dir = RUNS_DIR / uuid.uuid4().hex
    input_dir = run_dir / ("pdfs" if input_kind == "PDF" else "markdowns")
    markdown_dir = run_dir / "markdowns"
    output_dir = run_dir / "results"
    raw_dir = run_dir / "raw_responses"
    _save_uploads(files, input_dir)

    mode = "all" if input_kind == "PDF" else "query"
    command = [
        sys.executable,
        "-u",
        "main.py",
        "--mode",
        mode,
        "--questions",
        str(question_path),
        "--markdown-folder",
        str(markdown_dir),
        "--output-folder",
        str(output_dir),
        "--raw-response-folder",
        str(raw_dir),
        "--api-base",
        api_base,
        "--model",
        model,
        "--max-workers",
        str(max_workers),
        "--device",
        "auto",
        "--verbose",
    ]
    if input_kind == "PDF":
        command.extend(["--input-folder", str(input_dir)])

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    log_lines: list[str] = []
    if process.stdout is not None:
        for line in process.stdout:
            log_lines.append(line)
            if on_output is not None:
                on_output(line)

    return PipelineRun(
        returncode=process.wait(),
        output_dir=output_dir,
        log_text="".join(log_lines),
    )


def _section_header(number: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="step-heading">
          <span class="step-number">{number}</span>
          <div>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _file_label(count: int, input_kind: str) -> str:
    suffix = "file" if count == 1 else "files"
    return f"{count} {input_kind} {suffix} ready"


st.set_page_config(
    page_title="PaperQA",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --pq-ink: #37352f;
        --pq-muted: #787774;
        --pq-faint: #9b9a97;
        --pq-canvas: #f7f6f3;
        --pq-surface: #ffffff;
        --pq-soft: #f1f1ef;
        --pq-blue: #2383e2;
        --pq-blue-active: #1b6fbd;
        --pq-line: rgba(55, 53, 47, 0.16);
        --pq-success: #448361;
        --pq-error: #d44c47;
      }

      html, body, [class*="css"] {
        color: var(--pq-ink);
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
          "Segoe UI", sans-serif;
      }
      .stApp { background: var(--pq-canvas); }
      [data-testid="stDecoration"] { display: none; }
      [data-testid="stHeader"] { background: rgba(247, 246, 243, .88); }
      [data-testid="stToolbar"] { right: 1rem; }
      .block-container {
        max-width: 880px;
        padding: 4.6rem 3rem 6rem;
      }

      section[data-testid="stSidebar"] {
        background: var(--pq-soft);
        border-right: 1px solid var(--pq-line);
      }
      section[data-testid="stSidebar"] .block-container {
        padding: 2rem 1.25rem;
      }

      .page-icon {
        align-items: center;
        background: #e8e7e4;
        border-radius: 8px;
        display: inline-flex;
        font-size: 1.6rem;
        height: 52px;
        justify-content: center;
        margin-bottom: 1.25rem;
        width: 52px;
      }
      .page-title {
        color: var(--pq-ink);
        font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
        font-size: clamp(2.5rem, 6vw, 3.75rem);
        font-weight: 700;
        letter-spacing: -.045em;
        line-height: 1.02;
        margin: 0;
      }
      .page-lede {
        color: var(--pq-muted);
        font-size: 1.02rem;
        line-height: 1.65;
        margin: .85rem 0 .55rem;
        max-width: 650px;
      }
      .page-meta {
        color: var(--pq-faint);
        font-size: .75rem;
        font-weight: 600;
        letter-spacing: .06em;
        text-transform: uppercase;
      }
      .page-rule {
        border: 0;
        border-top: 1px solid var(--pq-line);
        margin: 2rem 0 2.4rem;
      }

      .step-heading {
        align-items: flex-start;
        display: grid;
        gap: .9rem;
        grid-template-columns: 30px 1fr;
        margin: 2.2rem 0 1rem;
      }
      .step-number {
        align-items: center;
        background: var(--pq-ink);
        border-radius: 6px;
        color: white;
        display: inline-flex;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .72rem;
        font-weight: 700;
        height: 30px;
        justify-content: center;
        width: 30px;
      }
      .step-heading h2 {
        color: var(--pq-ink);
        font-size: 1.15rem;
        font-weight: 650;
        letter-spacing: -.012em;
        line-height: 1.3;
        margin: .1rem 0 .15rem;
      }
      .step-heading p {
        color: var(--pq-muted);
        font-size: .9rem;
        line-height: 1.45;
        margin: 0;
      }

      .readiness {
        background: var(--pq-surface);
        border: 1px solid var(--pq-line);
        border-radius: 12px;
        display: grid;
        gap: 0;
        margin: .5rem 0 1rem;
        overflow: hidden;
      }
      .readiness-row {
        align-items: center;
        border-bottom: 1px solid var(--pq-line);
        display: flex;
        font-size: .88rem;
        gap: .65rem;
        justify-content: space-between;
        padding: .72rem .85rem;
      }
      .readiness-row:last-child { border-bottom: 0; }
      .readiness-label { color: var(--pq-muted); }
      .readiness-value { color: var(--pq-ink); font-weight: 550; }
      .readiness-dot {
        background: var(--pq-faint);
        border-radius: 50%;
        display: inline-block;
        height: 7px;
        margin-right: .45rem;
        width: 7px;
      }
      .readiness-dot.ready { background: var(--pq-success); }

      div[data-testid="stFileUploaderDropzone"] {
        background: var(--pq-surface);
        border: 1px dashed rgba(55, 53, 47, .3);
        border-radius: 8px;
        min-height: 126px;
      }
      div[data-testid="stFileUploaderDropzone"]:hover {
        background: #fbfbfa;
        border-color: var(--pq-blue);
      }
      div[data-testid="stExpander"] {
        background: var(--pq-surface);
        border-color: var(--pq-line);
        border-radius: 8px;
      }
      div[data-testid="stAlert"] { border-radius: 6px; }
      div[data-baseweb="select"] > div,
      .stTextInput input {
        background: var(--pq-surface);
        border-color: var(--pq-line);
        border-radius: 4px;
      }
      .stButton > button, .stDownloadButton > button {
        border-radius: 8px;
        font-size: .92rem;
        font-weight: 600;
        min-height: 44px;
        transition: background-color .12s ease, border-color .12s ease,
          transform .12s ease;
      }
      .stButton > button[kind="primary"],
      .stDownloadButton > button[kind="primary"] {
        background: var(--pq-blue);
        border-color: var(--pq-blue);
      }
      .stButton > button[kind="primary"]:hover,
      .stDownloadButton > button[kind="primary"]:hover {
        background: var(--pq-blue-active);
        border-color: var(--pq-blue-active);
        transform: translateY(-1px);
      }
      .stButton > button:disabled {
        background: #e7e6e3;
        border-color: #e0dfdc;
        color: var(--pq-faint);
        opacity: 1;
        transform: none;
      }
      [data-testid="stDataFrame"] {
        background: var(--pq-surface);
        border: 1px solid var(--pq-line);
        border-radius: 8px;
        overflow: hidden;
      }
      :focus-visible {
        outline: 2px solid var(--pq-blue) !important;
        outline-offset: 2px;
      }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { transition: none !important; }
      }
      @media (max-width: 767px) {
        .block-container { padding: 3.4rem 1.15rem 4rem; }
        .page-title { font-size: 2.6rem; }
        .readiness-row { align-items: flex-start; flex-direction: column; gap: .2rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### PaperQA")
    st.caption("Model connection")
    api_key = st.text_input(
        "API key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Kept in this process and passed to the CLI through the environment.",
    )
    model = st.text_input(
        "Model",
        value=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    )
    with st.expander("Advanced settings"):
        api_base = st.text_input(
            "OpenAI-compatible base URL",
            value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        max_workers = st.slider(
            "Parallel requests",
            min_value=1,
            max_value=16,
            value=4,
            help="Lower this if your provider enforces a strict rate limit.",
        )
    st.divider()
    st.caption(
        "PDF conversion stays local. Paper content is sent to the model endpoint "
        "only when extraction starts."
    )
    st.markdown("[View source on GitHub](https://github.com/SLEEPYBQ/PaperQA)")


st.markdown(
    """
    <div class="page-icon" aria-hidden="true">📄</div>
    <h1 class="page-title">PaperQA</h1>
    <p class="page-lede">
      Turn research papers into a reviewable workbook of answers and supporting text.
      Set up one extraction run below.
    </p>
    <div class="page-meta">Local workspace · Answers remain linked to sources</div>
    <hr class="page-rule">
    """,
    unsafe_allow_html=True,
)

configs = _question_configs()
if not configs:
    st.error("No question sets found. Add a `.yaml` file to `questions/` and reload.")
    st.stop()

_section_header(
    "1",
    "Add papers",
    "Upload PDFs for the full pipeline, or Markdown to skip local conversion.",
)

input_kind = st.radio(
    "Paper format",
    ["PDF", "Markdown"],
    horizontal=True,
    label_visibility="collapsed",
)
suffixes = ["pdf"] if input_kind == "PDF" else ["md"]
files = st.file_uploader(
    f"Upload {input_kind} papers",
    type=suffixes,
    accept_multiple_files=True,
    key=f"paper-upload-{input_kind.lower()}",
    label_visibility="collapsed",
)
if files:
    st.caption(_file_label(len(files), input_kind))
    with st.expander("Review selected papers"):
        for uploaded_file in files:
            size_mb = uploaded_file.size / (1024 * 1024)
            st.markdown(f"📄 `{uploaded_file.name}` · {size_mb:.1f} MB")
else:
    st.caption(
        f"Drop one or more {input_kind} files here. Files stay in this PaperQA "
        "workspace until extraction sends their content to your configured model."
    )

_section_header(
    "2",
    "Choose what to extract",
    "Question sets define the workbook columns and the evidence requested from each paper.",
)

selected_config = st.selectbox(
    "Question set",
    configs,
    format_func=lambda path: path.stem.replace("_", " ").title(),
    label_visibility="collapsed",
)

config_is_valid = False
preview_config = None
try:
    preview_config = load_questions(selected_config)
    config_is_valid = True
    st.caption(
        f"{preview_config.survey_name} · {len(preview_config.questions)} extraction fields"
    )
    with st.expander("Review extraction fields"):
        if preview_config.survey_description:
            st.caption(preview_config.survey_description)
        for index, question in enumerate(preview_config.questions, start=1):
            st.markdown(f"**{index}. {question.display_name}**")
            st.caption(question.prompt)
except QuestionLoaderError as exc:
    st.error(f"This question set cannot be used: {exc}")

_section_header(
    "3",
    "Build the workbook",
    "PaperQA will keep this run isolated and preserve the raw model responses for review.",
)

files_ready = bool(files)
connection_ready = bool(api_key and api_base and model)
run_ready = files_ready and config_is_valid and connection_ready
file_summary = _file_label(len(files), input_kind) if files else "Add at least one paper"
schema_summary = (
    f"{len(preview_config.questions)} fields selected"
    if preview_config is not None
    else "Choose a valid question set"
)
connection_summary = "Connection configured" if connection_ready else "Add provider credentials"

st.markdown(
    f"""
    <div class="readiness" aria-label="Run readiness">
      <div class="readiness-row">
        <span class="readiness-label">Papers</span>
        <span class="readiness-value"><i class="readiness-dot {'ready' if files_ready else ''}"></i>{file_summary}</span>
      </div>
      <div class="readiness-row">
        <span class="readiness-label">Question set</span>
        <span class="readiness-value"><i class="readiness-dot {'ready' if config_is_valid else ''}"></i>{schema_summary}</span>
      </div>
      <div class="readiness-row">
        <span class="readiness-label">Model connection</span>
        <span class="readiness-value"><i class="readiness-dot {'ready' if connection_ready else ''}"></i>{connection_summary}</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

start_run = st.button(
    "Build workbook",
    type="primary",
    use_container_width=True,
    disabled=not run_ready,
)
if not run_ready:
    st.caption("Complete the items above to start extraction.")

if start_run:
    st.session_state.pop("paperqa_result_path", None)
    st.session_state.pop("paperqa_log", None)

    with st.status("Preparing an isolated run…", expanded=True) as run_status:
        live_log = st.empty()
        live_lines: deque[str] = deque(maxlen=200)

        def update_run(line: str) -> None:
            live_lines.append(line)
            recent_log = "".join(live_lines)[-12_000:]
            if "Starting PDF to Markdown conversion" in line:
                run_status.update(label="Converting papers to Markdown…")
            if "Starting document queries" in line:
                run_status.update(label="Extracting answers and sources…")
            if "Query results saved" in line:
                run_status.update(label="Writing the workbook…")
            live_log.code(recent_log, language="text")

        pipeline_run = _run_pipeline(
            files,
            input_kind,
            selected_config,
            api_key,
            api_base,
            model,
            max_workers,
            on_output=update_run,
        )
        result_path = pipeline_run.output_dir / "query_results_latest.xlsx"
        st.session_state["paperqa_log"] = pipeline_run.log_text

        if pipeline_run.returncode == 0 and result_path.exists():
            st.session_state["paperqa_result_path"] = str(result_path)
            run_status.update(
                label="Workbook ready",
                state="complete",
                expanded=False,
            )
        else:
            run_status.update(
                label="The run stopped before a workbook was created",
                state="error",
                expanded=True,
            )

result_path_value = st.session_state.get("paperqa_result_path")
run_log = st.session_state.get("paperqa_log", "")

if result_path_value:
    result_path = Path(result_path_value)
    if result_path.exists():
        import pandas as pd

        st.divider()
        _section_header(
            "✓",
            "Review the result",
            "Scan the extracted fields here, then download the full workbook for verification.",
        )
        result_frame = pd.read_excel(result_path)
        document_count = result_frame.loc[
            result_frame["content_type"] == "answer", "document"
        ].nunique()
        field_count = max(len(result_frame.columns) - 2, 0)
        st.caption(f"{document_count} papers · {field_count} extraction fields")
        st.dataframe(result_frame, use_container_width=True, hide_index=True)

        download_col, clear_col = st.columns([2, 1])
        with download_col:
            st.download_button(
                "Download Excel workbook",
                data=result_path.read_bytes(),
                file_name="paperqa_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
        with clear_col:
            if st.button("Clear result", use_container_width=True):
                st.session_state.pop("paperqa_result_path", None)
                st.session_state.pop("paperqa_log", None)
                st.rerun()

if run_log:
    with st.expander("View the complete run log"):
        st.code(run_log, language="text")
