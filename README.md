# To Serve Man

*"It's a cookbook!"*

A Python-based cookbook system using [Cooklang](https://cooklang.org/) format that generates both a beautiful GitHub Pages website and a typeset PDF cookbook.

## Features

- **Plain text recipes** using the Cooklang markup language
- **Static website** with elegant, minimal design
- **PDF cookbook** with beautiful typography via LaTeX
- **Support for both food recipes and cocktails**
- **Automatic categorization** by cuisine, spirit, tags, and more
- **Schema.org markup** for SEO
- **Print-friendly** recipe pages
- **Responsive design** for all devices

## Design Philosophy

Elegant. Minimalist. Modern.

Both the website and PDF embody refined restraint. Generous whitespace, beautiful typography, and a near-monochromatic color palette let the recipes speak for themselves. Every design decision serves readability and beauty.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- LaTeX distribution (for PDF generation):
  - macOS: `brew install --cask mactex-no-gui`
  - Ubuntu/Debian: `sudo apt-get install texlive-latex-base texlive-fonts-recommended`
  - Windows: Install [MiKTeX](https://miktex.org/)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/to-serve-man.git
cd to-serve-man
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

Note: The cooklang-py parser will be installed from GitHub. If you encounter issues, the system will fall back to metadata-only parsing.

### Build

Generate the website and PDF:

```bash
python build.py all        # Generate both website and PDF
python build.py site       # Generate website only
python build.py pdf        # Generate PDF only
python build.py validate   # Validate all recipes
```

The website will be generated in `docs/` and the PDF in `output/cookbook.pdf`.

### Preview

To preview the website locally:

```bash
cd docs
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## Project Structure

```
to-serve-man/
├── recipes/              # Recipe files (.cook format)
│   ├── breakfast/
│   ├── mains/
│   ├── sides/
│   ├── desserts/
│   ├── basics/
│   └── cocktails/
├── templates/            # Jinja2 HTML templates
├── static/              # CSS, fonts, JavaScript
├── latex/               # LaTeX preamble and closing
├── images/              # Recipe images (optional)
├── docs/                # Generated website (GitHub Pages)
├── output/              # Generated PDF
├── build.py             # Build system
├── recipe_parser.py     # Recipe parsing and validation
├── site_generator.py    # Static site generator
└── pdf_generator.py     # PDF generator
```

## Adding Recipes

### Recipe Format

Recipes use the Cooklang format with YAML frontmatter for metadata.

**Food Recipe Example:**

```cooklang
---
title: Pasta Carbonara
source: https://www.example.com/recipe
author: Original Author
adapted_by: Your Name
tags:
  - pasta
  - italian
  - quick
cuisine: Italian
difficulty: easy
prep_time: 10 minutes
cook_time: 20 minutes
servings: 4
description: A rich, creamy Roman classic.
---

Bring a large #pot of @water{4%liters} to boil.

Cook @spaghetti{400%g} for ~{8%minutes}.

Serve immediately.
```

**Cocktail Recipe Example:**

```cooklang
---
title: Negroni
type: cocktail
source: https://www.example.com/cocktail
author: Count Camillo Negroni
tags:
  - gin
  - bitter
  - stirred
glass: rocks
garnish: orange peel
spirit_base: gin
difficulty: easy
servings: 1
description: The iconic Italian aperitif.
---

Add @gin{1%oz}, @Campari{1%oz}, and @sweet vermouth{1%oz} to a #mixing glass.

Stir for ~{30%seconds}.

Strain into a #rocks glass over ice.
```

### Metadata Fields

**Common Fields:**
- `title` (required) — Recipe name
- `source` — URL to original recipe
- `author` — Original creator
- `adapted_by` — Who modified it
- `tags` — List of tags
- `difficulty` — easy, medium, or hard
- `description` — Brief description
- `servings` — Number of servings

**Food-Specific:**
- `cuisine` — Italian, Mexican, Thai, etc.
- `prep_time` — Preparation time
- `cook_time` — Cooking time
- `yield` — What the recipe produces

**Cocktail-Specific:**
- `type: cocktail` — Identifies as cocktail
- `glass` — coupe, rocks, highball, etc.
- `garnish` — Garnish description
- `spirit_base` — bourbon, gin, rum, etc.

### Cooklang Syntax

- `@ingredient{quantity}` — Ingredient with quantity
- `@ingredient{}` — Ingredient without quantity
- `#cookware{}` — Cookware needed
- `~{time}` — Timer
- `>> Section` — Section header
- `-- comment` — Comment (won't appear in output)

See [Cooklang documentation](https://cooklang.org/docs/spec/) for complete syntax.

## Customization

### Website

- **Templates**: Edit files in `templates/`
- **Styles**: Modify `static/css/style.css`
- **Typography**: Change Google Fonts imports in `templates/base.html`
- **Colors**: Update CSS variables in `static/css/style.css`

### PDF

- **Typography**: Edit font packages in `latex/preamble.tex`
- **Layout**: Modify page geometry in `latex/preamble.tex`
- **Structure**: Adjust chapter/section formatting in preamble
- **Colophon**: Edit `latex/closing.tex`

## GitHub Pages Deployment

1. Build the site:
```bash
python build.py site --base-url /your-repo-name
```

2. Commit and push:
```bash
git add docs/
git commit -m "Update cookbook site"
git push origin main
```

3. Enable GitHub Pages:
   - Go to repository Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main`, folder: `/docs`
   - Save

Your site will be available at `https://yourusername.github.io/your-repo-name/`

## Validation

Before committing changes, validate your recipes:

```bash
python build.py validate
```

This checks for:
- Missing required fields (title)
- Type-specific fields (cuisine for food, glass for cocktails)
- YAML syntax errors

## Tips

- **Recipe organization**: Use subdirectories in `recipes/` to categorize recipes
- **Images**: Place images in `images/` and reference in metadata with `image: filename.jpg`
- **Testing**: Preview changes locally before deploying
- **Version control**: Track recipes in git for history and collaboration
- **Portability**: Cooklang files are plain text and will work with any Cooklang tool

## Troubleshooting

### LaTeX/PDF Issues

If PDF generation fails:

1. Verify LaTeX installation: `pdflatex --version`
2. Check the generated `.tex` file in `output/` for errors
3. Review special characters in recipe text (& % $ # _ { } ~ ^)
4. The system attempts to escape these automatically

### Website Issues

If the website doesn't look right:

1. Check browser console for CSS/JS errors
2. Verify `base_url` matches your deployment path
3. Ensure static files copied correctly to `docs/static/`

### Recipe Parsing Issues

If recipes don't parse correctly:

1. Run `python build.py validate` to check for errors
2. Verify YAML frontmatter is valid (use a YAML validator)
3. Check for unclosed brackets in Cooklang syntax
4. Ensure proper encoding (UTF-8)

## Contributing

This is a personal cookbook system, but feel free to fork and adapt it for your own use.

## License

MIT License - feel free to use and modify for your own cookbook.

## Acknowledgments

- [Cooklang](https://cooklang.org/) — The recipe markup language
- Typography inspiration from Phaidon and Ten Speed Press cookbooks
- *The Twilight Zone* episode "To Serve Man" for the name

---

*Built with Python, Jinja2, LaTeX, and love for good food and good design.*
