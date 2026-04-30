---
title: "REST Architecture"
category: "APIs & Protocols"
description: "What REST actually means per Fielding's dissertation, the six constraints, HATEOAS, and why most APIs aren't truly RESTful"
---

# What REST actually means, and why your API probably isn't RESTful

**REST is not "JSON over HTTP."** It is a formal architectural style defined by six constraints in Roy Fielding's 2000 doctoral dissertation, and the most important of those constraints — hypermedia as the engine of application state (HATEOAS) — is the one almost every "RESTful" API ignores entirely. Fielding himself has been publicly frustrated by this, writing in 2008: "if the engine of application state is not being driven by hypertext, then it cannot be RESTful and cannot be a REST API. Period." Understanding the gap between what REST actually requires and what the industry colloquially calls "REST" is essential for any senior engineer making architectural decisions. This report defines REST precisely, walks through each constraint with technical depth, and illustrates correct design with concrete HTTP examples.

## REST began as a theory of the web, not a spec for building APIs

Representational State Transfer was introduced in Chapter 5 of Roy Fielding's 2000 dissertation, *Architectural Styles and the Design of Network-Based Software Architectures*, at UC Irvine. Fielding co-authored the HTTP/1.1 specification, and REST is a post-hoc distillation of the architectural principles that guided HTTP's design. It was never conceived as a recipe for building web service APIs — those didn't exist yet in 2000.

Fielding derived REST by starting from **the null style** — an empty set of constraints with no distinguished boundaries between components — and incrementally adding constraints to shape the design space. The derivation path is: Null Style → Client-Server → Stateless → Cache → Uniform Interface → Layered System → Code-on-Demand (optional) = **REST**. Each constraint induces specific architectural properties while introducing known trade-offs. Fielding described this as designing by restraint rather than creativity: understanding a system's context and letting forces flow naturally.

