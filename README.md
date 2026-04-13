# 🚀 PMO Agentic AI System

An AI-powered PMO (Project Management Office) automation system that transforms unstructured inputs such as meeting recordings, documents, and communication threads into structured project outputs like Change Requests (CR), Project Plans, and RAID logs.

---

## 🧠 Overview

This system leverages Agentic AI (Autonomous AI Agents) to automate key activities in the SDLC (Software Development Life Cycle), reducing manual effort and improving project efficiency.

The platform processes:
- 🎤 Meeting recordings  
- 📄 SOW (Statement of Work) documents  
- 📧 Emails and communication threads  

And generates:
- 📌 CR (Change Request) documents  
- 📊 Project Plans  
- ⚠️ RAID (Risks, Assumptions, Issues, Dependencies) logs  

---

## ⚙️ Features

### ✅ Input Processing
- Collects and processes data from:
  - Meeting transcripts (via Speech-to-Text)
  - Scope documents
  - Emails and chats

---

### 🤖 AI Agents

#### 🔹 CR Agent (Change Request Agent)
- Generates structured CR documents  
- Performs impact analysis  
- Integrated with JIRA for automated ticket creation  

---

#### 🔹 Plan Agent
- Converts requirements into:
  - Tasks  
  - Timelines  
  - Dependencies  
- Automatically creates and organizes work items in JIRA / Smartsheet  

---

#### 🔹 RAID Agent (Risks, Assumptions, Issues, Dependencies Agent)
- Identifies and structures:
  - Risks  
  - Assumptions  
  - Issues  
  - Dependencies  
- Generates actionable RAID logs for project tracking  

---

## 🏗️ Architecture

Inputs (Video / Audio / Docs / Emails)
↓
Speech-to-Text (Whisper)
↓
LLM Processing (gemma 4 / Hugging Face Inference)
↓
Agent Layer
├── CR Agent
├── Plan Agent
└── RAID Agent
↓
Outputs
├── JIRA (tickets)
├── Project Plans
└── RAID Logs (Excel / Smartsheet)

---

## 🛠️ Tech Stack

### Backend
- Python  
- FastAPI (Web Framework)  

### AI / ML
- Whisper (Speech-to-Text)  
- Gemma 4 (Large Language Models)  
- Hugging Face Transformers  

### Integrations
- JIRA API (ticket automation)  
- IMAP (Email integration)  
- File processing (PDF/Text)  

---

## 🚀 Getting Started

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Tilak2k3/Agentic-AI.git
cd Agentic-AI
2️⃣ Create Virtual Environment
python -m venv .venv
.venv\Scripts\activate   # Windows
3️⃣ Install Dependencies
pip install -r requirements.txt
4️⃣ Run the Application
uvicorn agentic_ai.api.main:app --reload
5️⃣ Access the Application
API Docs: http://localhost:8000/docs
Application UI: http://localhost:8000/
🔐 Environment Variables

Create a .env file:

IMAP_HOST=imap.gmail.com
IMAP_USER=your_email@gmail.com
IMAP_PASSWORD=your_app_password

JIRA_URL=your_jira_url
JIRA_USERNAME=your_username
JIRA_API_TOKEN=your_token

🧾 Use Case

This system is ideal for:

Project Managers
Delivery Teams
Organizations following Agile / SDLC workflows
