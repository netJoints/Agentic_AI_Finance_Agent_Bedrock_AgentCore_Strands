"""
Enterprise Financial AI Platform - Web Interface
Protected by Britive Dynamic Privileged Access Management
This code is not using the hosted AWS Bedrock AgentCore yet
This code is working flawlessly using local laptop running the agents
This version has no MCP server yet.
"""

from flask import Flask, render_template_string, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import json
import os
from datetime import datetime
import subprocess
import boto3
import logging
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator
from strands.agent.conversation_manager import SummarizingConversationManager
from pydantic import BaseModel, Field
from typing import List
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [BRITIVE-PROTECTED] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Create output directory
os.makedirs("static", exist_ok=True)


class BritiveCredentialManager:
    """Britive Dynamic Credential Management for AI Agents"""
    
    def __init__(self, profile: str, tenant: str = "demo", agent_identity: str = "ai-agent"):
        self.profile = profile
        self.tenant = tenant
        self.agent_identity = agent_identity
        self.session_id = None
        self.credentials = None
        
    def checkout(self) -> dict:
        logger.info(f"🔐 Britive: Requesting JIT credentials for {self.agent_identity}")
        
        try:
            result = subprocess.run(
                ["pybritive", "checkout", self.profile, "-t", self.tenant],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"Credential checkout failed: {result.stderr}")
            
            self.credentials = json.loads(result.stdout)
            self.session_id = self.credentials.get("SessionToken", "")[:20] + "..."
            logger.info(f"✅ Credentials provisioned successfully")
            
            return self.credentials
            
        except Exception as e:
            logger.error(f"❌ Credential provisioning error: {str(e)}")
            raise
    
    def checkin(self):
        if self.credentials:
            logger.info("🔒 Britive: Credentials returned - Zero standing privileges maintained")
            self.credentials = None


# Pydantic Models
class TransactionData(BaseModel):
    transaction_id: str
    amount: float
    merchant: str
    category: str
    risk_score: float

class FraudAnalysisReport(BaseModel):
    analysis_timestamp: str
    total_transactions_analyzed: int
    high_risk_transactions: List[TransactionData]
    fraud_probability: float
    recommended_actions: List[str]
    compliance_status: str
    risk_level: str

class ComplianceReport(BaseModel):
    regulation_framework: str
    compliance_score: int
    violations_detected: List[str]
    remediation_steps: List[str]
    audit_trail_complete: bool

class MarketRiskAnalysis(BaseModel):
    portfolio_value: float
    value_at_risk: float
    risk_categories: List[dict]
    stress_test_results: dict
    recommendations: List[str]


# System Prompts
FRAUD_DETECTION_PROMPT = """You are an enterprise-grade fraud detection AI agent.
Analyze transactions for fraud, calculate risk scores, and provide actionable recommendations."""

COMPLIANCE_MONITORING_PROMPT = """You are an enterprise compliance monitoring AI agent.
Perform SOX, PCI-DSS, GLBA, and AML compliance analysis."""

MARKET_RISK_PROMPT = """You are an enterprise market risk analysis AI agent.
Calculate VaR, perform stress tests, and provide portfolio risk assessments."""


# Tools
@tool
def analyze_transaction_pattern(transactions: List[dict], threshold: float = 0.7) -> str:
    high_risk = [t for t in transactions if t.get('risk_score', 0) > threshold]
    result = f"\n🔍 FRAUD DETECTION ANALYSIS\n"
    result += f"Total Transactions: {len(transactions)}\n"
    result += f"High-Risk Transactions: {len(high_risk)}\n"
    for t in high_risk[:5]:
        result += f"• {t.get('transaction_id', 'N/A')} - ${t.get('amount', 0):,.2f}\n"
    return result

@tool
def calculate_value_at_risk(portfolio_value: float, volatility: float = 0.15) -> str:
    var = portfolio_value * volatility * 1.645
    result = f"\n📊 VALUE AT RISK ANALYSIS\n"
    result += f"Portfolio Value: ${portfolio_value:,.2f}\n"
    result += f"Daily VaR (95%): ${var:,.2f}\n"
    return result

