<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0F0C1D,50:211B36,100:0F0C1D&height=200&section=header&text=SNJB%20Assistant&fontSize=54&fontColor=22E5D0&animation=fadeIn&fontAlignY=38&desc=AI%20College%20Helpdesk%20%C2%B7%20Powered%20by%20LangGraph&descAlignY=58&descSize=17&descColor=9C97B8" width="100%"/>

<img src="https://readme-typing-svg.demolab.com/?font=IBM+Plex+Mono&size=16&pause=1500&color=B18CFF&center=true&vCenter=true&width=680&lines=Classifier+%E2%86%92+Academic+RAG+%2F+Fee+RAG+%2F+General+%E2%86%92+Response;Grounded+in+Real+SNJB+Academic+%26+Fee+Documents;Live+Animated+Graph+Shows+Every+Routing+Decision" alt="Typing SVG" />

<br>



<img src="https://komarev.com/ghpvc/?username=BhairavThakare08&repo=snjb-college-assistant&color=b18cff&style=for-the-badge&label=REPO+VIEWS" alt="views"/>

🔗 Live Demo  ·  📖 How It Works  ·  📚 Data Sources  ·  ⚙️ Setup

</div>

<br>

An AI helpdesk for SNJB College of Engineering, built on a LangGraph pipeline instead of a single prompt-and-pray chatbot. Every question is classified, routed to the right knowledge base (or straight to the LLM for casual chat), and answered in a consistent college-assistant persona — with the frontend visualizing that exact routing decision live, as an animated graph.

<br>

📸 Preview

<table>
<tr>
<td width="50%" align="center">
<b>Programme selection</b><br><br>
<img src="docs/screenshot-onboarding.png" alt="SNJB Assistant onboarding screen with campus photo background" width="100%">
</td>
<td width="50%" align="center">
<b>Chat + live routing graph</b><br><br>
<img src="docs/screenshot-chat.png" alt="SNJB Assistant chat interface with animated LangGraph routing visualization" width="100%">
</td>
</tr>
</table>

<sub>⬆ add your own screenshots to a docs/ folder — one of the programme picker, one of a chat with the routing graph open.</sub>

<br>

🔗 Live Demo





Status

Runs locally — not yet deployed

Backend

uvicorn main:app --reload --port 8000

Frontend

Open frontend/index.html directly, or serve with python -m http.server

See Setup below to run it yourself in under 5 minutes.

<br>

📚 Data Sources

This isn't answering from the LLM's general training data — the Academic and Fee RAG branches are grounded in SNJB's actual 2026–27 official documents:

Document

Used for

A few real facts it retrieves

SNJB Academic Handbook 2026-27

Attendance, exams, grading, promotion, course structure

75% minimum attendance, 10-point grading scale (O=10 → F=0), ATKT promotion rules

SNJB Fee Structure 2026-27

Tuition, payment schedule, refunds, concessions

Programme-wise annual fees, MahaDBT category concessions, late-fee penalty slabs

Both PDFs are chunked (chunk_size=800, chunk_overlap=100), embedded with sentence-transformers/all-MiniLM-L6-v2, and indexed in FAISS — so answers cite real institute policy, not guesses.

<br>

💡 Why This Project

Most tutorial chatbots are one classifier and one prompt. This one is a small multi-branch LangGraph pipeline — the kind of routing architecture real production RAG systems actually use once "one prompt for everything" stops scaling. Two engineering decisions worth calling out:

Persona consistency bug → fix. Early on, the general branch (no retrieval) had zero identity context, so "who are you?" got a generic "I'm an AI language model" answer instead of a proper SNJB Assistant introduction. Fixed by giving every branch — not just the RAG ones — a shared SYSTEM_PERSONA, with an explicit rule to introduce itself only on the first greeting or identity question, not on every single reply.

The routing graph is not decoration. The frontend's animated diagram lights up the exact nodes and edges route_query() actually took for that message — it's a live view into the LangGraph state, not a static illustration.

<br>

📖 How It Works

