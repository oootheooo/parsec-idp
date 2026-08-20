# UX / UI Specification

## 1. Overall style

Modern B2B application:
- clean;
- dense enough for operations work;
- neutral;
- accessible;
- responsive desktop-first;
- no excessive gradients or decorative AI imagery.

Use a left sidebar on desktop.

## 2. Routes

Public:
- `/login`
- `/register`

Authenticated:
- `/`
- `/documents`
- `/documents/new`
- `/documents/:id`
- `/documents/:id/review`
- `/processors`
- `/processors/new`
- `/processors/:id`
- `/processors/:id/edit`
- `/workflows`
- `/developer`
- `/settings`
- `/settings/members`

## 3. App shell

Sidebar:
- HANDL Document Intelligence logo/name
- Dashboard
- Documents
- Processors
- Workflows
- API & Webhooks
- Settings

Topbar:
- workspace switcher
- optional global upload button
- user menu

## 4. Dashboard

Cards:
- Documents processed
- Review queue
- Success rate
- Avg processing time
- Pages processed

Chart:
- documents by day/status

Table:
- recent documents

## 5. Documents list

Columns:
- document/filename
- processor
- pages
- status
- confidence summary
- review
- uploaded
- actions

Filters:
- search
- processor
- status
- date
- review required

Click row -> document detail.

## 6. Upload flow

Drag/drop panel + file picker.

Fields:
- file
- processor selection
- optional auto-detect processor
- process immediately

After upload:
- navigate to document detail;
- show status timeline;
- poll.

Batch upload may be future; supporting multiple files is a bonus.

## 7. Document detail

Header:
- filename
- status
- processor
- uploaded time
- page count

Actions:
- review
- reprocess
- download original
- export
- delete

Sections:
- processing timeline
- extracted summary
- validation summary
- extraction history

## 8. Review screen — highest priority

Desktop two-pane layout.

### Left pane: document
- PDF/page viewer;
- page thumbnails optional;
- zoom;
- page navigation;
- highlighted bbox overlay;
- scroll to evidence page when field clicked.

For non-PDF documents, render converted page imagery or a structured preview.

### Right pane: data
Header:
- processor/version
- overall confidence
- validation state
- progress e.g. `12 / 15 fields reviewed`

Fields rendered recursively from schema:
- label
- current/effective value
- confidence
- state
- validation message
- source excerpt
- edit button/control
- approve/reject controls

Nested objects:
- grouped sections.

Arrays:
- table/grid when objects share columns;
- add/remove rows only in reviewer override layer;
- preserve model result separately.

When field clicked:
- select field;
- evidence card expands;
- left viewer moves/highlights.

Footer/sticky action:
- approve document
- save progress is automatic or explicit.

## 9. Processor builder

Tabs/steps:
1. Basic info
2. Fields / Schema
3. Instructions
4. Validation
5. Review settings
6. Test / Publish

### Schema UI
Support visual fields:
- text
- number
- integer
- boolean
- date (represented as string + format/description)
- enum
- object/group
- list of primitive/object

Also raw JSON Schema editor.

Actions:
- "Generate fields with AI"
- add field
- nest field
- reorder if practical
- required toggle
- description
- example optional

### AI assist
Modal:
"What should this processor extract?"
Returns proposed schema with preview diff, then user accepts.

## 10. Processor test mode

Upload a sample doc and run draft processor without publishing if practical.

If implementing draft extraction complicates immutability, allow temporary test run linked to draft version.

Display extracted preview.

## 11. API & Webhooks screen

Tabs:
- API keys
- Webhooks
- API examples

API key creation:
- name
- expiration
- show secret once in copyable panel.

Webhook:
- name
- URL
- subscribed events
- enable
- secret shown once/rotate
- delivery history.

## 12. Workflows

Simple card/list UI.

Rule builder:
- trigger
- processor
- condition
- action

Keep MVP rule UI constrained to supported declarative conditions.

## 13. Error handling

Never show stack traces.

Examples:
- "This file type isn't supported."
- "Document parsing failed. You can retry processing."
- "AI extraction is not configured for this environment."
- "The extraction service temporarily failed. Retrying…"

## 14. Accessibility

- keyboard reachable controls;
- form labels;
- semantic buttons;
- visible focus;
- sufficient contrast;
- confidence should not rely on color alone.

## 15. Empty states

Each main screen should have a useful CTA.

Processors empty:
"Create a processor to define what you want to extract."

Documents empty:
"Upload your first document."

Review queue empty:
"No documents currently require review."
