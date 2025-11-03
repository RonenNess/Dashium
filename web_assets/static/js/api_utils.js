
/**
 * Data fetching utilities.
 */
const DataFetcher = 
{
    /**
     * Fetch events data from server.
     * @param {string} name - Event name to get.
     * @param {number} maxAgeDays - Maximum age of events to fetch (in days).
     * @param {string[]|null} tags - Array of tags to filter events, or null to get all.
     * @param {boolean} lastUniqueByTag - If true, only the last event for each tag will be kept.
     * @param {number} maxResults - Maximum number of results to fetch (0 for no limit).
     * @returns {Promise<Object[]>} Promise resolving to fetched event data array.
     */
    fetchEventData: function(name, maxAgeDays, tags, lastUniqueByTag = false, maxResults = 0)
    {
        return new Promise((resolve, reject) => {

            // Build query parameters
            const params = new URLSearchParams();
            if (name) params.append('name', name);
            if (maxAgeDays) params.append('max_age_days', maxAgeDays);
            
            if (tags && tags.length > 0) {
                tags.forEach(tag => params.append('tags', tag));
            }

            if (maxResults && maxResults > 0) {
                params.append('max_results', maxResults);
            }

            if (lastUniqueByTag) {
                params.append('last_unique_by_tag', 'true');
            }

            // Make GET request
            fetch(`/api/events?${params.toString()}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Extract events from response
                    if (data && data.data) {
                        resolve(data.data);
                    } else {
                        reject(new Error('Invalid response format: missing "data" key.'));
                    }
                })
                .catch(error => {
                    console.error('Error fetching event data:', error);
                    reject(error);
                });
        });
    }
}

