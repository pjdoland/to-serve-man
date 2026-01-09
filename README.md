# To Serve Man

> It's a cookbook!

A personal cookbook system built with [Cooklang](https://cooklang.org/) that generates both a beautiful static website and a professionally typeset PDF.

## Features

- **Plain Text Recipes** - Store recipes in Cooklang format, making them portable and version-controllable
- **Static Website** - Beautiful, responsive website with Schema.org markup for recipe discoverability
- **PDF Cookbook** - Professionally typeset PDF using LaTeX with elegant typography
- **Dual Format Support** - Separate handling for food recipes and cocktails
- **Multiple Browse Options** - Filter by category, cuisine, tags, and spirit base
- **Customizable** - Easy configuration via `.env` file and Markdown content
- **Responsive Design** - Mobile-friendly website with print-optimized recipe pages

## Quick Start

### Prerequisites

- Python 3.8 or higher
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
   - Install all dependencies
   - Create a `.env` configuration file
   - Prompt you to configure your cookbook
   - Validate your recipes

3. **Build your cookbook**

   ```bash
   source venv/bin/activate  # Activate virtual environment
   python build.py all       # Build both website and PDF
   ```

4. **Preview your cookbook**

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

- **`static/css/style.css`** - Website styles
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

# Validate recipes
python build.py validate

# Build with custom base URL
python build.py site --base-url /my-cookbook
```

### Output

- **Website** - Generated in `docs/` directory
- **PDF** - Generated as `output/cookbook.pdf`

## Deployment

### GitHub Pages

1. **Enable GitHub Pages**
   - Go to your repository Settings → Pages
   - Select "main" branch and "/docs" folder
   - Click Save

2. **Update configuration**

   Edit `.env`:
   ```bash
   BASE_URL=/your-repo-name
   SITE_URL=https://yourusername.github.io/your-repo-name
   ```

3. **Rebuild and push**

   ```bash
   python build.py site
   git add docs/
   git commit -m "Update site"
   git push
   ```

Your cookbook will be live at `https://yourusername.github.io/your-repo-name/`

### Custom Domain

1. Configure your domain in GitHub Pages settings
2. Set `.env` configuration:
   ```bash
   BASE_URL=
   SITE_URL=https://your-domain.com
   ```
3. Rebuild and deploy

## Project Structure

```
to-serve-man/
├── recipes/           # Recipe files (.cook)
│   ├── mains/
│   ├── sides/
│   ├── desserts/
│   └── cocktails/
├── content/           # Markdown content files
│   ├── hero.md       # Homepage hero section
│   └── about.md      # About page
├── templates/         # Jinja2 HTML templates
├── static/           # CSS and static assets
├── latex/            # LaTeX templates for PDF
├── docs/             # Generated website (output)
├── output/           # Generated PDF (output)
├── recipe_parser.py  # Recipe parsing logic
├── site_generator.py # Static site generator
├── pdf_generator.py  # PDF generator
├── config.py         # Configuration management
├── build.py          # Build script
├── setup.sh          # Setup script
├── .env              # Your configuration (gitignored)
└── .env.example      # Configuration template
```

## Recipe Metadata

### Food Recipes

Required:
- `title` - Recipe name
- `category` - One of: breakfast, basics, mains, sides, desserts

Optional:
- `cuisine` - E.g., Italian, Indian, American
- `tags` - List of tags for categorization
- `servings` - Number of servings
- `prep_time` - Preparation time
- `cook_time` - Cooking time
- `description` - Brief description
- `source` - Source URL
- `author` - Original author
- `adapted_by` - Your name if adapted

### Cocktails

Required:
- `title` - Cocktail name
- `type` - Must be "cocktail"

Optional:
- `glass` - Glass type (rocks, coupe, highball, etc.)
- `spirit_base` - Primary spirit (gin, vodka, rum, etc.)
- `garnish` - Garnish description
- `tags` - List of tags
- `description` - Brief description

## Development

### Adding New Features

1. **Modify templates** in `templates/`
2. **Update styles** in `static/css/style.css`
3. **Extend generators** in `site_generator.py` or `pdf_generator.py`
4. **Update LaTeX** in `latex/preamble.tex` or `latex/closing.tex`

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

Dependencies are listed in `requirements.txt`:

- Jinja2 - Template engine
- PyYAML - YAML parsing
- python-slugify - URL-friendly slugs
- python-dotenv - Environment configuration
- markdown - Markdown processing
- cooklang-py - Cooklang parser

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

Typography:
- **Web**: Cormorant Garamond (serif) + Inter (sans-serif)
- **PDF**: Palatino (serif) + Helvetica (sans-serif)

## Contributing

Issues and pull requests welcome! If you create something cool with this, we'd love to hear about it.
