<h1> Synsure Insurance Claims Processing API Documentation</h1>

<h2> Base Information</h2>
<ul>
<li><strong>Base URL:</strong> <code>http://localhost:8000</code></li>
<li><strong>API Version:</strong> 2.0.0</li>
<li><strong>Authentication:</strong> All endpoints require <code>x-api-key</code> header</li>
<li><strong>Content-Type:</strong> <code>application/json</code> (unless specified otherwise)</li>
</ul>

<hr>

<h2> Table of Contents</h2>
<ol>
<li><a href="#authentication">Authentication</a></li>
<li><a href="#response-format">Response Format</a></li>
<li><a href="#tenants-api">Tenants API</a></li>
<li><a href="#claims-management-api">Claims Management API</a></li>
<li><a href="#cases-api">Cases API</a></li>
<li><a href="#files-api">Files API</a></li>
<li><a href="#ai-processing-api">AI Processing API</a></li>
<li><a href="#tasks-api">Tasks API</a></li>
<li><a href="#email-api">Email API</a></li>
<li><a href="#error-handling">Error Handling</a></li>
<li><a href="#usage-examples">Usage Examples</a></li>
</ol>

<hr>

<h2 id="authentication"> Authentication</h2>

<p>All API endpoints require authentication via API key in the request header:</p>

<pre><code class="language-javascript">headers: {
  'x-api-key': 'your-api-key-here',
  'Content-Type': 'application/json'
}
</code></pre>

<hr>

<h2 id="response-format"> Response Format</h2>

<p>All API responses follow a consistent format:</p>

<pre><code class="language-typescript">interface StandardResponse {
  success: boolean;
  error?: string;  // Present only if success is false
}

interface DataResponse extends StandardResponse {
  result?: any;    // Contains the actual data
}
</code></pre>

<hr>

<h2 id="tenants-api">👥 Tenants API</h2>

<h3>Create New Tenant</h3>
<pre><code>POST /tenant/
</code></pre>

<p><strong>Request Body:</strong></p>
<pre><code class="language-json">{
  "tenant_name": "Acme Insurance Corp"
}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "message": "Tenant created successfully"
}
</code></pre>

<h3>Get All Tenants</h3>
<pre><code>GET /tenant/
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": [
    {
      "id": "tenant-uuid",
      "name": "Acme Insurance Corp",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
</code></pre>

<h3>Get Tenant Details</h3>
<pre><code>GET /tenant/{tenant_id}
</code></pre>

<p><strong>Path Parameters:</strong></p>
<ul>
<li><code>tenant_id</code> (string): The unique tenant identifier</li>
</ul>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": {
    "id": "tenant-uuid",
    "name": "Acme Insurance Corp",
    "created_at": "2025-01-01T00:00:00Z",
    "cases_count": 15,
    "active_cases": 8
  }
}
</code></pre>

<hr>

<h2 id="claims-management-api">📄 Claims Management API</h2>

<h3>Create New Claim</h3>
<pre><code>POST /claim/manager/
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>tenant_id</code> (string): Tenant ID</li>
<li><code>case_name</code> (string): Name of the claim/case</li>
<li><code>files</code> (file[], optional): Files to upload</li>
</ul>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "message": "Claim created successfully"
}
</code></pre>

<h3>Get All Claims</h3>
<pre><code>GET /claim/manager/
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": [
    {
      "id": "claim-uuid",
      "name": "Auto Accident - John Doe",
      "tenant_id": "tenant-uuid",
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
</code></pre>

<h3>Get Claim Details</h3>
<pre><code>GET /claim/manager/{claim_id}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": {
    "id": "claim-uuid",
    "name": "Auto Accident - John Doe",
    "tenant_id": "tenant-uuid",
    "files": [
      {
        "id": "file-uuid",
        "name": "police_report.pdf",
        "size": 1024000,
        "uploaded_at": "2025-01-01T00:00:00Z"
      }
    ],
    "status": "active",
    "created_at": "2025-01-01T00:00:00Z"
  }
}
</code></pre>

<h3>Update Claim Name</h3>
<pre><code>PATCH /claim/manager/{claim_id}
</code></pre>

<p><strong>Request Body:</strong></p>
<pre><code class="language-json">{
  "new_name": "Updated Claim Name"
}
</code></pre>

<h3>Upload Files to Existing Case</h3>
<pre><code>POST /claim/manager/{tenant_id}/{case_id}
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>files</code> (file[]): Files to upload</li>
</ul>

