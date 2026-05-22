import os
import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.document_loaders import TextLoader

def load_url(url: str) -> Document:
    """Fetch content from a URL and extract readable text."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove boilerplate elements to get high-quality content
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            element.extract()
            
        text = soup.get_text(separator="\n")
        
        # Clean up excessive newlines and whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
        
        title = soup.title.string.strip() if soup.title else url
        return Document(
            page_content=cleaned_text,
            metadata={"source": url, "title": title}
        )
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def ingest_documents(inputs, source_type="file", persist_dir="vector_store"):
    """
    Ingest files or URLs into the vector store.
    source_type can be "file" or "url".
    """
    docs = []
    
    if source_type == "file":
        for path in inputs:
            if not os.path.exists(path):
                print(f"File not found: {path}")
                continue
            try:
                loader = TextLoader(path, encoding="utf-8")
                docs.extend(loader.load())
            except Exception as e:
                print(f"Error reading file {path}: {e}")
    elif source_type == "url":
        for url in inputs:
            doc = load_url(url)
            if doc:
                docs.append(doc)
                
    if not docs:
        print("No documents were loaded.")
        return 0

    # Chunking strategy: Technical documentation is structural.
    # We use RecursiveCharacterTextSplitter with chunk_size=800 and chunk_overlap=100.
    # This captures complete code blocks and API descriptions while maintaining continuity.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(docs)

    embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordb = Chroma.from_documents(chunks, embeddings, persist_directory=persist_dir)
    
    # In newer langchain-chroma versions, persist() is handled automatically, but we call it if available
    if hasattr(vectordb, "persist"):
        vectordb.persist()
        
    print(f"Successfully ingested {len(chunks)} chunks into {persist_dir} from {len(docs)} sources.")
    return len(chunks)

if __name__ == "__main__":
    # Perform initial ingestion of our core corpus files
    doc_files = ["docs/fastapi.md", "docs/pydantic.md", "docs/langgraph.md"]
    ingest_documents(doc_files, source_type="file")
