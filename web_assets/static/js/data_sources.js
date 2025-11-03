
/**
 * Fetch data sources from server and manage them.
 */
const DataSources = {

    // Store loaded data sources
    loadedData: {},

    /**
     * Add a new data source and fetch its data.
     * @param {string} dataSourceId Data source identifier.
     * @param {string} eventName Event name to fetch.
     * @param {Array<string>} tags Optional tags to filter the events.
     * @param {number} maxAgeDays Maximum age of events in days.
     * @param {boolean} lastUniqueByTag If true, only the last event for each tag will be kept.
     * @param {number} maxResults Maximum number of results to fetch (0 for no limit).
     */
    addDataSource: function (dataSourceId, eventName, tags, maxAgeDays, lastUniqueByTag = false, maxResults = 0) 
    {
        // init data source
        console.log("Initializing data source: " + dataSourceId);
        DataSources.loadedData[dataSourceId] = null;

        // fetch the data
        DataFetcher.fetchEventData(eventName, maxAgeDays, tags, lastUniqueByTag, maxResults)
            .then(data => {
                DataSources.loadedData[dataSourceId] = {
                    events: data,
                    tags: tags,
                    maxAgeDays: maxAgeDays,
                    eventName: eventName,
                    maxResults: maxResults,
                    lastUniqueByTag: lastUniqueByTag
                };
            })
            .catch(error => {
                console.error("Error fetching data for source " + dataSourceId + ":", error);
            });
    },
}