<h3>Replace Existing File</h3>
<pre><code>PUT /claim/manager/{tenant_id}/{case_id}/{file_id}
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>new_file</code> (file): New file to replace the existing one</li>
</ul>

<h3>Remove Files</h3>
<pre><code>DELETE /claim/manager/files
</code></pre>

<p><strong>Request Body:</strong></p>
<pre><code class="language-json">{
  "file_ids": ["file-uuid-1", "file-uuid-2"]
}
</code></pre>

<h3>Remove Case</h3>
<pre><code>DELETE /claim/manager/{case_id}
</code></pre>

<hr>

<h2 id="cases-api">📁 Cases API</h2>

<h3>Get All Cases for Tenant</h3>
<pre><code>GET /api/v2/case/{tenant_id}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
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
</code></pre>

<h3>Get Case Details</h3>
<pre><code>GET /api/v2/case/{tenant_id}/{case_id}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": {
    "id": "case-uuid",
    "name": "Property Damage Claim",
    "tenant_id": "tenant-uuid",
    "files": [
      {
        "id": "file-uuid",
        "name": "estimate.pdf",
        "size": 2048000,
        "type": "application/pdf"
      }
    ],
    "responses": [
      {
        "id": "response-uuid",
        "ai_analysis": "Analysis results...",
        "created_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
</code></pre>

<h3>Create New Case</h3>
<pre><code>POST /api/v2/case/
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>tenant_id</code> (string): Tenant ID</li>
<li><code>case_name</code> (string): Case name</li>
<li><code>files</code> (file[], optional): Files to upload</li>
</ul>

<h3>Get Latest AI Response</h3>
<pre><code>GET /api/v2/case/latestresponse/{tenant_id}/{case_id}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": {
    "id": "response-uuid",
    "ai_analysis": "The claim appears to be valid based on the documentation provided...",
    "confidence_score": 0.85,
    "recommendations": [
      "Request additional medical documentation",
      "Verify repair estimates"
    ],
    "created_at": "2025-01-01T00:00:00Z"
  }
}
</code></pre>

<hr>

<h2 id="files-api">📎 Files API</h2>

<h3>Check for Duplicate Files</h3>
<pre><code>POST /api/v1/file/dupcheck
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>tenant_id</code> (string): Tenant ID</li>
<li><code>case_id</code> (string): Case ID</li>
<li><code>files</code> (file[]): Files to check</li>
</ul>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
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
</code></pre>

<h3>Upload Files</h3>
<pre><code>POST /api/v1/file/upload
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>tenant_id</code> (string): Tenant ID</li>
<li><code>case_id</code> (string): Case ID</li>
<li><code>files</code> (file[]): Files to upload</li>
<li><code>file_actions</code> (string): JSON string of actions</li>
</ul>

<p><strong>file_actions JSON format:</strong></p>
<pre><code class="language-json">[
  {
    "target_id": "existing-file-uuid-or-empty",
    "action": "upload" // "upload", "overwrite", or "keep"
  }
]
</code></pre>

<hr>

<h2 id="ai-processing-api">🤖 AI Processing API</h2>

<h3>Create New Case with AI Processing</h3>
<pre><code>POST /api/v1/submission/newcase
Content-Type: multipart/form-data
</code></pre>

<p><strong>Form Data:</strong></p>
<ul>
<li><code>tenant_id</code> (string): Tenant ID</li>
<li><code>case_name</code> (string): Case name</li>
<li><code>files</code> (file[]): Files to process</li>
</ul>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "new_case_id": "case-uuid",
  "result": {
    "ai_analysis": "Analysis results...",
    "processing_time": "2.3s",
    "confidence_score": 0.89
  }
}
</code></pre>

<h3>Process Selected Files</h3>
<pre><code>POST /api/v1/submission/start
</code></pre>

<p><strong>Request Body:</strong></p>
<pre><code class="language-json">{
  "tenant_id": "tenant-uuid",
  "case_id": "case-uuid",
  "chosen_files": ["file-uuid-1", "file-uuid-2"]
}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "result": {
    "ai_analysis": "Based on the selected documents...",
    "processing_time": "1.8s",
    "confidence_score": 0.92,
    "recommendations": ["Action item 1", "Action item 2"]
  }
}
</code></pre>

<h3>Batch Process Cases (Async)</h3>
<pre><code>POST /api/v1/submission/submit-batch-async
</code></pre>

