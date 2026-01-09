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
from pathlib import Path

from recipe_parser import RecipeCollection
from site_generator import generate_site
from pdf_generator import generate_pdf


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


def build_site(base_url: str = ""):
    """Generate static website."""
    try:
        generate_site(recipes_dir="recipes", output_dir="docs", base_url=base_url)
        return True
    except Exception as e:
        print(f"✗ Error generating site: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_pdf():
    """Generate PDF cookbook."""
    try:
        generate_pdf(recipes_dir="recipes", output_dir="output")
        return True
    except Exception as e:
        print(f"✗ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_all(base_url: str = ""):
    """Generate both website and PDF."""
    print("=" * 60)
    print("Building everything...")
    print("=" * 60)
    print()

    site_success = build_site(base_url)
    print()

    pdf_success = build_pdf()
    print()

    print("=" * 60)
    if site_success and pdf_success:
        print("✓ Build completed successfully!")
    else:
        print("✗ Build completed with errors")
        if not site_success:
            print("  - Site generation failed")
        if not pdf_success:
            print("  - PDF generation failed")
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
        default='',
        help='Base URL for the website (e.g., /to-serve-man for GitHub Pages)'
    )

    args = parser.parse_args()

    # Run the appropriate command
    if args.command == 'validate':
        success = validate_recipes()
    elif args.command == 'site':
        success = build_site(args.base_url)
    elif args.command == 'pdf':
        success = build_pdf()
    elif args.command == 'all':
        success = build_all(args.base_url)
    else:
        parser.print_help()
        sys.exit(1)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
