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
from pdf_generator import PDFGenerator, generate_pdf
from recipe_parser import RecipeCollection
from site_generator import generate_site

logger = logging.getLogger("tsm")

WATCH_PATHS = ["recipes", "templates", "content", "static", "src", "config.py"]


def validate_recipes():
    """Validate all recipes and report errors."""
    logger.info("Validating recipes...\n")

    collection = RecipeCollection("recipes")
    collection.load_recipes(use_cooklang_parser=False)

    errors = collection.validate_all()

    if not errors:
        logger.info(f"✓ All {len(collection.recipes)} recipes are valid!")
        return True

    logger.error(f"✗ Found validation errors in {len(errors)} recipes:\n")
    for filepath, error_list in errors.items():
        logger.error(f"  {filepath}:")
        for error in error_list:
            logger.error(f"    - {error}")
        logger.error("")
    return False


def build_typescript():
    """Compile TypeScript files."""
    try:
        logger.info("  Compiling TypeScript...")
        subprocess.run(["npm", "run", "build:ts"], check=True, capture_output=True)
        logger.info("  ✓ TypeScript compiled successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"  ✗ Error compiling TypeScript: {e}")
        return False
    except FileNotFoundError:
        logger.warning("  ⚠ npm not found, skipping TypeScript compilation")
        return False


def build_site(base_url: str = None):
    """Generate static website."""
    try:
        build_typescript()
        generate_site(base_url=base_url)
        return True
    except Exception:
        logger.exception("✗ Error generating site")
        return False


def build_pdf():
    """Generate PDF cookbook."""
    try:
        generate_pdf()
        return True
    except Exception:
        logger.exception("✗ Error generating PDF")
        return False


def build_latex():
    """Generate LaTeX source only (no pdflatex compilation). Used by CI."""
    try:
        tex_file = PDFGenerator().write_latex()
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
    """Run a local dev server with auto-rebuild on file change."""
    from watchfiles import watch

    docs = Path(config.DOCS_DIR)

    def rebuild(reason: str = "initial"):
        logger.info(f"\n→ Rebuild ({reason})")
        try:
            generate_site(base_url=base_url)
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
