/**
 * 03DxD12 Extensions Directory Client
 * Live extension browsing, filtering, and 1-click APK installation
 */

document.addEventListener('DOMContentLoaded', () => {
  let allExtensions = [];
  let filteredExtensions = [];

  // DOM Elements
  const extensionsGrid = document.getElementById('extensionsGrid');
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const categoryTabs = document.getElementById('categoryTabs');
  const sortSelect = document.getElementById('sortSelect');
  const resultsCount = document.getElementById('resultsCount');
  const emptyState = document.getElementById('emptyState');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');
  const statCount = document.getElementById('statCount');

  // Copy Repo & Deep Link
  const copyRepoBtn = document.getElementById('copyRepoBtn');
  const repoUrlInput = document.getElementById('repoUrlInput');
  const toast = document.getElementById('toast');

  // Guide Modal
  const guideBtn = document.getElementById('guideBtn');
  const guideModal = document.getElementById('guideModal');
  const closeModalBtn = document.getElementById('closeModalBtn');
  const modalGotItBtn = document.getElementById('modalGotItBtn');

  let currentCategory = 'all';
  let currentSort = 'name-asc';

  // 1. Fetch Repository Extensions
  async function loadExtensions() {
    try {
      // Try local or deployed index.json, then index.min.json
      let response = await fetch('index.json');
      if (!response.ok) {
        response = await fetch('index.min.json');
      }
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      allExtensions = await response.json();
      statCount.textContent = allExtensions.length;
      applyFiltersAndSort();
    } catch (err) {
      console.warn('Could not fetch index.json, trying remote fallback...', err);
      try {
        const fallback = await fetch('https://raw.githubusercontent.com/03DxD12/tachiyomi-extensions/repo/index.json');
        allExtensions = await fallback.json();
        statCount.textContent = allExtensions.length;
        applyFiltersAndSort();
      } catch (fallbackErr) {
        console.error('Fatal: Failed to load extension index:', fallbackErr);
        resultsCount.textContent = 'Failed to load extensions. Please try again later.';
        extensionsGrid.innerHTML = '';
      }
    }
  }

  // 2. Filter & Sort Logic
  function applyFiltersAndSort() {
    const query = searchInput.value.trim().toLowerCase();

    filteredExtensions = allExtensions.filter(ext => {
      // Keyword Match
      const name = (ext.name || '').toLowerCase();
      const pkg = (ext.pkg || '').toLowerCase();
      const sourceMatch = ext.sources && ext.sources.some(s => 
        (s.name || '').toLowerCase().includes(query) || 
        (s.baseUrl || '').toLowerCase().includes(query)
      );
      const matchesSearch = !query || name.includes(query) || pkg.includes(query) || sourceMatch;

      if (!matchesSearch) return false;

      // Category filter
      if (currentCategory === 'en') {
        return ext.lang === 'en' || ext.lang === 'all';
      } else if (currentCategory === 'nsfw') {
        return ext.nsfw === 1;
      } else if (currentCategory === 'safe') {
        return ext.nsfw !== 1;
      }

      return true;
    });

    // Sort
    filteredExtensions.sort((a, b) => {
      if (currentSort === 'name-asc') {
        return (a.name || '').localeCompare(b.name || '');
      } else if (currentSort === 'name-desc') {
        return (b.name || '').localeCompare(a.name || '');
      } else if (currentSort === 'version') {
        return (b.code || 0) - (a.code || 0);
      }
      return 0;
    });

    renderGrid();
  }

  // 3. Render Extension Cards
  function renderGrid() {
    resultsCount.textContent = `Showing ${filteredExtensions.length} of ${allExtensions.length} extensions`;

    if (filteredExtensions.length === 0) {
      extensionsGrid.innerHTML = '';
      emptyState.style.display = 'block';
      return;
    }

    emptyState.style.display = 'none';
    extensionsGrid.innerHTML = '';

    filteredExtensions.forEach(ext => {
      const card = document.createElement('div');
      card.className = 'ext-card';

      const primarySource = (ext.sources && ext.sources.length > 0) ? ext.sources[0] : null;
      const baseUrl = primarySource ? primarySource.baseUrl : '';
      const domain = baseUrl ? baseUrl.replace(/^https?:\/\//, '').replace(/\/.*$/, '') : '';

      const iconPath = `icon/${ext.pkg}.png`;
      const apkPath = `apk/${ext.apk}`;

      card.innerHTML = `
        <div>
          <div class="ext-header">
            <div class="ext-icon-wrapper">
              <img class="ext-icon" src="${iconPath}" alt="${ext.name}" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'40\\' height=\\'40\\' viewBox=\\'0 0 24 24\\' fill=\\'none\\' stroke=\\'%238a2be2\\' stroke-width=\\'2\\'><rect width=\\'18\\' height=\\'18\\' x=\\'3\\' y=\\'3\\' rx=\\'2\\'/><path d=\\'m9 9 6 6\\'/><path d=\\'m15 9-6 6\\'/></svg>';">
            </div>
            <div class="ext-info">
              <h3 class="ext-title" title="${ext.name}">${ext.name}</h3>
              <div class="ext-pkg" title="${ext.pkg}">${ext.pkg}</div>
            </div>
          </div>

          <div class="ext-tags">
            <span class="tag tag-version">v${ext.version || '1.4.1'}</span>
            <span class="tag tag-lang">${(ext.lang || 'en').toUpperCase()}</span>
            ${ext.nsfw === 1 ? '<span class="tag tag-nsfw">18+ NSFW</span>' : ''}
          </div>

          ${domain ? `
            <div class="ext-source-info">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              <a href="${baseUrl}" target="_blank" rel="noopener noreferrer" class="ext-source-link">${domain}</a>
            </div>
          ` : ''}
        </div>

        <div class="ext-actions">
          <a href="${apkPath}" class="btn btn-primary" download>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download APK
          </a>
          <button class="btn btn-secondary copy-link-btn" data-url="${apkPath}" title="Copy APK direct link">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
          </button>
        </div>
      `;

      // Copy APK Link Event
      const copyBtn = card.querySelector('.copy-link-btn');
      copyBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const fullUrl = new URL(copyBtn.getAttribute('data-url'), window.location.href).href;
        navigator.clipboard.writeText(fullUrl).then(() => {
          showToast('APK link copied to clipboard!');
        });
      });

      extensionsGrid.appendChild(card);
    });
  }

  // 4. Toast Notification
  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  // 5. Search Handlers
  searchInput.addEventListener('input', () => {
    clearSearchBtn.style.display = searchInput.value ? 'block' : 'none';
    applyFiltersAndSort();
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    searchInput.focus();
    applyFiltersAndSort();
  });

  // Shortcut key '/' to focus search
  window.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput) {
      e.preventDefault();
      searchInput.focus();
    } else if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.value = '';
      clearSearchBtn.style.display = 'none';
      searchInput.blur();
      applyFiltersAndSort();
    }
  });

  // 6. Category Tabs
  categoryTabs.addEventListener('click', (e) => {
    if (!e.target.classList.contains('filter-tab')) return;
    categoryTabs.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    e.target.classList.add('active');
    currentCategory = e.target.getAttribute('data-filter');
    applyFiltersAndSort();
  });

  // 7. Sort Dropdown
  sortSelect.addEventListener('change', () => {
    currentSort = sortSelect.value;
    applyFiltersAndSort();
  });

  // Reset Filters
  resetFiltersBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    categoryTabs.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    categoryTabs.querySelector('[data-filter="all"]').classList.add('active');
    currentCategory = 'all';
    currentSort = 'name-asc';
    sortSelect.value = 'name-asc';
    applyFiltersAndSort();
  });

  // 8. Copy Repo URL
  copyRepoBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(repoUrlInput.value).then(() => {
      showToast('Repository URL copied! Paste it in Tachiyomi or Mihon.');
    });
  });

  // 9. Guide Modal
  guideBtn.addEventListener('click', () => {
    guideModal.style.display = 'flex';
  });

  closeModalBtn.addEventListener('click', () => {
    guideModal.style.display = 'none';
  });

  modalGotItBtn.addEventListener('click', () => {
    guideModal.style.display = 'none';
  });

  window.addEventListener('click', (e) => {
    if (e.target === guideModal) {
      guideModal.style.display = 'none';
    }
  });

  // Initial load
  loadExtensions();
});
