from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
load_dotenv()
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from mindmap_backend import prepross, embedding, workflow

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Cache so same video_id doesn't reprocess every request ──────────
video_cache = {}

def get_video_data(video_id: str):
    if video_id not in video_cache:
        trans, list_trans, docs_list_trans = prepross(video_id)
        vector_db = FAISS.from_documents(docs_list_trans, embedding)
        retriever = vector_db.as_retriever(search_kwargs={"k": 3})
        bm25 = BM25Retriever.from_documents(docs_list_trans)
        bm25.k = 3
        video_cache[video_id] = {
            "trans": trans,
            "list_trans": list_trans,
            "docs_list_trans": docs_list_trans,
            "retriever": retriever,
            "bm25": bm25,
        }
    return video_cache[video_id]


# ── RAG endpoint ─────────────────────────────────────────────────────
@app.post("/rag")
def rag(video_id: str = Form(...), query: str = Form(...)):
    data = get_video_data(video_id)
    result = workflow.invoke({
        "mode": "rag",
        "query": query,
        "translated_list": data["list_trans"],
        "translated_doc_list": data["docs_list_trans"],
        "retriever": data["retriever"],
        "bm25": data["bm25"],
    })
    return {"answer": result["answer"]}


# ── Summary endpoint ─────────────────────────────────────────────────
@app.post("/summary")
def summary(video_id: str = Form(...)):
    data = get_video_data(video_id)
    result = workflow.invoke({
        "mode": "summary",
        "translated_list": data["list_trans"],
        "translated_doc_list": data["docs_list_trans"],
    })
    return {"summary": result["summary"]}


# ── Mindmap endpoint ─────────────────────────────────────────────────
import os
from fastapi.responses import HTMLResponse

@app.post("/mindmap")
def mindmap(video_id: str = Form(...)):
    data = get_video_data(video_id)
    result = workflow.invoke({
        "mode": "mindmap",
        "translated_list": data["list_trans"],
        "translated_doc_list": data["docs_list_trans"],
    })
    
    output_path = result["output_path"]
    
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    finally:
        os.unlink(output_path)
    
    return HTMLResponse(content=html_content)