flowchart TD
    START(("START")) --> CLS["Classifier<br/><sub>LLM decides: academic / fee / general</sub>"]
    CLS -->|academic| ACA["Academic RAG<br/><sub>FAISS · Academic Handbook</sub>"]
    CLS -->|fee| FEE["Fee RAG<br/><sub>FAISS · Fee Structure</sub>"]
    CLS -->|general| GEN["General<br/><sub>no retrieval</sub>"]
    ACA --> RESP["Response<br/><sub>SYSTEM_PERSONA + context → Groq</sub>"]
    FEE --> RESP
    GEN --> RESP
    RESP --> END(("END"))

    style START fill:#171327,stroke:#F3F1FA,color:#F3F1FA
    style CLS fill:#171327,stroke:#F3F1FA,color:#F3F1FA
    style ACA fill:#171327,stroke:#22E5D0,color:#22E5D0
    style FEE fill:#171327,stroke:#FFC857,color:#FFC857
    style GEN fill:#171327,stroke:#B18CFF,color:#B18CFF
    style RESP fill:#171327,stroke:#F3F1FA,color:#F3F1FA
    style END fill:#171327,stroke:#F3F1FA,color:#F3F1FA

This is the exact graph the frontend animates in the "Routing graph" panel — same node names, same branches.

<details>
<summary><b>🔍 Request/response sequence (click to expand)</b></summary>
<br>

sequenceDiagram
    participant U as Browser (index.html)
    participant A as FastAPI (main.py)
    participant G as LangGraph workflow
    participant Q as Groq (Llama 3.3 70B)
    participant F as FAISS index

    U->>A: POST /chat { programme, message }
    A->>G: workflow.invoke(state)
    G->>Q: classifier_node → category
    alt academic or fee
        G->>F: retriever.invoke(query)
        F-->>G: top-4 chunks
    end
    G->>Q: response_node (SYSTEM_PERSONA + context)
    Q-->>G: answer
    G-->>A: { messages, query_type }
    A-->>U: { response, query_type }
    U->>U: render message + animate routing graph

</details>

<br>

✨ Features





🧭

LangGraph routing — classifier decides academic / fee / general, no manual if-else keyword matching

📚

RAG on real institute documents — FAISS-indexed Academic Handbook + Fee Structure, not generic LLM knowledge

🎭

Consistent persona — every branch (including general chat) knows it's the SNJB College Assistant

🎓

7-programme personalization — answers tailored to the student's actual programme where relevant

🔗

Live routing graph — animated SVG diagram lights up the real path each answer took through the graph

🏛️

Campus-themed onboarding — programme picker over a campus photo background, dark-overlaid for readability

🟢

API health check — frontend pings the backend on load and shows live connection status

<br>

🛠️ Tech Stack



⚙️ Setup

<details>
<summary><b>Backend (click to expand)</b></summary>
<br>

git clone https://github.com/BhairavThakare08/snjb-college-assistant.git
cd snjb-college-assistant/backend

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

Copy .env.example to .env and add your Groq API key:

GROQ_API_KEY=your_actual_key_here

uvicorn main:app --reload --port 8000

First run takes a little longer — it's building FAISS indexes from both PDFs. API is up at http://127.0.0.1:8000 once you see Uvicorn running.

</details>

<details>
<summary><b>Frontend (click to expand)</b></summary>
<br>

script.js points at http://127.0.0.1:8000 by default. Serve it with a local server rather than double-clicking the file (some browsers block fetch() from file:// URLs):

cd frontend
python -m http.server 5500

Then open http://127.0.0.1:5500 in your browser.

</details>

<br>

🔌 API Reference

<details>
<summary><b><code>POST /chat</code> — click to expand</b></summary>
<br>

Request

{
  "programme": "B.E. Artificial Intelligence and Data Science",
  "message": "What is the minimum attendance requirement?"
}

Response

{
  "response": "You need to maintain at least 75% aggregate attendance...",
  "query_type": "academic"
}

</details>

<details>
<summary><b><code>GET /programmes</code> and <code>GET /</code></b></summary>
<br>

GET /programmes → returns the list of 7 valid programme strings.GET / → health check, used by the frontend's live connection indicator.

</details>

<br>

🚀 Roadmap

Deploy backend (Render/Railway) + frontend (GitHub Pages/Vercel) for a real live link

Add a LangGraph checkpointer for real multi-turn conversation memory

Stream responses token-by-token instead of waiting for the full answer

Add source citations (which PDF page an answer came from)

<br>

👤 Author

Bhairav ThakareB.E. Artificial Intelligence & Data Science



<br>

<div align="center">

If this project helped you, consider giving it a ⭐

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0F0C1D,50:211B36,100:0F0C1D&height=100&section=footer" width="100%"/>

</div>
