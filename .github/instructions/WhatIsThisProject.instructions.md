---
applyTo: '.'
---
# Copilot Instructions – Mother‑2 Synthesis Agent

## 🧠 About This Project

This project is called **Mother‑2 Synthesis Agent**. It is a self-hosted tool that turns raw UX research transcripts into a visual whiteboard of themes, journeys, quotes, and opportunities. The end goal involves LLM agents, a tldraw-based canvas, and a pipeline architecture—but we are not there yet.

## 🧭 How We’re Building This

We are taking an intentionally **slow, controlled, minimal-first approach**. We are not scaffolding the full system or writing speculative code. Instead:

- We are building one **tiny, testable feature at a time**
- Each step must **work independently** before we move on
- We prefer clarity over abstraction
- We do not optimize, generalize, or restructure until necessary

## ✅ What You Should Do

- Help build **small features** with clean, modular code
- Focus on **just what we ask for**—no more, no less
- Use simple, readable logic and meaningful names
- Add light comments or `TODO:` markers when something is incomplete

## 🚫 What You Should Avoid

- Do not anticipate future features or folder structures
- Do not suggest routing, state libraries, or database code unless explicitly requested
- Do not scaffold or generate entire pipelines, boards, or LLM chains
- Do not combine multiple responsibilities into one function or component

## 🧘 Style Philosophy

- Keep functions and components small and focused
- Use plain language and clear docstrings
- Leave abstractions for later—code for understanding first
- If uncertain, leave a placeholder or `TODO:` rather than guessing
