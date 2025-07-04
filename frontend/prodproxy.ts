

import config from '../../../sites/common_site_config.json';
// const config = require("../../../sites/common_site_config.json");

console.log("config === ", config)
const host = window.location.href.split(":")[1]
// const host = "192.168.1.120"
export const proxyConfig = {
  "/api": {
    "target": `http://${host}:${config.webserver_port}`,
    "secure": false,
    "changeOrigin": true,
    "pathRewrite": {
      "^/api": ""
    }
  },
  "/socket.io": {
    "target": `http://${host}:${config.socketio_port}`,
    "ws": true
}
}
// module.exports = proxyConfig;
console.log(proxyConfig)