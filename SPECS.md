# NoxRunner Backend Specification

This document describes the interface specification for NoxRunner-compatible sandbox execution backends. Any backend that implements this specification will be compatible with the NoxRunner Python client library.

## Overview

NoxRunner is a specification for sandbox execution backends that provide isolated execution environments for running user code. The backend exposes a RESTful HTTP API that allows clients to:

- Create and manage sandbox execution environments
- Execute commands within sandboxes
- Upload and download files
- Manage sandbox lifecycle (TTL, expiration)

## Base Requirements

### HTTP Protocol

- **Protocol**: HTTP/1.1 or HTTP/2
- **Content Types**: 
  - JSON: `application/json`
  - Binary (tar archives): `application/x-tar`
- **Character Encoding**: UTF-8 for text content
- **Error Handling**: Standard HTTP status codes

### Session Management

- **Session ID**: Any string identifier provided by the client
- **Session Mapping**: Backend must maintain a stable mapping between session IDs and execution environments
- **TTL (Time To Live)**: Each sandbox has a configurable TTL that determines when it expires
- **Expiration**: Expired sandboxes should be automatically cleaned up

## API Endpoints

### 1. Health Check

**Endpoint**: `GET /healthz`

**Description**: Check if the backend is healthy and ready to accept requests.

**Request**: No body required

**Response**:
- **Status Code**: `200 OK`
- **Content-Type**: `text/plain`
- **Body**: `OK` (plain text)

**Error Responses**:
- `503 Service Unavailable`: Backend is not healthy

**Example**:
```http
GET /healthz HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: text/plain

OK
```

---

### 2. Create or Ensure Sandbox

**Endpoint**: `PUT /v1/sandboxes/{sessionId}`

**Description**: Create a new sandbox execution environment or ensure an existing one is ready. This operation is idempotent.

**Path Parameters**:
- `sessionId` (string): Unique session identifier

**Request Body** (JSON):
```json
{
  "ttlSeconds": 900,
  "image": "sandbox-runner:1.0.0",
  "cpuLimit": "1",
  "memoryLimit": "1Gi",
  "ephemeralStorageLimit": "2Gi"
}
```

**Request Fields**:
- `ttlSeconds` (integer, required): Time to live in seconds. Default: 900 (15 minutes)
- `image` (string, optional): Container image to use for the sandbox
- `cpuLimit` (string, optional): CPU limit (e.g., "1", "500m")
- `memoryLimit` (string, optional): Memory limit (e.g., "1Gi", "512Mi")
- `ephemeralStorageLimit` (string, optional): Ephemeral storage limit (e.g., "2Gi")

**Response** (JSON):
```json
{
  "podName": "sbx-abc123def4",
  "expiresAt": "2026-01-02T12:34:56Z"
}
```

**Response Fields**:
- `podName` (string): Identifier for the sandbox execution environment (backend-specific)
- `expiresAt` (string): ISO 8601 timestamp when the sandbox expires

**Status Codes**:
- `200 OK`: Sandbox created or already exists
- `400 Bad Request`: Invalid request (e.g., invalid sessionId, invalid TTL)
- `500 Internal Server Error`: Failed to create sandbox

**Example**:
```http
PUT /v1/sandboxes/my-session HTTP/1.1
Host: example.com
Content-Type: application/json

{
  "ttlSeconds": 1800,
  "image": "python:3.10",
  "cpuLimit": "1",
  "memoryLimit": "1Gi"
}

HTTP/1.1 200 OK
Content-Type: application/json

{
  "podName": "sbx-abc123def4",
  "expiresAt": "2026-01-02T12:34:56Z"
}
```

---

### 3. Touch (Extend TTL)

**Endpoint**: `POST /v1/sandboxes/{sessionId}/touch`

**Description**: Update the last active time and extend the expiration time by resetting the TTL timer.

**Path Parameters**:
- `sessionId` (string): Session identifier

**Request**: No body required

**Response**:
- **Status Code**: `200 OK`
- **Body**: Empty or success message

**Status Codes**:
- `200 OK`: TTL extended successfully
- `404 Not Found`: Sandbox not found
- `500 Internal Server Error`: Failed to update TTL

**Example**:
```http
POST /v1/sandboxes/my-session/touch HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
```

**Notes**:
- This operation should update `lastActiveAt` to the current time
- This operation should update `expiresAt` to `lastActiveAt + ttlSeconds`

---

### 4. Execute Command

