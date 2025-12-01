from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from uuid import uuid4
from openai import OpenAI

Líneas corregidas
import config
from rag_module import query_rag


FAULT_KEYWORDS = [
    "alpha call-up", "alpha call up", "acms", "acars", "eicas", "ecam",
    "bite", "fault code", "status message", "maintenance message", "advisory", "caution", "warning",
]

AIRCRAFT_TOKENS = [
    "a318", "a319", "a320", "a321", "a330", "a340", "a350", "a380",
    "b737", "b747", "b757", "b767", "b777", "b787",
]


def contains_fault_indicators(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in FAULT_KEYWORDS)


@dataclass
class AeroAgent:
    company_id: Optional[int]
    conversation_id: str
    memory: list = field(default_factory=list)

    def ask(self, question: str, aircraft_model: Optional[str], ata: Optional[str]) -> Dict[str, Any]:
        # Build system prompt
        system_prompt = (
            "You are a hybrid expert:\n"
            "- A senior aircraft maintenance engineer with more than 30 years of hands-on experience in line maintenance, base maintenance, MCC, and quality inspection.\n"
            "- A senior aircraft design engineer with more than 30 years of experience.\n\n"
            "HARD CONSTRAINTS:\n"
            "- You do NOT have access to proprietary OEM manuals (AMM, SRM, IPC, FCOM, TSM, WDM, schematics, etc.).\n"
            "- You must NOT quote, paraphrase, or simulate OEM procedures.\n"
            "- You may only use:\n"
            "  • Public MMELs and equivalent public documents.\n"
            "  • Public regulations and safety documents (FAA/EASA, advisory circulars).\n"
            "  • Human Factors and safety handbooks.\n"
            "  • Company MEL, MOE, procedures, engineering memos, and reliability reports that the tenant has uploaded.\n\n"
            "YOUR ROLE:\n"
            "- You are NOT a manual search engine.\n"
            "- You behave as an experienced engineering colleague who:\n"
            "  • Interprets and explains fault codes (Alpha Call-Up, ACMS, EICAS, BITE, status messages) in clear language.\n"
            "  • Correlates symptoms, ATA chapters, and system interdependencies.\n"
            "  • Highlights potential risks, Human Factors issues, and FOD exposure.\n"
            "  • Guides technicians on what TYPE of OEM documentation to consult (AMM, TSM, SRM, etc.) WITHOUT reproducing or guessing OEM procedures.\n"
            "  • Asks for missing data when information is incomplete (aircraft model, ATA, phase of flight, environment, recent maintenance, MEL deferrals, history of similar defects).\n"
            "  • Simplifies complex technical concepts for less experienced TMAs.\n\n"
            "BEHAVIOUR:\n"
            "- If you lack sufficient context, ask for more data instead of guessing.\n"
            "- Never state that an aircraft is serviceable, ready for Return-to-Service, or fit to fly.\n"
            "- Always remind the user to verify against OEM manuals, MMEL/MEL, and approved organisational procedures.\n"
            "- Respond in the same language the user writes in.\n"
        )

        is_fault_centric = contains_fault_indicators(question)

        # Query RAG (will return empty if not implemented)
        rag_result = query_rag(
            question,
            company_id=self.company_id,
            aircraft_model=aircraft_model,
            ata_chapter=ata,
        )
        docs = rag_result.get("fuentes", [])
        confianza = float(rag_result.get("confianza", 0.0))

        # Build context from RAG docs if available
        rag_context = ""
        if docs:
            rag_context = "\n\nRELEVANT DOCUMENTS FROM KNOWLEDGE BASE:\n"
            for i, doc in enumerate(docs, 1):
                rag_context += f"\n[Doc {i}] {doc.get('doc_title', 'Unknown')}:\n{doc.get('content', '')[:1000]}\n"

        # Build user message with context
        user_message = question
        if aircraft_model:
            user_message = f"[Aircraft: {aircraft_model}] {user_message}"
        if ata:
            user_message = f"[ATA: {ata}] {user_message}"
        if rag_context:
            user_message += rag_context

        # Check if API key is configured
        if not config.OPENAI_API_KEY:
            return {
                "respuesta": f"ERROR: OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.\n\n{config.SAFETY_DISCLAIMER}",
                "fuentes": [],
                "confianza": 0.0,
                "tipo": "error_no_api_key",
                "metadata": {},
            }

        # Call OpenAI API
        try:
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            
            # Add to memory for context
            self.memory.append({"role": "user", "content": user_message})
            
            # Build messages with conversation history (last 10 messages)
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.memory[-10:])
            
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL_CHAT,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
            )
            
            answer_body = response.choices[0].message.content
            
            # Save assistant response to memory
            self.memory.append({"role": "assistant", "content": answer_body})
            
            # Set confidence based on RAG results
            if docs and confianza >= 0.75:
                final_confidence = confianza
                tipo = "ok"
                caution_prefix = ""
            elif docs and confianza >= 0.5:
                final_confidence = confianza
                tipo = "low_confidence"
                caution_prefix = (
                    "⚠️ LOW-CONFIDENCE ADVISORY:\n"
                    "The following reasoning is based on limited context. "
                    "Verify carefully against OEM manuals and approved procedures.\n\n"
                )
            else:
                # No RAG docs, but OpenAI answered with general knowledge
                final_confidence = 0.6
                tipo = "general_knowledge"
                caution_prefix = ""

            full_answer = caution_prefix + answer_body + "\n\n" + config.SAFETY_DISCLAIMER
            
            return {
                "respuesta": full_answer,
                "fuentes": docs,
                "confianza": final_confidence,
                "tipo": tipo,
                "metadata": {
                    "ata_hint": ata,
                    "aircraft_model": aircraft_model,
                    "fault_mode": is_fault_centric,
                    "model_used": config.OPENAI_MODEL_CHAT,
                },
            }

        except Exception as e:
            error_msg = f"Error calling OpenAI API: {str(e)}"
            return {
                "respuesta": f"{error_msg}\n\n{config.SAFETY_DISCLAIMER}",
                "fuentes": [],
                "confianza": 0.0,
                "tipo": "error",
                "metadata": {"error": str(e)},
            }


class AgentManager:
    """Multi-tenant agent manager.
    Maps (company_id, conversation_id) -> AeroAgent.
    """
    def __init__(self) -> None:
        self.agents = {}

    def get_agent(self, company_id: Optional[int], conversation_id: Optional[str]) -> AeroAgent:
        if not conversation_id:
            conversation_id = str(uuid4())
        key = (company_id, conversation_id)
        if key not in self.agents:
            self.agents[key] = AeroAgent(company_id=company_id, conversation_id=conversation_id)
        return self.agents[key]
