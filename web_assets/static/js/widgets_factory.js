/**
 * Helper function to normalize data source IDs to consistent format.
 * @param {Array<String|Object>} dataSources Array of data source IDs or objects with dataSourceId and tags.
 * @returns {Array<Object>} Array of normalized data source objects with dataSourceId and tags.
 */
function normalizedataSources(dataSources) 
{
    if (!dataSources) return [];
    
    return dataSources.map(item => {
        if (typeof item === 'string') 
        {
            return { dataSourceId: item, tags: null };
        } 
        else if (typeof item === 'object' && item.id) 
        {
            return { 
                dataSourceId: item.id, 
                tags: item.tags || null,
                mutators: item.mutators || null,
                additionalInfoFilter: item.additional_info_filter || null
            };
        } 
        else 
        {
            throw new Error(`Invalid data source format: ${JSON.stringify(item)}. Expected string or object with dataSourceId property.`);
        }
    });
}

/**
 * Helper function to filter events by tags.
 * @param {Array} events Array of events to filter by, or null for no filtering.
 * @param {Array<String>|null} tags Array of tags to filter by, or null for no filtering.
 * @returns {Array} Filtered array of events.
 */
function filterEventsByTags(events, tags) 
{
    // no tags to filter? return as-is
    if (!tags || tags.length === 0) {
        return events; // No tag filtering
    }
    
    // tags are string? convert to array
    if (typeof tags === 'string') {
        tags = [tags]; // Convert single string to array
    }

    // return filtered events by tag
    return events.filter(event => {
        return tags.includes(event.tag);
    });
}

/**
 * Helper function to generate time range timestamps based on max age days and aggregation interval.
 * @param {Number|null} maxAgeDays Maximum age in days, or null if not specified.
 * @param {String} aggregationInterval Aggregation interval ('hour', 'day', '10m', etc.) or 'disabled'.
 * @param {Array} existingEvents Existing events to determine oldest timestamp if maxAgeDays is not set.
 * @returns {Array<String>} Array of formatted timestamp strings for X-axis.
 */
function generateTimeRangeTimestamps(maxAgeDays, aggregationInterval, existingEvents) 
{
    // get now and oldest date
    const now = new Date();
    let oldestDate;
    
    // Use max age days to determine the oldest date
    if (maxAgeDays && maxAgeDays > 0) 
    {
        oldestDate = new Date(now.getTime() - (maxAgeDays * 24 * 60 * 60 * 1000));
    }
    // Find oldest event timestamp 
    else if (existingEvents && existingEvents.length > 0) 
    {
        const sortedEvents = existingEvents.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        oldestDate = new Date(sortedEvents[0].timestamp);
    }
    // No data and no max age, return empty array 
    else 
    {
        return [];
    }
    
    // should we show the time component of the timestamps?
    let showTime = true;

    // Determine step size based on aggregation interval
    let stepMs;
    switch (aggregationInterval) {
        case '10m':
            stepMs = 10 * 60 * 1000; // 10 minutes
            break;
        case '30m':
            stepMs = 30 * 60 * 1000; // 30 minutes
            break;
        case 'hour':
            stepMs = 60 * 60 * 1000; // 1 hour
            break;
        case 'day':
            stepMs = 24 * 60 * 60 * 1000; // 1 day
            showTime = false;
            break;
        case 'week':
            stepMs = 7 * 24 * 60 * 60 * 1000; // 1 week
            showTime = false;
            break;
        case 'month':
            stepMs = 30 * 24 * 60 * 60 * 1000; // ~1 month (30 days)
            showTime = false;
            break;
        case 'year':
            stepMs = 365 * 24 * 60 * 60 * 1000; // ~1 year (365 days)
            showTime = false;
            break;
        default:
            // Default to 5 minutes
            stepMs = 5 * 60 * 1000; // 5 minute
            break;
    }
    
    // get oldest date rounded down to aggregation boundary
    let currentDate = new Date(oldestDate.getTime());
    switch (aggregationInterval) {
        case '10m':
            currentDate.setMinutes(Math.floor(currentDate.getMinutes() / 10) * 10, 0, 0);
            break;
        case '30m':
            currentDate.setMinutes(Math.floor(currentDate.getMinutes() / 30) * 30, 0, 0);
            break;
        case 'hour':
            currentDate.setMinutes(0, 0, 0);
            break;
        case 'day':
            currentDate.setHours(0, 0, 0, 0);
            break;
        case 'week':
            // Round to Monday
            const dayOfWeek = currentDate.getDay();
            const daysToSubtract = (dayOfWeek + 6) % 7; // Convert Sunday=0 to Monday=0
            currentDate.setDate(currentDate.getDate() - daysToSubtract);
            currentDate.setHours(0, 0, 0, 0);
            break;
        case 'month':
            currentDate.setDate(1);
            currentDate.setHours(0, 0, 0, 0);
            break;
        case 'year':
            currentDate.setMonth(0, 1);
            currentDate.setHours(0, 0, 0, 0);
            break;
        default:
            currentDate.setMinutes(0, 0, 0);
            break;
    }
    
    // generate timestamps until now
    const timestamps = [];
    while (currentDate <= now) 
    {
        // Format as local time to avoid timezone conversion issues
        let localTimestamp;
        if (showTime) {
            localTimestamp = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(currentDate.getDate()).padStart(2, '0')} ${String(currentDate.getHours()).padStart(2, '0')}:${String(currentDate.getMinutes()).padStart(2, '0')}:${String(currentDate.getSeconds()).padStart(2, '0')}`;
        }
        else {
            localTimestamp = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(currentDate.getDate()).padStart(2, '0')}`;
        }
        timestamps.push(localTimestamp);
        currentDate = new Date(currentDate.getTime() + stepMs);
    }
    
    // return timestamps
    return timestamps;
}

/**
 * Helper function to assign values to timestamp buckets.
 * @param {Array} values Array of value objects with timestamp, value, and name properties.
 * @param {Array<String>} timestampList Array of timestamp strings to use as buckets.
 * @returns {Array} Array of objects with timestamp and aggregated value for each bucket.
 */
function assignValuesToTimestamp(values, timestampList) 
{
    // no values or no timestamps? return empty
    if (!values || !timestampList || timestampList.length === 0) {
        return [];
    }
    
    // Convert timestamps to numeric milliseconds for proper comparison
    const timestampBuckets = timestampList.map(ts => ({
        timestamp: ts,
        timestampMs: new Date(ts).getTime(),
        value: null
    }));
    
    // Sort buckets by timestamp (should already be sorted but ensure it)
    timestampBuckets.sort((a, b) => a.timestampMs - b.timestampMs);
    
    // Process each value and assign to appropriate bucket
    values.forEach(valueObj => {
        const valueTimestampMs = new Date(valueObj.timestamp).getTime();
        
        // Find the bucket this value belongs to
        for (let i = 0; i < timestampBuckets.length; i++) {
            const currentBucketMs = timestampBuckets[i].timestampMs;
            const nextBucketMs = i < timestampBuckets.length - 1 ? timestampBuckets[i + 1].timestampMs : Infinity;
            
            // Value belongs to this bucket if: currentBucket <= value < nextBucket
            if (valueTimestampMs >= currentBucketMs && valueTimestampMs < nextBucketMs) {
                if (timestampBuckets[i].value === null) {
                    timestampBuckets[i].value = valueObj.value;
                }
                else {
                    timestampBuckets[i].value = (timestampBuckets[i].value + valueObj.value) / 2;
                }
                break;
            }
        }
    });
    
    // Return final array with timestamp and aggregated values
    return timestampBuckets.map(bucket => ({
        timestamp: bucket.timestamp,
        value: bucket.value,
        name: values.length > 0 ? values[0].name : "unknown"
    }));
}

/**
 * Helper function to determine the oldest max age days from multiple data sources.
 * @param {Array} dataSourceConfigs Array of normalized data source configuration objects.
 * @returns {Number|null} The oldest (largest) max age days value, or null if none specified.
 */
function getOldestMaxAgeDays(dataSourceConfigs) {
    let oldestMaxAge = null;
    
    for (const config of dataSourceConfigs) {
        const sourceId = config.dataSourceId;
        const sourceData = DataSources.loadedData[sourceId];
        
        if (sourceData && sourceData.maxAgeDays && sourceData.maxAgeDays > 0) {
            if (oldestMaxAge === null || sourceData.maxAgeDays > oldestMaxAge) {
                oldestMaxAge = sourceData.maxAgeDays;
            }
        }
    }
    
    return oldestMaxAge;
}

/**
 * Helper function to parse timestamp string to milliseconds, handling both string and numeric formats.
 * @param {string|number} timestamp Timestamp in "YYYY-MM-DD HH:mm:ss" format or numeric milliseconds.
 * @returns {number} Timestamp in milliseconds since epoch.
 */
function parseTimestampToMs(timestamp) {
    // If already numeric, use directly
    if (typeof timestamp === 'number') {
        return timestamp;
    }
    
    // Parse "YYYY-MM-DD HH:mm:ss" format explicitly to avoid timezone issues
    const parts = timestamp.toString().match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
    if (parts) {
        const [, year, month, day, hour, minute, second] = parts;
        const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), parseInt(hour), parseInt(minute), parseInt(second));
        return date.getTime();
    } else {
        // Fallback to regular Date parsing
        return new Date(timestamp).getTime();
    }
}

