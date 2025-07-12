---
applyTo: '.'
---

## 🔹 Think simple, stay simple
- Prefer clarity over cleverness—write code that a junior developer could pick up in a week.
- Don’t over-engineer. Only abstract when the pattern has repeated at least twice.

## 🔹 Don’t repeat yourself (DRY)
- Avoid duplicate logic. Extract repeated code into functions or helpers.
- If similar blocks appear more than once, suggest a shared utility or loop.

## 🔹 Don’t assume, ask
- Don’t invent parameters, folder structures, or config unless explicitly defined.
- Leave `TODO` comments where something needs clarification or is outside current scope.

## 🔹 Write small, testable units
- Favor short, single-purpose functions.
- Make code easy to unit test—even if we’re not writing tests yet.

## 🔹 Fail gracefully
- Handle errors with care. Return informative messages instead of crashing.
- Prefer `try/except` or error-aware data models where possible.

## 🔹 Embrace modern defaults
- Use async functions when writing I/O-heavy logic (e.g., web APIs, file access).
- Use list comprehensions, f-strings, and context managers (`with open(...)`) as default.

## 🔹 Document as you go
- Every function should include a one-line docstring describing what it does and what it expects.
- Use meaningful variable names even in quick drafts.

## 🔹 Be lazy in the right way
- Don’t rewrite boilerplate. Use frameworks and built-ins to your advantage.
- Generate scaffolds (e.g., route handlers, React components) that can be edited—not finished masterpieces.

## 🔹 Default to modularity
- If a function starts doing too much, split it.
- Group related logic together, but don’t build monoliths.

## 🔹 Never guess, never assume
- If unsure how a part connects to others, leave a clear placeholder and comment:  
  `# TODO: Clarify this integration point`
