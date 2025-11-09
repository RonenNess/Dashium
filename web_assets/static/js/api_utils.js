
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
    },
}

/**
 * hash utilities.
 */
const HashUtils = 
{
    /**
     * Synchronous SHA-256 implementation that produces the same output as crypto.subtle.digest('SHA-256', data)
     * @param {string|Uint8Array} data - The data to hash
     * @returns {ArrayBuffer} The hash as an ArrayBuffer (same format as crypto.subtle.digest)
     */
    sha256: function(data) 
    {
        // Convert input to bytes if it's a string
        let bytes;
        if (typeof data === 'string') {
            bytes = new TextEncoder().encode(data);
        } else if (data instanceof Uint8Array) {
            bytes = data;
        } else if (data instanceof ArrayBuffer) {
            bytes = new Uint8Array(data);
        } else {
            throw new Error('Data must be a string, Uint8Array, or ArrayBuffer');
        }

        // SHA-256 constants
        const K = [
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
        ];

        // Initial hash values
        let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
        let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;

        // Pre-processing: adding a single 1 bit
        const msgLen = bytes.length;
        const bitLen = msgLen * 8;
        
        // Calculate padding length
        let paddingLen = 64 - ((msgLen + 9) % 64);
        if (paddingLen === 64) paddingLen = 0;
        
        // Create padded message
        const paddedLen = msgLen + 1 + paddingLen + 8;
        const paddedMsg = new Uint8Array(paddedLen);
        paddedMsg.set(bytes, 0);
        paddedMsg[msgLen] = 0x80; // append single '1' bit (plus seven '0' bits)
        
        // Append original length in bits as 64-bit big-endian integer
        const lengthBytes = new DataView(paddedMsg.buffer, paddedLen - 8, 8);
        lengthBytes.setUint32(0, Math.floor(bitLen / 0x100000000), false); // high 32 bits
        lengthBytes.setUint32(4, bitLen & 0xffffffff, false); // low 32 bits

        // Helper functions
        function rightRotate(value, amount) {
            return (value >>> amount) | (value << (32 - amount));
        }

        function sha256Transform(chunk) {
            const w = new Array(64);
            
            // Copy chunk into first 16 words W[0..15] of the message schedule array
            for (let i = 0; i < 16; i++) {
                w[i] = new DataView(chunk.buffer, chunk.byteOffset + i * 4, 4).getUint32(0, false);
            }

            // Extend the first 16 words into the remaining 48 words W[16..63]
            for (let i = 16; i < 64; i++) {
                const s0 = rightRotate(w[i - 15], 7) ^ rightRotate(w[i - 15], 18) ^ (w[i - 15] >>> 3);
                const s1 = rightRotate(w[i - 2], 17) ^ rightRotate(w[i - 2], 19) ^ (w[i - 2] >>> 10);
                w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
            }

            // Initialize working variables
            let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;

            // Main loop
            for (let i = 0; i < 64; i++) {
                const S1 = rightRotate(e, 6) ^ rightRotate(e, 11) ^ rightRotate(e, 25);
                const ch = (e & f) ^ (~e & g);
                const temp1 = (h + S1 + ch + K[i] + w[i]) >>> 0;
                const S0 = rightRotate(a, 2) ^ rightRotate(a, 13) ^ rightRotate(a, 22);
                const maj = (a & b) ^ (a & c) ^ (b & c);
                const temp2 = (S0 + maj) >>> 0;

                h = g;
                g = f;
                f = e;
                e = (d + temp1) >>> 0;
                d = c;
                c = b;
                b = a;
                a = (temp1 + temp2) >>> 0;
            }

            // Add this chunk's hash to result so far
            h0 = (h0 + a) >>> 0;
            h1 = (h1 + b) >>> 0;
            h2 = (h2 + c) >>> 0;
            h3 = (h3 + d) >>> 0;
            h4 = (h4 + e) >>> 0;
            h5 = (h5 + f) >>> 0;
            h6 = (h6 + g) >>> 0;
            h7 = (h7 + h) >>> 0;
        }

        // Process the message in successive 512-bit chunks
        for (let i = 0; i < paddedLen; i += 64) {
            sha256Transform(paddedMsg.subarray(i, i + 64));
        }

        // Produce the final hash value as an ArrayBuffer
        const result = new ArrayBuffer(32);
        const view = new DataView(result);
        view.setUint32(0, h0, false);
        view.setUint32(4, h1, false);
        view.setUint32(8, h2, false);
        view.setUint32(12, h3, false);
        view.setUint32(16, h4, false);
        view.setUint32(20, h5, false);
        view.setUint32(24, h6, false);
        view.setUint32(28, h7, false);

        return result;
    }


}
