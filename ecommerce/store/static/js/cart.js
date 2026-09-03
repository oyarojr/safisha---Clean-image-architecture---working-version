const humburger = document.querySelector('#menu');
const navigator = document.querySelector('.navigation')

humburger.addEventListener('click', () => {
    humburger.classList.toggle('show');
    navigator.classList.toggle('show');
});

// Close mobile menu when clicking outside
document.addEventListener('click', function (e) {
    if (
        navigator.classList.contains('show') &&
        !navigator.contains(e.target) &&
        !humburger.contains(e.target)
    ) {
        humburger.classList.remove('show');
        navigator.classList.remove('show');
    }
});

// Swipe left to close menu
let touchStartX = 0;

navigator.addEventListener('touchstart', function (e) {
    touchStartX = e.changedTouches[0].screenX;
});

navigator.addEventListener('touchend', function (e) {
    const touchEndX = e.changedTouches[0].screenX;

    if (touchStartX - touchEndX > 60) {
        humburger.classList.remove('show');
        navigator.classList.remove('show');
    }
});

/* CSRF helper (REQUIRED for Django POST) */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Get CSRF token from meta tag or cookie
function getCSRFToken() {
    // Try to get from meta tag first
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (tokenMeta) {
        return tokenMeta.getAttribute('content');
    }
    // Fall back to cookie
    return getCookie('csrftoken');
}

