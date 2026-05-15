import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime"
import { createOpenAI } from "@ai-sdk/openai"
import OpenAI from "openai"
import { NextRequest } from "next/server"

// Route ALL LLM traffic through the Python backend to bypass corporate DNS restrictions.
const BACKEND = process.env.NEXT_PUBLIC_JARVIS_URL || "http://localhost:8000"

// Override getLanguageModel() so @ai-sdk/openai uses Chat Completions (not Responses API)
class BackendAdapter extends OpenAIAdapter {
  getLanguageModel() {
    const provider = createOpenAI({
      baseURL: `${BACKEND}/llm`,
      apiKey: "proxy",
      name: "groq",
    })
    return provider.chat(this.model)
  }
}

const runtime = new CopilotRuntime()
const serviceAdapter = new BackendAdapter({
  openai: new OpenAI({ baseURL: `${BACKEND}/llm`, apiKey: "proxy" }),
  model: "gpt-4o-mini",
})

const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  serviceAdapter,
  endpoint: "/api/copilotkit",
})

// POST — main AG-UI / CopilotKit chat protocol (single-route envelope)
export const POST = async (req: NextRequest) => handleRequest(req)

// GET — inspector endpoints (threads list, runtime info).
// copilotRuntimeNextJSAppRouterEndpoint uses single-route mode which hard-rejects GET
// with 405. We handle these lightweight REST paths directly to avoid importing Hono
// (which breaks Next.js 14 chunk generation).
export const GET = async (req: NextRequest) => {
  const { pathname, searchParams } = new URL(req.url)

  // Runtime info — inspector heartbeat
  if (pathname.endsWith("/info")) {
    return Response.json({ runtimeVersion: "2.0", hasAgents: true })
  }

  // Threads list — return in-memory threads from the CopilotRuntime runner
  if (pathname.endsWith("/threads")) {
    try {
      const runner = (runtime as any).instance?.runner
      let threads: unknown[] = []
      if (typeof runner?.listThreads === "function") {
        const agentId = searchParams.get("agentId") ?? undefined
        threads = runner.listThreads().filter((t: any) => !agentId || t.agentId === agentId)
      }
      return Response.json({ threads, nextCursor: null })
    } catch {
      return Response.json({ threads: [], nextCursor: null })
    }
  }

  return new Response(JSON.stringify({ error: "Not found" }), {
    status: 404,
    headers: { "Content-Type": "application/json" },
  })
}

export const PATCH = async (_req: NextRequest) => new Response(null, { status: 204 })
export const DELETE = async (_req: NextRequest) => new Response(null, { status: 204 })
