from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from app.services.llm import get_llm

class MatchState(TypedDict, total=False):
    resume_text: str
    job_description: str
    matched_skills: list[str]
    missing_skills: list[str]
    score: float
    explanation: str

def build_match_graph():
    def explain(state: MatchState) -> MatchState:
        llm = get_llm()
        prompt = f"""You are a careful career analyst. Explain this resume-to-job comparison using only the supplied evidence. Do not infer protected characteristics, invent experience, or claim the score guarantees hiring. Distinguish evidence from uncertainty. Keep response under 180 words.
Score: {state['score']}/100 (deterministic skill/evidence estimate)
Matched skills: {state['matched_skills']}
Missing skills: {state['missing_skills']}
Resume excerpt: {state['resume_text'][:7000]}
Job description: {state['job_description'][:5000]}"""
        result = llm.invoke([SystemMessage(content="Provide transparent, evidence-based career analysis."), HumanMessage(content=prompt)])
        return {"explanation": str(result.content)}
    graph = StateGraph(MatchState)
    graph.add_node("explain_match", explain)
    graph.set_entry_point("explain_match")
    graph.add_edge("explain_match", END)
    return graph.compile()

def run_match_explanation(data: dict) -> str:
    return build_match_graph().invoke(data).get("explanation", "")

class ContentState(TypedDict, total=False):
    task: str
    context: str
    result: str

def build_content_graph():
    def generate(state: ContentState) -> ContentState:
        llm = get_llm()
        response = llm.invoke([SystemMessage(content="You are an honest AI career coach. Return useful, structured, actionable content. Never fabricate credentials, job openings, or guarantees."), HumanMessage(content=f"""Task: {state['task']}\nContext: {state['context'][:12000]}""")])
        return {"result": str(response.content)}
    graph = StateGraph(ContentState)
    graph.add_node("generate", generate)
    graph.set_entry_point("generate")
    graph.add_edge("generate", END)
    return graph.compile()

def run_content_agent(task: str, context: str) -> str:
    return build_content_graph().invoke({"task": task, "context": context}).get("result", "")