document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', function () {
            const productId = this.dataset.productId;
            const csrfToken = getCSRFToken();

            fetch(`/add-to-cart/${productId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                },
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Disable button briefly (double-tap protection)
                        button.disabled = true;
                        setTimeout(() => button.disabled = false, 800);

                        showToast(button.closest('.product-card'));

                        const cartCount = document.getElementById('cart-count');
                        if (cartCount) {
                            cartCount.innerText = data.cart_count;
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        });
    });

});

// PRODUCT SEARCH
const searchInput = document.getElementById('searchInput');

if (searchInput) {
    searchInput.addEventListener('keyup', function (e) {
        if (e.key === 'Enter') {
            const query = searchInput.value.trim();
            window.location.href = query
                ? `/?q=${encodeURIComponent(query)}`
                : '/';
        }
    });
}

// TOAST NOTIFICATION
function showToast(productCard) {
    const container = document.getElementById('toast-container');
    if (!container || !productCard) return;

    const existingToasts = container.querySelectorAll('.toast');
    if (existingToasts.length >= 3) {
        existingToasts[0].remove(); // remove oldest
    }

    const img = productCard.querySelector('img');
    const name = productCard.querySelector('h4')?.innerText || 'Item';

    const toast = document.createElement('div');
    toast.className = 'toast';

    toast.innerHTML = `
    <img src="${img ? img.src : ''}" alt="">
    <div class="toast-content">
        <strong>${name}</strong><br>
        added to cart<br>
        <a href="/cart/" class="toast-link">View cart →</a>
    </div>
`;

    container.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// BACK TO TOP BUTTON
const backToTopBtn = document.getElementById('backToTop');

if (backToTopBtn) {
    window.addEventListener('scroll', () => {
        backToTopBtn.style.display =
            window.scrollY > 300 ? 'block' : 'none';
    });

    backToTopBtn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// Note: Account menu is handled in home.html inline script to avoid conflicts

// ========================================
// PRODUCT MODAL FUNCTIONALITY
// ========================================

let currentProductId = null;
let maxQuantity = 99;

function openProductModal(productId) {
    const productCard = document.querySelector(`.product-card[data-product-id="${productId}"]`);
    if (!productCard) return;

    const productDataScript = productCard.querySelector('.product-data');
    if (!productDataScript) return;

    const productData = JSON.parse(productDataScript.textContent);
    currentProductId = productData.id;
    maxQuantity = productData.stock_quantity;

    // Populate modal
    document.getElementById('modalProductImage').src = productData.image;
    document.getElementById('modalProductName').textContent = productData.name;
    document.getElementById('modalProductCategory').textContent = productData.category;
    document.getElementById('modalProductPrice').textContent = `KSH ${parseFloat(productData.price).toFixed(2)}`;
    document.getElementById('modalProductDescription').textContent = productData.description;

    // Update stock status
    const stockEl = document.getElementById('modalProductStock');
    stockEl.className = 'modal-stock';

    if (productData.stock_status === 'in') {
        stockEl.innerHTML = '<i class="fas fa-check-circle"></i><span>In Stock</span>';
        stockEl.classList.add('in-stock');
    } else if (productData.stock_status === 'low') {
        stockEl.innerHTML = '<i class="fas fa-exclamation-circle"></i><span>Few items remaining</span>';
        stockEl.classList.add('low-stock');
    } else {
        stockEl.innerHTML = '<i class="fas fa-times-circle"></i><span>Out of stock</span>';
        stockEl.classList.add('out-stock');
    }

    // Reset quantity
    document.getElementById('modalQuantity').value = 1;
    document.getElementById('modalQuantity').max = maxQuantity;

    // Enable/disable add to cart button
    const addToCartBtn = document.getElementById('modalAddToCart');
    if (productData.stock_quantity > 0) {
        addToCartBtn.disabled = false;
        addToCartBtn.style.opacity = '1';
    } else {
        addToCartBtn.disabled = true;
        addToCartBtn.style.opacity = '0.5';
    }

    // Show modal
    const modal = document.getElementById('productModal');
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    setTimeout(() => {
        modal.querySelector('.modal-content').classList.add('show');
    }, 10);
}

function closeProductModal() {
    const modal = document.getElementById('productModal');
    modal.querySelector('.modal-content').classList.remove('show');

    setTimeout(() => {
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
        currentProductId = null;
    }, 300);
}

function increaseModalQuantity() {
    const input = document.getElementById('modalQuantity');
    const currentVal = parseInt(input.value) || 1;
    if (currentVal < maxQuantity) {
        input.value = currentVal + 1;
    }
}

function decreaseModalQuantity() {
    const input = document.getElementById('modalQuantity');
    const currentVal = parseInt(input.value) || 1;
    if (currentVal > 1) {
        input.value = currentVal - 1;
    }
}

function addToCartFromModal() {
    if (!currentProductId) return;

    const quantity = parseInt(document.getElementById('modalQuantity').value) || 1;
    const button = document.getElementById('modalAddToCart');
    const csrfToken = getCSRFToken();

    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Adding...</span>';

    // Add to cart multiple times based on quantity
    let addedCount = 0;

    function addOne() {
        if (addedCount >= quantity) {
            button.innerHTML = '<i class="fas fa-check"></i><span>Added!</span>';
            setTimeout(() => {
                button.innerHTML = '<i class="fas fa-shopping-cart"></i><span>Add to Cart</span>';
                button.disabled = false;
                closeProductModal();
            }, 1000);
            return;
        }

        fetch(`/add-to-cart/${currentProductId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addedCount++;

                    const cartCount = document.getElementById('cart-count');
                    if (cartCount) {
                        cartCount.innerText = data.cart_count;
                    }

                    if (addedCount === quantity) {
                        const productCard = document.querySelector(`.product-card[data-product-id="${currentProductId}"]`);
                        if (productCard) {
                            showToast(productCard);
                        }
                    }

                    addOne();
                } else {
                    button.innerHTML = '<i class="fas fa-shopping-cart"></i><span>Add to Cart</span>';
                    button.disabled = false;
                    alert('Error adding to cart');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.innerHTML = '<i class="fas fa-shopping-cart"></i><span>Add to Cart</span>';
                button.disabled = false;
                alert('Failed to add to cart. Please try again.');
            });
    }

    addOne();
}

// Close modal with Escape key
document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        closeProductModal();
    }
});