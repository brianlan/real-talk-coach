const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// Read the certificate files
const certPath = path.join(__dirname, '.certs');
const options = {
  key: fs.readFileSync(path.join(certPath, 'key.pem')),
  cert: fs.readFileSync(path.join(certPath, 'cert.pem')),
};

// Target HTTP server (Next.js dev server)
const targetHost = 'localhost';
const targetPort = 3000;

// Create HTTPS server
const server = https.createServer(options, (req, res) => {
  // Proxy request to the HTTP server
  const proxyReq = http.request(
    {
      hostname: targetHost,
      port: targetPort,
      path: req.url,
      method: req.method,
      headers: req.headers,
    },
    (proxyRes) => {
      // Forward the response
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );

  // Forward the request body
  req.pipe(proxyReq);

  proxyReq.on('error', (err) => {
    console.error('Proxy error:', err);
    res.writeHead(502);
    res.end('Bad Gateway');
  });
});

const HTTPS_PORT = 3443;
const LAN_IP = process.env.LAN_IP || '192.168.71.57';
server.listen(HTTPS_PORT, '0.0.0.0', () => {
  console.log(`\nHTTPS Proxy Server running at:`);
  console.log(`  - Local:   https://localhost:${HTTPS_PORT}`);
  console.log(`  - Network: https://${LAN_IP}:${HTTPS_PORT}`);
  console.log(`\nProxying to HTTP server at http://${targetHost}:${targetPort}`);
  console.log(`\nNote: Accept the self-signed certificate warning in your browser.\n`);
});
