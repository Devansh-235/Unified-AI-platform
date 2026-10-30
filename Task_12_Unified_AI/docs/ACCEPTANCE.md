# Task 11 → Task 12 acceptance map

| Requirement | Implementation / evidence |
|---|---|
| LangGraph basics summary | README architecture section |
| Supervisor node | `platform_core/graph.py: supervisor` |
| RAG, SQL, OCR nodes | Three named graph nodes, each ending at `END` |
| Conditional routing | `add_conditional_edges` selects one node or clarification |
| One chat + uploads | `app.py` uses a single `st.chat_input` with attachments |
| No manual agent selectors | Sidebar has only sample-document context and conversation reset |
| Real capability tests | `tests/test_platform.py` asserts graph paths and actual answers |
| Clean independent folder | Local package imports; no imports from the old project folders |
| No keys / no private env | Only `.env.example` with placeholders, plus `.gitignore` |
| Setup and run instructions | README includes Windows, macOS/Linux, Tesseract, optional HF |
| RAG samples | Fictional policy TXT and supplied AI lecture PDF |
| Budget sample | Fixed `samples/budget.csv` loaded into guarded in-memory SQLite |
| Three clear receipts | `samples/receipts/01_cafe.png`, `02_stationery.png`, `03_grocery.png` |
| Supplied receipts preserved | `samples/user_receipts/` includes original files unchanged |
| Six demo inputs | README example table and `docs/DEMO.md` |
| Working UI evidence | Actual screenshot files and validation notes |
| No document | RAG returns an actionable upload instruction |
| Invalid question | Router requests clarification |
| Wrong / unknown route | Safe conditional-edge fallback to clarification |
| OCR failure | Invalid/corrupt/blank image and timeout handling; raw text + warnings |
| Missing API key | Optional HF backend fails clearly; local mode needs no key |

“Productionize” here means a clean, reproducible local demonstration as specified in the assignment. Hosted multi-user hardening is explicitly outside this submission's claims.
