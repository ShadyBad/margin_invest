"use client"

import { motion } from "framer-motion"
import { ButtonPrimary } from "../button-primary"

const ease = [0.22, 1, 0.36, 1] as const

export function FinalCTA() {
  return (
    <section>
      <div
        className="mx-auto flex justify-center"
        style={{
          maxWidth: "1280px",
          paddingLeft: "8vw",
          paddingRight: "8vw",
          paddingTop: "160px",
          paddingBottom: "120px",
        }}
      >
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, ease }}
        >
          <ButtonPrimary href="/dashboard">Explore the Engine</ButtonPrimary>
        </motion.div>
      </div>
    </section>
  )
}
