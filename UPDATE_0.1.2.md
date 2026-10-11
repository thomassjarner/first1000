# Version 0.1.2

Fix confirmed missing msgpack/six Pyodide wheel downloads in GitHub Pages no-CDN builds. The build now bundles micropip, packaging, msgpack, six and their Pyodide dependencies using filenames and SHA-256 checksums from the pinned runtime lockfile. Distribution verification rejects missing or damaged dependency wheels. App code and browser progress storage are unchanged from 0.1.1.
