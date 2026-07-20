# Architecture Documentation

HunterOS is an operational intelligence platform.

## Event-Driven Architecture
Every action in HunterOS emits an event to the internal Event Bus. This allows decoupled components (like the Friction Engine or the Recommendations Engine) to react to business activity in real-time.

## Security Architecture
RBAC is enforced via JWT claims and explicit Permissions policies.

*More documentation to be generated via OpenAPI...*
