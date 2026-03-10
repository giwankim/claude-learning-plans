---
title: "Mastering WebSockets in Spring Boot"
category: "Spring / Real-Time"
description: "12-week curriculum covering STOMP messaging, reactive WebFlux WebSocket, Redis Pub/Sub broadcasting, Kafka integration, and AWS EKS deployment for real-time systems"
---

# Mastering WebSockets in Spring Boot: a 12-week curriculum

**This learning plan takes a mid-level Kotlin/Spring Boot engineer from WebSocket fundamentals to production-grade real-time systems running on AWS EKS with Redis and Kafka.** The curriculum is organized into six two-week phases, each ending with a concrete milestone project. It covers both traditional STOMP-based messaging and reactive WebFlux WebSocket, with explicit attention to the infrastructure realities of running stateful connections in Kubernetes. Every resource referenced is compatible with Spring Boot 3.x / Spring Framework 6.x, and Kotlin-first where available.

The plan draws on production lessons from companies operating WebSockets at massive scale — Netflix handling **10 million concurrent connections**, Slack managing **5 million+ simultaneous sessions**, Discord pushing **26 million events/second**, and Korean fintech Toss Securities delivering real-time stock quotes via Spring STOMP. These battle-tested patterns inform every phase of the curriculum.

---

## Phase 1: Protocol foundations and architectural decision-making (Weeks 1–2)

