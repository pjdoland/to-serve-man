#!/usr/bin/env python3
"""
To Serve Man — Build System

Build script for generating the website and PDF cookbook.

Usage:
    python build.py site        # Generate website only
    python build.py pdf         # Generate PDF only
    python build.py all         # Generate both website and PDF
    python build.py validate    # Validate all recipes
"""

import argparse
import http.server
import logging
import shutil
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

import config
from pdf_generator import PDFGenerator
from recipe_parser import RecipeCollection
from site_generator import SiteGenerator

logger = logging.getLogger("tsm")

WATCH_PATHS = ["recipes", "templates", "content", "static", "src", "config.py"]


def validate_recipes(collection: RecipeCollection | None = None, quiet_on_success: bool = False) -> bool:
    """Validate all recipes and report errors.

    Returns False if any .cook file failed to load OR any recipe failed
    schema validation. Pass a pre-loaded `collection` to avoid re-parsing
    the corpus when called from build_site/build_pdf/build_latex (each of
    those already loads recipes via SiteGenerator/PDFGenerator init).
    """
    if not quiet_on_success:
        logger.info("Validating recipes...\n")

    if collection is None:
        collection = RecipeCollection("recipes")
        collection.load_recipes(use_cooklang_parser=False)

    if collection.load_errors:
        logger.error(f"✗ Failed to load {len(collection.load_errors)} recipe file(s):\n")
        for filepath, msg in collection.load_errors:
            # Truncate gnarly multi-line YAML errors so CI logs stay scannable.
            short = msg if len(msg) < 500 else msg[:500] + "… (truncated)"
            logger.error(f"  {filepath}: {short}")
        logger.error("")

    errors = collection.validate_all()
    if errors:
        logger.error(f"✗ Found validation errors in {len(errors)} recipes:\n")
        for filepath, error_list in errors.items():
            logger.error(f"  {filepath}:")
            for error in error_list:
                logger.error(f"    - {error}")
            logger.error("")

    if collection.load_errors or errors:
        return False

    if not quiet_on_success:
        logger.info(f"✓ All {len(collection.recipes)} recipes are valid!")
    return True


