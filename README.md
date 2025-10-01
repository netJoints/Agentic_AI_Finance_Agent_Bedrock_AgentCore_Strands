# Agentic AI Finance Agent with Bedrock AgentCore using Strands
Software and Security Architecture 
https://claude.ai/public/artifacts/8595c79c-4d8f-44f3-bbc8-68ff4a118887

<iframe src="https://claude.site/public/artifacts/8595c79c-4d8f-44f3-bbc8-68ff4a118887/embed" title="Claude Artifact" width="100%" height="600" frameborder="0" allow="clipboard-write" allowfullscreen></iframe>



<img width="1084" height="1185" alt="image" src="https://github.com/user-attachments/assets/59c609fd-665d-4df7-ab6c-eca8a3afd595" />

<img width="1039" height="574" alt="image" src="https://github.com/user-attachments/assets/98cb1eda-de7d-41c7-af19-dcb5c573c7fc" />

<img width="1084" height="1194" alt="image" src="https://github.com/user-attachments/assets/d278a9d0-e2aa-4329-8d00-710a326e776d" />

Diagram Explnation 

📊 Architecture Layers:
Layer 1: Web Interface (Purple)

Flask backend with REST API
Tailwind CSS frontend
Real-time chat interface

Layer 2: Britive Security Layer (Blue Gradient)

JIT credential checkout via pybritive
Dynamic AWS credentials (AccessKeyId, SecretAccessKey, SessionToken)
Zero standing privileges
Complete audit trail

Layer 3: Agent Factory & Strands Core (Green)

create_enterprise_agent() factory function
Agent configuration with BedrockModel
System prompts and tool assignment

Layer 4: Three Agentic AI Agents (Color-coded)

🔴 Fraud Detection Agent - Red/Orange
🔵 Compliance Monitoring Agent - Blue/Indigo
🟢 Market Risk Analysis Agent - Green/Emerald

Each agent shows:

System prompt
Available tools
Output model (Pydantic)

Layer 5: Strands Processing Pipeline (Yellow)

Query reception → Tool selection → Execution → LLM call → Streaming

Layer 6: AWS Bedrock & Claude Sonnet (Orange/Red)

AWS Bedrock API (us-west-2)
Claude Sonnet 4.5 model
LLM reasoning and function calling

🔐 Security Highlights Section
Shows Britive's zero-trust architecture benefits
The diagram uses arrows to show data flow from top to bottom, with clear visual separation of each layer and color-coding for easy understanding! 🎨
