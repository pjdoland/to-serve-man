"""
Configuration management for To Serve Man cookbook.

Loads settings from .env file and provides defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


def get_config(key: str, default: str = "") -> str:
    """Get configuration value from environment or use default."""
    return os.getenv(key, default)


# Cookbook Information
COOKBOOK_TITLE = get_config('COOKBOOK_TITLE', 'To Serve Man')
COOKBOOK_DESCRIPTION = get_config('COOKBOOK_DESCRIPTION', 'A personal collection of recipes worth keeping')
COOKBOOK_AUTHOR = get_config('COOKBOOK_AUTHOR', '')

# Website Configuration
BASE_URL = get_config('BASE_URL', '')
SITE_URL = get_config('SITE_URL', '')

# PDF Configuration
PDF_AUTHOR = get_config('PDF_AUTHOR', COOKBOOK_AUTHOR)
PDF_TITLE = get_config('PDF_TITLE', COOKBOOK_TITLE)

# Directories
RECIPES_DIR = 'recipes'
OUTPUT_DIR = 'output'
DOCS_DIR = 'docs'
CONTENT_DIR = 'content'
TEMPLATES_DIR = 'templates'
STATIC_DIR = 'static'
LATEX_DIR = 'latex'
