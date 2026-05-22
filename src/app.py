import os
import gradio as gr
from src.workflow import graph
from src.memory import get_history

def rag_query(question):
    """Invoke the LangGraph self-corrective RAG workflow and return structured results."""
    if not question.strip():
        return "Please enter a valid question.", "N/A", "No sources cited.", get_history()
        
    try:
        # Initialize state dict
        state = {
            "question": question,
            "retries": 0,
            "retrieved_docs": [],
            "graded_docs": []
        }
        
        result = graph.invoke(state)
        
        # Build Markdown links for references
        sources = []
        seen_sources = set()
        for doc in result.get("graded_docs", []):
            src = doc.metadata.get("source", "unknown")
            if src in seen_sources:
                continue
            seen_sources.add(src)
            title = doc.metadata.get("title", "Doc Chunk")
            sources.append(f"🔗 **[{title}]({src})** ({src})")
            
        sources_text = "\n\n".join(sources) if sources else "No local/web sources were graded as relevant."
        query_type = result.get("query_type", "conceptual").upper()
        
        return result["answer"], f"🏷️ {query_type}", sources_text, get_history()
    except Exception as e:
        return f"An error occurred in the pipeline: {str(e)}", "ERROR", "N/A", get_history()

# Custom CSS for state-of-the-art premium visual aesthetic
custom_css = """
body {
    background-color: #0b0f19;
}
.gradio-container {
    font-family: 'Outfit', 'Inter', sans-serif !important;
    max-width: 1100px !important;
}
.header-container {
    text-align: center;
    background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
    padding: 2.5rem;
    border-radius: 16px;
    margin-bottom: 2rem;
    border: 1px solid #312e81;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7);
}
.header-container h1 {
    font-size: 2.5rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 0.5rem;
    background: linear-gradient(90deg, #6366f1, #d946ef);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.header-container p {
    color: #94a3b8;
    font-size: 1.1rem;
}
.submit-btn {
    background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
.submit-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4) !important;
}
"""

# Build Gradio Block UI with Soft theme and dark colors
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="purple",
    neutral_hue="slate"
).set(
    body_background_fill="#0b0f19",
    block_background_fill="#111827",
    block_border_color="#1f2937",
    block_title_text_color="#e2e8f0",
    body_text_color="#cbd5e1"
)

with gr.Blocks(theme=theme, css=custom_css, title="Express Analytics | AI/ML Intern RAG") as demo:
    
    # Elegant Custom Header
    gr.HTML("""
        <div class="header-container">
            <h1>📘 Technical Documentation Assistant</h1>
            <p>Self-Corrective LangGraph Pipeline &bull; Gemini 1.5 &bull; ChromaDB &bull; Serper Web Fallback</p>
        </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=5):
            gr.Markdown("### 📥 Ask Your Technical Question")
            question_input = gr.Textbox(
                label="Question",
                placeholder="e.g., How do I define a Pydantic model with validation rules?",
                lines=3,
                max_lines=5
            )
            
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear", variant="secondary")
                submit_btn = gr.Button("⚡ Run Graph Workflow", variant="primary", elem_classes=["submit-btn"])
                
            gr.Markdown("### 🏷️ Query Classification")
            query_type_output = gr.Label(label="Classified Intent")
            
        with gr.Column(scale=6):
            gr.Markdown("### 🤖 Assistant Answer")
            answer_output = gr.Markdown(value="*Results will be displayed here...*")
            
            gr.Markdown("### 📚 Source Citations & References")
            sources_output = gr.Markdown(value="*No sources cited yet.*")

    with gr.Row(variant="panel"):
        with gr.Column():
            gr.Markdown("### 🧠 Conversation Short-term Memory (Chat History)")
            memory_output = gr.Textbox(
                label="Active History",
                interactive=False,
                lines=6,
                placeholder="No previous interactions in this session yet."
            )
            
    # Set up interactive events
    submit_btn.click(
        fn=rag_query,
        inputs=[question_input],
        outputs=[answer_output, query_type_output, sources_output, memory_output]
    )
    
    clear_btn.click(
        fn=lambda: ("", "N/A", "*No sources cited yet.*", get_history()),
        outputs=[question_input, query_type_output, sources_output, memory_output]
    )

if __name__ == "__main__":
    # In production/deployment, run FastAPI. For local UI, run Gradio.
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)

