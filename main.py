from typing import Optional, Dict, Any
from fastapi import FastAPI, Body, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import uuid4

# main.py: REEMPLAZA las líneas que tienen 'from ....' con esto
import config
from agents import AgentManager
from vision_module import analyze_image
from stt_module import transcribe_audio
from sql_agent import search_failures
from ml_faults import compute_trends # Asegúrate de que esta esté en la lista si la usas
from .ml_faults import compute_trends


app = FastAPI(title="AeroEngineer AI Brain V3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_manager = AgentManager()


class ChatRequest(BaseModel):
    pregunta: str
    modelo: Optional[str] = None
    ata: Optional[str] = None
    conversation_id: Optional[str] = None
    language: Optional[str] = "es"
    user_id: Optional[int] = None

    company_id: Optional[int] = None


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list
    confianza: float
    num_documentos: int
    tipo: str
    correlation_id: Optional[str] = None
    metadata: Optional[dict] = None


AVIATION_KEYWORDS = [
    "aircraft", "engine", "apu", "cfm", "v2500", "trent", "boeing", "airbus",
    "embraer", "ata", "amm", "mmel", "mro", "eicas", "ecam", "bite", "hydraulic",
    "flap", "slat", "spoiler", "brake", "landing gear", "lgciu", "fdr", "cvr",
    "bleed", "pack", "fuel pump", "generator", "idg", "starter",
]


def is_aviation_question(question: str, modelo: Optional[str], ata: Optional[str]) -> bool:
    q = (question or "").lower()
    if modelo:
        m = modelo.lower()
        if any(tok in m for tok in ["a320", "a330", "a350", "b737", "b777", "b787"]):
            return True
    if ata and ata.strip():
        return True
    return any(kw in q for kw in AVIATION_KEYWORDS)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest = Body(...)) -> ChatResponse:
    correlation_id = str(uuid4())

    if not is_aviation_question(payload.pregunta, payload.modelo, payload.ata):
        respuesta = "Out of aviation domain. Please rephrase.\n\n" + config.SAFETY_DISCLAIMER
        return ChatResponse(
            respuesta=respuesta,
            fuentes=[],
            confianza=0.0,
            num_documentos=0,
            tipo="out_of_domain",
            correlation_id=correlation_id,
            metadata={},
        )

    agent = agent_manager.get_agent(payload.company_id, payload.conversation_id)
    result = agent.ask(payload.pregunta, payload.modelo, payload.ata)

    fuentes = result.get("fuentes", [])
    confianza = float(result.get("confianza", 0.0))
    tipo = result.get("tipo", "ok")
    metadata = result.get("metadata", {})

    return ChatResponse(
        respuesta=result["respuesta"],
        fuentes=fuentes,
        confianza=confianza,
        num_documentos=len(fuentes),
        tipo=tipo,
        correlation_id=correlation_id,
        metadata=metadata,
    )


@app.post("/api/vision/analyze")
async def vision_analyze(
    image: UploadFile = File(...),
    question: str = Form("Describe what you see from a maintenance perspective"),
):
    data = await image.read()
    analysis = analyze_image(data, question)
    analysis["respuesta"] = analysis.get("summary", "") + "\n\n" + config.SAFETY_DISCLAIMER
    analysis["fuentes"] = []
    analysis["confianza"] = 0.0
    analysis["num_documentos"] = 0
    return analysis


@app.post("/api/stt/transcribe")
async def stt_transcribe(audio: UploadFile = File(...), language: str = Form("es")):
    data = await audio.read()
    result = transcribe_audio(data, language=language)
    return result


@app.get("/api/faults/search")
def faults_search(
    company_id: int,
    aircraft: Optional[str] = None,
    ata: Optional[str] = None,
    fault_code: Optional[str] = None,
):
    filters = {"aircraft": aircraft, "ata": ata, "fault_code": fault_code}
    result = search_failures(company_id, filters)
    result["respuesta"] = result.get("respuesta", "") + "\n\n" + config.SAFETY_DISCLAIMER
    return result


@app.get("/api/faults/trends")
def faults_trends(company_id: int):
    data = compute_trends(company_id)
    return data
