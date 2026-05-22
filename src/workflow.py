import os
import json
from typing import TypedDict, List, Any, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from src.websearch import serper_search
from src.memory import update_memory, get_history

# Load environment variables
load_dotenv(override=True)

# Initialize Gemini model (Gemini 1.5 Flash is recommended for fast, cheap inference)
from langchain_google_genai import ChatGoogleGenerativeAI
import os

gemini_llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash-001"),  # default to a valid model
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)



# 1. State Schema
class RAGState(TypedDict):
    question: str
    rewritten_query: str
    query_type: str
    retrieved_docs: List[Any]
    graded_docs: List[Any]
    answer: str
    retries: int

# Initialize the embedding model (MUST match the one used during ingestion)
embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Nodes
def query_analysis(state: RAGState):
    """Analyze the user's raw question, perform query expansion, and classify the query type."""
    question = state["question"]
    
    prompt = f"""
    You are an AI assistant analyzing a technical documentation query.
    Analyze the following user question:
    "{question}"

    Perform two tasks:
    1. Rewrite or expand the query to improve similarity search in a technical vector store (add synonyms, clarify ambiguity, make it keyword-rich).
    2. Classify the query type as one of: "conceptual", "how-to", "troubleshooting", or "API reference".

    Respond ONLY in valid JSON format with the following keys:
    - "rewritten_query": the optimized query string
    - "query_type": the classification category

    Do not include any markdown styling like ```json or ```, just the raw JSON text.
    """
    
    try:
        res = gemini_llm.invoke(prompt)
        content = res.content.strip()
        
        # Clean markdown codeblock backticks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        parsed = json.loads(content)
        rewritten = parsed.get("rewritten_query", question)
        query_type = parsed.get("query_type", "conceptual")
    except Exception as e:
        print(f"Error in query_analysis parsing: {e}")
        rewritten = question
        query_type = "conceptual"
        
    return {
        "rewritten_query": rewritten,
        "query_type": query_type,
        "retries": 0,
        "graded_docs": [],
        "retrieved_docs": []
    }

def retrieval(state: RAGState):
    """Retrieve relevant documents from the Chroma vector store."""
    query = state["rewritten_query"]
    vectordb = Chroma(persist_directory="vector_store", embedding_function=embedding_model)
    results = vectordb.similarity_search(query, k=4)
    return {"retrieved_docs": results}

def grading(state: RAGState):
    """Filter retrieved documents based on relevance to the user's question."""
    question = state["question"]
    retrieved = state.get("retrieved_docs", [])
    
    graded = []
    for doc in retrieved:
        prompt = f"""
        Analyze whether the following document chunk is relevant to help answer the user's question.
        
        Question: {question}
        Document:
        {doc.page_content}
        
        Respond ONLY with 'relevant' if it is useful, or 'irrelevant' if it is not. Do not explain.
        """
        try:
            res = gemini_llm.invoke(prompt)
            verdict = res.content.strip().lower()
            if "relevant" in verdict:
                graded.append(doc)
        except Exception as e:
            print(f"Error during document grading: {e}")
            
    return {"graded_docs": graded}

def rewrite_query(state: RAGState):
    """Rewrite query to search differently since previous query returned no relevant documents."""
    question = state["question"]
    prev_query = state.get("rewritten_query", "")
    current_retries = state.get("retries", 0) + 1
    
    prompt = f"""
    You are working on a self-corrective RAG pipeline.
    The previous search query '{prev_query}' returned no relevant documents for the technical question:
    "{question}"
    
    Please write an alternate search query using different keywords, synonyms, or technical terms to locate relevant documentation.
    Return ONLY the new query string, with no commentary or quotes.
    """
    
    try:
        res = gemini_llm.invoke(prompt)
        new_query = res.content.strip()
    except Exception as e:
        print(f"Error rewriting query: {e}")
        new_query = question
        
    print(f"Retry #{current_retries} rewriting query from '{prev_query}' to '{new_query}'")
    return {"rewritten_query": new_query, "retries": current_retries}

def generation(state: RAGState):
    """Generate final answer using retrieved context and historical conversation context."""
    question = state["question"]
    graded = state.get("graded_docs", [])
    
    context_str = "\n\n".join([
        f"[Source: {doc.metadata.get('source', 'unknown')} | Title: {doc.metadata.get('title', 'Doc')}]\n{doc.page_content}"
        for doc in graded
    ])
    
    history = get_history()
    
    prompt = f"""
    You are a professional RAG-Based Technical Documentation Assistant.
    Answer the question accurately using ONLY the provided context and conversation history.
    
    Guidelines:
    1. Rely ONLY on the clear facts in the context. Do not make up information.
    2. Always cite your sources in line (e.g. "...as described in [source_name]").
    3. If the context does not contain enough information to answer, state clearly that you don't have enough documentation to answer.
    
    Conversation History:
    {history}
    
    Context:
    {context_str}
    
    Question: {question}
    
    Helpful Technical Answer:
    """
    
    try:
        res = gemini_llm.invoke(prompt)
        answer = res.content.strip()
    except Exception as e:
        answer = f"Error generating answer: {e}"
        
    update_memory(question, answer)
    return {"answer": answer}

