# PaperQA design system

Use this reference for every change to `web_app.py` or another user-facing surface. The direction is Notion-inspired warm minimalism adapted to a research extraction workspace. It is an independent implementation, not a Notion product or an endorsed replica.

## Product thesis

PaperQA is a document workspace for researchers. The page has one job: help a researcher configure one extraction run, understand whether it is ready, follow its progress, and verify the result.

Prefer the calm rhythm of a research notebook over a marketing dashboard. Every visible element should help the user answer one of four questions:

1. What papers am I processing?
2. What information will be extracted?
3. Is the run ready, active, complete, or blocked?
4. Where can I inspect and download the evidence?

## Visual tokens

| Role | Value | Use |
| --- | --- | --- |
| Ink | `#37352f` | headings and primary text |
| Muted ink | `#787774` | explanations and metadata |
| Faint ink | `#9b9a97` | placeholders and low-priority labels |
| Canvas | `#f7f6f3` | warm page background |
| Surface | `#ffffff` | uploads, expanders, readiness, and tables |
| Soft surface | `#f1f1ef` | sidebar and quiet callouts |
| Primary blue | `#2383e2` | the single primary action and focus |
| Active blue | `#1b6fbd` | pressed and hover state |
| Hairline | `rgba(55, 53, 47, 0.16)` | dividers and surface outlines |
| Success | `#448361` | ready and completed states |
| Error | `#d44c47` | failed and blocked states |

Blue is functional, not decorative. Reserve it for the action that advances the workflow, links, active focus, and progress. Keep the rest of the chrome neutral.

## Type and rhythm

- Use a restrained serif for the page title only: `ui-serif`, Georgia, Cambria, fallback serif.
- Use Inter or the native system sans stack for interface text.
- Use the native monospace stack only for logs, run identifiers, and compact step numbers.
- Body text is 14–16px with 1.45–1.65 line height. Interface headings are 18–20px. The page title may scale from 40–60px.
- Build spacing from 4, 8, 12, 16, 24, and 32px. Use 24px inside major surfaces and 32px or more between workflow sections.

## Layout

- Desktop: a quiet settings sidebar plus a centered document column no wider than 880px.
- Mobile: one column with 18px side padding; readiness rows stack; all primary actions fill the width.
- The main page is a real sequence: papers, question set, workbook. Step numbers encode that order.
- Keep provider details in the sidebar. Keep paper and evidence decisions in the document.
- Use whitespace and hairlines before adding containers. A surface needs a border only when it groups interactive content or state.

## Controls and surfaces

- Form fields use 4px corners; utility controls use 8px; content surfaces use 8–12px.
- Primary actions are at least 44px high, blue, and singular within their section.
- Cards use a 1px hairline. Elevation is reserved for overlays; use a barely visible layered shadow if one is required.
- File upload is an invitation with an explicit empty state. Once files exist, show the count and offer a compact review list.
- Question sets show their name and field count before the user expands the full prompts.
- Tables prioritize scanning: subtle dividers, compact metadata, no ornamental color.

## Interaction states

The interface must expose these states without requiring the user to interpret logs:

- **Empty:** explain the next action beside the empty control.
- **Ready:** summarize papers, extraction fields, and model connection immediately above the primary action.
- **Running:** stream the CLI log and change the status label when conversion, extraction, and workbook writing begin.
- **Complete:** persist the result across Streamlit reruns, preview the table, and present download as the primary action.
- **Error:** say that the workbook was not created and leave the expanded log visible for diagnosis.

Disable the primary action until its prerequisites are satisfied. Keep advanced provider settings collapsed by default. Preserve uploaded inputs when a user inspects settings or downloads a result.

## Accessibility and responsive behavior

- Maintain a visible 2px blue keyboard focus ring.
- Use a 44px minimum touch target for actions.
- Pair semantic colors with text; color alone never communicates readiness or failure.
- Respect `prefers-reduced-motion` and keep motion limited to short hover feedback.
- At widths below 768px, collapse multi-column regions and let labels wrap rather than truncate.

## Completion criteria

A frontend change is complete when every affected empty, ready, running, complete, and error state remains understandable; keyboard focus is visible; the layout works at mobile width; and the change uses the tokens above instead of introducing a parallel visual language.

Design direction adapted from the public [Notion DESIGN.md analysis](https://getdesign.md/notion/design-md) in [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md).
