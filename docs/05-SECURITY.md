# Snapcast MVP - Security

## Threat Model

| Threat | Likelihood | Mitigation |
|--------|------------|------------|
| Unauthorized server access | Low | Local network only, no auth in Snapcast |
| Malformed server response | Medium | Validate JSON schema, handle exceptions |
| Config file tampering | Low | QSettings uses native secure storage |
| WebSocket injection | Low | Read-only protocol, no exec |

## Security Requirements

1. **Input Validation**
   - Validate host:port from user input
   - Sanitize server responses before processing
   - Type checking on all JSON-RPC data

2. **Error Handling**
   - Never expose raw stack traces to UI
   - Log security events (connection failures)
   - Graceful degradation on protocol errors

3. **Data Storage**
   - QSettings uses platform-native secure storage
   - No passwords stored (Snapcast has no auth)
   - Config files: platform AppData locations

4. **Network Security**
   - WebSocket only (ws://, no wss:// required for local)
   - Connection timeout: 10 seconds
   - Retry limits to prevent DoS

---

## Compliance

- No personal data collected
- No internet connectivity
- Open source (MIT license)

---

*Next: [Infrastructure](docs/06-INFRASTRUCTURE.md) →*
