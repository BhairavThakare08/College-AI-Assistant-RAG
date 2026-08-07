import os
from typing import TypedDict, Annotated

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ------------------------------------------------------------------
# Persona — this is the actual fix. Every response (academic, fee,
# AND general) now knows who it is, instead of only the general
# branch silently falling back to a generic "I'm an AI" answer.
# ------------------------------------------------------------------
SYSTEM_PERSONA = (
    "You are the SNJB College Assistant, an AI helpdesk built for SNJB's Late Sau. Kantabai "
    "Bhavarlalji Jain College of Engineering, Chandwad — an autonomous institute affiliated to "
    "Savitribai Phule Pune University (SPPU), approved by AICTE, and accredited A+ by NAAC. "
    "Your job is to help students with academic policies, fee structure, and general campus "
    "information, using the official college documents you have access to.\n\n"
    "IMPORTANT — only introduce yourself (your name and a welcome) when the student explicitly "
    "asks who you are, what your name is, or sends a plain greeting like 'hi' / 'hello' / 'hey'. "
    "For every other question, answer directly and naturally, with no self-introduction and no "
    "'Welcome to SNJB' preamble — the student is already mid-conversation, so repeating your "
    "name and a welcome in every single reply is repetitive and annoying. Just answer the question. "
    "Never claim to be a generic AI/language model when asked about your identity."
)

# Step 1 - Building the RAG retrievers
# NOTE: embeddings now run via Hugging Face's hosted Inference API instead of
# loading the model locally with sentence-transformers/torch — that alone was
# using 300-400MB+ RAM, which is why this crashed Render's 512MB free tier.

embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction",
    huggingfacehub_api_token=os.environ.get("HUGGINGFACEHUB_API_TOKEN"),
)


def build_retriver(pdf_path: str):
    loader = PyPDFLoader(pdf_path)
    document = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    chunks = splitter.split_documents(document)

    vectorstore = FAISS.from_documents(chunks, embeddings)

    return vectorstore.as_retriever(search_kwargs={"k": 4})


acedemic_retriever = build_retriver(os.path.join(DATA_DIR, "SNJBAcademic_Handbook_2026.pdf"))
fee_retriever = build_retriver(os.path.join(DATA_DIR, "SNJB_Fee_Structure_2026.pdf"))

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.4)

# step 2 - State


class State(TypedDict):
    programme: str
    messages: Annotated[list, add_messages]
    query_type: str
    retrieved_context: str


# Step 3 - Nodes generation

def classifier_node(state: State) -> dict:
    """Look at the latest user message and decide which path to take."""

    last_message = state["messages"][-1].content

    prompt = (
        "Classify the following student query into exactly one category: "
        "'academic', 'fee', or 'general'.\n\n"
        "Use 'academic' for questions about attendance, exams, grading, credits, "
        "promotion, course structure, summer training, or degree requirements.\n"
        "Use 'fee' for questions about tuition, payment, refund, late charges, "
        "scholarships, or any money-related topic.\n"
        "Use 'general' for greetings, casual talk, questions about who the assistant is, "
        "or anything not related to the college rules or fee.\n\n"
        f"Query: {last_message}\n\n"
        "Return only one word: academic, fee, or general."
    )

    response = llm.invoke(prompt)
    category = response.content.strip().lower()

    if "academic" in category:
        category = "academic"
    elif "fee" in category:
        category = "fee"
    else:
        category = "general"

    return {"query_type": category}


def academic_rag_node(state: State) -> dict:
    """Retrieves relevant chunks from the academics handbook."""
    query = state["messages"][-1].content
    docs = acedemic_retriever.invoke(query)
    context = "\n\n".join([doc.page_content for doc in docs])
    return {"retrieved_context": context}


def fee_rag_node(state: State) -> dict:
    """Retrieves relevant chunks from the fee structure PDF."""
    query = state["messages"][-1].content
    docs = fee_retriever.invoke(query)
    context = "\n\n".join([doc.page_content for doc in docs])
    return {"retrieved_context": context}


def general_node(state: State) -> dict:
    """Answers directly using the LLM's own knowledge, no retrieval needed."""
    return {"retrieved_context": "NO_RETRIEVAL_NEEDED"}


def response_node(state: State) -> dict:
    """Generates the final answer, personalized using the student's programme.
    Every branch now gets SYSTEM_PERSONA prepended, so identity stays
    consistent whether the query was academic, fee, or general."""
    query = state["messages"][-1].content
    programme = state.get("programme", "Unknown")
    context = state["retrieved_context"]

    if context == "NO_RETRIEVAL_NEEDED":
        prompt = (
            f"{SYSTEM_PERSONA}\n\n"
            f"You are currently talking to a {programme} student.\n\n"
            f"Answer this using your own general knowledge, staying in character as the "
            f"SNJB College Assistant:\n\n{query}"
        )
    else:
        prompt = (
            f"{SYSTEM_PERSONA}\n\n"
            f"You are currently helping a {programme} student. "
            f"Use the following context from the official college documents to answer "
            f"the question accurately. If the context mentions specific figures for "
            f"different programmes, highlight the one relevant to {programme} if possible.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {query}\n\n"
            f"Give a clear, friendly, and precise answer."
        )

    response = llm.invoke(prompt)
    return {"messages": [("ai", response.content.strip())]}


# step 4 - router function

def route_query(state: State):
    if state["query_type"] == "academic":
        return "academic_rag"
    elif state["query_type"] == "fee":
        return "fee_rag"
    else:
        return "general"


# step 5 - Building the graph

graph = StateGraph(State)

graph.add_node("classifier", classifier_node)
graph.add_node("academic_rag", academic_rag_node)
graph.add_node("fee_rag", fee_rag_node)
graph.add_node("general", general_node)
graph.add_node("response", response_node)

# edges

graph.add_edge(START, "classifier")

graph.add_conditional_edges("classifier", route_query)

graph.add_edge("academic_rag", "response")
graph.add_edge("fee_rag", "response")
graph.add_edge("general", "response")

graph.add_edge("response", END)

workflow = graph.compile()

# ------------------------------------------------------------------
# step 6 - FastAPI wrapper (replaces the old input()/while-loop CLI
# so the HTML/CSS/JS frontend can talk to this over HTTP)
# ------------------------------------------------------------------

app = FastAPI(title="SNJB College Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROGRAMME_MAP = {
    "1": "B.E. Computer Engineering",
    "2": "B.E. Artificial Intelligence and Data Science",
    "3": "B.E. Mechanical Engineering",
    "4": "B.E. Civil Engineering",
    "5": "B.E. Electronics & Telecommunication Engineering",
    "6": "MBA",
    "7": "M.Tech",
}
VALID_PROGRAMMES = set(PROGRAMME_MAP.values())


class ChatRequest(BaseModel):
    programme: str = Field(..., description="Student's programme, e.g. 'B.E. Computer Engineering'")
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    query_type: str


@app.get("/")
def health():
    return {"status": "ok", "message": "SNJB College Assistant API is running"}


@app.get("/programmes")
def get_programmes():
    return {"programmes": sorted(VALID_PROGRAMMES)}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    programme = req.programme if req.programme in VALID_PROGRAMMES else "B.E. Computer Engineering"

    if not req.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty.")

    result = workflow.invoke({
        "programme": programme,
        "messages": [("human", req.message)],
    })

    return ChatResponse(
        response=result["messages"][-1].content,
        query_type=result.get("query_type", "general"),
    )
