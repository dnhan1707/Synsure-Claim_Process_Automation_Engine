# Synsure API Reference

Base URL
- http://localhost:8000

Auth
- All endpoints require the x-api-key header.
- For multipart/form-data (file uploads), do NOT set Content-Type manually; let the browser/client set it.

Standard Response Envelope
- success: boolean
- error?: string
- result?: any

Example:
```json
{ "success": true, "result": { /* data */ } }
```

Error format:
```json
{ "success": false, "error": "Detailed error message" }
```

---

## Tenants

Create tenant
- POST /tenant/
- Body (application/json):
```json
{ "tenant_name": "Acme Insurance Corp" }
```
- Response:
```json
{ "success": true, "message": "Tenant created successfully" }
```

List tenants
- GET /tenant/
- Response:
```json
{
  "success": true,
  "result": [
    { "id": "tenant-uuid", "name": "Acme Insurance Corp", "created_at": "2025-01-01T00:00:00Z" }
  ]
}
```

Get tenant
- GET /tenant/{tenant_id}
- Response:
```json
{
  "success": true,
  "result": {
    "id": "tenant-uuid",
    "name": "Acme Insurance Corp",
    "created_at": "2025-01-01T00:00:00Z",
    "cases_count": 15,
    "active_cases": 8
  }
}
```

---

## Cases (v2)