@tool
def check_compliance_status(transaction_count: int, violations: int = 0) -> str:
    score = max(0, 100 - (violations / max(transaction_count, 1) * 100))
    result = f"\n✅ COMPLIANCE REPORT\n"
    result += f"Transactions Reviewed: {transaction_count:,}\n"
    result += f"Violations: {violations}\n"
    result += f"Compliance Score: {score:.1f}%\n"
    return result


def create_enterprise_agent(agent_type: str):
    agent_configs = {
        "fraud_detection": {
            "profile": "AWS SE Demo/Britive Agentic AI Solution/Admin",
            "tenant": "demo",
            "prompt": FRAUD_DETECTION_PROMPT,
            "identity": "Fraud Detection AI"
        },
        "compliance": {
            "profile": "AWS SE Demo/Britive Agentic AI Solution/Admin",
            "tenant": "demo",
            "prompt": COMPLIANCE_MONITORING_PROMPT,
            "identity": "Compliance Monitoring AI"
        },
        "risk_analysis": {
            "profile": "AWS SE Demo/Britive Agentic AI Solution/Admin",
            "tenant": "demo",
            "prompt": MARKET_RISK_PROMPT,
            "identity": "Risk Analysis AI"
        }
    }
    
    config = agent_configs.get(agent_type, agent_configs["fraud_detection"])
    
    cred_manager = BritiveCredentialManager(
        profile=config["profile"],
        tenant=config["tenant"],
        agent_identity=config["identity"]
    )
    
    creds = cred_manager.checkout()
    
    session = boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name="us-west-2",
    )
    
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        boto_session=session,
        temperature=0.0,
    )
    
    conversation_manager = SummarizingConversationManager(
        summary_ratio=0.5,
        preserve_recent_messages=5,
    )
    
    agent = Agent(
        model=bedrock_model,
        system_prompt=config["prompt"],
        tools=[analyze_transaction_pattern, calculate_value_at_risk, check_compliance_status, calculator],
        conversation_manager=conversation_manager,
    )
    
    return agent, cred_manager


# Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        agent_type = data.get('agent_type', 'fraud_detection')
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        def run_analysis():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(process_query(agent_type, query))
            loop.close()
            return result
        
        result = run_analysis()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

