from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from dotenv import load_dotenv  
from typing import Annotated
from langgraph.graph import add_messages
from langchain_community.document_loaders import (
    PyPDFLoader,
    PyMuPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    TextLoader,
    WebBaseLoader,
    UnstructuredImageLoader,
    UnstructuredPDFLoader
)
load_dotenv()
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Any, Dict
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_community.retrievers import BM25Retriever
from langgraph.graph import StateGraph, END, START
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from deep_translator import GoogleTranslator
from typing import TypedDict
import time

# llm = HuggingFaceEndpoint(
#     repo_id="meta-llama/Llama-3.1-8B-Instruct",
#     task="text-generation",
#     max_new_tokens=512,
#     temperature=0.7,
# )
import os
from langchain_groq import ChatGroq
model_text = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.5,
)
# model_text = ChatHuggingFace(llm=llm)

embedding = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)


from youtube_transcript_api import YouTubeTranscriptApi

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
import os

import os
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

import os
import ssl
import urllib3
urllib3.disable_warnings()
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

def get_transcript(video_id):
    scraper_api_key = os.getenv("SCRAPER_API_KEY")
    
    proxy_url = f"http://scraperapi:{scraper_api_key}@proxy-server.scraperapi.com:8001"
    
    proxy_config = GenericProxyConfig(
        http_url=proxy_url,
        https_url=proxy_url,
    )
    
    api = YouTubeTranscriptApi(proxy_config=proxy_config)
    
    # Patch requests to disable SSL verification
    import requests
    old_request = requests.Session.request
    def new_request(self, *args, **kwargs):
        kwargs['verify'] = False
        return old_request(self, *args, **kwargs)
    requests.Session.request = new_request
    
    try:
        transcript = api.fetch(video_id)
    except:
        transcript = api.list(video_id).find_generated_transcript(["en", "hi"]).fetch()

    return " ".join([t.text for t in transcript])
# ml algo-reMj4t7DQgI    RSeXGH2kxdo





def translation_list(trans):
    
    splitter=RecursiveCharacterTextSplitter(chunk_size=2000,chunk_overlap=100)
    splitted_doc=splitter.split_text(trans)
    translated_list=[]
    for item in splitted_doc:
        translated = GoogleTranslator(source='auto', target='en').translate(item)
        translated_list.append(translated)
    
    return translated_list

def translation_doc_list(translated_list):
    docs_list=[]
    for item in translated_list:
        doc=Document(page_content=item)
        docs_list.append(doc)
    
    return docs_list
    
    
    
def prepross(video_id):
    trans=get_transcript(video_id)
    list_trans=translation_list(trans)
    docs_list_trans=translation_doc_list(list_trans)
    
    return trans,list_trans,docs_list_trans
    
    




class state(TypedDict,total=False):
    mode:str
    video_id:str
    mindmap_list:List
    mindmap_content:str
    transcript:str
    translated_list:List
    translated_doc_list:List
    json_output:Any
    query: str
    multi_queries_result: List[str]
    merged_docs: List[Dict]
    reranked: List[Dict]
    retriever: Any
    bm25: Any
    context: str
    answer: str
    summary:str
    output_path:str
    
    
class QueryList(BaseModel):
    queries: List[str] = Field(description="List of exactly 3 search queries")

parser = PydanticOutputParser(pydantic_object=QueryList)

def multi_query(question):
    prompt = PromptTemplate(
        template="""
You are a query expansion assistant.

Generate exactly 3 different search queries 
to retrieve relevant documents.

Question: {question}

{format_instructions}
""",
        input_variables=["question"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        },
    )
    chain = prompt | model_text | parser
    result = chain.invoke({"question": question})
    return result.queries



def hybrid_search(state, query):
    all_docs = []
    retriever = state["retriever"]
    bm25_retrive = state["bm25"]

    vector_docs = retriever.invoke(query)
    for doc in vector_docs:
        all_docs.append({"doc": doc, "retriver": "vector", "query": query})

    bm25_docs = bm25_retrive.invoke(query)
    for doc in bm25_docs:
        all_docs.append({"doc": doc, "retriver": "bm25", "query": query})

    return all_docs


def multi_query_retrival(state):
    query = state["query"]
    docs = []
    queries = multi_query(query)
    for que in queries:
        res = hybrid_search(state, que)
        docs.extend(res)
    return {"multi_queries_result": docs}


