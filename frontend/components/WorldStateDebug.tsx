interface WorldStateDebugProps {
  worldState: Record<string, any>
}

export function WorldStateDebug({ worldState }: WorldStateDebugProps) {
  const renderJSON = (obj: any, depth: number = 0): JSX.Element => {
    if (obj === null || obj === undefined) {
      return <span className="text-gray-400">null</span>
    }

    if (typeof obj === "boolean") {
      return <span className="text-blue-300">{obj.toString()}</span>
    }

    if (typeof obj === "number") {
      return <span className="text-green-300">{obj}</span>
    }

    if (typeof obj === "string") {
      return <span className="text-amber-300">"{obj}"</span>
    }

    if (Array.isArray(obj)) {
      if (obj.length === 0) return <span className="text-gray-400">[]</span>
      return (
        <div className="ml-4 border-l border-white/10">
          <span className="text-gray-400">[</span>
          {obj.map((item, idx) => (
            <div key={idx} className="text-white/70">
              {renderJSON(item, depth + 1)}
              {idx < obj.length - 1 && <span className="text-gray-400">,</span>}
            </div>
          ))}
          <span className="text-gray-400">]</span>
        </div>
      )
    }

    if (typeof obj === "object") {
      const keys = Object.keys(obj)
      if (keys.length === 0) return <span className="text-gray-400">{"{}"}</span>
      return (
        <div className="ml-4 border-l border-white/10">
          <span className="text-gray-400">{"{"}</span>
          {keys.map((key, idx) => (
            <div key={key} className="text-white/70">
              <span className="text-purple-300">"{key}"</span>
              <span className="text-gray-400">: </span>
              {renderJSON(obj[key], depth + 1)}
              {idx < keys.length - 1 && <span className="text-gray-400">,</span>}
            </div>
          ))}
          <span className="text-gray-400">{"}"}</span>
        </div>
      )
    }

    return <span className="text-white">{String(obj)}</span>
  }

  return (
    <div className="fixed right-80 top-0 bottom-0 w-96 border-l border-white/10 bg-[#030810] backdrop-blur overflow-y-auto">
      <div className="sticky top-0 px-4 py-3 border-b border-white/10 bg-black/40">
        <h3 className="font-semibold text-sm">WORLD STATE</h3>
      </div>

      <div className="p-4 font-mono text-xs">
        {Object.keys(worldState).length > 0 ? (
          <pre className="whitespace-pre-wrap break-words text-white/80">
            {renderJSON(worldState)}
          </pre>
        ) : (
          <p className="text-white/40">No world state yet...</p>
        )}
      </div>
    </div>
  )
}
