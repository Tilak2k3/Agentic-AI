"""Manual runner for CR agent."""

from __future__ import annotations

import argparse

from agentic_ai.cr_agent import run_cr_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate CR document and Jira items.")
    parser.add_argument("--meeting", required=True, help="Meeting recording path (text or audio).")
    parser.add_argument("--scope", required=True, help="Scope/SOW document path.")
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for generated outputs (cr_document.md, jira_items.json).",
    )
    parser.add_argument(
        "--no-jira",
        action="store_true",
        help="Only generate CR document; skip Jira creation.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use deterministic CR/Jira templates instead of the HF router LLM agent.",
    )
    args = parser.parse_args()
    result = run_cr_agent(
        meeting_path=args.meeting,
        scope_path=args.scope,
        output_dir=args.output_dir,
        create_jira=not args.no_jira,
        use_llm=not args.no_llm,
    )
    print(f"CR document: {result.cr_file}")
    print(f"LLM agent:   {result.llm_used}")
    if result.jira_output_file:
        print(f"Jira items:  {result.jira_output_file}")
        print(f"Created Jira items: {len(result.jira_items)}")


if __name__ == "__main__":
    main()