def merging(state):
    docs = state["multi_queries_result"]
    merged = {}
    for item in docs:
        doc = item["doc"]
        query = item["query"]
        retriver = item["retriver"]
        doc_id = hash(doc.page_content)
        if doc_id not in merged:
            merged[doc_id] = {
                "doc": doc,
                "query": set(),
                "retriver": set(),
                "count": 0
            }
        merged[doc_id]["query"].add(query)
        merged[doc_id]["retriver"].add(retriver)
        merged[doc_id]["count"] += 1
    return {"merged_docs": list(merged.values())}


def re_ranking(state):
    reranked = []
    docs = state["merged_docs"]
    for item in docs:
        score = 0
        score += item["count"] * 2
        score += 3 if len(item["retriver"]) > 1 else 1
        score += len(item["query"])
        reranked.append({
            "doc": item["doc"],
            "score": score,
            "meta_info": {
                "query": item["query"],
                "retriver": item["retriver"],
                "count": item["count"]
            }
        })
    final = sorted(reranked, key=lambda x: x["score"], reverse=True)
    return {"reranked": final}


def context_builder(state):
    docs = state["reranked"]
    context_list = docs[:3]
    return {"context": " \n ".join([item["doc"].page_content for item in context_list])}



strparser = StrOutputParser()

def answer_generator(state):
    query = state["query"]
    context = state["context"]
    prompt = PromptTemplate(
        template="""You are a RAG assistant.

Answer ONLY using provided context.
If answer not in context say "Not found in context"

Query: {query}

Context:
{context}""",
        input_variables=["query", "context"]
    )
    chain = prompt | model_text | strparser
    result = chain.invoke({"query": query, "context": context})
    return {"answer": result}


def topic_extraction(text):
    prompt = PromptTemplate(
        template="""
You are a mind map extraction assistant. Your job is to analyze the given transcript chunk and extract only the most important topics and their relationships.

INSTRUCTIONS:
- Extract 2 to 4 most important key topics from this chunk only.
- For each topic, identify how it relates to other topics found in the same chunk.
- Be concise. Use short labels (2 words max per topic or relation).
- Ignore filler words, repetitions, and off-topic content.
- Focus only on concepts that carry real meaning or insight.

TRANSCRIPT CHUNK:
\"\"\"
{chunk}
\"\"\"
        """,
        input_variables=["chunk"]
    )

    parser = StrOutputParser()

    # Correct order: prompt → chat_model → parser
    chain = prompt | model_text | parser

    ans = chain.invoke({"chunk": text})
    return ans


def final_context(state):
    new_list=state["translated_list"]
    final_list=[]
    for text in new_list:
        data=topic_extraction(text)
        final_list.append(data)
    final_context=" ".join(item for item in final_list)
    
    
    return {"mindmap_content":final_context} 




from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

def final_extraction(state):
    text=state["translated_list"]
    parser = JsonOutputParser()
    
    prompt = PromptTemplate(
        template="""You are an expert mind map architect specializing in distilling YouTube video transcripts into clear, insightful knowledge structures.

You will receive extracted topics and relationships from chunked transcript segments.

YOUR TASK:
- Merge semantically similar or overlapping topics into unified concepts
- Eliminate duplicate, redundant, or overly granular topics
- Identify the core thesis or central idea of the video as the ROOT node
- Build logical parent-child hierarchies that reflect how ideas flow in the video
- Preserve only the most meaningful conceptual relationships

STRICT RULES:
- Return between 5 and 12 final topics (no more, no less)
- Root node must represent the video's central theme
- Merge near-identical labels (e.g. "AI" = "Artificial Intelligence", "ML" = "Machine Learning")
- All labels must be 2-5 words, title case, no punctuation
- Prefer hierarchical ("contains", "includes", "leads to") over flat relationships
- Remove weak, tangential, or filler topics (e.g. "Introduction", "Conclusion", "Example")
- Every topic must connect to at least one other topic
- Do NOT include timestamps, speaker names, or filler phrases

RELATIONSHIP TYPES (use only these):
- "contains" → parent holds child concept
- "leads to" → one idea causes or enables another
- "contrasts with" → opposing or alternative concepts
- "supports" → evidence or example backing a claim
- "requires" → dependency relationship

OUTPUT FORMAT — return STRICT valid JSON only.
No markdown, no code fences, no explanation, no preamble:

{{
  "central_theme": "Short Video Title or Core Idea",
  "topics": [
    {{"id": "T1", "label": "Root Concept"}},
    {{"id": "T2", "label": "Sub Concept"}}
  ],
  "relations": [
    {{"from": "T1", "to": "T2", "label": "contains"}}
  ]
}}

EXTRACTED TOPICS AND RELATIONSHIPS:
{text}""",
        input_variables=["text"]
    )
    
    chain = prompt | model_text | parser
    result = chain.invoke({"text": text})
    return {"json_output":result}


