# Duplex channel contracts and model-internal communication

## Motivation

Active intention should influence perception without making the current observer the only route by which the environment can provide information. Some systems expose a measurement channel; others also accept addressed requests and return responses. Those are different capabilities.

A format shared by a sensor and a source is not, by itself, proof that the source can be addressed. This module therefore separates:

- an observation schema: what the channel can emit to the observer;
- a request schema: what the observer may send to the channel;
- a response schema: what the channel may return to a correlated request;
- a protocol identifier: the shared framing/encoding language for messages.

A contract is addressable only when both request and response schemas are declared. Observation capability does not imply addressability.

## Message directions

ChannelMessage has one of three directions:

- observation: incoming, uncorrelated message supported by observation_schema;
- request: outbound request intent supported by request_schema;
- reply: incoming response supported by response_schema and correlated to an earlier request message_id.

ChannelExchangeLedger validates channel identity, protocol identity, declared direction, unique message IDs, and request/reply correlation. Replies cannot be attached to requests from another channel or protocol.

propose_request records a local request intent only; it does not transmit anything. exchange invokes a concrete ChannelAdapter, then records the request and the returned reply. If a transport fails and the request intent needs to be retained, record it with propose_request before invoking the adapter separately.

## Common protocol and distinct schemas

The protocol_id is common to both directions and identifies the wire/framing language. Request and response schema identifiers are separate because the same framing can carry different message shapes. These schema identifiers are declarations, not general JSON Schema validators; each adapter remains responsible for validating its payload semantics.

The channel contract makes read and write capabilities explicit. It does not infer outbound authority from the fact that a sensor can receive or decode a signal. Any real-world write path requires an adapter that is actually authorized to perform that operation.

## Reference adapter: querying a predictive Ground

PredictiveGroundAdapter is an internal reference implementation. It accepts a request payload containing exactly source and action, then responds using the same protocol identifier.

The reply reports one of:

- known: a single evidence-backed target and output;
- unknown: the state/action cell is absent, and no target/output is fabricated;
- ambiguous: all represented alternatives, support count, and evidence references are returned.

This is an addressable dialogue with the finite model, not a connection to a physical environment. It demonstrates the interaction contract without overstating what the current VGI can sense or actuate.

## From reply to encounter

Only inbound observations and replies can be materialized as Encounters. Outbound request intents cannot be turned into observations. The derived Encounter retains the raw message payload, original provenance, channel/protocol identity, direction, and correlation identifier.

The encounter layer remains interpretation-neutral. A reply may later be associated with other encounters; it is not automatically promoted to a Ground transition or universal fact.

## Limits and next work

- No physical sensor/actuator adapter is included.
- No source authentication or transport encryption is provided.
- Schema IDs are labels; adapter code validates request semantics.
- The reference predictive-Ground adapter can answer only about declared state/action vocabulary.
- A future source adapter should implement ChannelAdapter, declare its actual capabilities, and preserve the same request/reply provenance and correlation discipline.
