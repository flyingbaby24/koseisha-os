import React from "react";
import ReactDOM from "react-dom/client";
import "leaflet/dist/leaflet.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/controls.css";
import "./styles/map.css";
import "./styles/detail.css";
import "./styles/ranking.css";
import "./styles/dialog.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
