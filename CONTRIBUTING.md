# Contributing to PaperQA

Thanks for helping improve PaperQA. Small, focused contributions are easiest to review.

## Set up the project

```bash
git clone https://github.com/SLEEPYBQ/PaperQA.git
cd PaperQA
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` only if your local tooling loads dotenv files. Never commit API keys, PDFs containing private data, raw model responses, or generated workbooks.

## Make a change

1. Open an issue first for changes to output formats, question schemas, or pipeline behavior.
2. Keep pull requests focused on one problem.
3. Update the README when a command, default, or user-facing workflow changes.
4. Include a small reproducible example for bug fixes. Do not include copyrighted papers.

Before opening a pull request, run the lightweight checks that apply to your change:

```bash
python -m compileall main.py config.py question_loader.py query_engine.py pdf_converter.py utils.py web_app.py
python main.py --help
```

Full PDF conversion and paid LLM calls are not expected for documentation-only changes.

## Question configurations

New extraction schemas belong in `questions/`. Every question needs a unique identifier, a readable display name, and a prompt that explains what counts as evidence. Prefer source-grounded questions whose answers can be checked against the paper.

## Reporting security issues

Do not open a public issue for leaked credentials or vulnerabilities that expose private documents. Contact the maintainer privately through the email address listed on their GitHub profile.
