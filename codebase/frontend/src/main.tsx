/**
 * main.tsx — React entry point.
 *
 * WHAT IT DOES: mounts <App/> into #root inside a BrowserRouter.
 * On boot, App attempts a silent POST /auth/refresh (cookie) to restore the session
 * (access token is kept in memory only — never localStorage). See useAuth.
 */
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
