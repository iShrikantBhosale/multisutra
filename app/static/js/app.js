// MultiSutra CMS JavaScript

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var itemName = this.getAttribute('data-confirm-delete');
            var message = itemName ? 
                'Are you sure you want to delete "' + itemName + '"?' :
                'Are you sure you want to delete this item?';
            
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Form auto-save (for drafts)
    var autoSaveForms = document.querySelectorAll('[data-auto-save]');
    autoSaveForms.forEach(function(form) {
        var timeout;
        var inputs = form.querySelectorAll('input, textarea, select');
        
        inputs.forEach(function(input) {
            input.addEventListener('input', function() {
                clearTimeout(timeout);
                timeout = setTimeout(function() {
                    autoSaveForm(form);
                }, 2000); // Auto-save after 2 seconds of inactivity
            });
        });
    });
    
    // Media library functionality
    initializeMediaLibrary();
    
    // Search functionality
    initializeSearch();
    
    // Image upload preview
    initializeImagePreviews();
});

// Auto-save form data
function autoSaveForm(form) {
    var formData = new FormData(form);
    formData.append('auto_save', '1');
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Draft saved automatically', 'success');
        }
    })
    .catch(error => {
        console.error('Auto-save error:', error);
    });
}

// Media library functionality
function initializeMediaLibrary() {
    // File upload handling
    var fileInputs = document.querySelectorAll('input[type="file"][data-upload]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            var files = e.target.files;
            if (files.length > 0) {
                uploadFiles(files, input.getAttribute('data-upload-url'));
            }
        });
    });
    
    // Drag and drop upload
    var dropZones = document.querySelectorAll('[data-drop-zone]');
    dropZones.forEach(function(zone) {
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            zone.classList.remove('dragover');
        });
        
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            zone.classList.remove('dragover');
            
            var files = e.dataTransfer.files;
            if (files.length > 0) {
                uploadFiles(files, zone.getAttribute('data-upload-url'));
            }
        });
    });
    
    // Media selection for posts
    var mediaButtons = document.querySelectorAll('[data-select-media]');
    mediaButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            openMediaSelector(button.getAttribute('data-target'));
        });
    });
}

// Upload files via AJAX
function uploadFiles(files, uploadUrl) {
    var formData = new FormData();
    
    for (var i = 0; i < files.length; i++) {
        formData.append('file', files[i]);
    }
    
    // Show loading indicator
    showToast('Uploading files...', 'info');
    
    fetch(uploadUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Files uploaded successfully!', 'success');
            if (data.files) {
                // Refresh media library or update UI
                location.reload();
            }
        } else {
            showToast('Upload failed: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        showToast('Upload failed: ' + error.message, 'error');
    });
}

// Open media selector modal
function openMediaSelector(targetInput) {
    // This would open a modal with media library
    // For now, we'll use a simple file picker
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.addEventListener('change', function(e) {
        var file = e.target.files[0];
        if (file) {
            // Upload file and set URL in target input
            var formData = new FormData();
            formData.append('file', file);
            
            fetch('/dashboard/media/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById(targetInput).value = data.file.file_url;
                    showToast('Image selected!', 'success');
                }
            });
        }
    });
    input.click();
}

// Search functionality
function initializeSearch() {
    var searchInputs = document.querySelectorAll('[data-live-search]');
    
    searchInputs.forEach(function(input) {
        var timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                performLiveSearch(input);
            }, 300);
        });
    });
}

// Perform live search
function performLiveSearch(input) {
    var query = input.value.trim();
    var searchUrl = input.getAttribute('data-search-url');
    var resultsContainer = document.getElementById(input.getAttribute('data-results-target'));
    
    if (query.length < 2) {
        resultsContainer.innerHTML = '';
        return;
    }
    
    fetch(searchUrl + '?q=' + encodeURIComponent(query))
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data.results, resultsContainer);
        })
        .catch(error => {
            console.error('Search error:', error);
        });
}

// Display search results
function displaySearchResults(results, container) {
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<div class="text-muted p-3">No results found</div>';
        return;
    }
    
    results.forEach(function(result) {
        var item = document.createElement('div');
        item.className = 'search-result-item p-2 border-bottom';
        item.innerHTML = '<strong>' + escapeHtml(result.title) + '</strong><br>' +
                        '<small class="text-muted">' + escapeHtml(result.excerpt || '') + '</small>';
        item.addEventListener('click', function() {
            // Handle result selection
            window.location.href = result.url;
        });
        container.appendChild(item);
    });
}

// Initialize image upload previews
function initializeImagePreviews() {
    var imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    
    imageInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            var file = e.target.files[0];
            var previewContainer = document.getElementById(input.getAttribute('data-preview'));
            
            if (file && previewContainer) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    previewContainer.innerHTML = '<img src="' + e.target.result + '" class="img-thumbnail" style="max-width: 200px;">';
                };
                reader.readAsDataURL(file);
            }
        });
    });
}

// Utility functions
function showToast(message, type = 'info') {
    // Create toast element
    var toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-' + 
                     (type === 'error' ? 'danger' : type) + ' border-0';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${escapeHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Add to toast container
    var container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1056';
        document.body.appendChild(container);
    }
    
    container.appendChild(toast);
    
    // Show toast
    var bsToast = new bootstrap.Toast(toast, {
        delay: type === 'error' ? 7000 : 4000
    });
    bsToast.show();
    
    // Remove from DOM after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function escapeHtml(text) {
    var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

// AJAX helper function
function ajaxRequest(url, options = {}) {
    const defaults = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    const config = Object.assign({}, defaults, options);
    
    return fetch(url, config)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
}

// Export functions for use in other scripts
window.MultiSutra = {
    showToast: showToast,
    ajaxRequest: ajaxRequest,
    escapeHtml: escapeHtml
};