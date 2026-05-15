"use client"
import {
  CalendarDays,
  Car,
  Check,
  Cloud,
  Lightbulb,
  Target,
  Trash2,
  UtensilsCrossed,
  X,
} from "lucide-react"
import { useState } from "react"

interface Nudge {
  id: string
  type: string
  message: string
  card_data: Record<string, unknown>
  priority: string
}

interface Goal {
  id: string
  name: string
  status: string
  urgency: string
  last_touched: string
}

interface NudgePanelProps {
  nudges: Nudge[]
  goals: Goal[]
  onClose: () => void
  onGoalUpdate: (goals: Goal[]) => void
  onDismissNudge: (id: string) => void
}

function NudgeTypeIcon(props: { type: string }) {
  const key = props.type.toLowerCase()
  if (key === "weather") return <Cloud className="h-4 w-4 text-sky-200" />
  if (key === "food") return <UtensilsCrossed className="h-4 w-4 text-amber-200" />
  if (key === "traffic") return <Car className="h-4 w-4 text-emerald-200" />
  if (key === "goal") return <Target className="h-4 w-4 text-violet-200" />
  if (key === "calendar") return <CalendarDays className="h-4 w-4 text-indigo-200" />
  return <Lightbulb className="h-4 w-4 text-yellow-200" />
}

function priorityStyle(priority: string) {
  if (priority === "high") return "border-l-red-400 bg-red-950/20"
  if (priority === "medium") return "border-l-amber-400 bg-amber-950/20"
  return "border-l-gray-400 bg-gray-950/20"
}

export function NudgePanel(props: NudgePanelProps) {
  const [editingGoals, setEditingGoals] = useState(props.goals)

  const handleGoalToggle = (id: string) => {
    const updated = editingGoals.map((g) =>
      g.id === id ? { ...g, status: g.status === "active" ? "done" : "active" } : g,
    )
    setEditingGoals(updated)
    props.onGoalUpdate(updated)
  }

  const handleGoalDelete = (id: string) => {
    const updated = editingGoals.filter((g) => g.id !== id)
    setEditingGoals(updated)
    props.onGoalUpdate(updated)
  }

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-[360px] border-l border-white/10 bg-[#0b1220] flex flex-col">
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/10">
        <h2 className="text-sm font-semibold text-white">Nudges</h2>
        <button onClick={props.onClose} className="p-2 hover:bg-white/5 rounded-md transition-colors">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {props.nudges.length > 0 && (
          <div className="p-3 border-b border-white/5">
            <p className="text-[11px] font-semibold text-white/40 mb-2 tracking-wide">PENDING</p>
            <div className="space-y-2">
              {props.nudges.map((nudge) => (
                <div
                  key={nudge.id}
                  className={`border-l-2 rounded-xl p-3 flex items-start justify-between ${priorityStyle(nudge.priority)}`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-white/5 border border-white/10">
                        <NudgeTypeIcon type={nudge.type} />
                      </span>
                      <p className="text-sm font-medium text-white leading-snug">{nudge.message}</p>
                    </div>
                    <p className="text-xs text-white/40 capitalize">{nudge.type}</p>
                  </div>
                  <button
                    onClick={() => props.onDismissNudge(nudge.id)}
                    className="p-2 hover:bg-white/5 rounded-md transition-colors ml-2 flex-shrink-0"
                    aria-label="Dismiss nudge"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {editingGoals.length > 0 && (
          <div className="p-3">
            <p className="text-[11px] font-semibold text-white/40 mb-2 tracking-wide">GOALS</p>
            <div className="space-y-1">
              {editingGoals.map((goal) => (
                <div
                  key={goal.id}
                  className="flex items-center gap-2 p-2 hover:bg-white/5 rounded group transition-colors"
                >
                  <button
                    onClick={() => handleGoalToggle(goal.id)}
                    className={`flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                      goal.status === "done"
                        ? "bg-green-500/30 border-green-400"
                        : "border-white/20 hover:border-white/40"
                    }`}
                    aria-label={goal.status === "done" ? "Mark active" : "Mark done"}
                  >
                    {goal.status === "done" && <Check className="w-3 h-3 text-green-300" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm truncate transition-all ${
                        goal.status === "done" ? "text-white/40 line-through" : "text-white"
                      }`}
                    >
                      {goal.name}
                    </p>
                  </div>
                  <button
                    onClick={() => handleGoalDelete(goal.id)}
                    className="p-2 hover:bg-red-900/20 rounded-md opacity-0 group-hover:opacity-100 transition-all flex-shrink-0"
                    aria-label="Delete goal"
                  >
                    <Trash2 className="w-3 h-3 text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {props.nudges.length === 0 && editingGoals.length === 0 && (
          <div className="p-4 text-center text-white/40">
            <p className="text-sm">No nudges yet.</p>
            <p className="text-xs mt-1">JARVIS will surface them when needed.</p>
          </div>
        )}
      </div>
    </div>
  )
}