The first two weeks build the mental model that prevents costly architectural mistakes later. The single most important decision in real-time system design is **choosing the right transport** — and roughly 95% of "real-time" applications only need server-to-client push, making SSE sufficient. Understanding when WebSockets are genuinely necessary (and when they're overkill) saves months of operational complexity.

### Week 1: The WebSocket protocol and its alternatives

Start by reading RFC 6455 (the WebSocket specification) at a conceptual level — understand the HTTP upgrade handshake, frame structure, opcodes (text, binary, ping, pong, close), and the distinction between the protocol layer and application-layer subprotocols like STOMP. Then systematically compare the four real-time transport options:

**WebSocket** provides full-duplex bidirectional communication with minimal overhead after handshake. Use it for chat, collaborative editing, multiplayer games, and any scenario requiring low-latency bidirectional data flow. **Server-Sent Events (SSE)** deliver server-to-client push over standard HTTP with automatic reconnection via the `EventSource` API — LinkedIn chose SSE over WebSocket for their entire real-time delivery platform because they only needed unidirectional push. **HTTP/2 streaming** multiplexes streams over a single connection, eliminating SSE's 6-connection-per-domain limit on HTTP/1.1. **Long polling** simulates push via repeated HTTP requests and works universally but carries the highest overhead.

The critical insight: **WebSocket introduces stateful connections into your infrastructure**, which fundamentally conflicts with Kubernetes' ephemeral pod model. Every WebSocket connection binds a client to a specific pod, requiring sticky sessions, cross-pod message routing via Redis, and graceful connection draining during deployments. SSE avoids most of this complexity. Toss Securities' engineering team noted in retrospect that SSE would have been sufficient for their unidirectional stock ticker — they chose WebSocket anticipating future bidirectional needs that hadn't materialized.

Study these resources in order:

- Spring Framework WebSocket reference: `docs.spring.io/spring-framework/reference/web/websocket.html` — read the "Introduction" and "When to Use WebSockets" sections first. The docs include both Java and Kotlin code examples throughout.
- Baeldung's "Intro to WebSockets with Spring" (`baeldung.com/websockets-spring`) — updated for Spring 6.x, covers STOMP, SockJS, and JavaScript client setup.
- The Toptal article "Using Spring Boot for WebSocket Implementation with STOMP" (`toptal.com/java/stomp-spring-boot-websocket`) — an unusually thorough treatment covering server and client setup, pub-sub patterns, user-specific messaging, and security, updated January 2026.

### Week 2: Real-world use-case analysis and when NOT to use WebSockets

Study production architectures from companies that have made deliberate transport choices. Netflix's Zuul Push system handles 10M concurrent connections using both WebSocket and SSE; their key auto-scaling insight is that **CPU and RPS are useless metrics for WebSocket servers** because connections sit idle — they scale on open connection count instead. Uber migrated from the WAMP WebSocket subprotocol to GraphQL Subscriptions over WebSocket for their customer support chat, reducing error rates from **46% to 0.45%** while handling 3 million tickets per week. Woowahan Brothers (Baemin) replaced a polling-based order system that caused DB select storms with Socket.io WebSockets for their real-time rider dispatch system.

Read these engineering blog posts:

- Uber's scalable real-time chat: `uber.com/en-IN/blog/building-scalable-real-time-chat/`
- Slack's real-time messaging infrastructure: `slack.engineering/real-time-messaging/`
- Netflix's live events architecture: `netflixtechblog.com/behind-the-streams-real-time-recommendations-for-live-events-e027cb313f8f`
- Woowahan Brothers real-time service (Korean): `techblog.woowahan.com/2547/`
- Kakao's real-time comments series (3 parts): `tech.kakao.com/posts/390`, `/391`, `/392`
- Toss Securities' WebSocket for stock quotes (Slash 22 conference): `toss.im/slash-22/sessions/2-6`

**When NOT to use WebSockets**: unidirectional server-to-client updates (use SSE), low-frequency updates (polling suffices), serverless/stateless architectures (stateful connections conflict fundamentally), environments behind restrictive corporate firewalls (some packet-inspection firewalls break WebSocket traffic — Toss Securities discovered this only after launch), and scenarios requiring HTTP caching (WebSocket bypasses the cache layer entirely).

### Milestone project 1: Decision matrix document

Write a technical decision document for your team that maps six concrete use-cases (notifications, dashboards, chat, collaborative editing, financial tickers, gaming) to recommended transports. For each, specify the transport choice, justify it with production evidence from the blog posts studied, identify the key tradeoffs, and outline the infrastructure implications for your EKS/Redis/Kafka stack. This document becomes a reusable architectural reference.

---

## Phase 2: Traditional Spring WebSocket with STOMP messaging (Weeks 3–4)

### Week 3: STOMP protocol, message flow, and broker configuration

The traditional Spring WebSocket stack uses STOMP (Simple Text Oriented Messaging Protocol) as a subprotocol over WebSocket. STOMP defines frame types — CONNECT, SUBSCRIBE, SEND, ACK, DISCONNECT — and routes messages via destination prefixes. The three key prefixes to internalize: **`/app/`** routes to `@MessageMapping` controller methods, **`/topic/`** broadcasts to all subscribers (pub-sub), and **`/queue/`** delivers point-to-point. `@SendToUser` targets a specific user's queue via the `/user/` prefix.

Core configuration in Kotlin:

```kotlin
@Configuration
@EnableWebSocketMessageBroker
class WebSocketConfig : WebSocketMessageBrokerConfigurer {
    override fun configureMessageBroker(config: MessageBrokerRegistry) {
        config.enableSimpleBroker("/topic", "/queue")
        config.setApplicationDestinationPrefixes("/app")
        config.setUserDestinationPrefix("/user")
    }
    override fun registerStompEndpoints(registry: StompEndpointRegistry) {
        registry.addEndpoint("/ws").setAllowedOrigins("https://your-app.com").withSockJS()
    }
}
```

The **SimpleBrokerMessageHandler** is an in-memory broker suitable for development; it supports basic pub-sub but lacks ACK/receipt support and cannot span multiple instances. For production, you need an external broker configured via `enableStompBrokerRelay()` — this establishes a TCP connection to RabbitMQ or ActiveMQ's STOMP port. For your Redis-centric stack, the pattern is different: keep the simple broker locally but publish messages to Redis Pub/Sub for cross-instance distribution (detailed in Phase 4).

**SockJS fallback** is enabled by `.withSockJS()` and provides automatic transport downgrade: WebSocket → HTTP Streaming → HTTP Long Polling. The SockJS client sends `GET /info` to negotiate transports. Important caveat: SockJS uses iframes for some fallback transports, requiring `X-Frame-Options: SAMEORIGIN` in your Spring Security configuration. Note that **SockJS is not available in the reactive WebFlux stack** — this is a key decision factor when choosing between traditional and reactive approaches.

Study the official Spring guide: `github.com/spring-guides/gs-messaging-stomp-websocket` — clone it, run it, then convert it to Kotlin. Examine the `callicoder/spring-boot-websocket-chat-demo` repository on GitHub for a more complete chat implementation including RabbitMQ broker relay configuration.

### Week 4: Spring Security integration, user-specific messaging, and heartbeats

WebSocket security operates at two layers. **HTTP-level authentication** occurs during the handshake — the `Principal` from the HTTP session is automatically associated with the WebSocket session. For JWT-based authentication (typical in SPAs and mobile), implement a `HandshakeInterceptor` that extracts the token from query parameters, validates it, and sets the user in session attributes. For STOMP-level authorization, Spring Security 6.x provides `@EnableWebSocketSecurity` with `AuthorizationManager<Message<?>>` beans that authorize based on message destinations.

**CSRF is critical and often misunderstood**: browsers do not enforce Same Origin Policy for WebSocket connections, meaning `evil.com` can open WebSocket connections to `bank.com` using the victim's cookies. Spring Security requires a CSRF token in the STOMP CONNECT frame. Since SockJS cannot send custom HTTP headers, expose a `/csrf` REST endpoint for clients to fetch the token before connecting. Be aware of a known issue in Spring Security 6.x where `CsrfChannelInterceptor` can fail with deferred token loading (tracked in GitHub issue #12378).

Configure heartbeats to detect dead connections before TCP timeout:

```kotlin
override fun configureMessageBroker(config: MessageBrokerRegistry) {
    config.enableSimpleBroker("/topic", "/queue")
        .setHeartbeatValue(longArrayOf(10000, 10000)) // server-send, server-receive in ms
}
```

Read Baeldung's "Spring Security and WebSockets" (`baeldung.com/spring-security-websockets`) and "Send Messages to a Specific User" (`baeldung.com/spring-websockets-send-message-to-user`). Study the `xlui/WebSocketExample` repo on GitHub for auth token handling via STOMP headers with both browser and Android clients.

### Milestone project 2: Multi-room chat with authentication

Build a Kotlin Spring Boot 3.x STOMP chat application with these features: JWT authentication during WebSocket handshake, multiple chat rooms via `/topic/room/{id}`, user-to-user private messaging via `@SendToUser`, CSRF protection on STOMP CONNECT frames, SockJS fallback enabled, and heartbeat configuration. Use `SimpMessagingTemplate` for programmatic message sending from a REST endpoint (simulating a system notification). Write integration tests using Spring's `TestWebSocketStompClient`.

---

## Phase 3: Reactive WebSocket via Spring WebFlux and Kotlin coroutines (Weeks 5–6)

### Week 5: WebFlux WebSocket fundamentals and Project Reactor integration

The reactive WebSocket API in Spring WebFlux is fundamentally different from the STOMP approach: **it provides raw WebSocket access without any messaging subprotocol, message broker integration, or SockJS fallback**. You implement `WebSocketHandler` directly, working with `Flux<WebSocketMessage>` for both inbound and outbound streams. This gives you fine-grained control but requires building your own pub-sub routing, session management, and reconnection logic.

A basic Kotlin handler:

```kotlin
@Component
class EchoHandler : WebSocketHandler {
    override fun handle(session: WebSocketSession): Mono<Void> {
        val output = session.receive()
            .map { it.payloadAsText.uppercase() }
            .map { session.textMessage(it) }
        return session.send(output)
    }
}
```

Configuration uses `SimpleUrlHandlerMapping` with order `-1` (before annotated controllers) and `WebSocketHandlerAdapter`. The reactive approach runs on Reactor Netty by default, using a small number of event-loop threads rather than a thread-per-connection model. This makes it ideal for **massive concurrent connection counts** — Discord handles millions of concurrent connections using a similar event-loop architecture (though in Elixir/BEAM rather than Reactor Netty).

For broadcasting to multiple clients, use **Reactor Sinks** (which replaced the deprecated `EmitterProcessor`): `Sinks.many().multicast().onBackpressureBuffer()`. Each connected client subscribes to the sink's flux, and publishing to the sink fans out to all subscribers. Backpressure is handled through Reactor's standard operators: `onBackpressureBuffer()`, `onBackpressureDrop()`, and `limitRate()`.

Read the official reactive WebSocket docs at `docs.spring.io/spring-framework/reference/web/webflux-websocket.html` (includes Kotlin examples). Study the `luis-moral/sample-webflux-websocket-netty` repo (Spring Boot 3+, clean reactive patterns) and `RawSanj/spring-redis-websocket` (Java 21, Spring Boot 3.x WebFlux chat with reactive Redis Pub/Sub).

### Week 6: Kotlin coroutines bridge and RSocket as an alternative

Spring Framework 6.x provides first-class Kotlin coroutines support that bridges naturally with reactive types: `Mono<T>` maps to `suspend fun(): T`, `Flux<T>` maps to `Flow<T>`. For WebSocket handlers, use the `mono {}` and `asFlow()` bridges from `kotlinx-coroutines-reactor`:

```kotlin
class ChatHandler : WebSocketHandler {
    override fun handle(session: WebSocketSession): Mono<Void> = mono {
        session.receive().asFlow().collect { message ->
            // Process with coroutines — suspend functions work here
        }
    }.then()
}
```

Add dependencies: `kotlinx-coroutines-core`, `kotlinx-coroutines-reactor`, and `kotlinx-coroutines-reactive`.

**RSocket over WebSocket** deserves serious consideration as an alternative to raw WebFlux WebSocket. RSocket provides structured interaction models (request-response, fire-and-forget, request-stream, channel) with built-in backpressure, resumability, and multiplexing — essentially the reactive-native equivalent of STOMP. Spring's official Kotlin tutorial builds a chat application with RSocket over WebSocket using coroutines. Study the official guide at `github.com/spring-guides/tut-spring-webflux-kotlin-rsocket`.

**When to choose each approach:**

- **Traditional STOMP** — when you need pub-sub with broker relay, SockJS fallback, `@MessageMapping` annotation-driven development, and mature Spring Security integration. Best for teams adding real-time features to an existing Spring MVC application.
- **Reactive WebFlux WebSocket** — when your entire stack is already reactive (WebFlux, R2DBC, reactive Redis), you need raw protocol control, or you're optimizing for maximum concurrent connections with minimal threads.
- **RSocket over WebSocket** — when you want structured reactive messaging with backpressure, session resumption, and multiplexing without building your own protocol layer on top of raw WebSocket.

### Milestone project 3: Reactive stock ticker with backpressure

Build a Kotlin Spring WebFlux application that streams simulated stock prices to multiple connected clients via reactive WebSocket. Implement a `Sinks.Many` broadcaster, demonstrate backpressure handling with `onBackpressureLatest()` (appropriate for price tickers where only the latest price matters), add a Kotlin coroutines-based handler using `Flow`, and include a `ReactorNettyWebSocketClient`-based integration test. Compare connection throughput against the STOMP chat from Milestone 2 under load using a tool like `k6` or `artillery`.

---

## Phase 4: Production hardening — security, Redis, and Kafka integration (Weeks 7–8)

### Week 7: Redis Pub/Sub for multi-instance broadcasting and Kafka bridge

The fundamental scaling challenge: **WebSocket connections are bound to specific pods**. A message published on Pod A won't reach a user connected to Pod B unless you add cross-pod message routing. The production-proven pattern for your stack uses Redis Pub/Sub as the broadcast bus.

The architecture: keep Spring's in-memory STOMP broker locally on each pod, but wrap `SimpMessagingTemplate` with a service that publishes to Redis before sending locally. Every pod subscribes to the Redis channel and forwards received messages to its local WebSocket clients:

```kotlin
@Service
class RedisWebSocketBridge(
    private val redisTemplate: StringRedisTemplate,
    private val messagingTemplate: SimpMessagingTemplate,
    private val objectMapper: ObjectMapper
) {
    fun broadcast(topic: String, payload: Any) {
        val message = WebSocketMessage(topic, payload)
        redisTemplate.convertAndSend("ws-broadcast", objectMapper.writeValueAsString(message))
    }

    // Called by RedisMessageListenerContainer
    fun onRedisMessage(message: String) {
        val wsMessage = objectMapper.readValue(message, WebSocketMessage::class.java)
        messagingTemplate.convertAndSend(wsMessage.topic, wsMessage.payload)
    }
}
```

**Redis Pub/Sub vs Redis Streams**: Pub/Sub delivers sub-millisecond latency with fire-and-forget semantics — perfect for ephemeral WebSocket notifications. Redis Streams provides persistent append-only logs with consumer groups for guaranteed delivery — use this if you need to replay missed messages after client reconnection. For most WebSocket broadcasting, **Pub/Sub is the right choice**; add Streams only for the reconnection gap-fill use case.

For Kafka integration, the primary pattern is a **Kafka consumer → WebSocket push bridge**: backend microservices publish domain events to Kafka topics, and your WebSocket server consumes from Kafka and pushes to connected clients via STOMP:

```kotlin
@Service
class KafkaWebSocketBridge(private val messagingTemplate: SimpMessagingTemplate) {
    @KafkaListener(topics = ["order-events"], groupId = "websocket-push")
    fun onOrderEvent(event: String) {
        messagingTemplate.convertAndSend("/topic/orders", event)
    }
}
```

For the reactive stack, use **Reactor Kafka** (`spring-cloud-stream-binder-kafka-reactive`) for end-to-end non-blocking processing with automatic backpressure — the consumer pauses/resumes based on downstream WebSocket send capacity.

Study the `RawSanj/spring-redis-websocket` repo (WebFlux + reactive Redis Pub/Sub), the `ivangfr/springboot-kafka-websocket` repo on GitHub, and the DZone article "Live Dashboard Using Apache Kafka and Spring WebSocket."

### Week 8: Connection lifecycle, error handling, and observability

**Connection lifecycle management** requires attention at both server and client sides. On the server, implement a `WebSocketHandlerDecorator` or STOMP `ChannelInterceptor` to track sessions in a concurrent map, register connection metadata in Redis (user ID → pod ID → session ID mapping), and clean up on disconnect. On the client, implement exponential backoff with jitter for reconnection — the jitter prevents thundering herd when a pod restarts and thousands of clients reconnect simultaneously. Discord's approach uses sequence numbers in messages so clients can resume sessions and request missed messages.

Spring Boot exposes built-in WebSocket metrics via Actuator: `websocket.sessions.current`, `websocket.sessions.abnormallyClosed` (indicates proxy/network issues), and `websocket.sessions.sendLimitExceeded` (slow clients). Monitor `clientInboundChannel` and `clientOutboundChannel` thread pool stats — task queueing on these channels indicates your application can't keep up with message volume. Add custom Micrometer gauges for active connections and histograms for message latency:

```kotlin
@Component
class WebSocketMetrics(registry: MeterRegistry) {
    private val activeConnections = AtomicInteger(0)
    init {
        Gauge.builder("websocket.connections.active", activeConnections) { it.get().toDouble() }
            .description("Current active WebSocket connections")
            .register(registry)
    }
    fun opened() = activeConnections.incrementAndGet()
    fun closed() = activeConnections.decrementAndGet()
}
```

Export metrics to Prometheus via `/actuator/prometheus` and build Grafana dashboards tracking: active connections (gauge, the primary autoscaling signal), messages/second (counter), message latency p50/p99 (histogram), send buffer overflows (counter), and Kafka consumer lag for your WebSocket bridge consumer group.

For error handling, implement `StompSubProtocolErrorHandler` to catch message processing errors and return STOMP ERROR frames to clients. Log all abnormal session closures with close codes for debugging.

### Milestone project 4: Scaled chat with Redis broadcasting and Kafka events

Extend the Milestone 2 chat application: add Redis Pub/Sub for cross-instance message broadcasting, a Kafka consumer bridge that pushes system notifications to chat rooms, custom Micrometer metrics for active connections and message throughput, a `StompSubProtocolErrorHandler`, and client-side reconnection with exponential backoff and jitter. Run two instances locally behind an nginx reverse proxy with sticky sessions to verify cross-instance messaging works.

---

## Phase 5: AWS EKS infrastructure and horizontal scaling (Weeks 9–10)

### Week 9: Load balancer configuration and Kubernetes deployment

**AWS ALB is the recommended load balancer for WebSocket on EKS.** ALB automatically detects HTTP upgrade requests and maintains the WebSocket connection. A critical detail: ALB provides inherent stickiness for WebSocket — once the upgrade handshake succeeds with a target, all subsequent frames route to that target without additional cookie configuration. However, **the default idle timeout is 60 seconds**, which will kill quiescent WebSocket connections. Increase it to at least 3600 seconds (matching your heartbeat interval):

```yaml
# Target group attributes
stickiness.enabled: "true"
stickiness.type: app_cookie
stickiness.app_cookie.cookie_name: WEBSOCKET_SESSION
idle_timeout.timeout_seconds: "3600"
deregistration_delay.timeout_seconds: "30"
```

For NGINX Ingress Controller (common in EKS), WebSocket works out of the box but **you must increase proxy timeouts** from the 60-second default:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "WS_AFFINITY"
spec:
  rules:
  - host: ws.your-app.com
    http:
      paths:
      - path: /ws
        pathType: Prefix
        backend:
          service:
            name: websocket-service
            port:
              number: 8080
```

**Health checks must never depend on external services for liveness probes** — this causes cascading restart loops when Redis or Kafka is temporarily unavailable. Use a lightweight liveness endpoint that checks only JVM health. Readiness probes can verify Redis and Kafka connectivity since failing readiness only removes the pod from the service endpoint without restarting it.

**Graceful shutdown** is critical for WebSocket pods. Configure Spring Boot's graceful shutdown with a drain period:

```yaml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

Add a `@PreDestroy` handler that sends WebSocket close frames to all connected clients before the pod terminates. Combine with Kubernetes' `terminationGracePeriodSeconds: 60` and `preStop` lifecycle hooks to ensure the pod is removed from the service before connections are drained.

AWS published a reference architecture for scaling WebSocket on EKS that recommends offloading connection handling to **Amazon API Gateway** for very large deployments (100K+ connections), using KEDA for autoscaling the backend pods: `aws.amazon.com/blogs/containers/optimize-websocket-applications-scaling-with-api-gateway-on-amazon-eks/`. Study the `aws-samples/websocket-eks` GitHub repository for a complete EKS deployment example.

### Week 10: Autoscaling, rolling deployments, and operational runbooks

**Scale on connection count, not CPU or RPS.** Netflix learned this lesson at 10M connections — WebSocket servers sit at low CPU utilization because connections are idle most of the time. Configure a custom HPA metric using your Prometheus `websocket.connections.active` gauge:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: websocket-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: websocket-deployment
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Pods
    pods:
      metric:
        name: websocket_connections_active
      target:
        type: AverageValue
        averageValue: "5000"  # Scale when avg connections per pod exceeds 5K
```

**Rolling deployments cause reconnect storms.** When a pod terminates during deployment, all its WebSocket clients reconnect simultaneously to remaining pods. Mitigations: use `maxSurge: 1, maxUnavailable: 0` to ensure new pods are ready before old ones drain; implement client-side reconnection with jitter (random delay spread across seconds); and Netflix's approach of periodically terminating a small percentage of connections to prevent all clients from being concentrated on long-lived pods.

Each WebSocket connection consumes approximately **1–2 KB base memory** plus message buffers. At 10K connections per pod with 4 KB average buffer, that's ~60 MB just for connection state. Size your pod memory requests accordingly, accounting for JVM heap, thread stacks (each thread ≈1 MB), and Netty's direct memory buffers for the reactive stack.

Build operational runbooks for: connection storm response (increase HPA max, add jitter to client reconnection), Redis Pub/Sub failure (degrade to local-only broadcasting with a circuit breaker), Kafka consumer lag spike (check WebSocket send buffer saturation), and pod OOMKill debugging (correlate with connection count spikes).

### Milestone project 5: Full EKS deployment with load testing

Deploy the Milestone 4 application to EKS (or a local Kind/k3d cluster simulating EKS): 3 replicas behind NGINX Ingress with sticky sessions, Redis for cross-pod Pub/Sub, Kafka for event bridge, Prometheus + Grafana dashboards for WebSocket metrics, and custom HPA based on connection count. Run a load test using `k6` WebSocket support to simulate 5,000 concurrent connections with message exchanges. Verify that: messages reach all subscribers across pods, graceful shutdown sends close frames before pod termination, reconnecting clients resume within 5 seconds, and HPA scales up when connection threshold is breached.

---

## Phase 6: Capstone and advanced patterns (Weeks 11–12)

### Week 11: Advanced patterns — collaborative editing and event sourcing

Study how production systems handle the hardest WebSocket use-cases. **Collaborative editing** requires Operational Transformation (OT) or CRDT algorithms on top of WebSocket transport — the WebSocket layer is the easy part; conflict resolution is the hard part. **Event sourcing with WebSocket** combines Kafka as the event store with WebSocket as the delivery mechanism, enabling clients to replay events from any point in time by maintaining sequence numbers (Discord's approach to session resumption).

Explore LINE's architecture for their LINE LIVE chat: WebSocket for bidirectional messaging, **Akka actors** for high-concurrency message routing (one UserActor per user, one ChatRoomActor per room), and Redis Cluster for both temporary storage and inter-server pub/sub synchronization. This actor-per-entity pattern maps well to Kotlin coroutines — each coroutine can serve as a lightweight "actor" managing state for one user or room.

Read Slack's post-mortem on losing 1.6 million WebSocket connections in 2 minutes due to a cascading failure in their Flannel edge cache (`slack.engineering/flannel-an-application-level-edge-cache-to-make-slack-scale/`). Key takeaway: admission control and circuit breakers on the WebSocket connection path are not optional at scale. Also study Discord's optimization that reduced WebSocket traffic by **40%** using Zstandard streaming compression and delta updates for inactive users.

### Week 12: Capstone project and portfolio documentation

Build a **real-time order tracking dashboard** that demonstrates the full stack:

- **Backend**: Kotlin Spring Boot 3.x with both a STOMP endpoint (for browser clients with SockJS fallback) and a reactive WebFlux WebSocket endpoint (for mobile/high-performance clients)
- **Event pipeline**: Order service publishes events to Kafka → WebSocket server consumes and pushes to clients, with Redis Pub/Sub for multi-instance fanout
- **Security**: JWT authentication on WebSocket handshake, CSRF on STOMP CONNECT, origin checking, message-level authorization
- **Infrastructure**: Kubernetes manifests with NGINX Ingress (WebSocket-configured), HPA on connection count, Prometheus metrics, Grafana dashboard
- **Resilience**: Client reconnection with exponential backoff and jitter, graceful pod shutdown with connection draining, circuit breaker on Redis Pub/Sub failure degrading to local-only mode
- **Observability**: Active connections gauge, message throughput counter, message latency histogram, Kafka consumer lag monitoring

This capstone synthesizes every concept from the curriculum into a production-representative system.

---

## Curated resource library organized by phase

### Books (prioritized for Kotlin + Spring Boot 3.x)

- **Pro Spring Boot 3 with Kotlin** by Peter Späth and Felipe Gutierrez (Apress, 2025) — the single most relevant book, covering reactive Spring with Kotlin including a dedicated chapter on Spring Boot reactive patterns
- **Pro Java Clustering and Scalability** by Jorge Acetozi (Apress) — directly covers horizontally scaling WebSocket chat applications using a full STOMP broker with RabbitMQ, the closest book to production WebSocket patterns
- **Spring Boot in Practice** by Somnath Musib (Manning) — problem-solution format with Kotlin coverage and practical WebSocket recipes

### Online courses (verified current)

- **LinkedIn Learning**: "Building Real-Time Web Apps with Spring Boot and WebSockets" by Shonna Smith — focused STOMP/SockJS implementation course, good for Phase 2
- **Udemy**: "Reactive Redis Masterclass for Java Spring Boot Developers" — covers Spring WebFlux WebSocket with Redis Pub/Sub for real-time chat (4.7 rating), directly relevant for Phases 3 and 4
- **Udemy**: "WhatsApp Clone: Spring Boot, Angular, Keycloak & WebSocket" — full-stack project with Keycloak authentication, good for Phase 2 security concepts
- **Udemy**: "Spring RSocket Masterclass" — covers RSocket as a WebSocket-compatible reactive protocol, relevant for Phase 3's RSocket exploration

### Conference talks (available on YouTube)

- **"Full Stack Reactive with Spring WebFlux, WebSockets, and React"** — Josh Long live-coding session demonstrating the reactive WebSocket + frontend stack
- **"Bootiful Spring Boot 3"** — Josh Long at Devoxx 2023, covering Spring Boot 3 features including WebSocket improvements and virtual thread support
- **Spring Framework 6 / Spring Boot 3 introductions** — Stéphane Nicoll and Brian Clozel at Devoxx Belgium 2022, establishing the Spring Boot 3.x baseline

Search the **SpringDeveloper** YouTube channel for SpringOne and Spring I/O recordings, and the **Devoxx** channel for conference talks.

### GitHub repositories (organized by learning phase)

- **Phase 2**: `spring-guides/gs-messaging-stomp-websocket` (official), `callicoder/spring-boot-websocket-chat-demo` (popular chat with RabbitMQ relay)
- **Phase 3**: `spring-guides/tut-spring-webflux-kotlin-rsocket` (official Kotlin + RSocket), `luis-moral/sample-webflux-websocket-netty` (clean Spring Boot 3+ reactive patterns)
- **Phase 4**: `RawSanj/spring-redis-websocket` (WebFlux + reactive Redis Pub/Sub, Java 21), `ivangfr/springboot-kafka-websocket` (Kafka + WebSocket bridge)
- **Phase 5**: `aws-samples/websocket-eks` (AWS reference architecture)

### Korean tech company resources

Toss Securities' Slash 22 talk on WebSocket for real-time stock quotes provides especially valuable lessons for Spring STOMP production deployments — connection leak debugging, firewall compatibility issues, and routing server patterns with Redis. Kakao's three-part series on real-time comments covers WebSocket stress testing and Spring concurrency challenges at 600K DAU. Woowahan Brothers' tech blog post on their rider dispatch system documents the transition from polling to WebSocket with practical lessons on when HTTP fallback is necessary. LINE Engineering's architecture for LINE LIVE chat demonstrates the Redis Cluster pattern for inter-server WebSocket synchronization that directly applies to your EKS deployment.

---

## Conclusion: the three decisions that matter most

After 12 weeks, the curriculum converges on three architectural decisions that determine the success of any Spring Boot WebSocket deployment on Kubernetes. **First, transport selection**: use STOMP for most applications (annotation-driven development, broker relay, SockJS fallback, mature security), reactive WebFlux WebSocket only when your entire stack is already reactive and you need maximum connection density, and SSE whenever unidirectional push is sufficient — which is more often than engineers expect. **Second, cross-pod routing**: Redis Pub/Sub as the broadcast bus with connection metadata in Redis is the production-proven pattern; Kafka serves as the durable event backbone feeding into your WebSocket servers, not as the real-time fan-out layer. **Third, operational resilience**: scale on connection count not CPU, implement client-side reconnection with jitter from day one, and design every component assuming the pod holding your WebSocket connections will die without warning — because in Kubernetes, it will.