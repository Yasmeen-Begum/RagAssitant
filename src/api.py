import os
import json
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from src.ingest import ingest_documents
from src.workflow import graph, RAGState

app = FastAPI(
    title="RAG-Based Technical Documentation Assistant",
    description="A self-corrective RAG system powered by LangGraph, FastAPI, and Gemini.",
    version="1.0.0"
)

# 1. Pydantic Models for Input Validation
class QueryRequest(BaseModel):
    question: str

class FeedbackRequest(BaseModel):
    answer_id: str
    thumbs_up: bool
    comment: Optional[str] = None

# 2. Endpoints
@app.post("/query")
async def query_endpoint(data: QueryRequest):
    """
    Submit a question to the self-corrective RAG pipeline.
    Returns the answer along with query classification and document citations.
    """
    if not data.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    try:
        # Initialize LangGraph state
        state = RAGState(question=data.question, retries=0)
        result = graph.invoke(state)
        
        # Format and extract sources
        sources = [
            {
                "source": doc.metadata.get("source", "unknown"),
                "title": doc.metadata.get("title", "Doc")
            }
            for doc in result.get("graded_docs", [])
        ]
        
        return {
            "answer": result["answer"],
            "query_type": result.get("query_type", "conceptual"),
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.post("/ingest")
async def ingest_endpoint(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """
    Ingest a new document from either a local file upload or a public URL.
    Generates embeddings and splits content structurally into the vector database.
    """
    if not file and not url:
        raise HTTPException(status_code=400, detail="You must provide either a file upload or a url.")
        
    try:
        if file:
            os.makedirs("docs", exist_ok=True)
            path = f"docs/{file.filename}"
            with open(path, "wb") as f:
                f.write(await file.read())
            chunks = ingest_documents([path], source_type="file")
            return {"status": "success", "source": file.filename, "chunks_ingested": chunks}
            
        if url:
            chunks = ingest_documents([url], source_type="url")
            return {"status": "success", "source": url, "chunks_ingested": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")

@app.get("/documents")
async def list_docs():
    """
    List all indexed file-based documents in the corpus directory.
    """
    try:
        if not os.path.exists("docs"):
            return {"documents": []}
        return {"documents": os.listdir("docs")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.post("/feedback")
async def feedback(data: FeedbackRequest):
    """
    Submit thumbs up/down feedback along with an optional comment on generated answers.
    Feedback is stored locally for continuous model/retrieval evaluation.
    """
    feedback_file = "feedback.json"
    feedbacks = []
    
    try:
        if os.path.exists(feedback_file):
            with open(feedback_file, "r") as f:
                feedbacks = json.load(f)
    except Exception as e:
        print(f"Error loading existing feedback: {e}")
        
    new_feedback = data.dict()
    feedbacks.append(new_feedback)
    
    try:
        with open(feedback_file, "w") as f:
            json.dump(feedbacks, f, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing feedback to file: {str(e)}")
        
    return {"status": "recorded", "feedback": new_feedback}
