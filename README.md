# To Serve Man

> It's a cookbook!

A personal cookbook system built with [Cooklang](https://cooklang.org/) that generates both a beautiful static website and a professionally typeset PDF.

## Features

- **Plain Text Recipes** - Store recipes in Cooklang format, making them portable and version-controllable
- **Static Website** - Beautiful, responsive website with Schema.org markup for recipe discoverability
- **Client-Side Search** - Fast, accessible recipe search with keyboard navigation and weighted scoring
- **PDF Cookbook** - Professionally typeset PDF using LaTeX with elegant typography
- **Dual Format Support** - Separate handling for food recipes and cocktails
- **Multiple Browse Options** - Filter by category, cuisine, tags, and spirit base
- **Customizable** - Easy configuration via `.env` file and Markdown content
- **Responsive Design** - Mobile-friendly website with hamburger menu and print-optimized recipe pages
- **Modern CSS** - Built with Tailwind CSS for rapid styling and consistency

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 16+ and npm (for TypeScript compilation)
  - macOS: `brew install node`
  - Ubuntu: `sudo apt-get install nodejs npm`
  - Windows: [Node.js installer](https://nodejs.org/)
- LaTeX distribution (for PDF generation)
  - macOS: `brew install --cask mactex`
  - Ubuntu: `sudo apt-get install texlive-full`
  - Windows: [MiKTeX](https://miktex.org/)

### Installation

1. **Clone or fork this repository**

   ```bash
   git clone https://github.com/yourusername/to-serve-man.git
   cd to-serve-man
   ```

2. **Run the setup script**

   ```bash
   ./setup.sh
   ```

   The setup script will:
   - Create a Python virtual environment
   - Install all Python dependencies
   - Create a `.env` configuration file
   - Prompt you to configure your cookbook
   - Validate your recipes

3. **Install Node dependencies**

   ```bash
   npm install
   ```

   This installs TypeScript for the search feature compilation.

4. **Build your cookbook**

   ```bash
   source venv/bin/activate  # Activate virtual environment
   python build.py all       # Build both website and PDF
   ```

5. **Preview your cookbook**

   ```bash
   python -m http.server -d docs 8000
   ```

   Visit http://localhost:8000

## Configuration

### Environment Variables

Edit the `.env` file to customize your cookbook:

```bash
# Cookbook Information
COOKBOOK_TITLE=My Personal Cookbook
COOKBOOK_DESCRIPTION=Family recipes and culinary experiments
COOKBOOK_AUTHOR=Your Name

# Website Configuration
BASE_URL=/my-cookbook  # For GitHub Pages, or leave empty for custom domain
SITE_URL=https://yourusername.github.io/my-cookbook

# PDF Configuration
PDF_AUTHOR=Your Name
PDF_TITLE=My Personal Cookbook
```

### Content Customization

Edit Markdown files in the `content/` directory:

- **`content/hero.md`** - Homepage hero section
- **`content/about.md`** - About page content

### Styling

- **Tailwind CSS** - Main styling framework (loaded via CDN)
- **`static/css/custom.css`** - Custom CSS for components that need pseudo-elements or special styling
- **`latex/preamble.tex`** - PDF typography and layout
- **`latex/closing.tex`** - PDF back matter

## Writing Recipes

Recipes are stored in the `recipes/` directory using the Cooklang format with YAML frontmatter.

### Food Recipe Example

Create `recipes/mains/pasta-carbonara.cook`:

```yaml
---
title: Pasta Carbonara
category: mains
cuisine: Italian
tags:
  - pasta
  - italian
  - quick
servings: 4
prep_time: 10 minutes
cook_time: 20 minutes
description: A rich, creamy Roman classic made the authentic way—no cream needed.
source: https://www.example.com/recipe
author: Chef Name
---

Bring a large #pot of @water{4%liters} to boil. Season generously with @salt{2%tbsp}.

While waiting, cut @guanciale{200%g} into small strips.

Cook @spaghetti{400%g} in the boiling water for ~{2%minutes} less than package directions.

Meanwhile, cook the guanciale in a cold #skillet over medium heat for ~{8%minutes} until fat renders and meat is crispy.

Reserve @pasta water{1%cup}, then drain pasta. Off heat, add pasta to skillet, then quickly stir in egg mixture.
```

### Cocktail Recipe Example

Create `recipes/cocktails/negroni.cook`:

```yaml
---
title: Negroni
type: cocktail
glass: rocks
spirit_base: gin
garnish: orange peel
tags:
  - gin
  - classic
  - stirred
  - bitter
description: The iconic Italian aperitif. Bold, bitter, beautiful.
---

Add @gin{1%oz}, @Campari{1%oz}, and @sweet vermouth{1%oz} to a #mixing glass with ice.

Stir for ~{30%seconds} until well chilled.

Strain into a #rocks glass over @large ice cube{1}.

Express the oils from an @orange peel over the drink, then drop it in.
```

### Cooklang Syntax

- `@ingredient{quantity}` - Ingredients with quantities
- `#cookware` or `#cookware{}` - Cookware items
- `~{time}` - Timers
- `--` - Comments (not shown in output)
- `>> Section Name` - Section headers in instructions

## Building

### Build Commands

```bash
# Activate virtual environment first
source venv/bin/activate

# Build everything
python build.py all

# Build website only
python build.py site

# Build PDF only
python build.py pdf

# Generate LaTeX source only (no pdflatex compile — used by CI)
python build.py latex

# Validate recipes
python build.py validate

# Local dev server with auto-rebuild on file change
python build.py serve

# Run smoke tests
python -m unittest discover -s tests -t . -v

# Refresh snapshot fixtures after an intentional rendering change
UPDATE_SNAPSHOTS=1 python -m unittest discover -s tests -t .

# Lint and format
ruff check . && ruff format .

# Build with custom base URL
python build.py site --base-url /my-cookbook
```

### Output

Both output directories are gitignored and rebuilt on every CI run:

- **Website** - Generated in `docs/`
- **PDF** - Generated as `output/cookbook.pdf` (and copied to `docs/cookbook.pdf` for download)

## Deployment

Deployment is handled by `.github/workflows/deploy.yml`: every push to `main` validates recipes, runs the smoke tests, builds the site, compiles the PDF via `xu-cheng/latex-action`, and publishes to GitHub Pages via `actions/deploy-pages`.

### GitHub Pages setup

1. **Enable GitHub Pages with the workflow source**
   - Settings → Pages → Source: *GitHub Actions*
2. **Set the site URL in the workflow**

   Edit the `env:` block in `.github/workflows/deploy.yml`:
   ```yaml
   env:
     BASE_URL: /your-repo-name
     SITE_URL: https://yourusername.github.io/your-repo-name
   ```
3. **Push to `main`** — the workflow runs automatically.

Your cookbook will be live at `https://yourusername.github.io/your-repo-name/`.

### Custom Domain

1. Configure your domain in GitHub Pages settings.
2. Edit the workflow `env:` block:
   ```yaml
   env:
     BASE_URL: ""
     SITE_URL: https://your-domain.com
   ```
3. Push to `main`.

## Project Structure

```
to-serve-man/
├── recipes/              # Recipe files (.cook)
│   ├── breakfast/
│   ├── basics/
│   ├── mains/
│   ├── sides/
│   ├── desserts/
│   └── cocktails/
├── content/              # Markdown content files
│   ├── hero.md           # Homepage hero section
│   └── about.md          # About page
├── templates/            # Jinja2 HTML templates
├── static/               # CSS and static assets
│   ├── css/
│   │   └── custom.css    # Custom CSS overrides
│   └── js/               # Compiled JavaScript (gitignored)
├── src/                  # TypeScript source files
│   └── search.ts         # Client-side search implementation
├── latex/                # LaTeX templates for PDF
├── tests/                # Smoke tests (unittest)
├── .github/workflows/    # CI/CD (build + deploy to GitHub Pages)
├── docs/                 # Generated website (gitignored, built by CI)
├── output/               # Generated PDF/LaTeX (gitignored, built by CI)
├── recipe_parser.py      # Recipe parsing logic
├── site_generator.py     # Static site generator
├── pdf_generator.py      # PDF generator
├── config.py             # Configuration management
├── build.py              # Build script
├── setup.sh              # Setup script
├── package.json          # Node.js dependencies
├── tsconfig.json         # TypeScript configuration
├── .env                  # Your configuration (gitignored)
└── .env.example          # Configuration template
```

## Recipe Metadata

### Food Recipes

Required:
- `title` - Recipe name
- `category` - One of: breakfast, basics, mains, sides, desserts

Optional:
- `cuisine` - E.g., Italian, Indian, American
- `tags` - List of tags (see "Tags vs. facets" below for the vocabulary policy)
- `servings` - Number of servings
- `prep_time` - Preparation time (e.g., "15 minutes", "1 hour")
- `cook_time` - Cooking time (computed `total_time` is auto-derived from these two)
- `description` - Brief description
- `headnote` - Cook's voice/story (markdown), rendered above ingredients
- `source` - Source URL
- `author` - Original author
- `adapted_by` - Your name if adapted
- `make_ahead`, `storage`, `reheats`, `yield_notes` - Standardized notes block
- `variations` - List of `{name, swap, note}` for substitutions
- `serve_with`, `pairs_with`, `uses` - Lists of recipe slugs (cross-references)
- `season` - List of: spring, summer, fall, winter, year-round
- `occasion` - List of: weeknight, dinner-party, holiday, brunch, hangover, etc.
- `hero_image` - Path to hero photo, relative to site root (e.g. `images/recipes/foo.jpg`)
- `hero_alt` - Alt text — required if `hero_image` is set

### Cocktails

Required:
- `title` - Cocktail name
- `type` - Must be "cocktail"

Optional:
- `glass` - Glass type (rocks, coupe, highball, etc.)
- `spirit_base` - Primary spirit (gin, vodka, rum, etc.)
- `garnish` - Garnish description
- `tags` - List of tags (see "Tags vs. facets")
- `description` - Brief description
- All Phase 3 schema fields above (`headnote`, `variations`, cross-refs, etc.)
  apply to cocktails too.

### Tags vs. facets — vocabulary policy

The site has multiple ways to slice recipes. To keep them from competing,
each one has a distinct purpose:

| Field | Type | Purpose | Examples |
|---|---|---|---|
| `category` | controlled | Where it lives in the cookbook | mains, sides, desserts |
| `cuisine` | controlled (food only) | Culinary tradition | Italian, Indian, Italian-American |
| `spirit_base` | controlled (cocktails only) | Primary spirit | gin, rum, bourbon |
| `season` | controlled enum | When it's at its best | spring, summer, fall, winter, year-round |
| `occasion` | controlled enum | When you'd reach for it | weeknight, dinner-party, holiday, brunch |
| `tags` | freeform | Technique, dietary, mood | one-pot, vegetarian, no-knead, comfort-food |

**Rule of thumb:** if a value has its own dedicated field (cuisine, spirit,
season, occasion), don't also tag it. `tags` is reserved for cross-cuts the
named facets don't capture — e.g. cooking technique (`braise`, `no-knead`,
`grill`), dietary constraints (`vegan`, `gluten-free`), mood/feel (`comfort-food`,
`celebratory`, `easy-cleanup`).

If you find yourself adding the same tag to many recipes and treating it
structurally (e.g. filtering by it), promote it to a facet instead — add a
new field to `Recipe` in `recipe_parser.py` and a matching index page in
`site_generator.py`.

## Development

### Adding New Features

1. **Modify templates** in `templates/`
2. **Update styles** with Tailwind utilities or `static/css/custom.css`
3. **Add TypeScript** in `src/` and compile with `npm run build:ts`
4. **Extend generators** in `site_generator.py` or `pdf_generator.py`
5. **Update LaTeX** in `latex/preamble.tex` or `latex/closing.tex`

### Virtual Environment

Always activate the virtual environment before working:

```bash
source venv/bin/activate
```

To deactivate:

```bash
deactivate
```

### Dependencies

**Python** (in `pyproject.toml`):
- Jinja2 - Template engine
- PyYAML - YAML parsing
- python-slugify - URL-friendly slugs
- python-dotenv - Environment configuration
- markdown - Markdown processing

Dev extras (`pip install -e ".[dev]"`): ruff, mypy, watchfiles, pre-commit.

**Node.js** (in `package.json`):
- TypeScript - Type-safe JavaScript compilation

## Troubleshooting

### PDF Generation Fails

**Problem**: `pdflatex` not found

**Solution**: Install a LaTeX distribution:
- macOS: `brew install --cask mactex`
- Ubuntu: `sudo apt-get install texlive-full`
- Windows: Install [MiKTeX](https://miktex.org/)

### Website Formatting Issues

**Problem**: CSS not loading on GitHub Pages

**Solution**: Check that `BASE_URL` in `.env` matches your repository name:
```bash
BASE_URL=/repository-name
```

Then rebuild:
```bash
python build.py site
```

### Recipe Validation Errors

**Problem**: Recipes failing validation

**Solution**: Run validation to see specific errors:
```bash
python build.py validate
```

Common issues:
- Missing required metadata (title, category/type)
- Invalid category name
- Missing YAML frontmatter delimiters (`---`)

## The Name

"To Serve Man" references the classic 1962 *Twilight Zone* episode where an alien book titled "To Serve Man" turns out to be a cookbook. Here, we embrace the pun with affection—it is indeed a cookbook, and a delicious one at that.

## License

This project is open source. Feel free to fork and customize for your own cookbook!

## Credits

Built with:
- [Cooklang](https://cooklang.org/) - Recipe markup language
- [Python](https://www.python.org/) - Programming language
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [LaTeX](https://www.latex-project.org/) - Document typesetting system
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [TypeScript](https://www.typescriptlang.org/) - Type-safe JavaScript

Typography:
- **Web**: EB Garamond (serif) + Inter (sans-serif)
- **PDF**: EB Garamond (serif) + Helvetica (sans-serif)

## Contributing

Issues and pull requests welcome! If you create something cool with this, we'd love to hear about it.