**Endpoint**: `POST /v1/sandboxes/{sessionId}/exec`

**Description**: Execute a command in the sandbox execution environment.

**Path Parameters**:
- `sessionId` (string): Session identifier

**Request Body** (JSON):
```json
{
  "cmd": ["python3", "-c", "print('Hello')"],
  "workdir": "/workspace",
  "env": {
    "PYTHONUNBUFFERED": "1"
  },
  "timeoutSeconds": 30
}
```

**Request Fields**:
- `cmd` (array of strings, required): Command to execute as an array (not a shell string)
- `workdir` (string, optional): Working directory. Default: `/workspace`
- `env` (object, optional): Environment variables as key-value pairs
- `timeoutSeconds` (integer, optional): Command timeout in seconds. Default: 30

**Response** (JSON):
```json
{
  "exitCode": 0,
  "stdout": "Hello\n",
  "stderr": "",
  "durationMs": 12
}
```

**Response Fields**:
- `exitCode` (integer): Command exit code (0 = success, non-zero = failure)
- `stdout` (string): Standard output (UTF-8 encoded)
- `stderr` (string): Standard error (UTF-8 encoded)
- `durationMs` (integer): Execution duration in milliseconds

**Status Codes**:
- `200 OK`: Command executed successfully
- `400 Bad Request`: Invalid request (e.g., empty command, invalid timeout)
- `404 Not Found`: Sandbox not found
- `500 Internal Server Error`: Execution failed
- `503 Service Unavailable`: Sandbox not ready

**Example**:
```http
POST /v1/sandboxes/my-session/exec HTTP/1.1
Host: example.com
Content-Type: application/json

{
  "cmd": ["python3", "--version"],
  "workdir": "/workspace",
  "timeoutSeconds": 10
}

HTTP/1.1 200 OK
Content-Type: application/json

{
  "exitCode": 0,
  "stdout": "Python 3.10.12\n",
  "stderr": "",
  "durationMs": 45
}
```

**Notes**:
- Commands must be executed as arrays (not shell strings) for security
- `stdout` and `stderr` should be limited to a reasonable size (e.g., 1MB each)
- Environment variables are set before command execution
- Commands should be executed in isolated environments (containers, VMs, etc.)

---

### 5. Upload Files

**Endpoint**: `POST /v1/sandboxes/{sessionId}/files/upload`

**Description**: Upload files to the sandbox execution environment as a tar archive.

**Path Parameters**:
- `sessionId` (string): Session identifier

**Query Parameters**:
- `dest` (string, optional): Destination directory. Default: `/workspace`

**Request**:
- **Content-Type**: `application/x-tar`
- **Body**: Tar archive (binary, gzip-compressed)

**Response**:
- **Status Code**: `200 OK`
- **Body**: Empty or success message

**Status Codes**:
- `200 OK`: Files uploaded successfully
- `400 Bad Request`: Invalid tar archive
- `404 Not Found`: Sandbox not found
- `500 Internal Server Error`: Upload failed

**Example**:
```http
POST /v1/sandboxes/my-session/files/upload?dest=/workspace HTTP/1.1
Host: example.com
Content-Type: application/x-tar

[binary tar.gz data]

HTTP/1.1 200 OK
```

**Notes**:
- Tar archives should be gzip-compressed (`.tar.gz` format)
- Files are extracted to the destination directory
- The destination directory should be created if it doesn't exist
- File permissions should be preserved when possible

---

### 6. Download Files

**Endpoint**: `GET /v1/sandboxes/{sessionId}/files/download`

**Description**: Download files from the sandbox execution environment as a tar archive.

**Path Parameters**:
- `sessionId` (string): Session identifier

**Query Parameters**:
- `src` (string, optional): Source directory. Default: `/workspace`

**Response**:
- **Status Code**: `200 OK`
- **Content-Type**: `application/x-tar`
- **Body**: Tar archive (binary, gzip-compressed)

**Status Codes**:
- `200 OK`: Files downloaded successfully
- `404 Not Found`: Sandbox not found
- `500 Internal Server Error`: Download failed

**Example**:
```http
GET /v1/sandboxes/my-session/files/download?src=/workspace HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: application/x-tar

[binary tar.gz data]
```

**Notes**:
- Tar archives should be gzip-compressed (`.tar.gz` format)
- All files and directories in the source directory are included
- File permissions should be preserved when possible

---

### 7. Delete Sandbox

**Endpoint**: `DELETE /v1/sandboxes/{sessionId}`

