"use client"

import { MicroMetadata } from "./micro-metadata"
import { FACTOR_MODEL_VERSION } from "./candidate-data"

const STAGES = [
  "DATA",
  "FILTER",
  "FACTOR MODEL",
  "NORMALIZE",
  "SCORE",
  "PORTFOLIO",
]

interface PipelineChipsProps {
  activeStage: number
}

export function PipelineChips({ activeStage }: PipelineChipsProps) {
  return (
    <section id="pipeline" className="py-8">
      <div className="flex items-center justify-center flex-wrap gap-2 md:gap-3 px-6">
        {STAGES.map((stage, i) => {
          const isActive = i <= activeStage
          return (
            <div key={stage} className="flex items-center gap-2 md:gap-3">
              {i > 0 && (
                <span className="text-text-tertiary text-xs" aria-hidden="true">
                  &rarr;
                </span>
              )}
              <span
                data-testid="pipeline-stage"
                data-active={isActive ? "true" : "false"}
                className={`font-mono text-xs md:text-xs tracking-[0.15em] ${
                  isActive
                    ? "text-accent shadow-[0_0_8px_rgba(26,122,90,0.3)]"
                    : "text-text-tertiary"
                }`}
                style={{ transition: "all 250ms cubic-bezier(0.4, 0.0, 0.2, 1)" }}
              >
                {stage}
                {isActive && (
                  <span className="block h-[2px] bg-accent mt-0.5 rounded-full" />
                )}
              </span>
            </div>
          )
        })}
      </div>
      <div className="flex justify-center mt-3">
        <MicroMetadata text={`Factor Model ${FACTOR_MODEL_VERSION}`} />
      </div>
    </section>
  )
}