<p><strong>Request Body:</strong></p>
<pre><code class="language-json">{
  "tenant_id": "tenant-uuid",
  "case_ids": ["case-uuid-1", "case-uuid-2", "case-uuid-3"]
}
</code></pre>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "success": true,
  "message": "Submitted 3 cases for processing",
  "task_ids": {
    "case-uuid-1": "task-uuid-1",
    "case-uuid-2": "task-uuid-2",
    "case-uuid-3": "task-uuid-3"
  },
  "status_check_info": "Use /task/status/{tenant_id}?task_ids=id1,id2,id3 to check status"
}
</code></pre>

<hr>

<h2 id="tasks-api">⚙️ Tasks API</h2>

<h3>Get Task Status</h3>
<pre><code>GET /task/status/{tenant_id}?task_ids=task-uuid-1,task-uuid-2
</code></pre>

<p><strong>Query Parameters:</strong></p>
<ul>
<li><code>task_ids</code> (string): Comma-separated list of task IDs (max 50)</li>
</ul>

<p><strong>Response:</strong></p>
<pre><code class="language-json">{
  "summary": {
    "queued": 1,
    "running": 2,
    "completed": 5,
    "failed": 0
  },
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
</code></pre>

<h3>Debug: Process Task Manually</h3>
<pre><code>POST /task/debug/process-task
</code></pre>

<p><strong>Request Body:</strong></p>
<pre><code class="language-json">{
  "task_id": "task-uuid"
}
</code></pre>

<h3>Debug: Get Task Details</h3>
<pre><code>GET /task/debug/task/{task_id}
</code></pre>

<hr>

<h2 id="email-api">📧 Email API</h2>

<p><em>Note: Email API endpoints would be documented here based on your email_routes.py implementation</em></p>

<hr>

<h2 id="error-handling">❌ Error Handling</h2>

<h3>HTTP Status Codes</h3>
<ul>
<li><code>200</code> - Success</li>
<li><code>201</code> - Created successfully</li>
<li><code>400</code> - Bad request (validation errors)</li>
<li><code>404</code> - Resource not found</li>
<li><code>500</code> - Internal server error</li>
</ul>

<h3>Error Response Format</h3>
<pre><code class="language-json">{
  "success": false,
  "error": "Detailed error message"
}
</code></pre>

<h3>Common Error Examples</h3>

<p><strong>Validation Error (400):</strong></p>
<pre><code class="language-json">{
  "success": false,
  "error": "Missing required parameters: tenant_id, case_ids"
}
</code></pre>

<p><strong>Not Found (404):</strong></p>
<pre><code class="language-json">{
  "success": false,
  "error": "Case not found",
  "result": {}
}
</code></pre>

<p><strong>Server Error (500):</strong></p>
<pre><code class="language-json">{
  "success": false,
  "error": "Internal server error"
}
</code></pre>

<hr>

<h2 id="usage-examples">💡 Usage Examples</h2>

<h3>Complete Workflow Example (JavaScript)</h3>

<pre><code class="language-javascript">class SynsureAPI {
  constructor(apiKey, baseUrl = 'http://localhost:8000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'x-api-key': this.apiKey,
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    return await response.json();
  }

  // Create a new tenant
  async createTenant(tenantName) {
    return this.request('/tenant/', {
      method: 'POST',
      body: JSON.stringify({ tenant_name: tenantName })
    });
  }

  // Create a new case with files and get AI analysis
  async createCaseWithAI(tenantId, caseName, files) {
    const formData = new FormData();
    formData.append('tenant_id', tenantId);
    formData.append('case_name', caseName);
    files.forEach(file => formData.append('files', file));

    return this.request('/api/v1/submission/newcase', {
      method: 'POST',
      headers: { 'x-api-key': this.apiKey }, // Don't set Content-Type for FormData
      body: formData
    });
  }

  // Process specific files from existing case
  async processFiles(tenantId, caseId, fileIds) {
    return this.request('/api/v1/submission/start', {
      method: 'POST',
      body: JSON.stringify({
        tenant_id: tenantId,
        case_id: caseId,
        chosen_files: fileIds
      })
    });
  }

  // Batch process multiple cases asynchronously
  async batchProcess(tenantId, caseIds) {
    return this.request('/api/v1/submission/submit-batch-async', {
      method: 'POST',
      body: JSON.stringify({
        tenant_id: tenantId,
        case_ids: caseIds
      })
    });
  }

  // Check status of background tasks
  async checkTaskStatus(tenantId, taskIds) {
    const taskIdString = taskIds.join(',');
    return this.request(`/task/status/${tenantId}?task_ids=${taskIdString}`);
  }

  // Get latest AI analysis for a case
  async getLatestAnalysis(tenantId, caseId) {
    return this.request(`/api/v2/case/latestresponse/${tenantId}/${caseId}`);
  }
}

// Usage example
const api = new SynsureAPI('your-api-key');

// Complete workflow
async function processInsuranceClaim() {
  try {
    // 1. Create tenant
    const tenant = await api.createTenant('ABC Insurance');
    console.log('Tenant created:', tenant);

    // 2. Create case with files and get immediate AI analysis
    const files = [/* File objects from input */];
    const newCase = await api.createCaseWithAI(
      'tenant-uuid', 
      'Auto Accident Claim', 
      files
    );
    console.log('Case created with AI analysis:', newCase);

    // 3. For batch processing multiple cases
    const batchResult = await api.batchProcess('tenant-uuid', [
      'case-1', 'case-2', 'case-3'
    ]);
    console.log('Batch processing started:', batchResult);

    // 4. Monitor batch processing status
    const taskIds = Object.values(batchResult.task_ids);
    const status = await api.checkTaskStatus('tenant-uuid', taskIds);
    console.log('Task status:', status);

    // 5. Get final analysis results
    const analysis = await api.getLatestAnalysis('tenant-uuid', 'case-uuid');
    console.log('AI Analysis:', analysis);

  } catch (error) {
    console.error('API Error:', error);
  }
}
</code></pre>

<h3>React Hook Example</h3>

<pre><code class="language-typescript">import { useState, useEffect } from 'react';

interface TaskStatus {
  summary: {
    queued: number;
    running: number;
    completed: number;
    failed: number;
  };
  tasks: Record&lt;string, any&gt;;
}

export function useTaskMonitoring(tenantId: string, taskIds: string[]) {
  const [status, setStatus] = useState&lt;TaskStatus | null&gt;(null);
  const [loading, setLoading] = useState(false);

  const checkStatus = async () => {
    if (!taskIds.length) return;
    
    setLoading(true);
    try {
      const api = new SynsureAPI('your-api-key');
      const result = await api.checkTaskStatus(tenantId, taskIds);
      setStatus(result);
    } catch (error) {
      console.error('Failed to check task status:', error);
    } finally {
      setLoading(false);
    }
  };

  // Poll status every 5 seconds
  useEffect(() => {
    const interval = setInterval(checkStatus, 5000);
    checkStatus(); // Check immediately
    
    return () => clearInterval(interval);
  }, [tenantId, taskIds]);

  return { status, loading, refetch: checkStatus };
}
</code></pre>

<hr>

<h2>🔧 Development Notes</h2>

<h3>File Upload Guidelines</h3>
<ul>
<li>Maximum file size: Check with backend team</li>
<li>Supported formats: PDF, DOC, DOCX, JPG, PNG</li>
<li>Use <code>multipart/form-data</code> for file uploads</li>
<li>Use <code>application/json</code> for other requests</li>
</ul>

<h3>Task Processing</h3>
<ul>
<li>Batch processing is asynchronous - use task monitoring</li>
<li>Tasks have 4 states: <code>queued</code>, <code>running</code>, <code>completed</code>, <code>failed</code></li>
<li>Check task status periodically (recommended: every 5-10 seconds)</li>
<li>Maximum 50 task IDs per status check request</li>
</ul>

<h3>Rate Limiting</h3>
<ul>
<li>Implement client-side rate limiting for batch operations</li>
<li>Consider exponential backoff for failed requests</li>
<li>Don't poll task status more frequently than every 5 seconds</li>
</ul>

<h3>Error Handling Best Practices</h3>
<pre><code class="language-javascript">async function safeApiCall(apiFunction) {
  try {
    const result = await apiFunction();
    
    if (!result.success) {
      throw new Error(result.error || 'API request failed');
    }
    
    return result;
  } catch (error) {
    // Log error for debugging
    console.error('API Error:', error);
    
    // Show user-friendly message
    throw new Error('Something went wrong. Please try again.');
  }
}
</code></pre>

<hr>

<p><strong>📞 Support:</strong> For any questions or issues, please contact the backend development team or create an issue in this repository.</p>
