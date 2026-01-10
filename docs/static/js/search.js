"use strict";
// State management
class RecipeSearch {
    constructor() {
        this.recipes = [];
        this.searchInput = null;
        this.resultsContainer = null;
        this.searchTimeout = null;
        this.selectedIndex = -1;
        this.init();
    }
    async init() {
        // Load search data
        await this.loadSearchData();
        // Get DOM elements
        this.searchInput = document.getElementById('recipe-search');
        this.resultsContainer = document.getElementById('search-results');
        if (!this.searchInput || !this.resultsContainer) {
            console.error('Search elements not found');
            return;
        }
        // Attach event listeners
        this.attachEventListeners();
    }
    async loadSearchData() {
        try {
            const baseUrl = document.documentElement.dataset.baseUrl || '';
            const response = await fetch(`${baseUrl}/search-data.json`);
            const data = await response.json();
            this.recipes = data.recipes;
        }
        catch (error) {
            console.error('Failed to load search data:', error);
        }
    }
    attachEventListeners() {
        if (!this.searchInput)
            return;
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
    handleInput(event) {
        const query = event.target.value;
        // Clear previous timeout
        if (this.searchTimeout !== null) {
            clearTimeout(this.searchTimeout);
        }
        // Debounce search
        this.searchTimeout = window.setTimeout(() => {
            this.performSearch(query);
        }, 300);
    }
    performSearch(query) {
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
    searchRecipes(query) {
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
    calculateScore(recipe, query) {
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
            }
            else if (categoryLower.includes(query)) {
                score += 3; // Lower score for partial match
            }
        }
        return score;
    }
    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    displayResults(results, query) {
        if (!this.resultsContainer)
            return;
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
    createResultItem(recipe, index) {
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
    showNoResults(query) {
        if (!this.resultsContainer)
            return;
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
    showResults() {
        if (!this.resultsContainer || !this.searchInput)
            return;
        this.resultsContainer.removeAttribute('hidden');
        this.searchInput.setAttribute('aria-expanded', 'true');
    }
    hideResults() {
        if (!this.resultsContainer || !this.searchInput)
            return;
        this.resultsContainer.setAttribute('hidden', '');
        this.searchInput.setAttribute('aria-expanded', 'false');
        this.selectedIndex = -1;
    }
    handleKeydown(event) {
        if (!this.resultsContainer)
            return;
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
                    results[this.selectedIndex].click();
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
    updateSelection(results) {
        results.forEach((result, index) => {
            if (index === this.selectedIndex) {
                result.classList.add('selected');
                result.setAttribute('aria-selected', 'true');
                result.scrollIntoView({ block: 'nearest' });
            }
            else {
                result.classList.remove('selected');
                result.setAttribute('aria-selected', 'false');
            }
        });
    }
    handleFocus() {
        if (this.searchInput && this.searchInput.value.trim()) {
            this.performSearch(this.searchInput.value);
        }
    }
    handleBlur() {
        // Delay to allow click on results
        setTimeout(() => {
            this.hideResults();
        }, 200);
    }
    handleClickOutside(event) {
        const target = event.target;
        if (!this.searchInput || !this.resultsContainer)
            return;
        if (!this.searchInput.contains(target) && !this.resultsContainer.contains(target)) {
            this.hideResults();
        }
    }
    escapeHtml(text) {
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
}
else {
    new RecipeSearch();
}