/**
 * Helper function to process data sources for time-axis charts (both line and bar graphs).
 * @param {Array} dataSources Array of data sources to process.
 * @param {Array} normalizedDataSources Array of normalized data source configurations.
 * @param {string} aggregationInterval Time aggregation interval or 'disabled'.
 * @param {*} defaultValue Default value to use for empty data (null for lines, 0 for bars).
 * @returns {Array} Array of series updates with coordinate pairs.
 */
function processDataSourcesForTimeAxis(dataSources, normalizedDataSources, aggregationInterval, defaultValue = null) {
    const seriesUpdates = [];
    
    if (aggregationInterval === 'disabled') {
        // No aggregation - use raw event timestamps and values directly
        dataSources.forEach(events => {
            if (events && events.length > 0) {
                // Convert each event directly to coordinate pair [timestamp, value]
                const coordinatePairs = events.map(event => {
                    if (event && event.timestamp !== undefined) {
                        const timestampMs = parseTimestampToMs(event.timestamp);
                        return [timestampMs, event.value || defaultValue];
                    }
                    return null;
                }).filter(pair => pair !== null); // Remove null entries
                
                // Sort by timestamp for proper chart rendering
                coordinatePairs.sort((a, b) => a[0] - b[0]);
                seriesUpdates.push({ data: coordinatePairs });
            } else {
                // No events for this data source
                seriesUpdates.push({ data: [] });
            }
        });
    } else {
        // Time aggregation enabled - use interval generation and alignment
        const oldestMaxAgeDays = getOldestMaxAgeDays(normalizedDataSources);
        const allExistingEvents = dataSources.flat();
        
        const xAxisTimestamps = generateTimeRangeTimestamps(oldestMaxAgeDays, aggregationInterval, allExistingEvents);
        
        dataSources.forEach(events => {
            if (events && events.length > 0) {
                // Use assignValuesToTimestamp to properly align values with timestamps
                const alignedData = assignValuesToTimestamp(events, xAxisTimestamps);
                // Format as coordinate pairs [timestamp, value] for time axis
                const coordinatePairs = alignedData.map(item => {
                    const timestampMs = parseTimestampToMs(item.timestamp);
                    return [timestampMs, item.value || defaultValue];
                });
                seriesUpdates.push({ data: coordinatePairs });
            } else {
                // No events - create coordinate pairs with default values
                const defaultCoordinates = xAxisTimestamps.map(timestamp => {
                    const timestampMs = parseTimestampToMs(timestamp);
                    return [timestampMs, defaultValue];
                });
                seriesUpdates.push({ data: defaultCoordinates });
            }
        });
    }
    
    return seriesUpdates;
}

/**
 * Helper function to get common X-axis configuration for time-axis charts.
 * @returns {Object} X-axis configuration object for ECharts.
 */