**Description**: Immediately delete the sandbox execution environment.

**Path Parameters**:
- `sessionId` (string): Session identifier

**Request**: No body required

**Response**:
- **Status Code**: `204 No Content` or `200 OK`
- **Body**: Empty

**Status Codes**:
- `204 No Content`: Sandbox deleted successfully
- `200 OK`: Sandbox deleted successfully (alternative)
- `404 Not Found`: Sandbox not found (may be acceptable)
- `500 Internal Server Error`: Deletion failed

**Example**:
```http
DELETE /v1/sandboxes/my-session HTTP/1.1
Host: example.com

HTTP/1.1 204 No Content
```

**Notes**:
- This operation should immediately terminate and clean up the sandbox
- All resources associated with the sandbox should be released

---

## Error Handling

### Error Response Format

All error responses should follow a consistent format:

**JSON Error Response**:
```json
{
  "error": "Error message describing what went wrong"
}
```

**Plain Text Error Response** (for non-JSON endpoints):
```
Error message describing what went wrong
```

### HTTP Status Codes

- `200 OK`: Request succeeded
- `204 No Content`: Request succeeded, no content to return
- `400 Bad Request`: Invalid request (e.g., malformed JSON, invalid parameters)
- `404 Not Found`: Resource not found (e.g., sandbox not found)
- `500 Internal Server Error`: Server error (e.g., backend failure)
- `503 Service Unavailable`: Service temporarily unavailable (e.g., sandbox not ready)

---

## Implementation Guidelines

### Minimum Implementation Requirements

To be NoxRunner-compatible, a backend must implement:

1. ✅ Health check endpoint (`GET /healthz`)
2. ✅ Create sandbox endpoint (`PUT /v1/sandboxes/{sessionId}`)
3. ✅ Execute command endpoint (`POST /v1/sandboxes/{sessionId}/exec`)
4. ✅ Delete sandbox endpoint (`DELETE /v1/sandboxes/{sessionId}`)

### Recommended Implementation

For a complete implementation, also include:

- ✅ Touch endpoint (`POST /v1/sandboxes/{sessionId}/touch`)
- ✅ Upload files endpoint (`POST /v1/sandboxes/{sessionId}/files/upload`)
- ✅ Download files endpoint (`GET /v1/sandboxes/{sessionId}/files/download`)

### Optional Features

- Resource limits (CPU, memory, storage)
- Custom container images
- Streaming command output (future extension)
- Interactive command execution (future extension)

### Security Considerations

1. **Isolation**: Each sandbox should be isolated from other sandboxes
2. **Resource Limits**: Enforce CPU, memory, and storage limits
3. **Network Isolation**: Restrict network access (default deny, allow only necessary)
4. **File System**: Use read-only root filesystem when possible
5. **User Permissions**: Run as non-root user
6. **Command Execution**: Execute commands as arrays (not shell strings) to prevent injection

### Testing

To verify compatibility with NoxRunner:

1. Use the NoxRunner Python client library to test all endpoints
2. Verify error handling with invalid requests
3. Test concurrent requests
4. Verify TTL and expiration behavior
5. Test file upload/download with various file types

---

## Versioning

- **Current Version**: `v1`
- **API Path Prefix**: `/v1/`
- **Future Versions**: New versions may be introduced with different path prefixes (e.g., `/v2/`)

---

## Extensions and Future Considerations

### Potential Future Extensions

1. **Streaming Output**: Real-time command output via Server-Sent Events (SSE) or WebSocket
2. **Interactive Commands**: Support for commands requiring user input
3. **Authentication**: API key, OAuth, or mTLS authentication
4. **Rate Limiting**: Per-client or per-session rate limiting
5. **Metrics**: Prometheus metrics endpoint
6. **Logging**: Structured logging endpoint

### Backward Compatibility

- New optional fields in request/response bodies should not break existing clients
- New endpoints should not conflict with existing ones
- Deprecated endpoints should be maintained for a reasonable period

---

## Reference Implementation

A reference implementation is available in the `sandbox` project, which uses Kubernetes (K8s) to manage sandbox execution environments. This implementation demonstrates:

- Kubernetes Pod management
- Resource quotas and limits
- Network policies
- Pod security admission
- Automatic garbage collection

See the `sandbox` project for implementation details.

---

## License

This specification is provided under the MIT License. Implementations may use any license.

---

## Contributing

If you have suggestions for improving this specification, please open an issue or submit a pull request to the NoxRunner repository.

