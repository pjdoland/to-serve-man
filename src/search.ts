// Type definitions
interface Recipe {
  title: string;
  slug: string;
  description: string;
  tags: string[];
  category: string;
  is_cocktail: boolean;
  cuisine?: string;
  spirit_base?: string;
  url: string;
}

interface SearchData {
  recipes: Recipe[];
}

// State management
class RecipeSearch {
  private recipes: Recipe[] = [];
  private searchInput: HTMLInputElement | null = null;
  private resultsContainer: HTMLDivElement | null = null;
  private searchTimeout: number | null = null;
  private selectedIndex: number = -1;

  constructor() {
    this.init();
  }

  private async init(): Promise<void> {
    // Load search data
    await this.loadSearchData();

    // Get DOM elements
    this.searchInput = document.getElementById('recipe-search') as HTMLInputElement;
    this.resultsContainer = document.getElementById('search-results') as HTMLDivElement;

    if (!this.searchInput || !this.resultsContainer) {
      console.error('Search elements not found');
      return;
    }

    // Attach event listeners
    this.attachEventListeners();
  }

  private async loadSearchData(): Promise<void> {
    try {
      const baseUrl = document.documentElement.dataset.baseUrl || '';
      const response = await fetch(`${baseUrl}/search-data.json`);
      const data: SearchData = await response.json();
      this.recipes = data.recipes;
    } catch (error) {
      console.error('Failed to load search data:', error);
    }
  }

