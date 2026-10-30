# Validation record

## Environment

- Windows, Python 3.13.7.
- Tesseract 5.4.0 (20240606 build), English OCR data.
- Exact direct dependencies in `requirements.txt`; complete tested Windows environment in `requirements-lock-windows.txt`.
- Backend: `local`. No API key required or used.

## Automated checks

The suite contains **34 tests**. The included `test-results.xml` is the machine-readable execution report, including the run timestamp, elapsed time and failures. Run `python -m pytest -q` from the project folder to repeat it.

Coverage includes:

- Two policy questions: actual retrieval output, source filenames and graph paths.
- The supplied 128-page lecture PDF: retrieval of the science/engineering goals on page 4.
- Two SQL examples: exact allocation and ordered departmental overspend values.
- Three real receipt-image OCR checks: vendor, date, currency, subtotal, tax, total, item count, line count, item names, quantities, unit prices and amounts. Expected JSON is used only by tests, never by the OCR application.
- Invalid/empty questions, ambiguous intent, missing documents, malformed PDFs/images, blank images, missing Tesseract, missing model keys and unsupported routes.
- Rejection of SQL writes, multiple statements, forbidden functions and system-table reads.
- Current-quarter date handling, absent budget data, retained document context and retrieval abstention.
- Streamlit AppTest submission of RAG and SQL requests through the chat input.

## Browser checks and screenshots

Actual browser validation on 2026-09-16 submitted a document question, a budget question and two image uploads through the same chat input. No capability selector was used. The screenshots are unmodified captures of the running application, not mockups:

- `screenshots/01_rag.png`: annual-leave question, RAG route and cited policy excerpt.
- `screenshots/02_sql.png`: SQL route, Engineering/Marketing/Operations overspend results, SQL and bound parameters.
- `screenshots/03_ocr_cafe.png`: real cafe receipt extraction, date 2026-06-15, total INR 525.00, tax 25.00 and quantity 3.

The second uploaded receipt returned PAPER TRAIL, 2026-06-16, INR 294.00, tax 14.00 and quantity 5. A subsequent parser fix removes a duplicated OCR quantity marker; the automated suite verifies the corrected item names.

## Limits of validation

- Live Hugging Face inference was **not** tested with a paid/account-backed token. Missing-key behavior is tested. Model availability and account permissions remain provider-dependent.
- Windows/Python 3.13 is the tested platform. The README includes macOS/Linux installation guidance, but those operating systems were not tested here.
- The three generated clear receipt fixtures pass exact checks. Arbitrary receipts are not guaranteed: the supplied Walmart receipt produced partial item recognition, while the supplied Swiss and stylized shop images failed receipt recognition in this environment. Their original files are included as exploratory edge cases. Use the clear fixtures for the required demo and verify real OCR against the image.
- Local RAG is lexical retrieval with cited excerpts. Generated prose requires the optional backend. Local SQL routing/planning is constrained and does not cover every possible financial question.
- This is a local, demo-ready assignment submission. Authentication, durable multi-user storage, monitoring and public deployment are not implemented.

## Submission hygiene

Only placeholder environment settings are included. The original Task_11 `.env`, caches, logs and external-folder imports were not copied. Source files and the submission ZIP are checked for accidental credential patterns and excluded files. User-provided PDF and receipt images are preserved unchanged; the incompatible loan-default workbook is not used as budget data.
