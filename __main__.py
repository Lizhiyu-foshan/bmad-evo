"""
BMAD-EVO v4.0 CLI

Usage:
    python -m bmad_evo analyze "task description" [options]
    python -m bmad_evo pipeline --input task.json [options]
    python -m bmad_evo build "task description" [options]
"""

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))


def cmd_analyze(args):
    from api import analyze

    task = args.task
    if args.input_file:
        task = Path(args.input_file).read_text(encoding="utf-8")

    report = analyze(
        task=task,
        output_dir=args.output,
        interactive=not args.non_interactive,
        enable_data_collection=not args.no_data,
        config=_load_config(args),
    )

    if report.file_path:
        print(f"\nReport saved to: {report.file_path}")
    else:
        print(report.markdown)

    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False, default=str))

    sys.exit(0 if report.success else 1)


def cmd_pipeline(args):
    from api import pipeline

    task = args.task
    if args.input_file:
        raw = Path(args.input_file).read_text(encoding="utf-8")
        try:
            task = json.loads(raw)
        except json.JSONDecodeError:
            task = raw

    result = pipeline(
        task=task,
        project_path=args.output,
        enable_data_collection=not args.no_data,
        config=_load_config(args),
    )

    if result.output_dir:
        print(f"\nPipeline output directory: {result.output_dir}")
        print(f"  JSON metadata: pipeline_result.json")
        print(f"  Full report:   full_report.md")
        if result.output_files.get("role_outputs"):
            print(f"  Role outputs:  {len(result.output_files['role_outputs'])} files in roles/")
        if args.output_file:
            meta_path = Path(result.output_dir) / "pipeline_result.json"
            import shutil
            shutil.copy2(meta_path, args.output_file)
            print(f"  JSON copied to: {args.output_file}")
    else:
        print(result.json_str if result.json_str else json.dumps(
            result.to_dict(), indent=2, ensure_ascii=False, default=str
        ))

    sys.exit(0 if result.status == "success" else 1)


def cmd_build(args):
    from api import build

    task = args.task
    if args.input_file:
        task = Path(args.input_file).read_text(encoding="utf-8")

    result = build(
        task=task,
        output_dir=args.output,
        interactive=not args.non_interactive,
        code_language=args.language,
        config=_load_config(args),
    )

    print(f"\nBuild result: {'success' if result.success else 'failed'}")
    if result.code_files:
        print(f"Generated {len(result.code_files)} code files:")
        for f in result.code_files:
            print(f"  - {f}")
    if result.test_files:
        print(f"Generated {len(result.test_files)} test files:")
        for f in result.test_files:
            print(f"  - {f}")
    if result.file_path:
        print(f"Output directory: {result.file_path}")

    sys.exit(0 if result.success else 1)


def _load_config(args):
    config = {}
    if args.config_file:
        with open(args.config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
    if args.pass_threshold:
        config["pass_threshold"] = args.pass_threshold
    if args.max_iterations:
        config["max_iterations"] = args.max_iterations
    return config


def main():
    parser = argparse.ArgumentParser(
        prog="bmad-evo",
        description="BMAD-EVO v4.0 - Multi-Agent Analysis Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- analyze ---
    p_analyze = subparsers.add_parser("analyze", help="Terminal analysis mode (markdown report)")
    p_analyze.add_argument("task", nargs="?", help="Task description")
    p_analyze.add_argument("--input", dest="input_file", help="Read task from file")
    p_analyze.add_argument("--output", help="Output directory")
    p_analyze.add_argument("--no-data", action="store_true", help="Disable data collection")
    p_analyze.add_argument("--non-interactive", action="store_true", help="Non-interactive mode")
    p_analyze.add_argument("--json", dest="json_output", action="store_true", help="Also output JSON")
    _add_common_args(p_analyze)

    # --- pipeline ---
    p_pipeline = subparsers.add_parser("pipeline", help="Pipeline integration mode (JSON output)")
    p_pipeline.add_argument("task", nargs="?", help="Task description or JSON")
    p_pipeline.add_argument("--input", dest="input_file", help="Read task from JSON file")
    p_pipeline.add_argument("--output", help="Output directory")
    p_pipeline.add_argument("--output-file", help="Write pipeline JSON to file")
    p_pipeline.add_argument("--no-data", action="store_true", help="Disable data collection")
    _add_common_args(p_pipeline)

    # --- build ---
    p_build = subparsers.add_parser("build", help="Analysis + code generation mode")
    p_build.add_argument("task", nargs="?", help="Task description")
    p_build.add_argument("--input", dest="input_file", help="Read task from file")
    p_build.add_argument("--output", help="Output directory")
    p_build.add_argument("--lang", dest="language", default="python", help="Programming language")
    p_build.add_argument("--non-interactive", action="store_true", help="Non-interactive mode")
    _add_common_args(p_build)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if not args.task and not args.input_file:
        print(f"Error: provide a task description or --input file")
        sys.exit(1)

    commands = {
        "analyze": cmd_analyze,
        "pipeline": cmd_pipeline,
        "build": cmd_build,
    }
    commands[args.command](args)


def _add_common_args(parser):
    parser.add_argument("--config", dest="config_file", help="Custom config JSON file")
    parser.add_argument("--pass-threshold", type=int, help="Audit pass threshold (0-100)")
    parser.add_argument("--max-iterations", type=int, help="Max iterations per phase")


if __name__ == "__main__":
    main()
