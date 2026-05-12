# 🌸 Personal Diet Tracking Assistant

A self-hosted, AI-powered diet tracking assistant that reads your Excel meal plan and lets you log food through a natural-language chat interface.

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and APP_PASSWORD at minimum
```

### 2. Build and run

```bash
docker compose up -d --build
```

### 3. Access

Open `https://assistant.matrix-synamic.com` (or your configured domain / VPS IP on port 80).

Log in with the password from `APP_PASSWORD` in your `.env`.

### 4. Upload your diet plan

Go to **Plan Manager → Upload Plan** and upload your `.xlsx` diet plan file matching the supported format.

---

## Stack

| Layer | Technology |
|---|---|
| Reverse proxy | Caddy (auto HTTPS) |
| UI | Streamlit |
| API | FastAPI |
| Agent | PydanticAI |
| LLM | Anthropic Claude (or OpenAI) |
| Excel I/O | openpyxl + filelock |
| Fuzzy matching | RapidFuzz |
| Metadata DB | SQLite |
| Deployment | Docker Compose |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes* | — | Anthropic API key |
| `OPENAI_API_KEY` | Yes* | — | OpenAI API key (*one of these required) |
| `LLM_PROVIDER` | No | `anthropic` | `anthropic` or `openai` |
| `LLM_MODEL` | No | `claude-sonnet-4-6` | Model name |
| `APP_PASSWORD` | Yes | `dietassistant` | UI login password |
| `TZ` | No | `Asia/Tehran` | Timezone |
| `MATCH_CONFIDENCE_AUTO` | No | `90` | Auto-log threshold (%) |
| `MATCH_CONFIDENCE_CONFIRM` | No | `70` | Confirm-before-log threshold (%) |
| `BACKUP_RETENTION_DAYS` | No | `30` | Days to keep backups |

---

## Supported Excel Format

Your workbook must contain these sheets:

- `All Sections` — columns: `Section`, `Option No.`, `Diet option (exact PDF text)`, `PDF Page`
- `Breakfast`, `Lunch`, `Dinner`, `Snack 1`, `Snack 2`, `Snack 3` — columns: `Option No.`, `Diet option (exact PDF text)`, `PDF Page`
- `Index` — columns: `Section`, `Options Extracted`, `PDF Page(s)`

The app adds these sheets automatically (never modifying plan data):

- `Consumption_Log` — all logged consumption events
- `Parsed_Option_Items` — parsed food items from option text
- `Daily_Status` — daily summaries

Download a template from the Plan Manager page.

---

## Docker Compose Commands

```bash
docker compose up -d --build    # Start everything
docker compose ps               # Check service status
docker compose logs -f          # Stream logs
docker compose logs -f api      # API logs only
docker compose down             # Stop everything
```

---

## Restore from Backup

1. Stop the stack: `docker compose down`
2. Replace `data/active/diet_plan.xlsx` with the backup copy
3. Restart: `docker compose up -d`

Backups are stored in `data/backups/` and run daily at 02:00.

---

## Security Notes

- Never commit your `.env` file
- Change `APP_PASSWORD` before public deployment
- Only the API service writes to the Excel workbook
- All uploads are validated before activation
- File locks prevent concurrent write corruption