async def process_query(agent_type: str, query: str):
    agent, cred_manager = None, None
    
    try:
        agent, cred_manager = create_enterprise_agent(agent_type)
        
        response_text = ""
        async for event in agent.stream_async(query):
            if "data" in event:
                response_text += event["data"]
        
        structured_data = None
        if agent_type == "fraud_detection":
            try:
                structured_data = await agent.structured_output_async(
                    output_model=FraudAnalysisReport,
                    prompt=f"Generate fraud analysis for: {query}"
                )
                structured_data = structured_data.dict()
            except:
                pass
        elif agent_type == "compliance":
            try:
                structured_data = await agent.structured_output_async(
                    output_model=ComplianceReport,
                    prompt=f"Generate compliance report for: {query}"
                )
                structured_data = structured_data.dict()
            except:
                pass
        elif agent_type == "risk_analysis":
            try:
                structured_data = await agent.structured_output_async(
                    output_model=MarketRiskAnalysis,
                    prompt=f"Generate risk analysis for: {query}"
                )
                structured_data = structured_data.dict()
            except:
                pass
        
        return {
            'success': True,
            'response': response_text,
            'structured_data': structured_data,
            'agent_type': agent_type,
            'timestamp': datetime.now().isoformat()
        }
        
    finally:
        if cred_manager:
            cred_manager.checkin()

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Financial AI Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .chat-message { animation: slideIn 0.3s ease-out; }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="bg-gray-50">
    <header class="gradient-bg text-white shadow-lg">
        <div class="container mx-auto px-6 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-4">
                    <i class="fas fa-shield-alt text-3xl"></i>
                    <div>
                        <h1 class="text-2xl font-bold">Enterprise Financial AI Platform</h1>
                        <p class="text-sm text-purple-200">Protected by Britive Dynamic PAM</p>
                    </div>
                </div>
                <div class="bg-white bg-opacity-20 px-4 py-2 rounded-lg">
                    <span class="text-sm font-semibold">
                        <i class="fas fa-lock mr-2"></i>Zero Standing Privileges
                    </span>
                </div>
            </div>
        </div>
    </header>

    <div class="container mx-auto px-6 py-8">
        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-bold text-gray-800 mb-4">
                <i class="fas fa-robot mr-3 text-purple-600"></i>Select AI Agent
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button onclick="selectAgent('fraud_detection')" id="btn-fraud_detection"
                        class="agent-btn p-6 border-2 rounded-lg hover:shadow-lg bg-gradient-to-br from-red-50 to-orange-50 border-red-300">
                    <i class="fas fa-exclamation-triangle text-3xl text-red-600 mb-3"></i>
                    <h3 class="font-bold text-gray-800 mb-2">Fraud Detection</h3>
                    <p class="text-sm text-gray-600">Real-time transaction monitoring</p>
                </button>
                
                <button onclick="selectAgent('compliance')" id="btn-compliance"
                        class="agent-btn p-6 border-2 rounded-lg hover:shadow-lg bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-300">
                    <i class="fas fa-clipboard-check text-3xl text-blue-600 mb-3"></i>
                    <h3 class="font-bold text-gray-800 mb-2">Compliance Monitoring</h3>
                    <p class="text-sm text-gray-600">SOX, PCI-DSS, GLBA, AML</p>
                </button>
                
                <button onclick="selectAgent('risk_analysis')" id="btn-risk_analysis"
                        class="agent-btn p-6 border-2 rounded-lg hover:shadow-lg bg-gradient-to-br from-green-50 to-emerald-50 border-green-300">
                    <i class="fas fa-chart-line text-3xl text-green-600 mb-3"></i>
                    <h3 class="font-bold text-gray-800 mb-2">Risk Analysis</h3>
                    <p class="text-sm text-gray-600">Portfolio VaR & stress testing</p>
                </button>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 class="text-xl font-bold text-gray-800 mb-4">
                <i class="fas fa-lightbulb mr-3 text-yellow-500"></i>Example Queries
            </h2>
            <div id="examples" class="grid grid-cols-1 md:grid-cols-2 gap-3"></div>
        </div>

        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <div class="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-4">
                <h2 class="text-xl font-bold flex items-center">
                    <i class="fas fa-comments mr-3"></i>AI Agent Console
                    <span id="agent-status" class="ml-auto text-sm bg-white bg-opacity-20 px-3 py-1 rounded-full">Ready</span>
                </h2>
            </div>
            
            <div class="bg-blue-50 border-l-4 border-blue-500 p-4">
                <div class="flex items-start">
                    <i class="fas fa-info-circle text-blue-500 mt-1 mr-3"></i>
                    <div class="text-sm">
                        <p class="font-semibold text-blue-800 mb-1">Britive Security Context</p>
                        <ul class="text-blue-700 space-y-1">
                            <li>✓ Just-in-time credential provisioning</li>
                            <li>✓ Automatic credential rotation</li>
                            <li>✓ Complete audit trail</li>
                            <li>✓ Zero standing privileges</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <div id="messages" class="p-6 space-y-4 h-96 overflow-y-auto bg-gray-50">
                <div class="text-center text-gray-500 py-8">
                    <i class="fas fa-robot text-5xl mb-4 text-gray-300"></i>
                    <p>Select an AI agent and start your analysis</p>
                </div>
            </div>
            
            <div class="border-t bg-white p-4">
                <div class="flex space-x-3">
                    <input type="text" id="query-input" placeholder="Enter your query..."
                        class="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600"
                        onkeypress="if(event.key==='Enter') submitQuery()">
                    <button onclick="submitQuery()" id="submit-btn"
                        class="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-indigo-700">
                        <i class="fas fa-paper-plane mr-2"></i>Analyze
                    </button>
                </div>
            </div>
        </div>

        <div id="results-panel" class="mt-6 hidden">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-bold text-gray-800 mb-4">
                    <i class="fas fa-file-alt mr-3 text-green-600"></i>Structured Report
                </h2>
                <div id="structured-output" class="bg-gray-50 p-4 rounded-lg"></div>
            </div>
        </div>
    </div>

    <script>
        let selectedAgent = 'fraud_detection';
        let isProcessing = false;

        const examples = {
            fraud_detection: [
                "Analyze: TXN-001: $15,234 to OVERSEAS-ELECTRONICS, TXN-002: $45,000 to CRYPTO-EXCHANGE",
                "Review suspicious activity: Multiple $9,900 transactions to avoid reporting thresholds"
            ],
            compliance: [
                "Perform Q3 2025 compliance audit for 1.2M transactions with 5 PCI-DSS violations",
                "Verify SOX controls: 127 tests, 3 missing audit trails"
            ],
            risk_analysis: [
                "Calculate VaR for $2.5B portfolio: 60% equities, 30% bonds, 18% volatility",
                "Stress test: -30% equity markets, +200bps rates"
            ]
        };

        function selectAgent(type) {
            selectedAgent = type;
            document.querySelectorAll('.agent-btn').forEach(b => b.classList.remove('ring-4', 'ring-purple-500'));
            document.getElementById('btn-' + type).classList.add('ring-4', 'ring-purple-500');
            updateExamples(type);
            const names = {fraud_detection: 'Fraud Detection AI', compliance: 'Compliance AI', risk_analysis: 'Risk Analysis AI'};
            document.getElementById('agent-status').textContent = names[type];
        }

        function updateExamples(type) {
            document.getElementById('examples').innerHTML = examples[type].map(ex => 
                '<button onclick="useExample(`' + ex + '`)" class="text-left p-3 bg-gray-50 hover:bg-purple-50 rounded-lg border border-gray-200">' +
                '<i class="fas fa-arrow-right text-purple-600 mr-2"></i>' +
                '<span class="text-sm text-gray-700">' + ex + '</span></button>'
            ).join('');
        }

        function useExample(text) {
            document.getElementById('query-input').value = text;
        }

        async function submitQuery() {
            if (isProcessing) return;
            
            const query = document.getElementById('query-input').value.trim();
            if (!query) { alert('Please enter a query'); return; }

            isProcessing = true;
            const btn = document.getElementById('submit-btn');
            const msgs = document.getElementById('messages');
            
            if (msgs.querySelector('.text-center')) msgs.innerHTML = '';
            
            addMessage('user', query);
            btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
            btn.disabled = true;
            addMessage('system', '🔐 Britive: Requesting JIT credentials...');
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({agent_type: selectedAgent, query: query})
                });

                const data = await response.json();
                
                if (data.success) {
                    addMessage('system', '✅ Britive: Credentials provisioned');
                    addMessage('agent', data.response);
                    if (data.structured_data) displayStructuredData(data.structured_data);
                    addMessage('system', '🔒 Britive: Credentials returned');
                } else {
                    addMessage('error', 'Error: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                addMessage('error', 'Connection error: ' + error.message);
            } finally {
                isProcessing = false;
                btn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Analyze';
                btn.disabled = false;
                document.getElementById('query-input').value = '';
            }
        }

        function addMessage(type, content) {
            const msgs = document.getElementById('messages');
            const div = document.createElement('div');
            const styles = {
                user: 'bg-purple-100 border-l-4 border-purple-500 ml-12',
                agent: 'bg-blue-50 border-l-4 border-blue-500 mr-12',
                system: 'bg-green-50 border-l-4 border-green-500',
                error: 'bg-red-50 border-l-4 border-red-500'
            };
            const icons = {user: 'fa-user', agent: 'fa-robot', system: 'fa-shield-alt', error: 'fa-exclamation-triangle'};
            
            div.className = 'chat-message p-4 rounded-lg ' + styles[type];
            div.innerHTML = '<div class="flex items-start"><i class="fas ' + icons[type] + ' mt-1 mr-3 text-gray-600"></i>' +
                           '<div class="flex-1"><pre class="whitespace-pre-wrap font-sans text-sm text-gray-800">' + 
                           content + '</pre></div></div>';
            
            msgs.appendChild(div);
            msgs.scrollTop = msgs.scrollHeight;
        }

        function displayStructuredData(data) {
            const panel = document.getElementById('results-panel');
            const output = document.getElementById('structured-output');
            
            let html = '';
            
            if (data.analysis_timestamp) {
                // Fraud Analysis Report
                const riskColor = data.fraud_probability > 0.7 ? 'text-red-600' : data.fraud_probability > 0.4 ? 'text-yellow-600' : 'text-green-600';
                const riskBg = data.fraud_probability > 0.7 ? 'bg-red-50 border-red-200' : data.fraud_probability > 0.4 ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200';
                
                html = `
                    <div class="space-y-6">
                        <!-- Header Stats -->
                        <div class="grid grid-cols-4 gap-4">
                            <div class="bg-blue-50 p-4 rounded-lg border border-blue-200">
                                <div class="text-xs text-blue-600 font-semibold uppercase mb-1">Timestamp</div>
                                <div class="text-sm font-bold text-gray-800">${data.analysis_timestamp}</div>
                            </div>
                            <div class="bg-purple-50 p-4 rounded-lg border border-purple-200">
                                <div class="text-xs text-purple-600 font-semibold uppercase mb-1">Transactions</div>
                                <div class="text-2xl font-bold text-gray-800">${data.total_transactions_analyzed}</div>
                            </div>
                            <div class="${riskBg} p-4 rounded-lg border">
                                <div class="text-xs font-semibold uppercase mb-1" style="color: inherit;">Fraud Probability</div>
                                <div class="text-2xl font-bold ${riskColor}">${(data.fraud_probability * 100).toFixed(1)}%</div>
                            </div>
                            <div class="bg-gray-100 p-4 rounded-lg border border-gray-300">
                                <div class="text-xs text-gray-600 font-semibold uppercase mb-1">Risk Level</div>
                                <div class="text-lg font-bold ${riskColor}">${data.risk_level}</div>
                            </div>
                        </div>
                        
                        <!-- Compliance Status -->
                        <div class="bg-gradient-to-r from-orange-50 to-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
                            <div class="flex items-center">
                                <i class="fas fa-exclamation-circle text-red-600 text-xl mr-3"></i>
                                <div>
                                    <div class="text-xs text-red-700 font-semibold uppercase mb-1">Compliance Status</div>
                                    <div class="font-bold text-gray-800">${data.compliance_status}</div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- High-Risk Transactions -->
                        <div>
                            <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
                                <i class="fas fa-flag text-red-600 mr-2"></i>
                                High-Risk Transactions (${data.high_risk_transactions.length})
                            </h3>
                            <div class="space-y-3">
                                ${data.high_risk_transactions.map((t, idx) => `
                                    <div class="bg-white border-2 border-red-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                                        <div class="flex items-start justify-between">
                                            <div class="flex-1">
                                                <div class="flex items-center mb-2">
                                                    <span class="bg-red-100 text-red-800 text-xs font-bold px-2 py-1 rounded mr-2">
                                                        #${idx + 1}
                                                    </span>
                                                    <code class="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">${t.transaction_id}</code>
                                                </div>
                                                <div class="grid grid-cols-2 gap-3 text-sm">
                                                    <div>
                                                        <span class="text-gray-600">Amount:</span>
                                                        <span class="font-bold text-gray-900 ml-2">${t.amount.toLocaleString()}</span>
                                                    </div>
                                                    <div>
                                                        <span class="text-gray-600">Category:</span>
                                                        <span class="font-semibold text-gray-800 ml-2">${t.category}</span>
                                                    </div>
                                                    <div class="col-span-2">
                                                        <span class="text-gray-600">Merchant:</span>
                                                        <span class="font-semibold text-gray-800 ml-2">${t.merchant}</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="ml-4 text-right">
                                                <div class="text-xs text-gray-600 mb-1">Risk Score</div>
                                                <div class="text-3xl font-bold text-red-600">${(t.risk_score * 100).toFixed(0)}%</div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        
                        <!-- Recommended Actions -->
                        <div>
                            <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
                                <i class="fas fa-tasks text-blue-600 mr-2"></i>
                                Recommended Actions
                            </h3>
                            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <ol class="space-y-3">
                                    ${data.recommended_actions.map((action, idx) => `
                                        <li class="flex items-start">
                                            <span class="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold mr-3 mt-0.5">
                                                ${idx + 1}
                                            </span>
                                            <span class="text-sm text-gray-800 flex-1">${action}</span>
                                        </li>
                                    `).join('')}
                                </ol>
                            </div>
                        </div>
                    </div>
                `;
            } else if (data.regulation_framework) {
                // Compliance Report
                const scoreColor = data.compliance_score >= 95 ? 'text-green-600' : data.compliance_score >= 80 ? 'text-yellow-600' : 'text-red-600';
                const scoreBg = data.compliance_score >= 95 ? 'bg-green-50 border-green-200' : data.compliance_score >= 80 ? 'bg-yellow-50 border-yellow-200' : 'bg-red-50 border-red-200';
                
                html = `
                    <div class="space-y-6">
                        <!-- Header Stats -->
                        <div class="grid grid-cols-3 gap-4">
                            <div class="bg-blue-50 p-4 rounded-lg border border-blue-200">
                                <div class="text-xs text-blue-600 font-semibold uppercase mb-1">Framework</div>
                                <div class="text-sm font-bold text-gray-800">${data.regulation_framework}</div>
                            </div>
                            <div class="${scoreBg} p-4 rounded-lg border">
                                <div class="text-xs font-semibold uppercase mb-1">Compliance Score</div>
                                <div class="text-3xl font-bold ${scoreColor}">${data.compliance_score}%</div>
                            </div>
                            <div class="bg-gray-100 p-4 rounded-lg border border-gray-300">
                                <div class="text-xs text-gray-600 font-semibold uppercase mb-1">Audit Trail</div>
                                <div class="text-lg font-bold ${data.audit_trail_complete ? 'text-green-600' : 'text-red-600'}">
                                    ${data.audit_trail_complete ? '✓ Complete' : '✗ Incomplete'}
                                </div>
                            </div>
                        </div>
                        
                        ${data.violations_detected.length > 0 ? `
                        <!-- Violations -->
                        <div>
                            <h3 class="text-lg font-bold text-red-600 mb-3 flex items-center">
                                <i class="fas fa-exclamation-triangle mr-2"></i>
                                Violations Detected (${data.violations_detected.length})
                            </h3>
                            <div class="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg">
                                <ul class="space-y-2">
                                    ${data.violations_detected.map(v => `
                                        <li class="flex items-start">
                                            <i class="fas fa-times-circle text-red-600 mr-2 mt-1"></i>
                                            <span class="text-sm text-gray-800">${v}</span>
                                        </li>
                                    `).join('')}
                                </ul>
                            </div>
                        </div>
                        ` : '<div class="bg-green-50 border-l-4 border-green-500 p-4 rounded-r-lg"><p class="text-green-800 font-semibold"><i class="fas fa-check-circle mr-2"></i>No violations detected</p></div>'}
                        
                        <!-- Remediation Steps -->
                        <div>
                            <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
                                <i class="fas fa-wrench text-blue-600 mr-2"></i>
                                Remediation Steps
                            </h3>
                            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <ol class="space-y-3">
                                    ${data.remediation_steps.map((step, idx) => `
                                        <li class="flex items-start">
                                            <span class="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold mr-3 mt-0.5">
                                                ${idx + 1}
                                            </span>
                                            <span class="text-sm text-gray-800 flex-1">${step}</span>
                                        </li>
                                    `).join('')}
                                </ol>
                            </div>
                        </div>
                    </div>
                `;
            } else if (data.portfolio_value) {
                // Risk Analysis
                const varPercent = ((data.value_at_risk / data.portfolio_value) * 100).toFixed(2);
                const varColor = varPercent > 10 ? 'text-red-600' : varPercent > 5 ? 'text-yellow-600' : 'text-green-600';
                
                html = `
                    <div class="space-y-6">
                        <!-- Header Stats -->
                        <div class="grid grid-cols-3 gap-4">
                            <div class="bg-blue-50 p-4 rounded-lg border border-blue-200">
                                <div class="text-xs text-blue-600 font-semibold uppercase mb-1">Portfolio Value</div>
                                <div class="text-2xl font-bold text-gray-800">${data.portfolio_value.toLocaleString()}</div>
                            </div>
                            <div class="bg-red-50 p-4 rounded-lg border border-red-200">
                                <div class="text-xs text-red-600 font-semibold uppercase mb-1">Value at Risk (95%)</div>
                                <div class="text-2xl font-bold text-red-600">${data.value_at_risk.toLocaleString()}</div>
                            </div>
                            <div class="bg-orange-50 p-4 rounded-lg border border-orange-200">
                                <div class="text-xs text-orange-600 font-semibold uppercase mb-1">VaR Percentage</div>
                                <div class="text-2xl font-bold ${varColor}">${varPercent}%</div>
                            </div>
                        </div>
                        
                        <!-- Risk Categories -->
                        <div>
                            <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
                                <i class="fas fa-chart-pie text-purple-600 mr-2"></i>
                                Risk Categories
                            </h3>
                            <div class="grid grid-cols-2 gap-3">
                                ${data.risk_categories.map(cat => {
                                    const color = cat.value > 70 ? 'red' : cat.value > 50 ? 'yellow' : 'green';
                                    return `
                                        <div class="bg-white border-2 border-gray-200 rounded-lg p-4">
                                            <div class="flex justify-between items-center mb-2">
                                                <span class="font-semibold text-gray-800">${cat.type || 'Category'}</span>
                                                <span class="text-2xl font-bold text-${color}-600">${cat.value}%</span>
                                            </div>
                                            <div class="w-full bg-gray-200 rounded-full h-2">
                                                <div class="bg-${color}-600 h-2 rounded-full" style="width: ${cat.value}%"></div>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                        
                        <!-- Stress Test Results -->
                        <div>
                            <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
                                <i class="fas fa-vial text-yellow-600 mr-2"></i>
                                Stress Test Results
                            </h3>
                            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                <div class="grid grid-cols-1 gap-2">
                                    ${Object.entries(data.stress_test_results).map(([scenario, impact]) => `
                                        <div class="flex justify-between items-center py-2 border-b border-yellow-200 last:border-b-0">
                                            <span class="text-sm font-semibold text-gray-700">${scenario}</span>
                                            <span class="text-sm font-bold text-gray-900">${impact}</span>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                        
                        <!-- Recommendations -->
                        <div>
                            <h3 class="text-lg font-bold text-gray-800 mb-3 flex items-center">
                                <i class="fas fa-lightbulb text-green-600 mr-2"></i>
                                Risk Mitigation Recommendations
                            </h3>
                            <div class="bg-green-50 border border-green-200 rounded-lg p-4">
                                <ul class="space-y-2">
                                    ${data.recommendations.map(rec => `
                                        <li class="flex items-start">
                                            <i class="fas fa-check-circle text-green-600 mr-2 mt-1"></i>
                                            <span class="text-sm text-gray-800">${rec}</span>
                                        </li>
                                    `).join('')}
                                </ul>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // Fallback for unknown structure
                html = '<pre class="text-sm text-gray-700 bg-gray-100 p-4 rounded overflow-auto">' + JSON.stringify(data, null, 2) + '</pre>';
            }
            
            output.innerHTML = html;
            panel.classList.remove('hidden');
        }

        selectAgent('fraud_detection');
        updateExamples('fraud_detection');
    </script>

    <footer class="bg-gray-800 text-white mt-12 py-6">
        <div class="container mx-auto px-6 text-center">
            <p class="text-sm"><i class="fas fa-shield-alt mr-2"></i>Secured by Britive Dynamic PAM</p>
            <p class="text-xs text-gray-400 mt-2">Enterprise Financial AI Platform</p>
        </div>
    </footer>
</body>
</html>"""


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║  ENTERPRISE FINANCIAL AI PLATFORM - WEB INTERFACE                   ║
║  Protected by Britive Dynamic Privileged Access Management          ║
╚══════════════════════════════════════════════════════════════════════╝

🌐 Access: http://127.0.0.1:5000/
🔒 Security: Britive JIT credentials
📊 Features: 3 AI agents with real-time analysis
""")
    
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
