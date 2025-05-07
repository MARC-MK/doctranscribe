from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from typing import List, Dict, Any, Optional
import json
from ..deps import get_s3_client
from ..config import settings
import openai
import os
from pydantic import BaseModel

router = APIRouter(prefix="/assistant", tags=["assistant"])

# ---------- Models ----------

class AssistantMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    job_id: str
    user_message: str

class ChatResponse(BaseModel):
    assistant_messages: List[AssistantMessage]

class DismissRequest(BaseModel):
    dismissed_by: str

# ---------- WebSocket Manager ----------

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def broadcast_anomaly_update(self, client_id: str, job_id: str, anomaly_count: int):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                await connection.send_json({
                    "type": "anomaly:update",
                    "data": {
                        "job_id": job_id,
                        "anomaly_count": anomaly_count
                    }
                })

manager = ConnectionManager()

# ---------- WebSocket Endpoint ----------

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)

# ---------- REST Endpoints ----------

@router.get("/test", status_code=status.HTTP_200_OK)
async def test_assistant_router():
    """Simple test endpoint to check if the assistant router is working."""
    return {"status": "ok", "message": "Assistant router is working"}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Proxy endpoint to OpenAI Assistants API"""
    try:
        # In a real implementation, we would:
        # 1. Validate the job_id belongs to the user
        # 2. Fetch context for the job (JSON file, anomalies)
        # 3. Create or retrieve an OpenAI thread
        # 4. Add the user message to the thread
        # 5. Run the assistant to generate a response
        
        # For now, we'll simulate a response with a mock implementation
        
        # Check if OpenAI API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Fall back to simulated response
            return generate_simulated_response(request.job_id, request.user_message)
        
        # For demo purposes, we'll just return a simulated response
        return generate_simulated_response(request.job_id, request.user_message)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )

def generate_simulated_response(job_id: str, user_message: str) -> ChatResponse:
    """Generate a simulated response for demonstration purposes"""
    lower_message = user_message.lower()
    
    if "summary" in lower_message:
        return ChatResponse(
            assistant_messages=[
                AssistantMessage(
                    role="assistant", 
                    content="I've analyzed the 2 anomalies in this survey batch:\n\n"
                            "**1. Row 4 (Cholesterol)**: Value 240 mg/dL exceeds reference range (<200 mg/dL)\n"
                            "- Algorithm: Range check\n"
                            "- Confidence: 98%\n"
                            "- Clinical relevance: High cholesterol is associated with increased cardiovascular risk\n\n"
                            "**2. Row 7 (Glucose)**: Value 42 mg/dL is below reference range (70-100 mg/dL)\n"
                            "- Algorithm: Statistical outlier\n"
                            "- Confidence: 85%\n"
                            "- Clinical relevance: Low glucose may indicate hypoglycemia\n\n"
                            "The cholesterol reading has the highest confidence score. Would you like me to suggest possible actions for either of these?"
                )
            ]
        )
    elif "row-by-row" in lower_message or "row by row" in lower_message:
        return ChatResponse(
            assistant_messages=[
                AssistantMessage(
                    role="assistant", 
                    content="Let's review each anomaly in detail:\n\n"
                            "**Anomaly 1**: Row 4 (Cholesterol)\n"
                            "- Value: 240 mg/dL\n"
                            "- Reference range: <200 mg/dL\n"
                            "- Algorithm: Range check\n"
                            "- Confidence: 98%\n\n"
                            "This is a common clinical finding indicating borderline high cholesterol. The algorithm has high confidence as this is a straightforward range violation. This level may warrant lifestyle modifications or medication depending on other risk factors.\n\n"
                            "Would you like me to analyze the next anomaly or provide potential clinical recommendations for this one?"
                )
            ]
        )
    elif "tell me about row" in lower_message or "tell me about row-" in lower_message:
        # Extract the row number from the message
        row_id = "row-4"  # Default to row 4 (cholesterol) if we can't extract
        if "row-7" in lower_message or "row 7" in lower_message:
            row_id = "row-7"
            
        if row_id == "row-4":
            return ChatResponse(
                assistant_messages=[
                    AssistantMessage(
                        role="assistant", 
                        content="**Detailed analysis of Row 4 (Cholesterol)**\n\n"
                                "- Value: 240 mg/dL\n"
                                "- Reference range: <200 mg/dL\n"
                                "- Algorithm: Range check\n"
                                "- Confidence: 98%\n\n"
                                "**Clinical context:**\n"
                                "Total cholesterol of 240 mg/dL is classified as high according to ATP III guidelines. This level is associated with increased risk of cardiovascular disease.\n\n"
                                "**Possible causes:**\n"
                                "- Diet high in saturated fats\n"
                                "- Genetic factors (familial hypercholesterolemia)\n"
                                "- Secondary causes: hypothyroidism, kidney disease, or medications\n\n"
                                "**Recommendation:**\n"
                                "Consider flagging for clinical review, especially if other risk factors are present."
                    )
                ]
            )
        else:  # row-7 (glucose)
            return ChatResponse(
                assistant_messages=[
                    AssistantMessage(
                        role="assistant", 
                        content="**Detailed analysis of Row 7 (Glucose)**\n\n"
                                "- Value: 42 mg/dL\n"
                                "- Reference range: 70-100 mg/dL\n"
                                "- Algorithm: Statistical outlier\n"
                                "- Confidence: 85%\n\n"
                                "**Clinical context:**\n"
                                "This glucose level is significantly below the normal fasting range and could indicate hypoglycemia. This is a clinically significant finding that may require immediate attention.\n\n"
                                "**Possible causes:**\n"
                                "- Medication effect (insulin, sulfonylureas)\n"
                                "- Prolonged fasting\n"
                                "- Endocrine disorders\n"
                                "- Lab error or sample handling issues\n\n"
                                "**Recommendation:**\n"
                                "This requires immediate clinical verification and potential follow-up with the patient."
                    )
                ]
            )
    elif "dismiss" in lower_message and ("all" in lower_message or "row" in lower_message):
        row_num = "all anomalies" if "all" in lower_message else "row " + next((s for s in lower_message.split() if s.isdigit()), "")
        return ChatResponse(
            assistant_messages=[
                AssistantMessage(
                    role="assistant", 
                    content=f"Are you sure you want to dismiss {row_num}? This action will mark the anomaly as reviewed and reduce the anomaly count in your dashboard.\n\nType 'Yes, dismiss {row_num}' to confirm."
                )
            ]
        )
    elif "yes" in lower_message and "dismiss" in lower_message:
        return ChatResponse(
            assistant_messages=[
                AssistantMessage(
                    role="assistant", 
                    content="I've dismissed the anomaly. The count has been updated in your dashboard.\n\nIs there anything else you'd like to do with the remaining anomalies?"
                )
            ]
        )
    elif "clinical" in lower_message or "significance" in lower_message:
        # Respond to requests about clinical significance
        if "cholesterol" in lower_message or "row 4" in lower_message or "row-4" in lower_message:
            return ChatResponse(
                assistant_messages=[
                    AssistantMessage(
                        role="assistant", 
                        content="**Clinical significance of elevated cholesterol (240 mg/dL):**\n\n"
                                "- **Borderline high** according to ATP III guidelines (200-239 mg/dL is borderline, ≥240 mg/dL is high)\n"
                                "- Associated with approximately **2x increased risk** of coronary heart disease compared to levels below 200 mg/dL\n"
                                "- Part of lipid panel interpretation requiring context of HDL, LDL, and triglycerides\n"
                                "- Often requires lifestyle modifications as first-line intervention\n"
                                "- May warrant medication (statins) depending on overall cardiovascular risk profile\n\n"
                                "Would you like more information about treatment guidelines or next steps?"
                    )
                ]
            )
        else:
            return ChatResponse(
                assistant_messages=[
                    AssistantMessage(
                        role="assistant", 
                        content="**Clinical significance of low glucose (42 mg/dL):**\n\n"
                                "- **Hypoglycemia** defined as glucose <70 mg/dL, with <54 mg/dL considered clinically significant\n"
                                "- May present with symptoms: confusion, dizziness, sweating, tachycardia\n"
                                "- Can progress to loss of consciousness, seizures if severe\n"
                                "- **Urgent clinical finding** requiring immediate verification\n"
                                "- Patients on insulin or sulfonylureas are at higher risk\n"
                                "- May require immediate intervention (glucose administration) depending on patient status\n\n"
                                "This finding should be prioritized for follow-up due to potential acute clinical significance."
                    )
                ]
            )
    else:
        return ChatResponse(
            assistant_messages=[
                AssistantMessage(
                    role="assistant", 
                    content="I found 2 anomalies in this survey batch. How would you like to proceed?\n\n"
                            "You can say:\n"
                            "- 'Show me a summary'\n"
                            "- 'Review row by row'\n"
                            "- 'Tell me about row 4' (Cholesterol anomaly)\n"
                            "- 'Tell me about row 7' (Glucose anomaly)\n"
                            "- 'Dismiss all anomalies'\n"
                            "- Or ask me about clinical significance of any finding"
                )
            ]
        )

@router.post("/jobs/{job_id}/anomalies/{row_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_anomaly(job_id: str, row_id: str, request: DismissRequest, req: Request):
    """Dismiss an anomaly by marking it as reviewed"""
    try:
        # In a real implementation, we would:
        # 1. Validate the job_id and row_id
        # 2. Update the anomaly status in the database
        # 3. Broadcast the update via WebSocket
        
        # For demonstration, we'll just simulate success
        # and broadcast a mock update via WebSocket
        client_id = "demo_client"  # In reality, this would come from auth
        await manager.broadcast_anomaly_update(client_id, job_id, 1)  # Decrement count by 1
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error dismissing anomaly: {str(e)}"
        ) 