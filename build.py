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

import sys
import argparse
import shutil
import subprocess
from pathlib import Path

from recipe_parser import RecipeCollection
from site_generator import generate_site
from pdf_generator import generate_pdf
import config


def validate_recipes():
    """Validate all recipes and report errors."""
    print("Validating recipes...")
    print()

    collection = RecipeCollection("recipes")
    collection.load_recipes(use_cooklang_parser=False)

    # Get validation errors
    errors = collection.validate_all()

    if not errors:
        print(f"✓ All {len(collection.recipes)} recipes are valid!")
        return True

    print(f"✗ Found validation errors in {len(errors)} recipes:")
    print()

    for filepath, error_list in errors.items():
        print(f"  {filepath}:")
        for error in error_list:
            print(f"    - {error}")
        print()

    return False


def build_typescript():
    """Compile TypeScript files."""
    try:
        print("  Compiling TypeScript...")
        subprocess.run(['npm', 'run', 'build:ts'], check=True, capture_output=True)
        print("  ✓ TypeScript compiled successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error compiling TypeScript: {e}")
        return False
    except FileNotFoundError:
        print("  ⚠ npm not found, skipping TypeScript compilation")
        return False


def build_site(base_url: str = None):
    """Generate static website."""
    try:
        # Compile TypeScript first
        build_typescript()

        # Generate site
        generate_site(base_url=base_url)
        return True
    except Exception as e:
        print(f"✗ Error generating site: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_pdf():
    """Generate PDF cookbook."""
    try:
        generate_pdf()
        return True
    except Exception as e:
        print(f"✗ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def copy_pdf_to_site():
    """Copy generated PDF to site directory for download."""
    pdf_source = Path(config.OUTPUT_DIR) / "cookbook.pdf"
    pdf_dest = Path(config.DOCS_DIR) / "cookbook.pdf"

    if pdf_source.exists():
        try:
            shutil.copy2(pdf_source, pdf_dest)
            print(f"  PDF copied to {pdf_dest}")
            return True
        except Exception as e:
            print(f"✗ Error copying PDF: {e}")
            return False
    else:
        print(f"⚠ PDF not found at {pdf_source}, skipping copy")
        return False


def build_all(base_url: str = None):
    """Generate both website and PDF."""
    print("=" * 60)
    print("Building everything...")
    print("=" * 60)
    print()

    site_success = build_site(base_url)
    print()

    pdf_success = build_pdf()
    print()

    pdf_copy_success = False
    if pdf_success:
        print("Copying PDF to site...")
        pdf_copy_success = copy_pdf_to_site()
        print()

    print("=" * 60)
    if site_success and pdf_success:
        print("✓ Build completed successfully!")
        if pdf_copy_success:
            print("  PDF is available for download on the site")
    else:
        print("✗ Build completed with errors")
        if not pdf_success:
            print("  - PDF generation failed")
        if not site_success:
            print("  - Site generation failed")
    print("=" * 60)

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
  all         Generate both website and PDF (default)
  validate    Validate all recipes

Examples:
  python build.py site
  python build.py pdf
  python build.py all
  python build.py validate
  python build.py site --base-url /to-serve-man
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='all',
        choices=['site', 'pdf', 'all', 'validate'],
        help='Build command to run (default: all)'
    )

    parser.add_argument(
        '--base-url',
        default=None,
        help='Base URL for the website (e.g., /to-serve-man for GitHub Pages). If not specified, uses value from .env'
    )

    args = parser.parse_args()

    # Convert empty string to None for base_url
    base_url = args.base_url if args.base_url else None

    # Run the appropriate command
    if args.command == 'validate':
        success = validate_recipes()
    elif args.command == 'site':
        success = build_site(base_url)
    elif args.command == 'pdf':
        success = build_pdf()
        if success:
            print()
            print("Copying PDF to site...")
            copy_pdf_to_site()
    elif args.command == 'all':
        success = build_all(base_url)
    else:
        parser.print_help()
        sys.exit(1)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