from pyvis.network import Network
from collections import defaultdict, deque


def json_to_mindmap(data, output_path="mindmap.html"):

    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#0d0d0d",
        font_color="white",
        directed=True
    )

    net.set_options("""
    {
      "nodes": {
        "shape": "box",
        "margin": 12,
        "font": { "size": 15, "color": "white", "bold": true, "face": "Georgia" },
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "shadow": { "enabled": true, "color": "#000000", "size": 12, "x": 4, "y": 4 },
        "fixed": { "x": false, "y": false }
      },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.7 } },
        "font": { "size": 9, "color": "#aaaaaa", "align": "middle", "background": "none", "strokeWidth": 0 },
        "smooth": { "type": "cubicBezier", "forceDirection": "none", "roundness": 0.4 },
        "width": 2,
        "shadow": { "enabled": true, "color": "#000000", "size": 6 },
        "color": { "inherit": false }
      },
      "physics": {
        "enabled": false
      },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "levelSeparation": 120,
          "nodeSpacing": 200,
          "treeSpacing": 250,
          "blockShifting": true,
          "edgeMinimization": true,
          "parentCentralization": true,
          "direction": "UD",
          "sortMethod": "directed"
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "zoomView": true,
        "dragNodes": true,
        "dragView": true,
        "navigationButtons": false,
        "keyboard": {
          "enabled": true,
          "bindToWindow": false
        }
      }
    }
    """)

    # ── Build children map ─────────────────────────────────────────────
    children    = defaultdict(list)
    all_targets = {r["to"] for r in data["relations"]}
    top_level   = [t["id"] for t in data["topics"] if t["id"] not in all_targets]

    for tid in top_level:
        children["ROOT"].append(tid)
    for rel in data["relations"]:
        children[rel["from"]].append(rel["to"])

    # ── BFS level assignment ───────────────────────────────────────────
    level_map = {"ROOT": 0}
    queue = deque(["ROOT"])
    while queue:
        node = queue.popleft()
        for kid in children.get(node, []):
            level_map[kid] = level_map[node] + 1
            queue.append(kid)

    # ── Style maps per level ───────────────────────────────────────────
    level_styles = {
        0: {"bg": "#C0392B", "border": "#FF6B6B", "size": 40, "font_size": 20, "shape": "ellipse"},
        1: {"bg": "#1A5276", "border": "#3498DB", "size": 30, "font_size": 15, "shape": "box"},
        2: {"bg": "#145A32", "border": "#27AE60", "size": 25, "font_size": 13, "shape": "box"},
        3: {"bg": "#4A235A", "border": "#8E44AD", "size": 20, "font_size": 12, "shape": "box"},
        4: {"bg": "#784212", "border": "#D35400", "size": 18, "font_size": 11, "shape": "box"},
    }
    default_style = {"bg": "#1A2530", "border": "#1ABC9C", "size": 16, "font_size": 10, "shape": "box"}

    # ── Add ROOT node ──────────────────────────────────────────────────
    s = level_styles[0]
    net.add_node(
        "ROOT",
        label=data["central_theme"],
        shape=s["shape"],
        color={"background": s["bg"], "border": s["border"],
               "highlight": {"background": "#E74C3C", "border": "#FF6B6B"}},
        size=s["size"],
        font={"size": s["font_size"], "color": "white", "bold": True},
        level=0,
        title=f"<b>Central Theme</b><br>{data['central_theme']}",
        widthConstraint={"minimum": 160, "maximum": 200}
    )

    # ── Add topic nodes ────────────────────────────────────────────────
    for topic in data["topics"]:
        lvl = level_map.get(topic["id"], 2)
        s   = level_styles.get(lvl, default_style)

        net.add_node(
            topic["id"],
            label=topic["label"],
            shape=s["shape"],
            color={"background": s["bg"], "border": s["border"],
                   "highlight": {"background": s["border"], "border": "white"}},
            size=s["size"],
            font={"size": s["font_size"], "color": "white", "bold": True},
            level=lvl,
            title=f"<b>Level {lvl}</b><br>{topic['label']}",
            widthConstraint={"minimum": 120, "maximum": 180}
        )

    # ── Add relation edges ─────────────────────────────────────────────
    edge_colors = {
        0: "#E74C3C",
        1: "#3498DB",
        2: "#27AE60",
        3: "#8E44AD",
        4: "#D35400",
    }

    for rel in data["relations"]:
        src_lvl = level_map.get(rel["from"], 1)
        color   = edge_colors.get(src_lvl, "#888888")
        net.add_edge(
            rel["from"],
            rel["to"],
            label=rel["label"],
            color={"color": color, "highlight": "white", "opacity": 0.8},
            width=2,
            font={"size": 9, "color": "#aaaaaa", "bold": False, "strokeWidth": 0}
        )

    # ── Connect top-level nodes to ROOT ───────────────────────────────
    for node_id in top_level:
        net.add_edge(
            "ROOT",
            node_id,
            label="covers",
            color={"color": "#E74C3C", "highlight": "#FF6B6B", "opacity": 0.9},
            width=3,
            font={"size": 9, "color": "#E74C3C", "strokeWidth": 0}
        )

    net.show(output_path, notebook=False)

    # ── Inject custom CSS + JS to unlock free dragging ────────────────
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    # This JS runs after the network is drawn and disables the
    # hierarchical layout lock so nodes can be dragged freely in X and Y
    unlock_js = """
    <script>
      // Wait for vis network to be ready, then unlock all nodes
      document.addEventListener("DOMContentLoaded", function () {
        // Poll until `network` is defined by pyvis's inline script
        var attempts = 0;
        var interval = setInterval(function () {
          attempts++;
          if (typeof network !== "undefined") {
            clearInterval(interval);

            // Disable hierarchical layout so nodes move freely
            network.setOptions({
              layout: { hierarchical: { enabled: false } },
              physics:  { enabled: false }
            });

            // Unfix every node so it can be dragged in any direction
            var nodeIds = network.body.data.nodes.getIds();
            var updates = nodeIds.map(function (id) {
              return { id: id, fixed: { x: false, y: false } };
            });
            network.body.data.nodes.update(updates);

          } else if (attempts > 100) {
            clearInterval(interval); // give up after ~5 s
          }
        }, 50);
      });
    </script>
    """

    custom_css = """
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }

      body {
        font-family: 'Georgia', serif;
        background: #0d0d1a;
        overflow: hidden;
      }

      body::before {
        content: '';
        position: fixed;
        inset: 0;
        z-index: -2;
        background:
          radial-gradient(ellipse at 20% 30%, rgba(52, 73, 170, 0.25) 0%, transparent 55%),
          radial-gradient(ellipse at 80% 70%, rgba(142, 68, 173, 0.2) 0%, transparent 55%),
          radial-gradient(ellipse at 50% 50%, rgba(22, 22, 50, 1) 0%, #0a0a14 100%);
      }

      body::after {
        content: '';
        position: fixed;
        width: 600px;
        height: 600px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(231,76,60,0.07) 0%, transparent 70%);
        top: -150px;
        left: -100px;
        z-index: -1;
        animation: drift 18s ease-in-out infinite alternate;
      }

      @keyframes drift {
        0%   { transform: translate(0px, 0px) scale(1); }
        50%  { transform: translate(80px, 60px) scale(1.1); }
        100% { transform: translate(-40px, 100px) scale(0.95); }
      }

      #mynetwork {
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        box-shadow:
          0 0 60px rgba(231, 76, 60, 0.12),
          0 0 120px rgba(52, 152, 219, 0.08),
          inset 0 0 40px rgba(0,0,0,0.4);
        background:
          url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Ccircle cx='50' cy='80' r='1' fill='rgba(255,255,255,0.35)'/%3E%3Ccircle cx='130' cy='20' r='0.8' fill='rgba(255,255,255,0.25)'/%3E%3Ccircle cx='210' cy='150' r='1.2' fill='rgba(255,255,255,0.3)'/%3E%3Ccircle cx='300' cy='60' r='0.7' fill='rgba(255,255,255,0.2)'/%3E%3Ccircle cx='370' cy='200' r='1' fill='rgba(255,255,255,0.35)'/%3E%3Ccircle cx='80' cy='280' r='0.9' fill='rgba(255,255,255,0.25)'/%3E%3Ccircle cx='180' cy='320' r='1.1' fill='rgba(255,255,255,0.3)'/%3E%3Ccircle cx='260' cy='250' r='0.8' fill='rgba(255,255,255,0.2)'/%3E%3Ccircle cx='340' cy='350' r='1' fill='rgba(255,255,255,0.3)'/%3E%3Ccircle cx='20' cy='370' r='0.7' fill='rgba(255,255,255,0.25)'/%3E%3Ccircle cx='390' cy='120' r='0.9' fill='rgba(255,255,255,0.2)'/%3E%3Ccircle cx='100' cy='180' r='1.3' fill='rgba(255,255,255,0.15)'/%3E%3Ccircle cx='240' cy='40' r='0.8' fill='rgba(255,255,255,0.3)'/%3E%3C/svg%3E"),
          radial-gradient(ellipse at center, #12122a 0%, #0a0a14 100%);
      }

      ::-webkit-scrollbar { width: 6px; background: #0d0d0d; }
      ::-webkit-scrollbar-thumb { background: #2c2c3e; border-radius: 3px; }
    </style>
    """

    html = html.replace("</head>", custom_css + unlock_js + "</head>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Mind map saved as '{output_path}' — nodes are freely draggable in any direction.")
    return output_path


