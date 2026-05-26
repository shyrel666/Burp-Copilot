# Running Ollama Locally

Ollama provides a privacy-first alternative to cloud LLM providers. All inference runs on your machine — no API key or internet access required.

## Prerequisites

- [Ollama](https://ollama.com) installed and running
- At least 8 GB RAM (16 GB recommended for larger models)

## Setup

1. Install Ollama following the instructions at <https://ollama.com>.

2. Pull a model:

   ```bash
   ollama pull llama3
   ```

3. Start the Ollama server (it usually starts automatically):

   ```bash
   ollama serve
   ```

   The default API endpoint is `http://localhost:11434`.

4. In the Burp AI dashboard, go to **Settings** and configure:

   - **Provider**: `ollama`
   - **Model**: `llama3` (or whichever model you pulled)
   - **Base URL**: `http://localhost:11434` (default)

   No API key is needed — the API key field is hidden for Ollama.

5. Click **Save Provider** and then use **Test Provider** to verify connectivity.

## Available Models

Popular models for security analysis:

| Model      | Pull command          | Notes                        |
|------------|----------------------|------------------------------|
| llama3     | `ollama pull llama3` | Good general-purpose model   |
| mistral    | `ollama pull mistral`| Smaller, faster responses    |
| codellama  | `ollama pull codellama` | Optimized for code analysis |

## Timeout Considerations

Local models are slower than cloud APIs. The Ollama provider uses a **120-second** timeout by default (vs. 20 seconds for cloud providers). If you see timeout errors with large prompts, try:

- Using a smaller model (e.g., `mistral` instead of `llama3`)
- Ensuring no other heavy processes compete for GPU/CPU
- Increasing the Ollama base URL to a machine with more resources

## Privacy

With Ollama, HTTP traffic never leaves your machine. The backend sends redacted prompts to the local Ollama endpoint at `localhost:11434`. No data is transmitted to any cloud service.
