Product Requirements Document (PRD) for JARVIS Personal AI MVP
1. Product Overview
Product Name: JARVIS
Version: 1.0 (MVP) with Phase 2 Enhancements
Description: JARVIS is a personal reasoning AI designed for a single user, accessible via browser on any device (laptop, phone, AirPods via iPhone). It leverages pre-built open-source tools to minimize custom development, focusing on assembly over building from scratch. The core stack provides authentication, voice I/O, memory, RAG (Retrieval-Augmented Generation) for documents, web search, URL fetching, and agentic capabilities. Phase 1 delivers a functional MVP in ~1 hour using Claude as the primary LLM. Phase 2 extends this to support multiple LLMs (including open-source models) for versatility, cost-efficiency, and redundancy, making it the most adaptable personal AI solution available today by combining top proprietary models with state-of-the-art open-source alternatives.
Target User: Single individual (you, the builder/user) – a professional seeking a direct, opinionated AI companion that merges human and AI thinking, remembers personal details, and operates always-on without device dependency.
Key Goals:

Achieve a production-ready personal AI in 1 hour (Phase 1).
Enhance with multi-LLM support in an additional ~30-45 minutes (Phase 2), allowing seamless switching between providers like Anthropic (Claude), OpenAI (GPT), Grok (xAI), and open-source models (e.g., Llama 3 via Ollama).
Ensure the solution is "best in the world" by prioritizing:
Versatility: Model selection based on task (e.g., fast open-source for simple queries, Claude for deep reasoning).
Accuracy: Mandatory tool use for facts, multi-model ensemble for cross-verification, and personalized "merge thinking" to align AI with user preferences.
Scalability: Low-cost (~$15-50/mo), always-on cloud hosting, with offline/local fallback options.
Privacy/Security: User-owned deployment, no shared data with third parties beyond API calls.


Success Metrics:

MVP live and usable in <1 hour.
Phase 2: Ability to switch between 3+ LLMs via UI, with <5s response time for simple tasks.
User satisfaction: AI remembers 10+ personal facts, merges thinking accurately 80%+ of the time (self-assessed), and handles voice interactions seamlessly.

2. Key Features
Core Features (Phase 1 – From Original Plan):

Browser-Accessible UI: Responsive web app for chat, accessible from any device.
Authentication: Built-in login with admin/user accounts.
Voice Input/Output: Browser-based speech-to-text (STT) and text-to-speech (TTS), compatible with AirPods via iPhone Safari.
Persistent Memory: Cloud-stored facts about the user, synced across devices.
Document RAG: Upload and query PDFs/docs.
Web Search & URL Fetch: Integrated search (DuckDuckGo) and page reading via "#" prefix.
Agentic Tools: Autonomous tool use by the LLM (e.g., search before answering facts).
Merge Thinking: Custom pipeline that asks for user's approach, researches independently, and merges recommendations while learning patterns.
System Prompt Personalization: AI tailored to user's name, background, goals, and behavior (e.g., direct feedback, no blind agreement).
Always-On Hosting: Cloud deployment ensures availability even if local devices are off.

Phase 2 Enhancements (Multi-LLM Support & Additional Features):

Multi-LLM Integration:
Support for multiple providers: Anthropic (Claude Opus/Haiku), OpenAI (GPT-4o), xAI (Grok), and open-source (e.g., Llama 3.1, Mistral via Ollama).
Configuration via environment variables (API keys) and a central config file.
UI Selection: Models appear in Open WebUI dropdown; user selects per chat or sets defaults.
Fallback/Routing: Auto-route tasks (e.g., simple to open-source for cost savings, complex to Claude). Inspired by GitHub repos like berriai/litellm (100+ providers) and open-webui/open-webui (native Ollama support).

Additional Features for Versatility & Accuracy:
Model Ensemble: For critical queries (e.g., decisions), query 2+ models in parallel and synthesize responses (via custom pipeline). Reduces hallucination by cross-verifying.
Vision Capabilities: Upload images for analysis (e.g., "What’s in this photo?") using vision-enabled models like Claude Sonnet or GPT-4V.
Custom Tools/Integrations:
Google Calendar/Drive Sync: Auto-pull events/notes for proactive reminders (via API in pipelines).
Email Integration: Scan Gmail for key info (e.g., "Summarize my inbox") using IMAP/OAuth in a pipeline.
Notification System: Push alerts to phone (via Pushover/Twilio) for background tasks (e.g., daily news digest).
Background Agents: Scheduled jobs (e.g., APScheduler) for monitoring (e.g., stock prices, news on user goals) and updating memory.

Offline/Local Fallback: Run open-source models on Raspberry Pi or local machine for zero-latency/privacy when cloud is unavailable.
Performance Monitoring: Log usage/costs in UI; auto-switch to cheaper models if budget thresholds hit.
Security Enhancements: API key rotation, rate limiting, and audit logs for all interactions.


Non-Functional Requirements:

Performance: <10s average response time; handle 100+ daily interactions.
Cost: Phase 1: $15-40/mo; Phase 2: +$5-20/mo for additional APIs/open-source hosting.
Reliability: 99% uptime via Railway; auto-restarts.
Scalability: Easy to add more models/tools without redeploy.
Tech Stack: Open WebUI (UI/auth/memory/RAG), LiteLLM (multi-LLM proxy), Ollama (open-source LLMs), Railway (hosting), Python pipelines (custom logic). No from-scratch code beyond configs/pipelines.
Compliance: User data stored privately; API calls encrypted.

Out of Scope (Future Phases):

Native mobile app (use browser/PWA).
Multi-user support.
Advanced ML training (e.g., fine-tuning on user data).

Risks & Mitigations:

LLM Costs: Monitor via LiteLLM logs; fallback to free open-source.
Deployment Issues: Use Railway's one-click templates.
Accuracy Gaps: Enforce tool use in prompts; ensemble for verification.
Time Overrun: Phase 1 is strictly 1-hour; Phase 2 optional extension.

Timeline:

Phase 1: 60 minutes.
Phase 2: Additional 30-45 minutes post-Phase 1.

3. User Stories

As the user, I want to log in securely from any device so JARVIS is personal and protected.
As the user, I want to speak to JARVIS via AirPods and hear responses so it's hands-free.
As the user, I want JARVIS to remember my goals/preferences across sessions for personalized advice.
As the user, I want to switch between LLMs (e.g., Claude for reasoning, Llama for quick tasks) via UI to optimize cost/accuracy.
As the user, I want JARVIS to merge my thinking with its own for decisions, learning my patterns over time.
As the user, I want proactive features like calendar reminders or news alerts to make it more versatile.

This PRD positions JARVIS as the "best in the world" personal AI by leveraging battle-tested open-source tools (e.g., Open WebUI's 87k+ stars on GitHub) with multi-LLM routing, reducing dependency on any single provider and enabling hybrid proprietary/open-source workflows unmatched in simplicity and power.