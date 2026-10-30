# Five-minute demo

1. Install requirements and Tesseract, then start `python -m streamlit run app.py`.
2. Point out the one chat input and its attachment icon. There are no capability selectors.
3. Ask the first two README questions. Show `START → router → rag → END` and the source citations.
4. Ask the two budget questions. Show `router → sql`, the correct INR values and the SQL expander.
5. Attach the cafe receipt and send “Extract this receipt”. Show `router → ocr`, date, tax, items and total.
6. Attach the stationery receipt and repeat. No settings changes are required to switch capabilities.
7. Ask “What is the total?” without an attachment. Show the clarification response.
8. Disable the sample policy, clear the conversation, disable the sample again if reset, then ask a document question to show the missing-document error.
9. Run `python -m pytest -q` to show repeatable checks.

Screenshots in `screenshots/` are actual captures from validation, not mockups. No hosted API credentials are necessary for this demo.