import tempfile
import os

def mindmap_renderer(state):
    data = state["json_output"]
    
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp_path = tmp.name  # ← something like /tmp/tmpABCD1234.html
    
    output_path = json_to_mindmap(data, output_path=tmp_path)
    return {"output_path": output_path}


def summary_text(transcript):
    summary_prompt = PromptTemplate(
        template="""You are an expert summarizer for YouTube video transcripts.

    Your job is to extract a clean, structured summary from the given transcript.

    Follow these rules strictly:
    - Do NOT add any information not present in the transcript
    - Be concise but complete
    - Use simple, clear language
    - Preserve key technical terms as-is

    Transcript:
    {transcript}

    """,
        input_variables=["transcript"]
    )
    chain = summary_prompt | model_text | StrOutputParser()
    result = chain.invoke({"transcript": transcript})
    #  net.show
    return result



def summarize(state):
    context_list=state["translated_list"]
    summary_list=[]
    for text in context_list:
        summarized_context=summary_text(text)
        summary_list.append(summarized_context)

    context_merged=" ".join([item for item in summary_list])
    prompt=PromptTemplate(
        
    template="""You are an expert summarizer.

You are given multiple partial summaries of a YouTube video transcript.
Each partial summary covers a different section of the same video.

Your job is to consolidate them into ONE clean, coherent, non-redundant final summary.

Rules:
- Do NOT repeat the same point twice even if it appears in multiple partial summaries
- Maintain the logical flow — intro → explanation → conclusion
- Do NOT add anything outside of the provided summaries
- Preserve important technical terms as-is

Partial Summaries:
{chunk_summaries}

Generate the final summary in this structure:

Topic: (One line — what is the overall video about?)

Key Concepts Covered:
- (concept 1)
- (concept 2)
- (concept 3)
- (max 7 points)

Final Summary:
(4-6 sentences — covering the complete arc of the video in a flowing paragraph)

Key Takeaways:
- (insight 1)
- (insight 2)
- (insight 3)

Final Summary:
""",
    input_variables=["chunk_summaries"]
)
    chain=prompt | model_text | StrOutputParser()
    result = chain.invoke({"chunk_summaries": context_merged})
    return {"summary": result}


