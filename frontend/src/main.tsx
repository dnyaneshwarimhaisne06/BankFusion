import { createRoot } from "react-dom/client";
import { StrictMode } from "react";
import App from "./App.tsx";
import "./index.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element not found");
}

// Add error boundary at the root level
window.addEventListener('error', (event) => {
  console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
});

try {
  const root = createRoot(rootElement);
  root.render(
    <StrictMode>
      <App />
    </StrictMode>
  );
} catch (error) {
  console.error("Failed to render app:", error);
  rootElement.innerHTML = `
    <div style="padding: 20px; font-family: sans-serif; background: white; min-height: 100vh;">
      <h1 style="color: #dc2626;">Application Error</h1>
      <p>Failed to load the application. Please check the browser console (F12) for details.</p>
      <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow: auto; margin-top: 20px;">
${error instanceof Error ? error.message + '\n\n' + error.stack : String(error)}
      </pre>
      <p style="margin-top: 20px; color: #666;">
        Common issues:<br/>
        1. Check browser console (F12) for detailed errors<br/>
        2. Ensure all dependencies are installed (npm install)<br/>
        3. Verify environment variables are set correctly (VITE_FLASK_API_URL)<br/>
        4. Check if backend server is accessible
      </p>
    </div>
  `;
}