def build_assets():
    """Compile TypeScript and Tailwind CSS in parallel — independent pipelines."""
    jobs = [("build:ts", "TypeScript"), ("build:css", "Tailwind CSS")]
    procs: list[tuple[subprocess.Popen, str]] = []
    try:
        for script, label in jobs:
            logger.info(f"  Building {label}...")
            procs.append(
                (
                    subprocess.Popen(["npm", "run", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE),
                    label,
                )
            )
    except FileNotFoundError:
        logger.warning("  ⚠ npm not found, skipping asset build")
        return
    for proc, label in procs:
        _, stderr = proc.communicate()
        if proc.returncode == 0:
            logger.info(f"  ✓ {label} built")
        else:
            logger.error(f"  ✗ Error building {label}: {stderr.decode().strip()}")


def build_site(base_url: str = None):
    """Generate static website. Fails the build on recipe load/validation
    errors so a YAML typo or missing required field can't silently ship a
    partial corpus to production."""
    try:
        build_assets()
        gen = SiteGenerator(base_url=base_url)
        if not validate_recipes(gen.collection, quiet_on_success=True):
            return False
        gen.generate_all()
        return True
    except Exception:
        logger.exception("✗ Error generating site")
        return False


def build_pdf():
    """Generate PDF cookbook."""
    try:
        gen = PDFGenerator()
        if not validate_recipes(gen.collection, quiet_on_success=True):
            return False
        return gen.generate_all()
    except Exception:
        logger.exception("✗ Error generating PDF")
        return False


def build_latex():
    """Generate LaTeX source only (no pdflatex compilation). Used by CI."""
    try:
        gen = PDFGenerator()
        if not validate_recipes(gen.collection, quiet_on_success=True):
            return False
        tex_file = gen.write_latex()
        logger.info(f"LaTeX written to {tex_file}")
        return True
    except Exception:
        logger.exception("✗ Error generating LaTeX")
        return False


def copy_pdf_to_site():
    """Copy generated PDF to site directory for download."""
    pdf_source = Path(config.OUTPUT_DIR) / "cookbook.pdf"
    pdf_dest = Path(config.DOCS_DIR) / "cookbook.pdf"

    if not pdf_source.exists():
        logger.warning(f"⚠ PDF not found at {pdf_source}, skipping copy")
        return False
    try:
        shutil.copy2(pdf_source, pdf_dest)
        logger.info(f"  PDF copied to {pdf_dest}")
        return True
    except Exception:
        logger.exception("✗ Error copying PDF")
        return False


def serve(host: str = "127.0.0.1", port: int = 8000, base_url: str = None):
    """Run a local dev server with auto-rebuild on file change.

    Intentionally bypasses the validation gate that build_site enforces — a
    typo mid-edit shouldn't freeze the dev loop. Errors surface as exceptions
    in the rebuild log instead.
    """
    from watchfiles import watch

    docs = Path(config.DOCS_DIR)

    def rebuild(reason: str = "initial"):
        logger.info(f"\n→ Rebuild ({reason})")
        try:
            SiteGenerator(base_url=base_url).generate_all()
            logger.info("  ✓ Site rebuilt")
        except Exception:
            logger.exception("  ✗ Rebuild failed")

    rebuild("initial")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(docs), **kwargs)

        def log_message(self, format, *args):
            logger.debug(format % args)

    httpd = socketserver.ThreadingTCPServer((host, port), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    logger.info(f"\nServing http://{host}:{port}/  (Ctrl-C to stop)")
    logger.info(f"Watching: {', '.join(WATCH_PATHS)}\n")

    try:
        for changes in watch(*WATCH_PATHS):
            paths = ", ".join(sorted({Path(p).name for _, p in changes})[:3])
            rebuild(paths)
    except KeyboardInterrupt:
        logger.info("\nStopped.")
    finally:
        httpd.shutdown()


def build_all(base_url: str = None):
    """Generate both website and PDF."""
    bar = "=" * 60
    logger.info(f"{bar}\nBuilding everything...\n{bar}\n")

    site_success = build_site(base_url)
    logger.info("")

    pdf_success = build_pdf()
    logger.info("")

    pdf_copy_success = False
    if pdf_success:
        logger.info("Copying PDF to site...")
        pdf_copy_success = copy_pdf_to_site()
        logger.info("")

    logger.info(bar)
    if site_success and pdf_success:
        logger.info("✓ Build completed successfully!")
        if pdf_copy_success:
            logger.info("  PDF is available for download on the site")
    else:
        logger.error("✗ Build completed with errors")
        if not pdf_success:
            logger.error("  - PDF generation failed")
        if not site_success:
            logger.error("  - Site generation failed")
    logger.info(bar)

    return site_success and pdf_success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build system for To Serve Man cookbook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  site        Generate website only
  pdf         Generate PDF only
  latex       Generate LaTeX source only (for CI)
  all         Generate both website and PDF (default)
  validate    Validate all recipes
  serve       Run local dev server with auto-rebuild on file change

Examples:
  python build.py site
  python build.py pdf
  python build.py all
  python build.py validate
  python build.py site --base-url /to-serve-man
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["site", "pdf", "latex", "all", "validate", "serve"],
        help="Build command to run (default: all)",
    )

    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for the website (e.g., /to-serve-man for GitHub Pages). If not specified, uses value from .env",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show warnings and errors")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else (logging.WARNING if args.quiet else logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")

    base_url = args.base_url if args.base_url else None

    if args.command == "validate":
        success = validate_recipes()
    elif args.command == "site":
        success = build_site(base_url)
    elif args.command == "pdf":
        success = build_pdf()
        if success:
            logger.info("\nCopying PDF to site...")
            copy_pdf_to_site()
    elif args.command == "latex":
        success = build_latex()
    elif args.command == "serve":
        serve(base_url=base_url)
        success = True
    elif args.command == "all":
        success = build_all(base_url)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
