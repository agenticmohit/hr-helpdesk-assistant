# Failure Diagnosis Write-Up

## The Failure
During initial testing of the `/classify-ticket` endpoint, the LLM consistently failed to output valid JSON for the `priority` field. Instead of returning one of the enumerated values (`low`, `medium`, `high`, `urgent`), it occasionally output values like `normal` or `critical`, which caused the Pydantic `TicketClassification` model to throw a validation error. This resulted in the API returning a 500-level error with the message "Model output did not match the required schema."

## Root Cause Category
**Behavior/Instruction Problem & Output Parsing Problem**

While the original prompt specified the expected schema, the behavior rules did not strictly constrain the LLM from inventing new values for the `priority` field. The output parser (Pydantic) correctly caught the discrepancy, but the LLM was not properly guided to respect the exact string enums.

## The Fix
I updated the `TICKET_CLASSIFICATION_PROMPT` to include a strict **[4. BEHAVIOR RULES]** section, explicitly stating:
1. "Do not invent category values."
2. "Do not invent priority values."

Additionally, I moved the schema definition directly into the **[3. OUTPUT CONTRACT]** section, making the allowed values highly visible. I also implemented structured JSON-mode via `client.chat.completions.create(response_format={"type": "json_object"})` which further forces the LLM to return strict JSON.

## Before/After Test Results

### Test Set
1. "My laptop is broken and I can't work!"
2. "I need help with my taxes."
3. "I submitted my travel expenses three weeks ago and haven't received the money yet."

### Before Fix
- Test 1 Output: `{"category": "workplace", "priority": "critical", ...}` -> **FAILED** (ValidationError)
- Test 2 Output: `{"category": "payroll", "priority": "normal", ...}` -> **FAILED** (ValidationError)
- Test 3 Output: `{"category": "reimbursement", "priority": "medium", ...}` -> **PASSED**

### After Fix
- Test 1 Output: `{"category": "workplace", "priority": "urgent", ...}` -> **PASSED** (Valid Enum)
- Test 2 Output: `{"category": "payroll", "priority": "low", ...}` -> **PASSED** (Valid Enum)
- Test 3 Output: `{"category": "reimbursement", "priority": "medium", ...}` -> **PASSED**

The strict behavior rules successfully constrained the LLM to the allowed enum values.
