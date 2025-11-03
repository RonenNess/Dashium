

/**
 * HTML-related utilities.
 */
const HtmlUtils = 
{
    // last created widget container
    _lastWidgetContainer: null,

    /**
     * Toggle dark mode on or off.
     */
    toggleDarkMode: function()
    {
        // get current mode
        const htmlEl = document.documentElement;
        const isDark = htmlEl.getAttribute('data-bs-theme') === 'dark';

        // change mode
        HtmlUtils.enableDarkMode(!isDark);
        
        // reload the page to apply changes
        location.reload();
    },

    /**
     * Current theme mode (true = dark, false = light)
     * @type {boolean}
     */
    isDarkMode: false,
    
    /**
     * Enable or disable dark mode.
     * @param {Boolean} dark Enable dark mode.
     */
    enableDarkMode: function(dark)
    {
        // Bootstrap: data-bs-theme on <html>
        const htmlEl = document.documentElement;
        htmlEl.setAttribute('data-bs-theme', dark ? 'dark' : 'light');
        
        // update button icon
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) { themeIcon.className = dark ? 'bi bi-sun-fill' : 'bi bi-moon-fill'; }

        // store last dark mode preference
        localStorage.setItem('darkMode', dark);
    },

    /**
     * Create and return a new HTML element from string.
     * @param {string} htmlString - HTML string to convert to element.
     * @returns {HTMLElement} The created HTML element.
     */
    generateHtmlElement: function (htmlString)
    {
        const temp = document.createElement('div');
        temp.innerHTML = htmlString;
        return temp.firstElementChild;
    },

    /**
     * Create and return the text/html for a "No Data Available" message.
     * @returns {string} HTML string for "No Data Available" message.
     */
    generateNoDataAvailableMessage: function(visible = false)
    {
        return `<div class="no-data-message" style="display: ${visible ? 'block' : 'none'};">
                <h3 class="text-danger" style="text-align: center; margin-top:2rem;">No Data Available</h3>
            </div>`;
    },

    /**
     * Create and return new dashboard container element.
     * @param {string} title - Widget title.
     * @param {string} description - Widget description.
     * @param {number} [widthColumns=12] - Bootstrap column width (1-12).
     * @param {number} [height=1.0] - Container height relative to base height (1.0 = 600 pixels).
     * @param {boolean} [generateLoadingSpinner=true] - Whether to show loading spinner.
     * @param {boolean} [allowScrollbars=true] - Whether to allow scrollbars when content overflows.
     * @returns {HTMLElement} The widget chart container element.
     */
    createWidgetContainer: function (title, description, widthColumns=12, height=1.0, generateLoadingSpinner=true, allowScrollbars=true)
    {
        // get widget container
        height = Math.floor(height * 600); // convert to pixels
        const container = document.getElementById("widgets-container");

        // generate loading spinner html
        const loadingSpinner = generateLoadingSpinner ? `<div class="text-center loading-spinner-element">
                <div class="spinner-border text-primary" style="width: 4rem; height: 4rem; position: relative; top: 10rem;" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>` : ``;

        // sanity
        if (typeof widthColumns !== 'number' || widthColumns < 0 || widthColumns > 12) {
            throw new Error('Invalid widthColumns value. Must be a number between 0 and 12.');
        }

        // overflow y style
        const overflow = (height === 0) ? 'visible' : (allowScrollbars ? 'auto' : 'hidden');

        // height value
        height = (height === 0) ? 'auto' : (height + 'px');

        // create and return the widget container
        const elem = HtmlUtils.generateHtmlElement(`
        <div class="widget-root-container col-lg-${(widthColumns !== 0) ? widthColumns : "xxx"}" style="overflow-x: hidden; overflow-y: ${overflow}; " >

            <h4 class="widget-title">${title}</h4>
            <p class="widget-description">${description}</p>
            <p class="widget-subtitle"></p>
            <div class="container">
                <div class="options-bar row"></div>
            </div>

            ${loadingSpinner}

            ${HtmlUtils.generateNoDataAvailableMessage()}

            <div class="widget-content" style="width: 100%; overflow-y: ${overflow}; overflow-x: hidden; height: ${height};">
            </div>
        </div>`) 

        // add to parent
        if (widthColumns === 0) {
            (HtmlUtils._lastWidgetContainer || container).appendChild(elem);
        }
        else {
            container.appendChild(elem);
        }

        // set last container
        HtmlUtils._lastWidgetContainer = elem;

        // return the widget content element
        return elem.getElementsByClassName('widget-content')[0];
    }
};