def hallucination_check(state: RAGState):
    """Verify if the generated answer is strictly supported by the retrieved documents (Self-RAG)."""
    answer = state.get("answer", "")
    graded = state.get("graded_docs", [])
    
    # If no graded documents (e.g. web fallback), we skip hallucination check
    if not graded:
        return {}
        
    context_str = "\n\n".join([doc.page_content for doc in graded])
    
    prompt = f"""
    Analyze if the generated answer is completely supported by the factual context provided.
    
    Context:
    {context_str}
    
    Generated Answer:
    {answer}
    
    Respond with 'supported' if the answer contains only facts from the context.
    Respond with 'unsupported' if the answer introduces outside information or claims not supported by the context.
    Do not explain, just return the single word.
    """
    
    try:
        res = gemini_llm.invoke(prompt)
        verdict = res.content.strip().lower()
        if "unsupported" in verdict:
            print("⚠️ Hallucination detected by self-corrective layer!")
            return {"answer": f"⚠️ [Self-Correction: Generated answer may contain unsupported claims]\n\n{answer}"}
    except Exception as e:
        print(f"Error in hallucination checking: {e}")
        
    return {}

def web_fallback(state: RAGState):
    """Web search fallback using Serper API when vector store yields no relevant results."""
    question = state["question"]
    print(f"Vector search returned no results. Performing web fallback for: '{question}'")
    
    results = serper_search(question)
    
    if not results:
        return {
            "answer": "I'm sorry, but I couldn't find any relevant documentation in my local database, and web search returned no results.",
            "graded_docs": []
        }
        
    context_str = "\n\n".join([
        f"[Web Source: {r.get('link')} | Title: {r.get('title')}]\n{r.get('snippet')}"
        for r in results
    ])
    
    prompt = f"""
    You are an AI technical assistant. You could not find local documentation for the query.
    Answer the user's question using the following organic search result snippets:
    
    {context_str}
    
    Question: {question}
    
    Provide an accurate answer citing the web links provided in the context:
    """
    
    try:
        res = gemini_llm.invoke(prompt)
        answer = res.content.strip()
    except Exception as e:
        answer = f"Error generating answer from web search: {e}"
        
    # Wrap results as standard documents for downstream usage/citations
    web_docs = [
        Document(
            page_content=r.get("snippet", ""),
            metadata={"source": r.get("link", "web"), "title": r.get("title", "Web Result")}
        )
        for r in results
    ]
    
    update_memory(question, answer)
    return {"answer": answer, "graded_docs": web_docs}

# 3. Define the Router (Conditional Edge)
def decide_next_step(state: RAGState):
    """Decide whether to proceed to generation, rewrite query, or trigger web search fallback."""
    if state.get("graded_docs"):
        return "generation"
        
    retries = state.get("retries", 0)
    if retries < 2:
        return "rewrite_query"
    else:
        return "web_fallback"

# 4. Build LangGraph Workflow
workflow = StateGraph(RAGState)

workflow.add_node("query_analysis", query_analysis)
workflow.add_node("retrieval", retrieval)
workflow.add_node("grading", grading)
workflow.add_node("rewrite_query", rewrite_query)
workflow.add_node("generation", generation)
workflow.add_node("hallucination_check", hallucination_check)
workflow.add_node("web_fallback", web_fallback)

# Setup graph edges
workflow.set_entry_point("query_analysis")
workflow.add_edge("query_analysis", "retrieval")
workflow.add_edge("retrieval", "grading")

# Conditional Edge for self-corrective query rewriting / fallback
workflow.add_conditional_edges(
    "grading",
    decide_next_step,
    {
        "generation": "generation",
        "rewrite_query": "rewrite_query",
        "web_fallback": "web_fallback"
    }
)

# Route query rewrite back to retrieval
workflow.add_edge("rewrite_query", "retrieval")

# Route final generation and fallback nodes to completion
workflow.add_edge("generation", "hallucination_check")
workflow.add_edge("hallucination_check", END)
workflow.add_edge("web_fallback", END)

# Compile graph
graph = workflow.compile()
