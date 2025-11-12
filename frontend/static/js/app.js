// Main application JavaScript

// Search functionality
document.getElementById('searchForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) return;
    
    showLoading();
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success) {
            displaySearchResults(data.results);
        } else {
            showError('Search failed. Please try again.');
        }
    } catch (error) {
        console.error('Search error:', error);
        showError('An error occurred. Please try again.');
    } finally {
        hideLoading();
    }
});

// Autocomplete functionality
let autocompleteTimeout;
document.getElementById('searchInput')?.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    
    if (query.length < 2) {
        hideSuggestions();
        return;
    }
    
    clearTimeout(autocompleteTimeout);
    autocompleteTimeout = setTimeout(() => {
        fetchAutocomplete(query);
    }, 300);
});

async function fetchAutocomplete(query) {
    try {
        const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.suggestions && data.suggestions.length > 0) {
            showSuggestions(data.suggestions);
        } else {
            hideSuggestions();
        }
    } catch (error) {
        console.error('Autocomplete error:', error);
    }
}

function showSuggestions(suggestions) {
    const container = document.getElementById('suggestions');
    container.innerHTML = suggestions.map(suggestion => `
        <button type="button" class="list-group-item list-group-item-action" 
                onclick="selectSuggestion('${suggestion.replace(/'/g, "\\'")}')">
            ${suggestion}
        </button>
    `).join('');
    container.style.display = 'block';
}

function hideSuggestions() {
    document.getElementById('suggestions').style.display = 'none';
}

function selectSuggestion(suggestion) {
    document.getElementById('searchInput').value = suggestion;
    hideSuggestions();
    document.getElementById('searchForm').dispatchEvent(new Event('submit'));
}

// Display search results
function displaySearchResults(results) {
    const container = document.getElementById('searchResults');
    
    if (results.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> No products found. Try a different search term.
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <h3 class="mb-4">Search Results (${results.length})</h3>
        <div class="row">
            ${results.map(product => createProductCard(product)).join('')}
        </div>
    `;
}

function createProductCard(product) {
    const sentimentBadge = getSentimentBadge(product.sentiment);
    
    return `
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card h-100 product-card">
                <img src="${product.image_url || 'https://via.placeholder.com/300x200'}" 
                     class="card-img-top" 
                     alt="${product.name}"
                     style="height: 200px; object-fit: cover;">
                <div class="card-body">
                    <h5 class="card-title">${truncate(product.name, 60)}</h5>
                    <p class="card-text text-muted">${truncate(product.description, 100)}</p>
                    
                    <div class="d-flex align-items-center mb-2">
                        <span class="badge bg-warning text-dark me-2">
                            ${product.avg_rating} <i class="bi bi-star-fill"></i>
                        </span>
                        <small class="text-muted">${product.total_reviews} reviews</small>
                    </div>
                    
                    <div class="mb-3">
                        ${sentimentBadge}
                    </div>
                    
                    <a href="/product/${product.id}" class="btn btn-primary w-100">
                        View Details <i class="bi bi-arrow-right"></i>
                    </a>
                </div>
            </div>
        </div>
    `;
}

function getSentimentBadge(sentiment) {
    const total = sentiment.positive + sentiment.neutral + sentiment.negative;
    if (total === 0) return '<span class="badge bg-secondary">No sentiment data</span>';
    
    const positive = sentiment.positive;
    const negative = sentiment.negative;
    
    if (positive > 60) {
        return `<span class="badge bg-success">${positive}% Positive</span>`;
    } else if (negative > 40) {
        return `<span class="badge bg-danger">${negative}% Negative</span>`;
    } else {
        return `<span class="badge bg-warning text-dark">Mixed Reviews</span>`;
    }
}

function truncate(text, length) {
    if (!text) return '';
    return text.length > length ? text.substring(0, length) + '...' : text;
}

function showLoading() {
    document.getElementById('loadingSpinner').style.display = 'block';
    document.getElementById('searchResults').innerHTML = '';
}

function hideLoading() {
    document.getElementById('loadingSpinner').style.display = 'none';
}

function showError(message) {
    document.getElementById('searchResults').innerHTML = `
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle"></i> ${message}
        </div>
    `;
}

// Star rating display helper
function createStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let stars = '';
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="bi bi-star-fill text-warning"></i>';
    }
    if (hasHalfStar) {
        stars += '<i class="bi bi-star-half text-warning"></i>';
    }
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="bi bi-star text-warning"></i>';
    }
    
    return stars;
}

// Format date helper
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Close suggestions when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
        hideSuggestions();
    }
});