The name itself is revealing. Fielding chose "Representational State Transfer" to evoke how a well-designed web application behaves: **a network of pages forming a virtual state machine**, where the user progresses by selecting links (state transitions), causing the next page (the next state's representation) to be transferred and rendered. This is fundamentally different from the RPC mental model most developers bring to API design.

## The six constraints that define REST

### Client-server separation

The first constraint enforces **separation of concerns** between user interface and data storage. The client handles presentation; the server handles data persistence and domain logic. This improves portability of the UI across platforms, improves scalability by simplifying server components, and — most critically for the web — allows components to **evolve independently** across organizational boundaries. A browser team and a server team can ship on different schedules without coordinating, as long as both respect the shared interface contract.

### Statelessness

Each request from client to server must contain **all information necessary to understand that request**. The server cannot rely on stored context from previous requests. Session state lives entirely on the client. Fielding was explicit about the properties this induces: **visibility** (a monitoring system can fully understand any single request in isolation), **reliability** (partial failures are easier to recover from), and **scalability** (servers can free resources immediately between requests, and any server in a cluster can handle any request). The trade-off is increased per-request overhead from repetitive data. Fielding considered HTTP cookies a violation of REST, writing that "cookie interaction fails to match REST's model of application state."

### Cacheability

Responses must be **implicitly or explicitly labeled as cacheable or non-cacheable**. When a response is cacheable, the client (or an intermediary) can reuse it for equivalent future requests. This partially or completely eliminates interactions, improving efficiency, scalability, and perceived latency. The trade-off is stale data — a cache may serve a response that no longer matches current server state. In HTTP, this is implemented through `Cache-Control`, `ETag`, `Last-Modified`, and conditional request headers like `If-None-Match`.

### Uniform interface

This is **the central feature that distinguishes REST from other network-based architectural styles**. By applying generality to the component interface, the system architecture is simplified and interaction visibility improves. Implementations decouple from the services they provide, enabling independent evolution. The trade-off is efficiency: a standardized interface is not optimal for every application's specific data transfer patterns. Fielding was clear that REST's interface is optimized for **large-grain hypermedia data transfer** — the common case of the web — and is "not optimal for other forms of architectural interaction." The uniform interface is defined by four sub-constraints, detailed in the next section.

### Layered system

Components cannot see beyond the immediate layer they interact with. A client cannot tell whether it is connected directly to an origin server or to an intermediary like a load balancer, CDN, or API gateway. This bounds overall system complexity, promotes substrate independence, enables legacy system encapsulation, and allows infrastructure like load balancers and shared caches to be inserted transparently. The trade-off is added latency from additional network hops, mitigated by shared caching at intermediaries. Combined with the uniform interface, this constraint enables intermediaries to **actively transform messages** because those messages are self-descriptive.

### Code-on-demand (optional)

Servers can extend client functionality by transferring executable code — applets, scripts, or compiled modules. This simplifies clients by reducing pre-implemented features and improves extensibility after deployment. However, it **reduces visibility** (intermediaries cannot inspect opaque code), making it the only optional REST constraint. JavaScript downloaded by browsers is the canonical example. Fielding noted that optional constraints gain benefits only when known to be in effect for a given realm of the system.

## The four sub-constraints of the uniform interface

The uniform interface is where REST gets precise and where most "RESTful" APIs diverge from the actual definition. Fielding specified four sub-constraints:

**Identification of resources.** The key abstraction in REST is a resource — any information that can be named. A document, an image, a temporal service ("today's weather in Los Angeles"), a collection, even a non-virtual object like a person. Critically, **a resource is a conceptual mapping to a set of entities, not the entity itself**. Fielding formalized this: a resource R is a temporally varying membership function M_R(t), mapping to a set of equivalent values at time t. Resources are identified by resource identifiers (URIs). The URI identifies the resource; what the resource maps to can change over time without changing the identifier.

**Manipulation of resources through representations.** Components perform actions on resources by transferring representations that capture the current or intended state of that resource. A representation is a sequence of bytes plus metadata describing those bytes. The format is selected dynamically based on the recipient's capabilities and the resource's nature. Whether the representation matches the raw source or is derived from it remains hidden behind the interface. This is why the same URI can serve JSON, XML, or HTML depending on the `Accept` header — the resource is one thing; its representations are many.

**Self-descriptive messages.** Each message includes enough information to describe how to process it: the action being requested (HTTP method), the representation format (media type via `Content-Type`), cacheability directives (`Cache-Control`), and other control data. A monitoring system or intermediary can understand any message without reference to previous messages. This constraint, combined with statelessness, is what enables the layered system constraint to work — proxies and caches can meaningfully process messages because they are self-contained.

**Hypermedia as the engine of application state (HATEOAS).** This is the most important and most ignored constraint. Application state is driven by examining the alternative state transitions present in the current representation and selecting among them. The server's response doesn't just contain data — it contains the **controls (links and forms) that drive what the client can do next**. Fielding described the model application as "an engine that moves from one state to the next by examining and choosing from among the alternative state transitions in the current set of representations." All control state is concentrated into received representations. A client needs no prior knowledge beyond an initial URI and understanding of the media types in use. Everything else is discovered at runtime through hypermedia.

## REST the style versus "RESTful" the industry term

REST, as defined by Fielding, is a **complete** set of architectural constraints. An API that satisfies all of them — including HATEOAS — is RESTful. An API that satisfies some of them is, at best, REST-like. Fielding drew this line explicitly in his 2008 blog post "REST APIs must be hypertext-driven," stating rules that include: a REST API should be entered with no prior knowledge beyond the initial URI; all application state transitions must be driven by client selection of server-provided choices present in received representations; and a REST API should spend almost all its descriptive effort defining the media types used for representing resources and driving application state.

**The industry diverged almost immediately.** The overwhelming majority of APIs labeled "RESTful" use resource-oriented URIs and HTTP verbs correctly but return plain JSON with no hypermedia links, require out-of-band documentation (OpenAPI/Swagger specs) to discover endpoints, and hardcode URL structures into clients. By Fielding's definition, these are not RESTful — they are what one commentator memorably called **"FIOH" (Fuck It, Overload HTTP)**: pragmatic use of HTTP semantics without the full architectural constraints. Fielding himself tweeted in 2019 that certain companies and authors "say REST when they know it is just HTTP; not because they don't know the meaning of the term, but because $$$ >> meaning."

The practical reality is nuanced. HATEOAS adds complexity that many teams find unjustified when the same organization controls both client and server. For short-lived, tightly-coupled systems, the full REST constraint set may be over-engineering. But Fielding designed REST for **"software design on the scale of decades"** — long-lived, multi-organization systems where independent evolution matters. If your API won't outlast your current sprint, REST's full constraints may not be for you — but then don't call it RESTful.

## The Richardson Maturity Model grades your API's RESTfulness

Leonard Richardson introduced a four-level model at QCon 2008, later popularized by Martin Fowler, that classifies APIs by how many REST mechanisms they employ. It is a useful heuristic, not an official REST metric — Richardson himself called it "very embarrassing" at RESTFest 2015. **Fowler stressed that Level 3 is a precondition of REST, not the finish line.**

**Level 0 — The swamp of POX.** A single URI endpoint, a single HTTP method (typically POST), with HTTP used purely as a transport tunnel. SOAP and XML-RPC are canonical examples. A booking system at Level 0 sends all requests to `/appointmentService` via POST, and errors return `200 OK` with error details in the body. HTTP semantics are completely ignored.

**Level 1 — Resources.** The information space is divided into individually addressable resources with distinct URIs, but all operations still use a single verb (POST). Instead of `POST /appointmentService`, you now send `POST /doctors/mjones` for queries and `POST /slots/1234` for bookings. This applies divide-and-conquer — breaking one big endpoint into many — but doesn't leverage HTTP's verb semantics.

**Level 2 — HTTP verbs.** Resources are combined with proper HTTP methods and status codes. Retrievals use `GET` (safe, cacheable), creation uses `POST` (returns **201 Created** with a `Location` header), conflicts return **409**, and so on. This is where most production APIs stop, and what the industry typically calls "RESTful." Fowler notes the key gain: strong separation between safe and non-safe operations, plus status codes communicating error semantics.

**Level 3 — Hypermedia controls.** Responses include links that tell the client what actions are available. A slot's response includes `<link rel="/linkrels/slot/book" uri="/slots/1234"/>`. After booking, the response includes links for canceling, adding tests, or changing the time — and these links change based on system state. The server can alter its URI scheme without breaking clients. This is HATEOAS, and it's the only level that begins to approach Fielding's definition of REST.

## Design patterns in practice, with HTTP on the wire

### HTTP methods carry precise semantics

Each HTTP method has defined safety and idempotency properties that must be respected:

```
GET /api/users/42 HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer eyJhbGciOi...
```
```
HTTP/1.1 200 OK
Content-Type: application/json
ETag: "a1b2c3"
Cache-Control: max-age=3600

{"id": 42, "name": "Alice Smith", "email": "alice@example.com"}
```

GET is **safe** (no side effects) and **idempotent** (repeatable with identical results). Responses are cacheable. Never use GET to mutate state.

```
POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/json

{"name": "Carol White", "email": "carol@example.com"}
```
```
HTTP/1.1 201 Created
Location: /api/users/43
Content-Type: application/json

{"id": 43, "name": "Carol White", "email": "carol@example.com"}
```

POST is **neither safe nor idempotent** — sending it twice may create two resources. The `Location` header provides the new resource's URI. Return **201 Created** for resource creation, **202 Accepted** for async processing.

PUT sends the **complete replacement** representation. It is idempotent — sending the same PUT repeatedly yields the same state. PATCH sends only the delta. Using `application/merge-patch+json` (RFC 7396), a partial update looks like:

```
PATCH /api/users/43 HTTP/1.1
Content-Type: application/merge-patch+json

{"email": "carol.new@example.com"}
```

DELETE is idempotent — deleting an already-deleted resource is a no-op. Return **204 No Content**.

### Resource URIs use nouns, never verbs

HTTP methods express the action; URIs identify the target. `GET /users` — not `GET /getUsers`. `DELETE /users/42` — not `POST /deleteUser?id=42`. Collections use plural nouns (`/users`), individual resources append an identifier (`/users/42`), and sub-resources nest one level deep (`/users/42/orders`). Query parameters handle filtering (`?status=active`), sorting (`?sort=-created`), and pagination (`?limit=25&offset=50`). Avoid nesting deeper than `collection/item/collection` — use links instead.

### Status codes communicate semantics precisely

The distinction between **400 Bad Request** and **422 Unprocessable Entity** matters: 400 means the request cannot be parsed (malformed JSON), while 422 means it parsed successfully but fails validation (negative age, invalid email format). Similarly, **401 Unauthorized** means "who are you?" (missing or invalid credentials), while **403 Forbidden** means "I know who you are, but you can't do this." **409 Conflict** signals state conflicts like duplicate unique keys or optimistic locking failures.

### Content negotiation separates resources from representations

The same resource at `/api/users/42` can produce different representations based on the `Accept` header:

```
GET /api/users/42 HTTP/1.1
Accept: application/xml
```

Returns XML. Change `Accept` to `application/json`, get JSON. The resource is one thing; its representations are many. This prevents encoding format into the URL and is a direct expression of the "manipulation through representations" sub-constraint. When the server can't satisfy the requested format, it returns **406 Not Acceptable**.

### Statelessness means no server-side sessions

Every request carries its own authentication context, typically via a JWT in the `Authorization: Bearer` header or an API key. The JWT contains the user's identity and claims; any server in the cluster can verify its signature independently. **Server-side session stores violate statelessness** because they create server affinity and require inter-node synchronization. Note: storing a JWT inside a cookie is acceptable — the cookie is a transport mechanism. What violates REST is the server-side session state the cookie traditionally references.

### HATEOAS makes the API a state machine

The most illustrative HATEOAS example is a bank account API. When the account has a positive balance, the response includes links for deposits, withdrawals, transfers, and close requests. When overdrawn, only the deposit link remains — **the available transitions change with resource state**:

```
GET /accounts/12345 HTTP/1.1
Accept: application/hal+json
```
```
HTTP/1.1 200 OK
Content-Type: application/hal+json

{
  "_links": {
    "self": {"href": "/accounts/12345"},
    "deposits": {"href": "/accounts/12345/deposits"},
    "withdrawals": {"href": "/accounts/12345/withdrawals"},
    "transfers": {"href": "/accounts/12345/transfers"}
  },
  "accountNumber": 12345,
  "balance": {"currency": "usd", "value": 100.00}
}
```

When the balance drops to -$25, the response links shrink to only `self` and `deposits`. The client never hardcodes URLs — it discovers them from responses. If the server restructures its URL scheme, clients following links continue working without modification. HAL (`application/hal+json`) is the most widely adopted hypermedia format; alternatives include Siren, JSON:API, and Collection+JSON, each with different trade-offs around embedded resources and action metadata.

## Seven misconceptions that persist across the industry

The most damaging misconception is that **any API using HTTP and returning JSON qualifies as RESTful**. JSON is not hypermedia. A JSON response with data fields but no navigational links is no more RESTful than an XML-RPC payload. Second, **REST is not CRUD-over-HTTP** — there is nothing in Fielding's dissertation about mapping HTTP verbs to create/read/update/delete operations. That mapping is a useful convention but belongs to the pragmatic "Level 2" world, not to REST itself.

Third, REST is **not a protocol, specification, or standard** — it is an architectural style. HTTP is the most common protocol used to implement REST-style systems, but REST is theoretically protocol-independent. Fourth, most "REST APIs" are architecturally **RPC** — the client must know endpoints, understand data semantics, and hardcode URL structures. Fielding identified this in 2008: "That is RPC. It screams RPC." Fifth, REST was designed for the web itself, not for web service APIs. Sixth, ignoring HATEOAS doesn't make an API "mostly RESTful" — it makes it not RESTful at all, by the originator's definition. Seventh, claiming versioned URLs like `/api/v2/users` are RESTful contradicts the principle that a REST API "must not define fixed resource names or hierarchies."

## Conclusion

REST's constraints form an **all-or-nothing architectural contract** designed for long-lived, multi-organization systems that must evolve independently over decades. The industry has adopted a useful subset — resource-oriented URIs, proper HTTP verbs, and meaningful status codes (Richardson Maturity Level 2) — and labeled it "RESTful," but this is technically a misnomer by the original definition. The critical missing piece is almost always HATEOAS: the principle that server responses drive all client navigation through hypermedia links, eliminating out-of-band coupling.

For senior engineers, the practical takeaway is not that every API must implement full HATEOAS — that carries real complexity costs — but that the architectural tradeoffs should be made consciously. If you control both client and server, ship frequently, and don't need decade-scale independent evolution, Level 2 with good documentation may serve you well. But if you're building a public API meant to survive changing server implementations, organizational boundaries, and years of client diversity, the constraints Fielding defined aren't academic overhead — they're the engineering solution to exactly that problem. Call your architecture what it is: if it lacks hypermedia, it's a well-designed HTTP API, not a REST API.