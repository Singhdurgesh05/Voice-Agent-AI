# Voice-Controlled Local AI Agent

<div align="center">
  <img src="https://img.shields.io/badge/Next.js-15-black?style=for-the-badge&logo=next.js" alt="Next.js">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Groq-Llama_3-f55036?style=for-the-badge" alt="Groq">
  <img src="https://img.shields.io/badge/Vector_DB-Qdrant-red?style=for-the-badge" alt="Qdrant">
  <img src="https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql" alt="PostgreSQL">
</div>

---

A pristine, high-performance **Voice-Controlled AI Agent** that accepts audio input, classifies intents via an LLM, executes local system actions, and provides a RAG-backed relational memory—all presented in a beautiful Next.js user interface.

## 🌟 Key Features

1. **Human-in-the-Loop File Output:** The agent can write code and create files directly to a restricted `output/` sandbox. The user is prompted with an **Approval Interface** within the UI before any file operation executes.
2. **Compound Commands:** Uses deterministic tool calling to support complex instructions (e.g., *"Create a fast API route and summarize what it does"*).
3. **Dual Memory Layer:** Combines **PostgreSQL** (for exact chat history, sessions, and tool structures) with **Qdrant** (Vector Database for long-term semantic conversation recall).
4. **Premium UI:** Built with React, TailwindCSS, and framer-style micro-animations. Contains real-time audio visualization using the browser's `MediaRecorder` API.

## ⚙️ Tool Execution

Based on detected intent, the backend triggers local tools with strict sandboxing.

- **File Operations:** create files and folders.
  - **Safety Constraint:** all file/folder creation and code writing is restricted to `output/` inside the repository.
- **Code Generation:** generates code and writes it directly to a target file.
- **Text Processing:** summarizes provided content and stores tool results for retrieval/export.

### UI Output Requirements Covered

The chat UI explicitly shows:
- transcribed text from audio,
- detected intent,
- specific action taken by the system,
- final output/result returned by the agent.

---

## 🏗️ Architecture & Model Selection

### Why Groq over Local LLMs? (Hardware Workaround)
While the assignment suggested a local model (via Ollama/Transformers), this project was architected for **sub-second time-to-first-token latency** to make Voice interaction feel naturally conversational.
* **LLM Engine:** We utilize the **Groq API (Llama 3.3 70B)** which runs on LPUs, providing near-instantaneous intent parsing and code generation. 
* **STT Engine:** We support `faster-whisper` (local), but heavily recommend and default to the **Groq Whisper-large-v3 API** for hardware environments without high-VRAM GPUs.

### Tech Stack
* **Frontend:** Next.js (App Router), React, TailwindCSS, Lucide Icons.
* **Backend:** FastAPI, Pydantic, SQLAlchemy.
* **Databases:** PostgreSQL (Relational) + Qdrant (Vector).
* **AI Orchestration:** Native OpenAI-compatible tool calling mapped to Python functions without heavy frameworks padding overhead.

---

## 💻 Setup & Installation Instructions

Ensure you have **Docker**, **Node.js (v18+)**, and **Python 3.10+** installed.

### 1. Database Infrastructure

We use Docker Compose to spin up the Qdrant and PostgreSQL memory layers.

```bash
docker-compose up -d
```

### 2. Backend Setup (FastAPI)

1. Navigate to the root directory.
2. Initialize a Python environment:
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Create an environment file (`.env`) from the example and add your Groq API Key:
```bash
cp .env.example .env
```
5. Run the server:
```bash
uvicorn backend.main:app --reload
```

### 3. Frontend Setup (Next.js)

1. Open a new terminal and navigate to the `frontend` directory:
```bash
cd frontend
```
2. Install npm packages:
```bash
npm install
```
3. Start the Next.js development server:
```bash
npm run dev
```

Visit `http://localhost:3000` in your browser. Allow microphone access, and you are ready to test!

---

## 📁 Repository Structure
```
.
├── backend/
│   ├── routes/          # API layer (chat & action approval endpoints)
│   ├── services/        # Orchestrators (Memory, Agent, LLM, STT)
│   ├── database/        # SQLAlchemy models and Qdrant client
│   └── tools/           # Sandboxed filesystem & text tools
├── frontend/
│   ├── app/             # Next.js App Router (page layouts & CSS)
│   └── components/      # Audio Recorder, Chat Interface, Action Cards
├── output/              # Isolated sandbox for all generated files
├── uploads/             # Temporary audio file holding room
├── docker-compose.yml   # Memory layer infrastructure
└── requirements.txt     # Python dependencies
```