List cases for a tenant
- GET /api/v2/case/{tenant_id}
- Response:
```json
{
  "success": true,
  "result": [
    {
      "id": "case-uuid",
      "name": "Property Damage Claim",
      "tenant_id": "tenant-uuid",
      "status": "active",
      "files_count": 5,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

Get case details
- GET /api/v2/case/{tenant_id}/{case_id}
- Response:
```json
{
  "success": true,
  "result": {
    "id": "case-uuid",
    "name": "Property Damage Claim",
    "tenant_id": "tenant-uuid",
    "files": [
      { "id": "file-uuid", "name": "estimate.pdf", "size": 2048000, "type": "application/pdf" }
    ],
    "responses": [
      { "id": "response-uuid", "ai_analysis": "Analysis results...", "created_at": "2025-01-01T00:00:00Z" }
    ]
  }
}
```

Create case
- POST /api/v2/case/
- Content-Type: multipart/form-data
- Form fields:
  - tenant_id: string
  - case_name: string
  - files?: file[]
- Response: StandardResponse (created case metadata)

Get latest AI response for a case
- GET /api/v2/case/latestresponse/{tenant_id}/{case_id}
- Response:
```json
{
  "success": true,
  "result": {
    "id": "response-uuid",
    "ai_analysis": "The claim appears to be valid based on the documentation provided...",
    "confidence_score": 0.85,
    "recommendations": ["Request additional medical documentation", "Verify repair estimates"],
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

---

## Files (v1)

Check duplicates before upload
- POST /api/v1/file/dupcheck
- Content-Type: multipart/form-data
- Form fields:
  - tenant_id: string
  - case_id: string
  - files: file[]
- Response (example shape; actual fields may vary by implementation):
```json
{
  "success": true,
  "duplicates": [
    {
      "file_name": "document.pdf",
      "existing_file_id": "existing-file-uuid",
      "is_duplicate": true
    }
  ],
  "actions_required": true
}
```

Upload files to a case
- POST /api/v1/file/upload
- Content-Type: multipart/form-data
- Form fields:
  - tenant_id: string
  - case_id: string
  - files: file[]
  - file_actions: string (JSON string array; see below)
- file_actions JSON item:
```json
[
  {
    "target_id": "existing-file-uuid-or-empty",
    "action": "upload" // "upload" | "overwrite" | "keep"
  }
]
```
- Response (from backend):
```json
{ "success": true, "uploaded_files": 3 }
```
- Status codes: 201 on success, 400/500 on error

Notes
- file_actions must be a string containing valid JSON (the API parses and validates each action).
- If duplicates were found via dupcheck, pass appropriate actions per item.

---

## AI Submission (v1)

Create new case and run AI immediately
- POST /api/v1/submission/newcase
- Content-Type: multipart/form-data
- Form fields:
  - tenant_id: string
  - case_name: string
  - files: file[]
- Response (example):
```json
{
  "success": true,
  "new_case_id": "case-uuid",
  "result": {
    "ai_analysis": "Analysis results...",
    "processing_time": "2.3s",
    "confidence_score": 0.89
  }
}
```

Run AI for selected files in an existing case
- POST /api/v1/submission/start
- Content-Type: application/json
- Body:
```json
{ "tenant_id": "tenant-uuid", "case_id": "case-uuid", "chosen_files": ["file-uuid-1", "file-uuid-2"] }
```
- Response (example):
```json
{
  "success": true,
  "result": {
    "ai_analysis": "Based on the selected documents...",
    "processing_time": "1.8s",
    "confidence_score": 0.92,
    "recommendations": ["Action item 1", "Action item 2"]
  }
}
```

Batch process multiple cases asynchronously
- POST /api/v1/submission/submit-batch-async
- Content-Type: application/json
- Body:
```json
{ "tenant_id": "tenant-uuid", "case_ids": ["case-uuid-1", "case-uuid-2", "case-uuid-3"] }
```
- Response:
```json
{
  "success": true,
  "message": "Submitted 3 cases for processing",
  "task_ids": {
    "case-uuid-1": "task-uuid-1",
    "case-uuid-2": "task-uuid-2",
    "case-uuid-3": "task-uuid-3"
  },
  "status_check_info": "Use /task/status/{tenant_id}?task_ids=id1,id2,id3 to check status"
}
```

---

## Tasks

Get task status
- GET /task/status/{tenant_id}?task_ids=task-uuid-1,task-uuid-2
- Query:
  - task_ids: comma-separated list (max 50)
- Response (example):
```json
{
  "summary": { "queued": 1, "running": 2, "completed": 5, "failed": 0 },
  "tasks": {
    "case-uuid-1": {
      "task_id": "task-uuid-1",
      "status": "completed",
      "error": null,
      "created_at": "2025-01-01T00:00:00Z",
      "completed_at": "2025-01-01T00:02:30Z"
    },
    "case-uuid-2": {
      "task_id": "task-uuid-2",
      "status": "running",
      "error": null,
      "created_at": "2025-01-01T00:01:00Z",
      "completed_at": null
    }
  },
  "total": 8,
  "found": 8,
  "requested": 2
}
```

Debug endpoints (if enabled)
- POST /task/debug/process-task
  - Body: { "task_id": "task-uuid" }
- GET /task/debug/task/{task_id}

---

## Usage Examples

JavaScript fetch (multipart upload)
```js
const form = new FormData();
form.append('tenant_id', tenantId);
form.append('case_id', caseId);
files.forEach(f => form.append('files', f));
form.append('file_actions', JSON.stringify([{ target_id: "", action: "upload" }]));

const res = await fetch(`${baseUrl}/api/v1/file/upload`, {
  method: 'POST',
  headers: { 'x-api-key': apiKey }, // do not set Content-Type
  body: form
});
const data = await res.json();
```

cURL (new case submission with files)
```bash
curl -X POST "$BASE/api/v1/submission/newcase" ^
  -H "x-api-key: %API_KEY%" ^
  -F tenant_id=%TENANT_ID% ^
  -F case_name="Auto Accident Claim" ^
  -F files=@C:\path\to\doc1.pdf ^
  -F files=@C:\path\to\doc2.pdf
```

Task status polling (JS)
```js
const ids = Object.values(taskIds).join(',');
const res = await fetch(`${baseUrl}/task/status/${tenantId}?task_ids=${ids}`, {
  headers: { 'x-api-key': apiKey }
});
const status = await res.json();
```

---

## Status Codes

- 200 OK: Successful request
- 201 Created: Resource created (e.g., file upload)
- 400 Bad Request: Validation issues
- 404 Not Found: Resource missing
- 500 Internal Server Error

---

## Notes

- File types typically supported: PDF, DOC, DOCX, JPG, PNG.
- Keep task status polling to every 5–10 seconds to avoid rate limits.
- For uploads, backend validates file_actions against the uploaded files.

---

## Where this spec comes from

- Files API routes: app/routes/file_routes.py
- Cases API routes: app/routes/case_routes_v2.py
- Submission (AI) routes: app/routes/submission_routes.py
- File handling services: app/service/file_service.py, app/service/case_service_v2.py