function getTimeAxisConfiguration(aggregationInterval) {
    if (aggregationInterval === 'disabled' || aggregationInterval === '10m' || aggregationInterval === '30m' || aggregationInterval === 'hour') 
    {
        return {
            type: 'time',
            axisLabel: {
                hideOverlap: true,
                formatter: function (value) {
                    const date = new Date(value);
                    return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
                }
            }
        };
    }
    else 
    {
        return {
            type: 'time',
            axisLabel: {
                hideOverlap: true,
                formatter: function (value) {
                    const date = new Date(value);
                    return `${String(date.getFullYear()).padStart(2, '0')}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
                }
            }
        };
    }
}

/**
 * Represents a generic widget instance.
 */
class Widget
{
    /**
     * Creates an instance of the Widget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     */
    constructor(title, description, widthColumns, height, dataSources)
    {
        this.title = title;
        this.description = description;
        this.widthColumns = widthColumns;
        this.height = height;
        this.dataSources = normalizedataSources(dataSources);
        this.showNoDataMessageIfNoData = true;
        this._dirty = true;
    }

    /**
     * Resolve color value.
     * @param {String|number} colorValue Color value: number, hex color value with #, or named color.
     * @param {*} index Element index for default color selection.
     * @returns Color value string.
     */
    resolveColorValue(colorValue, index)
    {
        const defaultColors = WidgetsFactory.defaultColors;
        const defaultColorNames = WidgetsFactory.defaultColorNames;

        // if color is a number, use as index into default colors
        if (colorValue && !isNaN(colorValue)) {
            colorValue = defaultColors[parseInt(colorValue) % defaultColors.length];
        }
        // if there's no color value, use default based on index
        else if (!colorValue) {
            colorValue = defaultColors[index % defaultColors.length];
        }
        // if color is a named color, map to default color
        else if (typeof colorValue === 'string' && defaultColorNames.hasOwnProperty(colorValue.toLowerCase())) {
            colorValue = defaultColors[defaultColorNames[colorValue.toLowerCase()]];
        }

        // return resolved color value
        return colorValue;
    }

    /**
     * Get the DOM element for this widget.
     * @returns {HTMLElement|null} The widget's DOM element, or null if not applicable.
     */
    getDomElement()
    {
        return null;
    }

    /**
     * Get the chart instance for this widget.
     * @returns {ECharts} The widget echart instance, if have one.
     */
    getChartInstance()
    {
        return null;
    }

    /**
     * Update / init data for this widget.
     * @param {Array<Array<dict>>} dataSources Array of data sources to update.
     */
    update(dataSources)
    {
    }

    /**
     * Get if this widget is dirty and need data update.
     */
    get isDirty()
    {
        return this._dirty;
    }

    /**
     * Mark the widget as dirty and needing an update.
     * */
    markDirty()
    {
        this._dirty = true;
    }

    /**
     * Get time aggregation settings for this widget.
     * @param {Boolean} resolvePageDefault Whether to resolve the page default value.
     * @returns {Object|null} Time aggregation settings or null if not applicable.
     */
    getTimeAggregationSettings(resolvePageDefault = true)
    {
        // got time aggregation?
        if (this._timeAggregation) 
        {
            // get value, either from selection or default
            let value = this._timeAggregation.allowSelection ? 
                this.getDomElement().parentElement.getElementsByClassName('time-agg-selection')[0].value : 
                this._timeAggregation.defaultValue;

            // page default?
            if (resolvePageDefault && value === "page_default") {
                value = WidgetsFactory._defaultTimeAggregation ||  "disabled";
            }

            // return aggregation settings
            return {
                interval: value,
                aggregationType: this._timeAggregation.aggregationType
            };
        }

        // no aggregation
        return null;
    }

    /**
     * Add time interval selection to the widget.
     * @param {String} defaultValue Default selected value.
     * @param {Boolean} allowSelection Show or hide the selection box (you can still set value without box, making it const).
     * @param {String} aggregationFunction Aggregation function to use (e.g. "average").
     * @param {Array|null} choices Optional array of choices for the selection.
     */
    addTimeAggregation(defaultValue = "page_default", allowSelection = true, aggregationFunction = "average", choices = null)
    {
        // store settings
        this._timeAggregation = {
            aggregationType: aggregationFunction,
            allowSelection: allowSelection,
            defaultValue: defaultValue
        }
        this._dirty = true;

        // default choices: all
        if (!choices) {
            choices = ["page_default", "disabled", "10m", "30m", "hour", "day", "week"];
        }

        // add selection
        if (allowSelection) {
            const containerDom = this.getDomElement();
            const chart = this.getChartInstance();
            const html = `<div class="col-lg-4 col-md-5 col-sm-6" style="display: ${allowSelection ? 'block' : 'none'}; margin-top:10px; margin-bottom:-10px; min-height:37px">
                <span>Time Interval (${aggregationFunction.split('_')[0]}) </span>
                <select class="time-agg-selection form-select form-select-sm" name="intervalSelect">
                <option style="${choices.includes("page_default") ? '' : 'display:none;'}" value="page_default" ${defaultValue === "page_default" ? 'selected' : ''}>Use Page Default</option>
                <option style="${choices.includes("disabled") ? '' : 'display:none;'}" value="disabled" ${defaultValue === "disabled" ? 'selected' : ''}>No Aggregation</option>
                <option style="${choices.includes("10m") ? '' : 'display:none;'}" value="10m" ${defaultValue === "10m" ? 'selected' : ''}>10 minutes</option>
                <option style="${choices.includes("30m") ? '' : 'display:none;'}" value="30m" ${defaultValue === "30m" ? 'selected' : ''}>30 minutes</option>
                <option style="${choices.includes("hour") ? '' : 'display:none;'}" value="hour" ${defaultValue === "hour" ? 'selected' : ''}>Hour</option>
                <option style="${choices.includes("day") ? '' : 'display:none;'}" value="day" ${defaultValue === "day" ? 'selected' : ''}>Day</option>
                <option style="${choices.includes("week") ? '' : 'display:none;'}" value="week" ${defaultValue === "week" ? 'selected' : ''}>Week</option>
                </select>
            </div>`;

            // append to options bar
            containerDom.parentElement.getElementsByClassName('options-bar')[0].innerHTML += html;
            containerDom.parentElement.getElementsByClassName('time-agg-selection')[0].addEventListener('change', (event) => {
                this._dirty = true;
            });
        }
    }
    
    /**
     * Called after widget data is updated.
     * @param {Array} data The updated data for the widget.
     */
    postDataUpdate(data)
    {
        // get dom element
        const domElement = this.getDomElement();

        // if this element has data sources
        if (this.dataSources && this.dataSources.length) {

            // is empty?
            let isEmpty = true;
            for (const item of data) {
                if (item && item.length > 0) {
                    isEmpty = false;
                    break;
                }
            }

            // remove loading spinner
            const spinner = domElement.parentElement.getElementsByClassName("loading-spinner-element")[0];
            if (spinner) { spinner.setHTMLUnsafe(""); }

            // Show "No Data" message if applicable
            if (this.showNoDataMessageIfNoData) {
                const noDataMessage = domElement.parentElement.getElementsByClassName("no-data-message")[0];
                if (noDataMessage) { noDataMessage.style.display = isEmpty ? "block" : "none"; }
            }
        }

        // make the chart responsive to screen size changes
        const chart = this.getChartInstance();
        if (chart) {
            if (this._prevResizeHandler) { window.removeEventListener('resize', this._prevResizeHandler); }
            this._prevResizeHandler = () => chart.resize();
            window.addEventListener('resize', this._prevResizeHandler);
        }

        // no longer dirty
        this._dirty = false;
    }
}


/**
 * Represents a free HTML widget instance.
 */
class FreeHtmlWidget extends Widget
{
    /**
     * Creates an instance of the FreeHtmlWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {String} htmlContent HTML content to display.
     */
    constructor(title, description, widthColumns, height, htmlContent)
    {
        // call parent constructor
        super(title, description, widthColumns, height, null);
        
        // create html widget
        let containerDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, false, true);
        containerDom.innerHTML = htmlContent;
        this._containerDom = containerDom;
    }

    getDomElement()
    {
        return this._containerDom;
    }
}


/**
 * Represents a counter widget instance.
 */
class CounterWidget extends Widget
{
    /**
     * Creates an instance of the CounterWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {String} counterType Type of counter (e.g. "total", "average").
     */
    constructor(title, description, widthColumns, height, dataSources, counterType)
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);

        // make sure only one data source id is provided
        if (this.dataSources.length != 1) {
            throw new Error(`Counter widget "${title}" requires exactly one data source ID.`);
        }

        // create container dom element
        let containerDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, false);
        containerDom.parentElement.style.marginTop = "2rem";
        containerDom.innerHTML = `<h1 class="counter-value"></h1>`;
        this._containerDom = containerDom;
        this.counterType = counterType;
    }

    getDomElement()
    {
        return this._containerDom;
    }
    
    update(dataSources)
    {
        // get container dom
        const containerDom = this.getDomElement();

        // get data (always from first data source for counter)
        const data = dataSources[0];

        // no data to show?
        if (!data || data.length === 0) {
            return;
        }
        containerDom.querySelector(".counter-value").innerHTML = "";

        // calculate counter value
        const value = EventsAggregator.aggregateValue(data, this.counterType);
        containerDom.querySelector(".counter-value").textContent = value;

        // unknown type
        if (value === null) {
            containerDom.querySelector(".counter-value").textContent = "ERR";
        }
    }
}


/**
 * Represents a table instance.
 */
class TableWidget extends Widget
{
    /**
     * Creates an instance of the TableWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Array<String>} tableColumns Array of table column definitions.
     * @param {Number} maxRows Maximum number of rows to display.
     * @param {Array<Object>} colorRules Array of color rules for the table.
     * @param {String} sliceFrom Where to slice the data from (e.g. "start", "end").
     */
    constructor(title, description, widthColumns, height, dataSources, tableColumns, maxRows, colorRules = null, sliceFrom = "start")
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);
                
        // create container dom element
        let containerDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, true);

        // build table headers
        let titles = "";
        for (const col of tableColumns) {
            titles += `<th>${col.title}</th>\n`;
        }

        // store arguments
        this.sliceFrom = sliceFrom;
        this.tableColumns = tableColumns;
        this.maxRows = maxRows;
        this.colorRules = colorRules;

        // build table headers
        containerDom.innerHTML = `<hr />
        <table class="table ${WidgetsFactory.isDarkMode ? 'table-dark' : ''}">
            <thead>
                <tr>
                    ${titles}
                </tr>
            </thead>
            <tbody>
            </tbody>
        </table>`;
        this._containerDom = containerDom;
    }

    getDomElement()
    {
        return this._containerDom;
    }
    
    update(dataSources)
    {
        // get arguments
        const sliceFrom = this.sliceFrom;
        const maxRows = this.maxRows;
        const colorRules = this.colorRules;
        const tableColumns = this.tableColumns;
        const containerDom = this.getDomElement();

        // iterate data sources
        let index = 1;
        for (let source of dataSources) 
        {
            // slice data if needed
            if (maxRows) 
            {
                // slice from end?
                if (sliceFrom === "end") {
                    source = source.slice(-maxRows);
                }
                // slice from start?
                else if (sliceFrom === "start") {
                    source = source.slice(0, maxRows);
                }
                // unknown slice?
                else {
                    throw new Error(`Unknown sliceFrom value "${sliceFrom}" for table widget "${title}". Defaulting to "start".`);
                }
            }

            // iterate events
            for (let i = 0; i < source.length; i++) 
            {
                // get event data
                const event = source[i];

                // set color
                let rowColor = "";
                for (const rule of (colorRules || [])) 
                {    
                    let fieldValue = {
                        "value": event.value,
                        "tag": event.tag,
                        "time": event.timestamp,
                        "additional_info": event.additional_info,
                        "event_name": event.name,
                        "index": index
                    }[rule.event_field];

                    if (EventConditions.evaluate(fieldValue, rule.condition, rule.value)) {
                        rowColor = 'table-' + rule.color;
                    }
                }

                // build row
                let rowHtml = `<tr class="${rowColor}">\n`;
                for (const col of tableColumns) 
                {
                    if (col.event_field === "value") {
                        rowHtml += `<td>${event.value}</td>\n`;
                    } 
                    else if (col.event_field === "tag") {
                        rowHtml += `<td>${event.tag}</td>\n`;
                    } 
                    else if (col.event_field === "time") {
                        rowHtml += `<td>${event.timestamp.replace('T', ' ').replace('Z', '')}</td>\n`;
                    }
                    else if (col.event_field === "additional_info") {
                        rowHtml += `<td>${event.additional_info || ""}</td>\n`;
                    }
                    else if (col.event_field === "event_name") {
                        rowHtml += `<td>${event.name}</td>\n`;
                    }
                    else if (col.event_field === "index") {
                        rowHtml += `<td>${index}</td>\n`;
                    }
                }
                rowHtml += "</tr>\n";
                containerDom.querySelector("tbody").innerHTML += rowHtml;

                // increment global index
                index++;
            }

            // check max rows
            if (maxRows && index > maxRows) {
                break;
            }
        }
    }
}



/**
 * Represents a line graph instance.
 */
class LineGraphWidget extends Widget
{
    /**
     * Creates an instance of the LineGraphWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Array<String>} style Style settings for the graph.
     * @param {Object} options Additional options for the graph.
     */
    constructor(title, description, widthColumns, height, dataSources, style, options)
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);
                
        // create chart
        let chartDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, false);
        const chart = echarts.init(chartDom, WidgetsFactory.isDarkMode ? 'dark' : null);
        this._containerDom = chartDom;

        // normalize style to array format
        let styles = [];
        if (Array.isArray(style)) {
            styles = style;
        } else {
            // single style object - use for all data sources
            for (let i = 0; i < this.dataSources.length; i++) {
                styles.push(style);
            }
        }

        // ensure we have styles for all data sources
        while (styles.length < this.dataSources.length) {
            styles.push(styles[styles.length - 1] || {});
        }

        // helper function to create markline for a style
        function createMarkLine(styleObj) {
            if (!styleObj.markline) return null;
            return {
                symbol: 'none',
                silent: true,
                label: {
                    show: Boolean(styleObj.markline.label),
                    position: 'end',
                    formatter: styleObj.markline.label
                },
                lineStyle: {
                    color: styleObj.markline.color || '#ff0000',
                    type: styleObj.markline.style || 'dashed'
                },
                data: [
                    { yAxis: styleObj.markline.value_y || undefined, xAxis: styleObj.markline.value_x || undefined }
                ]
            };
        }

        // default options
        options = options || {};
                    
        // get suffix to show on values
        const suffix = options.valuesSuffix || "";

        // build series array for multiple data sources
        const series = [];
        for (let i = 0; i < this.dataSources.length; i++) 
        {
            // get current series style
            const styleObj = styles[i % styles.length];

            // calc lines color
            let linesColor = this.resolveColorValue(styleObj.linesColor, i);
            
            series.push({
                name: styleObj.label || this.dataSources[i].dataSourceId,
                connectNulls: false, // will be set dynamically in update()
                data: [],
                type: 'line',
                smooth: Boolean(styleObj.linesSmooth),
                markLine: createMarkLine(styleObj),
                showAllSymbol: true,
                areaStyle: styleObj.areaFill ? {opacity: styleObj.areaOpacity || 0.25} : null,
                lineStyle: {
                    color: linesColor,
                    width: styleObj.linesWidth || 2,
                    type: styleObj.linesType || 'solid'
                },
                itemStyle: {
                    color: linesColor,
                    borderColor: styleObj.itemBorderColor,
                    borderWidth: styleObj.itemBorderWidth || 0
                }
            });
        }

        // build initial empty chart options
        const option = {
            tooltip: {
                valueFormatter: (value) => value + suffix,
                trigger: 'axis',  // show tooltip for all series at same x position
            },
            xAxis: {
                type: 'time',
                data: []
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}' + suffix 
                }
            },
            legend: this.dataSources.length > 1 ? {
                show: true,
                top: 'bottom',
            } : undefined,
            series: series
        };

        // Override background color in dark mode to be transparent
        if (WidgetsFactory.isDarkMode) {
            option.backgroundColor = 'transparent';
        }

        // set initial empty chart options
        chart.setOption(option);
        this._chart = chart;

        // track this chart instance for theme switching
        const chartInfo = {
            chart: chart,
            dom: chartDom,
            lastOptions: option
        };
    }

    getChartInstance()
    {
        return this._chart;
    }

    getDomElement()
    {
        return this._containerDom;
    }
    
    update(dataSources)
    {     
        // Get time aggregation settings
        const timeAggSettings = this.getTimeAggregationSettings(true);
        const aggregationInterval = timeAggSettings ? timeAggSettings.interval : 'disabled';
        
        // Determine connectNulls based on aggregation interval
        const connectNulls = aggregationInterval === 'disabled';
        
        // Process data sources using common function (null for line graphs)
        const seriesUpdates = processDataSourcesForTimeAxis(dataSources, this.dataSources, aggregationInterval, null);
        
        // Add connectNulls to each series update
        seriesUpdates.forEach(seriesUpdate => {
            seriesUpdate.connectNulls = connectNulls;
        });
        
        // Update chart (no xAxis.data needed for time axis)
        this.getChartInstance().setOption({
            xAxis: getTimeAxisConfiguration(aggregationInterval),
            series: seriesUpdates
        });
    }
}



/**
 * Represents a bar graph widget instance.
 */
class BarGraphWidget extends Widget
{
    /**
     * Creates an instance of the BarGraphWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Array<String>} style Style settings for the graph.
     * @param {Object} options Additional options for the graph.
     */
    constructor(title, description, widthColumns, height, dataSources, style, options)
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);
                
        // create chart
        let chartDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, false);
        const chart = echarts.init(chartDom, WidgetsFactory.isDarkMode ? 'dark' : null);
        this._containerDom = chartDom;

        // normalize style to array format
        let styles = [];
        if (Array.isArray(style)) {
            styles = style;
        } else {
            // single style object - use for all data sources
            for (let i = 0; i < this.dataSources.length; i++) {
                styles.push(style);
            }
        }

        // ensure we have styles for all data sources
        while (styles.length < this.dataSources.length) {
            styles.push(styles[styles.length - 1] || {});
        }

        // helper function to create markline for a style
        function createMarkLine(styleObj) {
            if (!styleObj.markline) return null;
            return {
                symbol: 'none',
                silent: true,
                label: {
                    show: Boolean(styleObj.markline.label),
                    position: 'end',
                    formatter: styleObj.markline.label
                },
                lineStyle: {
                    color: styleObj.markline.color || '#ff0000',
                    type: styleObj.markline.style || 'dashed'
                },
                data: [
                    { yAxis: styleObj.markline.value_y || undefined, xAxis: styleObj.markline.value_x || undefined }
                ]
            };
        }

        // default options
        options = options || {};
                    
        // get suffix to show on values
        const suffix = options.valuesSuffix || "";

        // build series array for multiple data sources
        const series = [];
        for (let i = 0; i < this.dataSources.length; i++) 
        {
            // get current series style
            const styleObj = styles[i % styles.length];

            // calc bar color
            let barColor = this.resolveColorValue(styleObj.barColor, i);
            
            series.push({
                name: styleObj.label || this.dataSources[i].dataSourceId,
                data: [],
                type: 'bar',
                markLine: createMarkLine(styleObj),
                barWidth: styleObj.barWidth || 'auto',
                barGap: styleObj.barGap || '20%',
                barCategoryGap: styleObj.barCategoryGap || '20%',
                itemStyle: {
                    color: barColor,
                    borderColor: styleObj.itemBorderColor,
                    borderWidth: styleObj.itemBorderWidth || 0,
                    borderRadius: styleObj.borderRadius || 0
                }
            });
        }

        // build initial empty chart options
        const option = {
            tooltip: {
                valueFormatter: (value) => value + suffix,
                trigger: 'axis',  // show tooltip for all series at same x position
            },
            xAxis: {
                type: 'time',
                data: []
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    formatter: '{value}' + suffix 
                }
            },
            legend: this.dataSources.length > 1 ? {
                show: true,
                top: 'bottom',
            } : undefined,
            series: series
        };

        // Override background color in dark mode to be transparent
        if (WidgetsFactory.isDarkMode) {
            option.backgroundColor = 'transparent';
        }

        // set initial empty chart options
        chart.setOption(option);
        this._chart = chart;

        // track this chart instance for theme switching
        const chartInfo = {
            chart: chart,
            dom: chartDom,
            lastOptions: option
        };
    }

    getChartInstance()
    {
        return this._chart;
    }

    getDomElement()
    {
        return this._containerDom;
    }
    
    update(dataSources)
    {     
        // Get time aggregation settings
        const timeAggSettings = this.getTimeAggregationSettings(true);
        const aggregationInterval = timeAggSettings ? timeAggSettings.interval : 'disabled';
        
        // Process data sources using common function (0 for bar graphs)
        const seriesUpdates = processDataSourcesForTimeAxis(dataSources, this.dataSources, aggregationInterval, 0);
        
        // Update chart (no xAxis.data needed for time axis)
        this.getChartInstance().setOption({
            xAxis: getTimeAxisConfiguration(aggregationInterval),
            series: seriesUpdates
        });
    }
}



/**
 * Represents a gauge widget instance.
 */
class GaugeWidget extends Widget
{
    /**
     * Creates an instance of the GaugeWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object} style Style settings for the gauge.
     * @param {String} aggregationType Type of aggregation to use for the gauge value.
     * @param {Boolean} showLastValueTime Whether to show the last value time.
     */
    constructor(title, description, widthColumns, height, dataSources, style, aggregationType = 'last', showLastValueTime = false)
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);

        // make sure only one data source id is provided
        if (this.dataSources.length != 1) {
            throw new Error(`Gauge widget "${title}" requires exactly one data source ID.`);
        }
                
        // create element and chart
        let chartDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, false);
        const chart = echarts.init(chartDom, WidgetsFactory.isDarkMode ? 'dark' : null);

        // normalize style
        const styleObj = style || {};
        this.style = styleObj;
        this.aggregationType = aggregationType;
        this.showLastValueTime = showLastValueTime;

        // get gauge color
        const gaugeColor = this.resolveColorValue(styleObj.gaugeColor, 0);

        // build initial empty chart options
        const option = {
            tooltip: {
                formatter: '{a} <br/>{b}: {c}'
            },
            series: [{
                name: title,
                type: 'gauge',
                min: styleObj.min || 0,
                max: styleObj.max || 100,
                splitNumber: styleObj.splitNumber || 10,
                radius: styleObj.radius || '75%',
                center: styleObj.center || ['50%', '55%'],
                startAngle: styleObj.startAngle || 225,
                endAngle: styleObj.endAngle || -45,
                clockwise: styleObj.clockwise !== false,
                data: [{
                    value: 0,
                    name: styleObj.label || title
                }],
                detail: {
                    valueAnimation: true,
                    formatter: styleObj.valueFormatter || '{value}',
                    color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000',
                    fontSize: styleObj.valueSize || 30,
                    offsetCenter: styleObj.valueOffset || [0, '70%']
                },
                title: {
                    show: styleObj.showTitle !== false,
                    fontSize: styleObj.titleSize || 14,
                    color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000',
                    offsetCenter: styleObj.titleOffset || [0, '90%']
                },
                pointer: {
                    itemStyle: {
                        color: gaugeColor
                    },
                    length: styleObj.pointerLength || '60%',
                    width: styleObj.pointerWidth || 6
                },
                progress: {
                    show: styleObj.showProgress !== false,
                    overlap: false,
                    roundCap: true,
                    clip: false,
                    itemStyle: {
                        borderWidth: 1,
                        borderColor: gaugeColor,
                        color: gaugeColor,
                        opacity: styleObj.progressOpacity || 0.8
                    }
                },
                axisLine: {
                    lineStyle: {
                        width: styleObj.axisWidth || 30,
                        color: this._processAxisColors(styleObj.axisColors || [
                            [30, '#67e0e3'],
                            [70, '#37a2da'], 
                            [100, '#fd666d']
                        ])
                    }
                },
                axisTick: {
                    distance: styleObj.tickDistance || -45,
                    length: styleObj.tickLength || 8,
                    lineStyle: {
                        color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000',
                        width: 2
                    }
                },
                splitLine: {
                    distance: styleObj.splitDistance || -52,
                    length: styleObj.splitLength || 14,
                    lineStyle: {
                        color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000',
                        width: 3
                    }
                },
                axisLabel: {
                    color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000',
                    distance: styleObj.labelDistance || -20,
                    fontSize: styleObj.labelSize || 12
                },
                anchor: {
                    show: styleObj.showAnchor !== false,
                    showAbove: true,
                    size: styleObj.anchorSize || 25,
                    itemStyle: {
                        borderWidth: styleObj.anchorBorderWidth || 10,
                        borderColor: gaugeColor,
                        color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000'
                    }
                }
            }]
        };

        // Override background color in dark mode to be transparent
        if (WidgetsFactory.isDarkMode) {
            option.backgroundColor = 'transparent';
        }

        // set initial empty chart options
        chart.setOption(option);

        // track this chart instance for theme switching
        const chartInfo = {
            chart: chart,
            dom: chartDom,
            lastOptions: option
        };

        // do basic init
        this._containerDom = chartDom;
        this._chart = chart;
    }

    getChartInstance()
    {
        return this._chart;
    }

    getDomElement()
    {
        return this._containerDom;
    }

    /**
     * Process axis colors for gauge widget.
     * Converts from [threshold, colorName] format to [fraction, hexColor] format.
     * @param {Array} axisColors Array of [threshold, color] pairs where threshold is 0-100 and color is name or hex.
     * @returns {Array} Processed array of [fraction, hexColor] pairs for ECharts.
     */
    _processAxisColors(axisColors)
    {
        if (!axisColors || !Array.isArray(axisColors)) {
            return [[0.3, '#67e0e3'], [0.7, '#37a2da'], [1, '#fd666d']];
        }

        return axisColors.map(([threshold, color]) => {
            // Convert threshold from percentage (0-100) to fraction (0-1)
            const fraction = Math.min(1, Math.max(0, threshold / 100));
            
            // Resolve color name to hex color
            const resolvedColor = this.resolveColorValue(color);
            
            return [fraction, resolvedColor];
        });
    }

    /**
     * Get the appropriate color for a given gauge value based on axis color zones.
     * @param {number} value The current gauge value.
     * @returns {string} The hex color for the value's zone.
     */
    _getColorForValue(value)
    {
        // Get processed axis colors or use defaults
        const axisColors = this._processAxisColors(this.style.axisColors);
        
        // Convert value to percentage for comparison
        const min = this.style.min || 0;
        const max = this.style.max || 100;
        const percentage = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
        
        // Find the appropriate color zone
        for (let i = 0; i < axisColors.length; i++) {
            const [thresholdFraction, color] = axisColors[i];
            const thresholdPercentage = thresholdFraction * 100;
            
            if (percentage <= thresholdPercentage) {
                return color;
            }
        }
        
        // If value exceeds all thresholds, use the last color
        return axisColors.length > 0 ? axisColors[axisColors.length - 1][1] : '#37a2da';
    }
    
    update(dataSources)
    {
        // get data (always from first data source for gauge)
        const data = dataSources[0];

        // no data to show?
        if (!data || data.length === 0) {
            return;
        }

        // calculate gauge value using aggregation
        const value = EventsAggregator.aggregateValue(data, this.aggregationType);
        const positiveValue = Math.abs(value || 0); // ensure positive values for gauge
        
        // show last value time if needed
        if (this.showLastValueTime) {
            const lastEvent = data[data.length - 1];
            const lastTime = new Date(lastEvent.timestamp);
            this._containerDom.parentElement.getElementsByClassName('widget-subtitle')[0].textContent = `Updated: ${lastTime.toLocaleString()}`;
        }

        // Determine color to use (dynamic or constant)
        let colorToUse;
        if (this.style.useDynamicColors !== false) { // default to true unless explicitly disabled
            colorToUse = this._getColorForValue(positiveValue);
        } else {
            // Use the original gauge_color setting
            colorToUse = this.resolveColorValue(this.style.gaugeColor, 0);
        }
        
        // Update chart with new data and colors
        const updateOption = {
            series: [{
                data: [{
                    value: positiveValue,
                    name: this.style.label || this.title
                }],
                pointer: {
                    itemStyle: {
                        color: colorToUse
                    }
                },
                progress: {
                    itemStyle: {
                        borderColor: colorToUse,
                        color: colorToUse
                    }
                },
                anchor: {
                    itemStyle: {
                        borderColor: colorToUse,
                        color: WidgetsFactory.isDarkMode ? '#1a1a1a' : '#ffffff' // keep center hollow but border matches
                    }
                }
            }]
        };

        // update chart
        this.getChartInstance().setOption(updateOption);
    }
}


/**
 * Represents a pie chart widget instance.
 */
class PieChartWidget extends Widget
{
    /**
     * Creates an instance of the PieChartWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object} style Style settings for the pie chart. Donut options: donut (boolean), innerRadius (string), outerRadius (string), showCenterText (boolean), centerTextFormatter (string), centerTextSize (number), centerTextColor (string).
     */
    constructor(title, description, widthColumns, height, dataSources, style)
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);
                
        // create element and chart
        let chartDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, false);
        const chart = echarts.init(chartDom, WidgetsFactory.isDarkMode ? 'dark' : null);

        // normalize style
        const styleObj = style || {};
        this.style = styleObj;

        // get colors
        let colors;
        if (styleObj.colors && Array.isArray(styleObj.colors)) {
            // Process provided colors through resolveColorValue
            colors = styleObj.colors.map((color, index) => this.resolveColorValue(color, index));
        } else {
            // Use default colors as-is (they're already hex values)
            colors = WidgetsFactory.defaultColors.slice(); // create a copy
        }
        
        // Store colors for use in updates
        this._colors = colors;
        if (this._colors.length > this.dataSources.length) {
            this._colors = this._colors.slice(0, this.dataSources.length);
        }

        // determine radius configuration for donut/pie chart
        let radiusConfig;
        if (styleObj.donut === true) {
            // Donut chart - use inner and outer radius
            const innerRadius = styleObj.innerRadius || '20%';
            const outerRadius = styleObj.outerRadius || styleObj.radius || '50%';
            radiusConfig = [innerRadius, outerRadius];
        } else {
            // Regular pie chart - single radius value
            radiusConfig = styleObj.radius || '50%';
        }

        // build initial empty chart options
        const option = {
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                show: styleObj.showLegend !== false,
                orient: styleObj.legendOrient || 'horizontal',
                left: 'center',
                top: 'bottom',
                textStyle: {
                    color: WidgetsFactory.isDarkMode ? '#ffffff' : '#000000',
                    fontSize: 14
                },
                // Force legend to be visible with explicit styling
                backgroundColor: WidgetsFactory.isDarkMode ? 'rgba(0,0,0,0.2)' : 'rgba(255,255,255,0.2)',
                borderColor: WidgetsFactory.isDarkMode ? '#666' : '#ccc',
                borderWidth: 1,
                padding: 8,
                itemGap: 10
            },
            series: [{
                name: title,
                type: 'pie',
                radius: radiusConfig,
                center: styleObj.center || ['50%', '50%'],
                data: [],
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                },
                label: {
                    show: Boolean(styleObj.showLabels !== false), // default true unless explicitly false
                    position: styleObj.labelPosition || 'outside',
                    formatter: styleObj.labelFormatter || '{b}: {c}'
                },
                labelLine: {
                    show: Boolean(styleObj.showLabelLines !== false) // default true unless explicitly false
                },
                itemStyle: {
                    borderWidth: styleObj.borderWidth || 0,
                    borderColor: styleObj.borderColor || '#fff'
                }
            }],
            color: colors
        };

        // Override background color in dark mode to be transparent
        if (WidgetsFactory.isDarkMode) {
            option.backgroundColor = 'transparent';
        }

        // set initial empty chart options
        chart.setOption(option);

        // track this chart instance for theme switching
        const chartInfo = {
            chart: chart,
            dom: chartDom,
            lastOptions: option
        };

        // do basic init
        this._containerDom = chartDom;
        this._chart = chart;
    }

    getChartInstance()
    {
        return this._chart;
    }

    getDomElement()
    {
        return this._containerDom;
    }
    
    update(dataSources)
    {
        // Function to process event data for pie chart display
        const processEventDataForPieChart = (allDataSources, aggregationType) => 
        {
            // no data?
            if (!allDataSources || allDataSources.length === 0) {
                return [];
            }

            const pieData = [];
            
            // Process each data source as a separate pie segment
            for (let i = 0; i < allDataSources.length; i++) 
            {
                const events = allDataSources[i];
                const sourceConfig = this.dataSources[i];
                let sourceId = sourceConfig.dataSourceId;
                if (sourceConfig.tags && sourceConfig.tags.length > 0) {
                    sourceId += ` [${sourceConfig.tags.join(', ')}]`;
                }
                const label = this.style.labels && this.style.labels[i] ? this.style.labels[i] : sourceId;
                
                if (!events || events.length === 0) {
                    pieData.push({
                        name: label,
                        value: 0
                    });
                    continue;
                }

                // Use the existing EventsAggregator to calculate value
                const value = EventsAggregator.aggregateValue(events, aggregationType);

                // push value
                pieData.push({
                    name: label,
                    value: Math.abs(value || 0) // ensure positive values for pie chart, handle null case
                });
            }
            
            return pieData;
        }

        // Process the data for pie chart display
        const aggregationType = this.style.aggregationType || 'sum';
        const pieData = processEventDataForPieChart(dataSources, aggregationType);
        
        // Calculate total for center text if donut with center text enabled
        let centerTextOption = null;
        if (this.style.donut && this.style.showCenterText) 
        {
            const total = pieData.reduce((sum, item) => sum + (item.value || 0), 0);
            const centerTextValue = this.style.centerTextFormatter ? 
                this.style.centerTextFormatter.replace('{total}', total.toString()) : 
                total.toString();
                
            centerTextOption = {
                graphic: {
                    elements: [{
                        type: 'text',
                        left: 'center',
                        top: 'middle',
                        style: {
                            text: centerTextValue,
                            fontSize: this.style.centerTextSize || 24,
                            fontWeight: 'bold',
                            fill: this.style.centerTextColor || (WidgetsFactory.isDarkMode ? '#ffffff' : '#000000'),
                            textAlign: 'center',
                            textVerticalAlign: 'middle'
                        }
                    }]
                }
            };
        }
        
        // Update chart with new data and force legend
        const updateOption = {
            legend: {
                show: true,
                data: pieData.map(item => item.name) // explicitly set legend data
            },
            series: [{
                data: pieData
            }],
            color: this._colors // Re-apply the colors array on each update
        };
        
        // Add center text graphic if configured
        if (centerTextOption) {
            Object.assign(updateOption, centerTextOption);
        }

        // update chart
        this.getChartInstance().setOption(updateOption);
    }
}



/**
 * Represents a scatter map widget instance.
 */
class ScatterMapWidget extends Widget
{
    /**
     * Creates an instance of the ScatterMapWidget class.
     * @param {String} title Widget title.
     * @param {String} description Widget description.
     * @param {Number} widthColumns Widget width in columns.
     * @param {Number} height Widget height in pixels.
     * @param {Array<String|Object>} dataSources Array of data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object} style Style settings for the scatter plot.
     * @param {Object} options Additional options for the scatter plot.
     */
    constructor(title, description, widthColumns, height, dataSources, style, options)
    {
        // call parent constructor
        super(title, description, widthColumns, height, dataSources);
                
        // create chart
        let chartDom = HtmlUtils.createWidgetContainer(title, description, widthColumns, height, true, false);
        const chart = echarts.init(chartDom, WidgetsFactory.isDarkMode ? 'dark' : null);
        this._containerDom = chartDom;

        // normalize style to array format
        let styles = [];
        if (Array.isArray(style)) {
            styles = style;
        } else {
            // single style object - use for all data sources
            for (let i = 0; i < this.dataSources.length; i++) {
                styles.push(style);
            }
        }

        // ensure we have styles for all data sources
        while (styles.length < this.dataSources.length) {
            styles.push(styles[styles.length - 1] || {});
        }

        // default options
        options = options || {};
                    
        // get suffix to show on values
        const suffixX = options.valuesSuffixX || "";
        const suffixY = options.valuesSuffixY || "";

        // build series array for multiple data sources
        const series = [];
        for (let i = 0; i < this.dataSources.length; i++) 
        {
            // get current series style
            const styleObj = styles[i % styles.length];

            // calc scatter color
            let scatterColor = this.resolveColorValue(styleObj.color, i);
            
            series.push({
                name: styleObj.label || this.dataSources[i].dataSourceId,
                data: [],
                type: 'scatter',
                symbolSize: styleObj.symbolSize || 10,
                symbol: styleObj.symbol || 'circle',
                itemStyle: {
                    color: scatterColor,
                    borderColor: styleObj.borderColor || scatterColor,
                    borderWidth: styleObj.borderWidth || 0,
                    opacity: styleObj.opacity || 0.8
                },
                emphasis: {
                    focus: 'series',
                    itemStyle: {
                        borderColor: styleObj.emphasisBorderColor || '#333',
                        borderWidth: styleObj.emphasisBorderWidth || 2
                    }
                }
            });
        }

        // determine if X-axis should be time-based (default behavior for single data source)
        const isTimeAxis = options.xAxisName === 'Time' || options.timeAxis !== false;

        // build initial empty chart options
        const option = {
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    let xLabel = params.data[0];
                    if (isTimeAxis && typeof params.data[0] === 'number') {
                        // Format timestamp for tooltip
                        const date = new Date(params.data[0]);
                        xLabel = date.toLocaleString();
                    } else {
                        xLabel = `${params.data[0]}${suffixX}`;
                    }
                    return `${params.seriesName}<br/>${options.xAxisName || 'X'}: ${xLabel}<br/>${options.yAxisName || 'Y'}: ${params.data[1]}${suffixY}`;
                }
            },
            xAxis: {
                type: isTimeAxis ? 'time' : 'value',
                name: options.xAxisName || 'X Axis',
                nameLocation: 'middle',
                nameGap: 30,
                axisLabel: isTimeAxis ? {
                    formatter: function(value) {
                        const date = new Date(value);
                        return date.toLocaleDateString() + '\n' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    }
                } : {
                    formatter: '{value}' + suffixX 
                }
            },
            yAxis: {
                type: 'value',
                name: options.yAxisName || 'Y Axis',
                nameLocation: 'middle',
                nameGap: 40,
                axisLabel: {
                    formatter: '{value}' + suffixY 
                }
            },
            legend: this.dataSources.length > 1 ? {
                show: true,
                top: 'bottom',
            } : undefined,
            series: series,
            dataZoom: options.enableZoom !== false ? [
                {
                    type: 'inside',
                    xAxisIndex: 0,
                    filterMode: 'none'
                },
                {
                    type: 'inside',
                    yAxisIndex: 0,
                    filterMode: 'none'
                }
            ] : undefined
        };

        // Override background color in dark mode to be transparent
        if (WidgetsFactory.isDarkMode) {
            option.backgroundColor = 'transparent';
        }

        // set initial empty chart options
        chart.setOption(option);
        this._chart = chart;

        // track this chart instance for theme switching
        const chartInfo = {
            chart: chart,
            dom: chartDom,
            lastOptions: option
        };
    }

    getChartInstance()
    {
        return this._chart;
    }

    getDomElement()
    {
        return this._containerDom;
    }
    
    update(dataSources)
    {     
        // Process each data source to format as scatter plot data
        const seriesUpdates = [];
        
        dataSources.forEach(events => {
            if (events && events.length > 0) {
                // Convert each event to scatter plot coordinate [x, y]
                // Expect events to have 'value' (y-axis) and 'additional_info' or custom field for x-axis
                const scatterData = events.map(event => {
                    if (event && event.value !== undefined) {
                        // Use timestamp as X by default, or additional_info if it's numeric
                        let xValue = event.timestamp;
                        if (event.additional_info && !isNaN(parseFloat(event.additional_info))) {
                            xValue = parseFloat(event.additional_info);
                        } else if (typeof event.timestamp === 'string') {
                            // Convert timestamp to numeric milliseconds for X-axis
                            xValue = parseTimestampToMs(event.timestamp);
                        }
                        
                        const yValue = parseFloat(event.value) || 0;
                        return [xValue, yValue];
                    }
                    return null;
                }).filter(point => point !== null); // Remove null entries
                
                seriesUpdates.push({ data: scatterData });
            } else {
                // No events for this data source
                seriesUpdates.push({ data: [] });
            }
        });
        
        // Update chart
        this.getChartInstance().setOption({
            series: seriesUpdates
        });
    }
}



/**
 * Wrapper methods to generate different widget types.
 */
const WidgetsFactory = {

    // default colors for multiple series
    defaultColors: ['#0d6efd', '#dc3545', '#198754', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#6c757d', '#6610f2', '#d63384'],
    defaultColorNames: {primary: 0, secondary: 7, success: 2, danger: 1, warning: 3, info: 6, special: 8},

    /**
     * Current theme mode (true = dark, false = light)
     * @type {boolean}
     */
    isDarkMode: localStorage.getItem('darkMode') === 'true',

    /**
     * List of registered widgets.
     * @type {array<Widget>}
     */
    _registeredWidgets: [],

    /**
     * Trigger data update callbacks, if needed.
     */
    _triggerDataUpdateCallbacks: function()
    {
        // iterate widgets
        for (let widget of WidgetsFactory._registeredWidgets) 
        {
            // get current widget source ids (now normalized objects)
            const dataSourceConfigs = widget.dataSources;

            // do we have any source configs? if so check if need to update them
            if (dataSourceConfigs && widget.isDirty) 
            {
                // collect data sources and mark if we got them all
                let foundAllDataSources = true;
                let data = [];
                for (const sourceConfig of dataSourceConfigs) 
                {
                    const sourceId = sourceConfig.dataSourceId;
                    const sourceTags = sourceConfig.tags;

                    // got data source
                    if (DataSources.loadedData.hasOwnProperty(sourceId) && DataSources.loadedData[sourceId]) {
                        let sourceEvents = DataSources.loadedData[sourceId].events;
                        
                        // apply tag filtering if tags are specified
                        if (sourceTags && sourceTags.length > 0) {
                            sourceEvents = filterEventsByTags(sourceEvents, sourceTags);
                        }
                        
                        data.push(sourceEvents);
                    }
                    // data source not found
                    else {
                        foundAllDataSources = false;
                        break;
                    }
                }

                // found? trigger callback and remove from list
                if (foundAllDataSources) 
                { 
                    // apply time aggregation settings
                    const timeAggSettings = widget.getTimeAggregationSettings(true);
                    if (timeAggSettings) {
                        data = data.map((source, index) => {
                            const sourceConfig = dataSourceConfigs[index];
                            // use the tags from the data source config for time aggregation
                            return EventsAggregator.timeIntervalAggregateEvents(source, timeAggSettings.interval, sourceConfig.tags, timeAggSettings.aggregationType);
                        });
                    }
                    
                    // apply additional filters and mutators
                    for (let i = 0; i < data.length; i++) {

                        // get current source config
                        let sourceConfig = dataSourceConfigs[i];

                        // apply additional data filter
                        if (sourceConfig.additionalInfoFilter) {
                            let additionalInfoFilter = sourceConfig.additionalInfoFilter;
                            if (typeof additionalInfoFilter === 'string') {
                                additionalInfoFilter = [additionalInfoFilter];
                            }
                            data[i] = data[i].filter((x) => additionalInfoFilter.includes(x.additional_info) );
                        }

                        // apply mutators
                        if (sourceConfig.mutators) {
                            data[i] = EventsMutators.mutate(data[i], sourceConfig.mutators);
                        }
                    }

                    // update data (this should also clear the dirty flag)
                    widget.update(data);
                    widget.postDataUpdate(data);
                }
            }
        }
    },

    /**
     * Register a widget instance.
     * @param {Widget} widgetInstance Widget instance.
     * @returns {Widget} The registered widget instance.
     */
    register: function(widgetInstance)
    {
        WidgetsFactory._registeredWidgets.push(widgetInstance);
        return widgetInstance;
    },

    /**
     * Create a free HTML content box.
     * @param {string} title - Box title.
     * @param {string} description - Box description.
     * @param {number} widthColumns - Box width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string} htmlContent - HTML content to display.
     * @returns {Widget} The new widget instance.
     */
    createFreeHtml: function(title, description, widthColumns, height, htmlContent)
    {
        return this.register(new FreeHtmlWidget(title, description, widthColumns, height, htmlContent));
    },

    /**
     * Create a counter widget.
     * @param {string} title - Widget title.
     * @param {string} description - Widget description.
     * @param {number} widthColumns - Widget width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string[]|Object[]} dataSources - Data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {string} counterType - Type of counter ("last", "first", "average", "average_round", "sum", "max", "min").
     * @returns {Widget} The new widget instance.
     */
    createCounter: function(title, description, widthColumns, height, dataSources, counterType)
    {
        return this.register(new CounterWidget(title, description, widthColumns, height, dataSources, counterType));
    },
      
    /**
     * Create a table widget.
     * @param {string} title - Widget title.
     * @param {string} description - Widget description.
     * @param {number} widthColumns - Widget width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string[]|Object[]} dataSources - Data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {array<dict>} tableColumns - Table columns definition. List of {title: string, event_field: string [value, event_name, tag, time, additional_info, index] }.
     * @param {number} maxRows - Maximum number of rows to show in the table.
     * @param {array<dict>} colorRules - Optional list of color rules to apply to table rows. Each rule is {field: string, operator: string, value: any, color: string}.
     * @param {string} sliceFrom - Whether to take rows from start or end of data ("start" or "end").
     * @returns {Widget} The new widget instance.
     */
    createTable: function(title, description, widthColumns, height, dataSources, tableColumns, maxRows, colorRules = null, sliceFrom = "start")
    {
        return this.register(new TableWidget(title, description, widthColumns, height, dataSources, tableColumns, maxRows, colorRules, sliceFrom));
    },

    /**
     * Create a line graph chart.
     * @param {string} title - Chart title.
     * @param {string} description - Chart description.
     * @param {number} widthColumns - Chart width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string[]|Object[]} dataSources - Data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object|Array} style - Chart style object or array of style objects. If object, applies to all series. If array, each index corresponds to a data source.
     * @param {Object} options - Additional options.
     * @returns {Widget} The new widget instance.
     */
    createLinesGraph: function(title, description, widthColumns, height, dataSources, style, options)
    {
        return this.register(new LineGraphWidget(title, description, widthColumns, height, dataSources, style, options));
    },

    /**
     * Create a bar graph chart.
     * @param {string} title - Chart title.
     * @param {string} description - Chart description.
     * @param {number} widthColumns - Chart width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string[]|Object[]} dataSources - Data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object|Array} style - Chart style object or array of style objects. If object, applies to all series. If array, each index corresponds to a data source.
     * @param {Object} options - Additional options.
     * @returns {Widget} The new widget instance.
     */
    createBarsGraph: function(title, description, widthColumns, height, dataSources, style, options)
    {
        return this.register(new BarGraphWidget(title, description, widthColumns, height, dataSources, style, options));
    },

    /**
     * Create a pie chart.
     * @param {string} title - Chart title.
     * @param {string} description - Chart description.
     * @param {number} widthColumns - Chart width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string[]|Object[]} dataSources - Data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object} style - Chart style object with pie chart specific options. Set donut: true for donut chart, use innerRadius and outerRadius to control donut thickness, showCenterText: true to display total in center.
     * @returns {Widget} The new widget instance.
     */
    createPieChart: function(title, description, widthColumns, height, dataSources, style)
    {
        return this.register(new PieChartWidget(title, description, widthColumns, height, dataSources, style));
    },

    /**
     * Create a scatter map chart.
     * @param {string} title - Chart title.
     * @param {string} description - Chart description.
     * @param {number} widthColumns - Chart width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string[]|Object[]} dataSources - Data source IDs (strings) or objects with dataSourceId and tags properties.
     * @param {Object|Array} style - Chart style object or array of style objects. If object, applies to all series. If array, each index corresponds to a data source.
     * @param {Object} options - Additional options for the scatter plot.
     * @returns {Widget} The new widget instance.
     */
    createScatterMap: function(title, description, widthColumns, height, dataSources, style, options)
    {
        return this.register(new ScatterMapWidget(title, description, widthColumns, height, dataSources, style, options));
    },

    /**
     * Create a gauge widget.
     * @param {string} title - Widget title.
     * @param {string} description - Widget description.
     * @param {number} widthColumns - Widget width, in Bootstrap columns (1-12). If 0, will be connected to previous widget column.
     * @param {number} height - Element height, in percent of base size (0.0 - 1.0, where 1.0 is 600 pixels).
     * @param {string|Object} dataSource - Single data source ID (string) or object with dataSourceId and tags properties.
     * @param {Object} style - Gauge style object with gauge-specific options.
     * @param {string} aggregationType - Type of aggregation to use ("last", "first", "average", "sum", "max", "min").
     * @returns {Widget} The new widget instance.
     */
    createGauge: function(title, description, widthColumns, height, dataSource, style, aggregationType = 'last', showLastValueTime = false)
    {
        // Ensure dataSource is wrapped in an array since gauge only takes one source
        const dataSources = Array.isArray(dataSource) ? dataSource : [dataSource];
        return this.register(new GaugeWidget(title, description, widthColumns, height, dataSources, style, aggregationType, showLastValueTime));
    },

    // current default page time interval
    _defaultTimeAggregation: "disabled",
    
    /**
     * Update the default time interval for all widgets.
     * @param {String} newInterval New time interval value.
     */
    updateDefaultTimeAggregation: function(newInterval)
    {
        WidgetsFactory._defaultTimeAggregation = newInterval;
        for (let widget of WidgetsFactory._registeredWidgets) {
            const currentInterval = widget.getTimeAggregationSettings(false);
            if (currentInterval && currentInterval.interval === "page_default") {
                widget.markDirty();
            }
        }
    }
};


// timer to wait for data source updates and trigger callbacks
setInterval(function() {
    WidgetsFactory._triggerDataUpdateCallbacks();
}, 1);


/**
 * Implement ways to process event data for different counter types.
 */
const EventsAggregator = {

    /**
     * Process event data for different counter types.
     * @param {array} data - The event data to process.
     * @param {string} counterType - The type of aggregation/function to use.
     * @returns {*} The processed value.
     */
    aggregateValue: function(data, counterType)
    {
        // get last
        if (counterType === "last") {
            const value = data[data.length - 1].value;
            return value;
        }
        // get first
        else if (counterType === "first") {
            const value = data[0].value;
            return value;
        }
        // get average
        else if (counterType === "average" || counterType === "average_round") {
            const sum = data.reduce((acc, item) => acc + item.value, 0);
            const avg = sum / data.length;
            return counterType === "average_round" ? Math.round(avg) : avg.toFixed(4);
        }
        // get sum
        else if (counterType === "sum") {
            return data.reduce((acc, item) => acc + item.value, 0);
        }
        // get max
        else if (counterType === "max") {
            return Math.max(...data.map(item => item.value));
        }
        // get min
        else if (counterType === "min") {
            return Math.min(...data.map(item => item.value));
        }
        // count events
        else if (counterType === "count") {
            return data.length;
        }
        // get first datetime
        else if (counterType === "first_datetime") {
            return data[0].datetime;
        }
        // get last datetime
        else if (counterType === "last_datetime") {
            return data[data.length - 1].datetime;
        }
        // get diff between last and first
        else if (counterType === "diff_last_first") {
            return data[data.length - 1].value - data[0].value;
        }
        // get diff between min and max
        else if (counterType === "diff_max_min") {
            const min = Math.min(...data.map(item => item.value));
            const max = Math.max(...data.map(item => item.value));
            return max - min;
        }
        // unknown type
        else {
            throw new Error(`Unknown event aggregation type "${counterType}".`);
        }
    },

    
    /**
     * Aggregate events by time intervals and optional tag.
     * @param {Array} events - Array of events with timestamp, value, and tag properties.
     * @param {string} interval - Time interval: "disabled", "10m", "30m", "hour", "day", "week", "month", "year".
     * @param {Array<string>} tags - Optional tags to filter events.
     * @param {string} aggregationType - Type of aggregation: "sum", "average", "max", "min", "count".
     * @returns {Array} Processed events grouped by tag and time interval.
     */
    timeIntervalAggregateEvents: function(events, interval, tags, aggregationType) 
    {
        // No aggregation or no events
        if (interval === 'disabled' || !interval || !events || events.length === 0) {
            return events;
        }

        // Get first event for name reference
        const first = events[0];
        
        // Helper function to get normalized timestamp in milliseconds for interval
        function getNormalizedTimestampMs(timestampStr, interval) {
            const date = new Date(timestampStr);
            const ms = date.getTime();
            
            switch(interval) {
                case '10m':
                    // Round down to 10-minute boundary
                    return Math.floor(ms / (10 * 60 * 1000)) * (10 * 60 * 1000);
                case '30m':
                    // Round down to 30-minute boundary
                    return Math.floor(ms / (30 * 60 * 1000)) * (30 * 60 * 1000);
                case 'hour':
                    // Round down to hour boundary
                    return Math.floor(ms / (60 * 60 * 1000)) * (60 * 60 * 1000);
                case 'day':
                    // Round down to day boundary (start of day in local timezone)
                    const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
                    return dayStart.getTime();
                case 'week':
                    // Round down to Monday of the week
                    const dayOfWeek = date.getDay();
                    const daysToSubtract = (dayOfWeek + 6) % 7; // Convert Sunday=0 to Monday=0
                    const weekStart = new Date(date.getFullYear(), date.getMonth(), date.getDate() - daysToSubtract);
                    return weekStart.getTime();
                case 'month':
                    // Round down to first day of month
                    const monthStart = new Date(date.getFullYear(), date.getMonth(), 1);
                    return monthStart.getTime();
                case 'year':
                    // Round down to first day of year
                    const yearStart = new Date(date.getFullYear(), 0, 1);
                    return yearStart.getTime();
                default:
                    return ms;
            }
        }
        
        // Process events - work entirely with numeric timestamps
        const aggregationMap = new Map();
        
        events.forEach(event => {
            // Skip if tags don't match
            if (tags && tags.length > 0 && !tags.includes(event.tag)) {
                return;
            }
            
            // Get normalized timestamp in milliseconds
            const normalizedMs = getNormalizedTimestampMs(event.timestamp, interval);
            
            // Initialize or update aggregation data
            if (!aggregationMap.has(normalizedMs)) {
                aggregationMap.set(normalizedMs, {
                    value: 0,
                    count: 0
                });
            }
            
            const aggData = aggregationMap.get(normalizedMs);
            
            // Aggregate based on type
            switch (aggregationType) {
                case 'sum':
                    aggData.value += event.value;
                    break;
                case 'average':
                case 'average_round':
                    aggData.value += event.value; // will divide by count later
                    break;
                case 'max':
                    aggData.value = aggData.count === 0 ? event.value : Math.max(aggData.value, event.value);
                    break;
                case 'min':
                    aggData.value = aggData.count === 0 ? event.value : Math.min(aggData.value, event.value);
                    break;
                default:
                    aggData.value += event.value; // default to sum
            }
            
            aggData.count++;
        });

        // For count, set value to count of events
        if (aggregationType === 'count') {
            for (let [timestampMs, aggData] of aggregationMap) {
                aggData.value = aggData.count;
            }
        }

        // Process averages
        if (aggregationType === 'average' || aggregationType === 'average_round') {
            for (let [timestampMs, aggData] of aggregationMap) {
                if (aggData.count > 0) {
                    aggData.value /= aggData.count;
                    if (aggregationType === 'average_round') {
                        aggData.value = Math.round(aggData.value);
                    } else {
                        aggData.value = parseFloat(aggData.value.toFixed(4));
                    }
                }
            }
        }
        
        // Sort by numeric timestamp and convert to final format
        const sortedEntries = Array.from(aggregationMap.entries())
            .sort(([a], [b]) => a - b) // Sort by numeric timestamp
            .map(([timestampMs, aggData]) => {
                // Convert back to Date object and format as local time string
                const date = new Date(timestampMs);
                const displayTimestamp = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`;
                
                return {
                    timestamp: displayTimestamp,
                    value: aggData.value,
                    name: first.name
                };
            });
            
        return sortedEntries;
    }
}


/**
 * Implement ways to evaluate event field conditions.
 */
const EventConditions = 
{
    /**
     * Evaluate an event field condition.
     * @param {*} fieldValue Field value to evaluate.
     * @param {*} condition Condition to check.
     * @param {*} value Value to compare against.
     * @returns {boolean}
     */
    evaluate: function(fieldValue, condition, value) 
    {
        switch (condition) {
            case "equals":
                return String(fieldValue) === String(value);
            case "not_equals":
                return String(fieldValue) !== String(value);
            case "greater_than":
                return Number(fieldValue) > Number(value);
            case "less_than":
                return Number(fieldValue) < Number(value);
            case "contains":
                return String(fieldValue).includes(String(value));
            default:
                return false;
        }
    }
}

const EventsMutators =
{
    /**
     * Mutate event data based on specified mutators.
     * @param {Array} events Events to mutate. It will not change their original values.
     * @param {Array} mutators List of mutators to apply. Each mutator is an object with {operation, value}.
     * possible operations: add, subtract, multiply, divide, round, floor, ceil, absolute, remove_negatives, to_delta, to_percentage_change.
     * @returns {Array} Mutated events.
     */
    mutate: function(events, mutators)
    {
        // first clone the events to avoid modifying original data
        const mutatedEvents = events.map(event => ({...event}));

        // apply each mutator in sequence
        for (const mutator of mutators) 
        {
            // break if no events left to mutate
            if (mutatedEvents.length === 0) {
                break;
            }

            // apply mutator operation
            switch (mutator.operation) 
            {
                case "add":
                    mutatedEvents.forEach(event => {
                        event.value += Number(mutator.value);
                    });
                    break;

                case "subtract":
                    mutatedEvents.forEach(event => {
                        event.value -= Number(mutator.value);
                    });
                    break;

                case "multiply":
                    mutatedEvents.forEach(event => {
                        event.value *= Number(mutator.value);
                    });
                    break;
                
                case "divide":
                    mutatedEvents.forEach(event => {
                        if (Number(mutator.value) !== 0) {
                            event.value /= Number(mutator.value);
                        }
                    });
                    break;

                case "round":
                    mutatedEvents.forEach(event => {
                        event.value = Math.round(event.value);
                    });
                    break;

                    case "floor":
                    mutatedEvents.forEach(event => {
                        event.value = Math.floor(event.value);
                    });
                    break;

                case "ceil":
                    mutatedEvents.forEach(event => {
                        event.value = Math.ceil(event.value);
                    });
                    break;

                case "absolute":
                    mutatedEvents.forEach(event => {
                        event.value = Math.abs(event.value);
                    });
                    break;

                case "remove_negatives":
                    mutatedEvents.forEach(event => {
                        if (event.value < 0) {
                            event.value = 0;
                        }
                    });
                    break;

                case "to_delta":
                    let previousValue = mutatedEvents[0];
                    mutatedEvents.unshift();
                    mutatedEvents.forEach(event => {
                        let valueBeforeChange = event.value;
                        event.value -= previousValue;
                        previousValue = valueBeforeChange;
                    });
                    break;

                case "to_percentage_change":
                    let prevValue = mutatedEvents[0];
                    mutatedEvents.unshift();
                    mutatedEvents.forEach(event => {
                        event.value = ((event.value - prevValue) / Math.abs(prevValue)) * 100;
                        prevValue = event.value;
                    });
                    break;

                default:
                    throw new Error(`Unknown event mutator operation "${mutator.operation}".`);
            }
            return mutatedEvents;
        }
    }
};

// get updates for page time interval
function updateDefaultTimeAggregation() {
    const newAggregation = document.getElementById('page-time-aggregation').value;
    WidgetsFactory.updateDefaultTimeAggregation(newAggregation);
}
document.getElementById('page-time-aggregation').addEventListener('change', updateDefaultTimeAggregation);
updateDefaultTimeAggregation();