def supervisor(state):
    mode=state["mode"]
    if mode=="rag":
        return "rag"
    
    elif mode=="summary":
        return "summary"
    else:
        return "mindmap"
    


graph = StateGraph(state)

graph.add_node("multi_query_retrival", multi_query_retrival)
graph.add_node("merging", merging)
graph.add_node("re_ranking", re_ranking)
graph.add_node("context_builder", context_builder)
graph.add_node("answer_generator", answer_generator)
graph.add_node("final_context",final_context)
graph.add_node("final_extraction",final_extraction)
graph.add_node("summarizer",summarize)
graph.add_node("mindmap_renderer",mindmap_renderer)

graph.add_conditional_edges(START,supervisor,{
    "rag":"multi_query_retrival",
    "mindmap":"final_context",
    "summary":"summarizer"
    
})

graph.add_edge("multi_query_retrival", "merging")
graph.add_edge("merging", "re_ranking")
graph.add_edge("re_ranking", "context_builder")
graph.add_edge("context_builder", "answer_generator")
graph.add_edge("final_context","final_extraction")
graph.add_edge("final_extraction","mindmap_renderer")
graph.add_edge("mindmap_renderer",END)
graph.add_edge("answer_generator",END)
graph.add_edge("summarizer",END)


workflow = graph.compile()
