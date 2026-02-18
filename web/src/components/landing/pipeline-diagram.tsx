"use client"

import { motion } from "framer-motion"

const STAGES = ["DATA", "FILTER", "FACTOR MODEL", "NORMALIZE", "SCORE", "PORTFOLIO"]

interface PipelineDiagramProps {
  activeStage: number
}

export function PipelineDiagram({ activeStage }: PipelineDiagramProps) {
  return (
    <div className="w-full overflow-x-auto py-4">
      <div className="flex items-center justify-center gap-1 md:gap-2 min-w-[600px] px-4">
        {STAGES.map((stage, i) => (
          <div key={stage} className="flex items-center">
            <motion.div
              data-pipeline-stage
              data-active={i <= activeStage ? "true" : "false"}
              className={`px-3 py-2 rounded-md font-mono text-[10px] md:text-xs tracking-wider transition-all duration-500 ${
                i <= activeStage
                  ? "bg-accent/20 text-accent border border-accent/40 shadow-[0_0_12px_rgba(26,122,90,0.15)]"
                  : "bg-bg-elevated text-text-tertiary border border-border-subtle"
              }`}
            >
              {stage}
            </motion.div>
            {i < STAGES.length - 1 && (
              <div className="flex items-center mx-1">
                <div
                  className={`h-px w-4 md:w-8 transition-colors duration-500 ${
                    i < activeStage ? "bg-accent/60" : "bg-border-subtle"
                  }`}
                />
                <span
                  className={`text-[8px] transition-colors duration-500 ${
                    i < activeStage ? "text-accent/60" : "text-border-subtle"
                  }`}
                >
                  ▸
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
