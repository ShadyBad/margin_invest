"use client"

import { motion } from "framer-motion"

interface PanelBackdropProps {
  onClose: () => void
}

export function PanelBackdrop({ onClose }: PanelBackdropProps) {
  return (
    <motion.div
      data-testid="panel-backdrop"
      className="fixed inset-0 z-40 bg-black/50"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      onClick={onClose}
      aria-hidden="true"
    />
  )
}
