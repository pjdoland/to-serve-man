#!/bin/bash
# To Serve Man - Setup Script
# Sets up the development environment and configures your cookbook

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      To Serve Man - Setup Script      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Check Python version
echo -e "${BLUE}→${NC} Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    echo "Please install Python 3.8 or higher from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}✗ Python $PYTHON_VERSION is too old${NC}"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment
echo -e "${BLUE}→${NC} Creating virtual environment..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠${NC}  Virtual environment already exists, skipping creation"
else
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi
echo ""

# Activate virtual environment
echo -e "${BLUE}→${NC} Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓${NC} Virtual environment activated"
echo ""

# Upgrade pip
echo -e "${BLUE}→${NC} Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓${NC} pip upgraded"
echo ""

# Install dependencies
echo -e "${BLUE}→${NC} Installing dependencies..."
pip install -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# Check for LaTeX
echo -e "${BLUE}→${NC} Checking for LaTeX (required for PDF generation)..."
if command -v pdflatex &> /dev/null; then
    echo -e "${GREEN}✓${NC} LaTeX is installed"
else
    echo -e "${YELLOW}⚠${NC}  LaTeX is not installed"
    echo "  PDF generation will not work without LaTeX"
    echo "  Install TeX Live (Linux/Mac) or MiKTeX (Windows)"
    echo "  macOS: brew install --cask mactex"
    echo "  Ubuntu: sudo apt-get install texlive-full"
fi
echo ""

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}→${NC} Creating .env configuration file..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env file created"
    echo ""

    # Prompt for configuration
    echo -e "${BLUE}Let's configure your cookbook!${NC}"
    echo ""

    read -p "Cookbook title [To Serve Man]: " TITLE
    TITLE=${TITLE:-"To Serve Man"}

    read -p "Cookbook description [A personal collection of recipes worth keeping]: " DESC
    DESC=${DESC:-"A personal collection of recipes worth keeping"}

    read -p "Author name (optional): " AUTHOR

    read -p "Base URL (e.g., /my-cookbook for GitHub Pages, or leave empty): " BASE_URL

    read -p "Full site URL (optional, e.g., https://username.github.io/my-cookbook): " SITE_URL

    # Update .env file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^COOKBOOK_TITLE=.*|COOKBOOK_TITLE=$TITLE|" .env
        sed -i '' "s|^COOKBOOK_DESCRIPTION=.*|COOKBOOK_DESCRIPTION=$DESC|" .env
        sed -i '' "s|^COOKBOOK_AUTHOR=.*|COOKBOOK_AUTHOR=$AUTHOR|" .env
        sed -i '' "s|^BASE_URL=.*|BASE_URL=$BASE_URL|" .env
        sed -i '' "s|^SITE_URL=.*|SITE_URL=$SITE_URL|" .env
        sed -i '' "s|^PDF_TITLE=.*|PDF_TITLE=$TITLE|" .env
        sed -i '' "s|^PDF_AUTHOR=.*|PDF_AUTHOR=$AUTHOR|" .env
    else
        # Linux
        sed -i "s|^COOKBOOK_TITLE=.*|COOKBOOK_TITLE=$TITLE|" .env
        sed -i "s|^COOKBOOK_DESCRIPTION=.*|COOKBOOK_DESCRIPTION=$DESC|" .env
        sed -i "s|^COOKBOOK_AUTHOR=.*|COOKBOOK_AUTHOR=$AUTHOR|" .env
        sed -i "s|^BASE_URL=.*|BASE_URL=$BASE_URL|" .env
        sed -i "s|^SITE_URL=.*|SITE_URL=$SITE_URL|" .env
        sed -i "s|^PDF_TITLE=.*|PDF_TITLE=$TITLE|" .env
        sed -i "s|^PDF_AUTHOR=.*|PDF_AUTHOR=$AUTHOR|" .env
    fi

    echo ""
    echo -e "${GREEN}✓${NC} Configuration saved to .env"
else
    echo -e "${YELLOW}⚠${NC}  .env file already exists, skipping configuration"
    echo "  Edit .env manually to change settings"
fi
echo ""

# Create output directories
echo -e "${BLUE}→${NC} Creating output directories..."
mkdir -p output
mkdir -p docs
echo -e "${GREEN}✓${NC} Output directories created"
echo ""

# Validate recipes
echo -e "${BLUE}→${NC} Validating recipes..."
python3 build.py validate
echo ""

# Success message
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Setup Complete! 🎉             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "1. Activate the virtual environment (in new terminal sessions):"
echo -e "   ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo "2. Add your recipes to the ${YELLOW}recipes/${NC} directory"
echo ""
echo "3. Build your cookbook:"
echo -e "   ${YELLOW}python build.py all${NC}    # Build both website and PDF"
echo -e "   ${YELLOW}python build.py site${NC}   # Build website only"
echo -e "   ${YELLOW}python build.py pdf${NC}    # Build PDF only"
echo ""
echo "4. Preview your cookbook:"
echo -e "   ${YELLOW}python -m http.server -d docs 8000${NC}"
echo "   Then visit: http://localhost:8000"
echo ""
echo "5. Customize your cookbook:"
echo "   - Edit ${YELLOW}.env${NC} to change title, description, etc."
echo "   - Edit ${YELLOW}content/*.md${NC} to customize text content"
echo "   - Edit ${YELLOW}static/css/style.css${NC} to change styling"
echo ""
echo -e "${GREEN}Happy cooking! 👨‍🍳${NC}"
echo ""