  private attachEventListeners(): void {
    if (!this.searchInput) return;

    // Input event (typing)
    this.searchInput.addEventListener('input', (e) => this.handleInput(e));

    // Keyboard navigation
    this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));

    // Focus/blur events
    this.searchInput.addEventListener('focus', () => this.handleFocus());
    this.searchInput.addEventListener('blur', () => this.handleBlur());

    // Click outside to close
    document.addEventListener('click', (e) => this.handleClickOutside(e));
  }

  private handleInput(event: Event): void {
    const query = (event.target as HTMLInputElement).value;

    // Clear previous timeout
    if (this.searchTimeout !== null) {
      clearTimeout(this.searchTimeout);
    }

    // Debounce search
    this.searchTimeout = window.setTimeout(() => {
      this.performSearch(query);
    }, 300);
  }

  private performSearch(query: string): void {
    const normalizedQuery = query.toLowerCase().trim();

    // Empty query - hide results
    if (!normalizedQuery) {
      this.hideResults();
      return;
    }

    // Search and score results
    const results = this.searchRecipes(normalizedQuery);

    // Display results
    this.displayResults(results, query);
  }

  private searchRecipes(query: string): Recipe[] {
    return this.recipes
      .map(recipe => ({
        recipe,
        score: this.calculateScore(recipe, query)
      }))
      .filter(result => result.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 10) // Limit to top 10 results
      .map(result => result.recipe);
  }

  private calculateScore(recipe: Recipe, query: string): number {
    let score = 0;

    // Title matching (substring is OK for titles)
    const titleLower = recipe.title.toLowerCase();
    if (titleLower.includes(query)) {
      score += titleLower === query ? 20 : 10;
      // Bonus for match at start
      if (titleLower.startsWith(query)) {
        score += 5;
      }
    }

    // Tag matching (substring is OK for tags)
    recipe.tags.forEach(tag => {
      const tagLower = tag.toLowerCase();
      if (tagLower.includes(query)) {
        score += tagLower === query ? 16 : 8;
      }
    });

    // Description matching (word boundary to avoid false positives like "gin" in "original")
    if (recipe.description) {
      const descLower = recipe.description.toLowerCase();
      // Use word boundary regex to match whole words
      const wordBoundaryRegex = new RegExp(`\\b${this.escapeRegex(query)}`, 'i');
      if (wordBoundaryRegex.test(descLower)) {
        score += 5;
      }
    }

    // Cuisine/Spirit matching (exact match preferred)
    const category = recipe.is_cocktail ? recipe.spirit_base : recipe.cuisine;
    if (category) {
      const categoryLower = category.toLowerCase();
      if (categoryLower === query) {
        score += 8; // Higher score for exact match
      } else if (categoryLower.includes(query)) {
        score += 3; // Lower score for partial match
      }
    }

    return score;
  }

  private escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  private displayResults(results: Recipe[], query: string): void {
    if (!this.resultsContainer) return;

    // Clear previous results
    this.resultsContainer.innerHTML = '';
    this.selectedIndex = -1;

    if (results.length === 0) {
      this.showNoResults(query);
      return;
    }

    // Create result items
    const resultsList = document.createElement('div');
    resultsList.className = 'search-results-list';
    resultsList.setAttribute('role', 'listbox');

    results.forEach((recipe, index) => {
      const item = this.createResultItem(recipe, index);
      resultsList.appendChild(item);
    });

    // Add result count
    const resultCount = document.createElement('div');
    resultCount.className = 'search-result-count';
    resultCount.textContent = `${results.length} recipe${results.length === 1 ? '' : 's'} found`;
    resultCount.setAttribute('role', 'status');
    resultCount.setAttribute('aria-live', 'polite');

    this.resultsContainer.appendChild(resultCount);
    this.resultsContainer.appendChild(resultsList);

    // Show results
    this.showResults();
  }

  private createResultItem(recipe: Recipe, index: number): HTMLElement {
    const item = document.createElement('a');
    item.href = recipe.url;
    item.className = 'search-result-item';
    item.setAttribute('role', 'option');
    item.setAttribute('data-index', index.toString());

    // Title
    const title = document.createElement('div');
    title.className = 'search-result-title';
    title.textContent = recipe.title;

    // Meta info
    const meta = document.createElement('div');
    meta.className = 'search-result-meta';

    const categoryText = recipe.is_cocktail
      ? recipe.spirit_base || 'Cocktail'
      : recipe.cuisine || recipe.category;
    meta.textContent = categoryText;

    // Tags (show first 3)
    if (recipe.tags.length > 0) {
      const tags = document.createElement('span');
      tags.className = 'search-result-tags';
      tags.textContent = ' • ' + recipe.tags.slice(0, 3).join(', ');
      meta.appendChild(tags);
    }

    item.appendChild(title);
    item.appendChild(meta);

    return item;
  }

  private showNoResults(query: string): void {
    if (!this.resultsContainer) return;

    const noResults = document.createElement('div');
    noResults.className = 'search-no-results';
    noResults.setAttribute('role', 'status');

    const message = document.createElement('p');
    message.textContent = `No recipes found for "${this.escapeHtml(query)}"`;

    const suggestion = document.createElement('p');
    suggestion.className = 'text-sm';
    suggestion.textContent = 'Try searching for ingredients, cuisines, or recipe types';

    noResults.appendChild(message);
    noResults.appendChild(suggestion);

    this.resultsContainer.appendChild(noResults);
    this.showResults();
  }

  private showResults(): void {
    if (!this.resultsContainer || !this.searchInput) return;

    this.resultsContainer.removeAttribute('hidden');
    this.searchInput.setAttribute('aria-expanded', 'true');
  }

  private hideResults(): void {
    if (!this.resultsContainer || !this.searchInput) return;

    this.resultsContainer.setAttribute('hidden', '');
    this.searchInput.setAttribute('aria-expanded', 'false');
    this.selectedIndex = -1;
  }

  private handleKeydown(event: KeyboardEvent): void {
    if (!this.resultsContainer) return;

    const results = this.resultsContainer.querySelectorAll('.search-result-item');

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        this.selectedIndex = Math.min(this.selectedIndex + 1, results.length - 1);
        this.updateSelection(results);
        break;

      case 'ArrowUp':
        event.preventDefault();
        this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
        this.updateSelection(results);
        break;

      case 'Enter':
        event.preventDefault();
        if (this.selectedIndex >= 0 && results[this.selectedIndex]) {
          (results[this.selectedIndex] as HTMLAnchorElement).click();
        }
        break;

      case 'Escape':
        event.preventDefault();
        this.hideResults();
        if (this.searchInput) {
          this.searchInput.value = '';
          this.searchInput.blur();
        }
        break;
    }
  }

  private updateSelection(results: NodeListOf<Element>): void {
    results.forEach((result, index) => {
      if (index === this.selectedIndex) {
        result.classList.add('selected');
        result.setAttribute('aria-selected', 'true');
        result.scrollIntoView({ block: 'nearest' });
      } else {
        result.classList.remove('selected');
        result.setAttribute('aria-selected', 'false');
      }
    });
  }

  private handleFocus(): void {
    if (this.searchInput && this.searchInput.value.trim()) {
      this.performSearch(this.searchInput.value);
    }
  }

  private handleBlur(): void {
    // Delay to allow click on results
    setTimeout(() => {
      this.hideResults();
    }, 200);
  }

  private handleClickOutside(event: Event): void {
    const target = event.target as HTMLElement;

    if (!this.searchInput || !this.resultsContainer) return;

    if (!this.searchInput.contains(target) && !this.resultsContainer.contains(target)) {
      this.hideResults();
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    new RecipeSearch();
  });
} else {
  new RecipeSearch();
}
