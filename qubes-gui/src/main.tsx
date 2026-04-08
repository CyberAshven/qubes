import ReactDOM from "react-dom/client";
import App from "./App";
import { VisualizerWindow } from "./pages/VisualizerWindow";
import { AudioProvider } from "./contexts/AudioContext";
import "./index.css";

// Check if this is the visualizer window based on the URL path
const isVisualizerWindow = window.location.pathname === '/visualizer';

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);

if (isVisualizerWindow) {
  // Render visualizer-only window
  root.render(
    <AudioProvider>
      <VisualizerWindow />
    </AudioProvider>,
  );
} else {
  // Render main application
  root.render(<App />);
}
