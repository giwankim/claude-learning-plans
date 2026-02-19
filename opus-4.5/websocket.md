---
title: "WebSockets"
category: "APIs & Protocols"
description: "Real-time communication with STOMP and Spring WebSocket"
---

# Mastering WebSockets as a Kotlin Spring Boot developer

**This three-phase curriculum takes an experienced Spring Boot Kotlin developer from protocol-level understanding through production-grade WebSocket mastery.** The plan emphasizes architectural trade-offs and decision-making over surface-level API usage. Each phase builds on the previous, with concrete milestones, Kotlin code patterns, and hands-on projects. Budget roughly 2–3 weeks per phase for deep engagement, or compress to weekends-only over 2–3 months.

---

## Phase 1: Protocol foundations and the real-time landscape

The goal of Phase 1 is to understand WebSockets at the wire level and build a mental model for when they're the right tool. Most developers skip this and pay for it later with poor architectural decisions.

### The WebSocket protocol from the ground up

Start with RFC 6455 itself — not a tutorial about it, the actual spec. WebSocket was finalized in **December 2011** by Ian Fette and Alexey Melnikov to solve a specific problem: the "real-time web" before WebSockets was a mess of hacks. Comet patterns (coined by Alex Russell in 2006), hidden iframes, XHR long polling, and script-tag tricks all tried to simulate server-initiated communication. They all suffered from HTTP's fundamental constraint: **the client must initiate every exchange**.

WebSocket solves this with a single persistent TCP connection that supports **full-duplex communication** — either side can send data at any time without waiting for a request. The overhead drops from ~700–800 bytes of HTTP headers per exchange to **2–14 bytes** per WebSocket frame.

**Study the handshake deeply.** The connection begins as a standard HTTP/1.1 request with specific upgrade headers:

```
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

The server responds with `101 Switching Protocols` and computes `Sec-WebSocket-Accept` as `Base64(SHA-1(Key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))`. This magic GUID is hardcoded in the RFC. The mechanism verifies both peers speak WebSocket — it provides no authentication. After the 101 response, the connection is no longer HTTP; it becomes a bidirectional binary pipe.

**Master the frame format.** Every WebSocket message is wrapped in frames with a FIN bit (marks final fragment), 4-bit opcode (`0x1` text, `0x2` binary, `0x8` close, `0x9` ping, `0xA` pong), a MASK bit (must be 1 for client-to-server, 0 for server-to-client), and variable-length payload. Client frames are XOR-masked with a 4-byte key to prevent cache-poisoning attacks on intermediary proxies. Control frames (close, ping, pong) are limited to **125 bytes** and cannot be fragmented.

**Key concepts to internalize:**
- `ws://` (port 80) and `wss://` (port 443, TLS) URI schemes
- Sub-protocols (like STOMP, MQTT) define application semantics over WebSocket, negotiated via `Sec-WebSocket-Protocol`
- Extensions (like `permessage-deflate` per RFC 7692) modify the framing itself, negotiated via `Sec-WebSocket-Extensions`
- Message fragmentation: a multi-frame message starts with FIN=0 and a non-zero opcode, continues with FIN=0/opcode=0 frames, and ends with FIN=1/opcode=0

### When WebSockets are the right choice — and when they aren't

A critical heuristic from production experience: **~95% of "real-time" features only need server-to-client push**. Only ~5% truly require bidirectional communication. This matters because simpler alternatives exist for the 95%.

WebSockets are the right tool when you need **bidirectional, low-latency, persistent communication from a browser**: real-time chat (Slack, Discord), collaborative editing (Google Docs, Figma), multiplayer gaming, financial trading platforms with order execution feedback, and IoT dashboards where commands and telemetry flow simultaneously.

WebSockets are the wrong tool for simple CRUD APIs, infrequent updates (hourly reports), server-to-client-only streaming (news feeds, LLM token streaming — SSE is simpler), file uploads/downloads (HTTP handles this with chunked transfer and CDN support), and any scenario where the added statefulness and operational complexity isn't justified.

### Alternatives: a deep comparative analysis

Understanding alternatives is what separates an architect from a framework user. Study each one:

**Server-Sent Events (SSE)** deserve the most attention as WebSocket's closest competitor. SSE uses a standard HTTP connection with `Content-Type: text/event-stream`. The browser's `EventSource` API provides **automatic reconnection** with `Last-Event-ID` for resumption — something you must build manually with WebSockets. SSE works transparently through corporate proxies, CDNs, and firewalls because it's standard HTTP. The limitations: unidirectional (server-to-client only), text-only (binary requires base64 at ~33% overhead), and **6 connections per domain on HTTP/1.1** (largely solved by HTTP/2's ~100 concurrent streams). SSE is underrated — it's the right choice for dashboards, notifications, live feeds, and streaming AI responses.

**Long polling** establishes a request that the server holds open until data is available or a timeout (20–60 seconds) is reached. Average latency is one network round trip, but worst-case is three (response → new request → response). Each cycle carries full HTTP header overhead. It has an interesting scaling property: connections naturally drain at timeout intervals, meaning autoscaling groups rebalance within the timeout period, unlike sticky WebSocket connections.

**Short polling** (fixed-interval HTTP requests) is the simplest possible approach. Average latency equals half the polling interval. It wastes bandwidth on empty responses but requires zero server-side complexity. Use it when updates are infrequent and freshness tolerance is high.

**HTTP/2 Server Push is effectively dead.** Chrome 106 disabled it by default (October 2022), Nginx 1.25.1 removed it entirely (June 2023), and Firefox 132 dropped support (October 2024). It was designed for preloading static assets, not real-time data — and even for that use case, it was used in only **0.04% of sessions**. Replaced by `103 Early Hints` and `<link rel="preload">`.

**gRPC bidirectional streaming** excels for backend-to-backend communication with strongly typed protobuf contracts and HTTP/2 multiplexing. However, browsers cannot use native gRPC. The grpc-web adapter requires a mandatory proxy (typically Envoy) and **does not support bidirectional streaming from browsers** — only unary and server streaming. This makes gRPC a poor WebSocket replacement for browser-facing real-time features.

**WebTransport** is the most promising future alternative, built on HTTP/3 and QUIC. It offers multiplexed streams (no head-of-line blocking), unreliable datagrams (ideal for gaming), 0-RTT connection establishment, and connection migration across network changes. Browser support reached ~82% globally, but **Safari has no support** — a showstopper for consumer-facing apps. Server-side support remains experimental.

#### Decision framework

| Criterion | WebSocket | SSE | Long Polling | gRPC Streaming | WebTransport |
|---|---|---|---|---|---|
| **Direction** | Bidirectional | Server → Client | Half-duplex | Bidirectional (backend only) | Bidirectional |
| **Latency** | Very low | Low | Medium-high | Very low | Lowest |
| **Browser support** | 99%+ | 97%+ | 100% | Limited (proxy required) | ~82% (no Safari) |
| **Proxy/firewall** | Sometimes blocked | Transparent | Transparent | May need proxy | Emerging |
| **Auto-reconnect** | Manual | Built-in | Manual | Manual | Manual |
| **Scalability** | Hard (sticky) | Easy (HTTP infra) | Medium | Medium | Good (QUIC) |
| **Binary data** | Yes | No (text only) | Via HTTP | Yes (protobuf) | Yes |
| **CDN friendly** | No | Yes | Yes | No | Emerging |

**The decision flowchart:** Need server-to-client only? → SSE. Need bidirectional from browsers? → WebSocket. Backend-to-backend with typed contracts? → gRPC. Need multiplexing or unreliable delivery and Safari isn't required? → WebTransport. Can't support persistent connections? → Long polling. Infrequent, low-freshness updates? → Short polling.

### Phase 1 milestone

Build a raw WebSocket echo server (no Spring) using a minimal library to understand the protocol at the TCP level. Use `wscat` or browser DevTools to inspect upgrade headers and frame exchanges. Then, build the same thing using SSE and compare the developer experience, reconnection behavior, and proxy compatibility. Document your findings as a trade-off matrix for your team.

---

## Phase 2: Spring's WebSocket ecosystem in Kotlin

Phase 2 covers the three layers of Spring WebSocket support — raw handlers, STOMP messaging, and reactive WebFlux — plus security, SockJS fallback, and configuration.

### Raw WebSocket with `WebSocketHandler`

The lowest level of Spring WebSocket support uses `TextWebSocketHandler` or `BinaryWebSocketHandler`. You implement lifecycle methods and manage sessions manually. This is the right choice when you need full control over the protocol, are implementing a custom sub-protocol, or STOMP's pub/sub model doesn't fit.

```kotlin
@Configuration
@EnableWebSocket
class WebSocketConfig : WebSocketConfigurer {
    override fun registerWebSocketHandlers(registry: WebSocketHandlerRegistry) {
        registry.addHandler(echoHandler(), "/ws/echo")
            .setAllowedOrigins("https://example.com")
            .addInterceptors(HttpSessionHandshakeInterceptor())
    }

    @Bean
    fun echoHandler(): WebSocketHandler = EchoWebSocketHandler()
}

class EchoWebSocketHandler : TextWebSocketHandler() {
    private val sessions = CopyOnWriteArrayList<WebSocketSession>()

    override fun afterConnectionEstablished(session: WebSocketSession) {
        // Wrap for thread-safe sending — JSR-356 forbids concurrent sends
        val safe = ConcurrentWebSocketSessionDecorator(session, 1000, 512 * 1024)
        sessions.add(safe)
    }

    override fun handleTextMessage(session: WebSocketSession, message: TextMessage) {
        session.sendMessage(TextMessage("Echo: ${message.payload}"))
    }

    override fun afterConnectionClosed(session: WebSocketSession, status: CloseStatus) {
        sessions.removeIf { it.id == session.id }
    }
}
```

**Key detail:** `ConcurrentWebSocketSessionDecorator` is essential. The JSR-356 WebSocket API does not allow concurrent sends — without this wrapper, two threads calling `sendMessage()` simultaneously will corrupt frames. The constructor takes the session, a send-time limit (ms), and a buffer-size limit (bytes).

### STOMP over WebSocket: Spring's messaging abstraction

STOMP (Simple Text Oriented Messaging Protocol) is where most Spring WebSocket applications live. It layers pub/sub messaging semantics on top of WebSocket, giving you destination-based routing, message broker integration, and annotation-driven controllers.

**Understand the message flow:** Client sends a STOMP frame → `StompSubProtocolHandler` decodes it → message enters `clientInboundChannel` → if the destination starts with the app prefix (e.g., `/app`), it routes to `@MessageMapping` controllers; if it starts with the broker prefix (e.g., `/topic`, `/queue`), it routes directly to the message broker → controller return values go through `brokerChannel` → message broker → `clientOutboundChannel` → clients.

```kotlin
@Configuration
@EnableWebSocketMessageBroker
class StompConfig : WebSocketMessageBrokerConfigurer {
    override fun configureMessageBroker(registry: MessageBrokerRegistry) {
        registry.enableSimpleBroker("/topic", "/queue")
            .setHeartbeatValue(longArrayOf(10000, 10000))
            .setTaskScheduler(heartbeatScheduler())
        registry.setApplicationDestinationPrefixes("/app")
        registry.setUserDestinationPrefix("/user")
    }

    override fun registerStompEndpoints(registry: StompEndpointRegistry) {
        registry.addEndpoint("/ws/chat")
            .setAllowedOriginPatterns("*")
            .withSockJS()
    }

    @Bean
    fun heartbeatScheduler(): TaskScheduler {
        return ThreadPoolTaskScheduler().apply {
            poolSize = 1
            setThreadNamePrefix("ws-heartbeat-")
        }
    }
}

data class ChatMessage(val from: String, val text: String, val timestamp: Long = System.currentTimeMillis())

@Controller
class ChatController(private val messagingTemplate: SimpMessagingTemplate) {
    @MessageMapping("/chat.send")
    @SendTo("/topic/public")
    fun sendMessage(@Payload message: ChatMessage): ChatMessage = message

    @MessageMapping("/chat.private")
    fun sendPrivateMessage(@Payload message: PrivateMessage, principal: Principal) {
        messagingTemplate.convertAndSendToUser(
            message.to, "/queue/private",
            ChatMessage(from = principal.name, text = message.text)
        )
    }
}
```

**Critical distinction — simple broker vs. external broker:** The in-memory `enableSimpleBroker()` supports a subset of STOMP and works only on a single instance. For any multi-instance deployment, you must use `enableStompBrokerRelay()` to connect to an external STOMP broker (RabbitMQ with the STOMP plugin on port 61613, ActiveMQ, or Apache Artemis). The relay, implemented by `StompBrokerRelayMessageHandler`, establishes TCP connections to the broker and forwards all messages bidirectionally. This requires the `reactor-netty` dependency.

For multi-instance user destinations, `MultiServerUserRegistry` broadcasts local user registries to a shared topic so `convertAndSendToUser()` resolves users connected to any instance. Configure via `setUserDestinationBroadcast("/topic/user-registry")` and `setUserRegistryBroadcast("/topic/simp-user-registry")`.

### Reactive WebSocket with WebFlux

WebFlux WebSocket is a fundamentally different programming model — built on Project Reactor with `Flux` and `Mono`, non-blocking, and running on Netty by default. **WebFlux has no built-in STOMP support** — it's a lower-level API where you handle streams directly.

```kotlin
@Component
class ReactiveChatHandler : WebSocketHandler {
    private val sink: Sinks.Many<String> = Sinks.many().multicast().onBackpressureBuffer()
    private val outputMessages: Flux<String> = sink.asFlux()

    override fun handle(session: WebSocketSession): Mono<Void> {
        val input = session.receive()
            .map { it.payloadAsText }
            .doOnNext { msg -> sink.tryEmitNext(msg) }
            .then()

        val output = session.send(
            outputMessages.map { session.textMessage(it) }
        )
        return Mono.zip(input, output).then()
    }
}

@Configuration
class WebFluxWebSocketConfig(private val chatHandler: ReactiveChatHandler) {
    @Bean
    fun webSocketHandlerAdapter() = WebSocketHandlerAdapter()

    @Bean
    fun handlerMapping(): HandlerMapping {
        return SimpleUrlHandlerMapping(mapOf("/ws/chat" to chatHandler), -1)
    }
}
```

Choose WebFlux WebSocket when you're already on the reactive stack, need fine-grained backpressure control, or need to integrate with reactive data sources (R2DBC, reactive Kafka). Choose servlet-based STOMP when you want the higher-level messaging abstraction with annotation-driven controllers.

### Securing WebSocket connections

Security is where many WebSocket implementations fail. WebSocket connections reuse authentication from the initial HTTP upgrade request — the `Principal` from `HttpServletRequest` carries over to `WebSocketSession`. This means you secure the handshake endpoint through standard Spring Security HTTP configuration.

For STOMP-level authorization, `@EnableWebSocketSecurity` provides message-level security:

```kotlin
@Configuration
@EnableWebSocketSecurity
class WebSocketSecurityConfig {
    @Bean
    fun messageAuthorizationManager(
        messages: MessageMatcherDelegatingAuthorizationManager.Builder
    ): AuthorizationManager<Message<*>> {
        messages
            .simpTypeMatchers(SimpMessageType.CONNECT).authenticated()
            .simpDestMatchers("/app/**").hasRole("USER")
            .simpSubscribeDestMatchers("/topic/admin/**").hasRole("ADMIN")
            .anyMessage().denyAll()
        return messages.build()
    }
}
```

**Token-based auth (JWT) requires a specific pattern** because the browser WebSocket API does not support custom headers after the initial handshake. The most secure approach is sending the JWT in the STOMP CONNECT frame headers and validating it with a custom `ChannelInterceptor` on `clientInboundChannel`:

```kotlin
override fun configureClientInboundChannel(registration: ChannelRegistration) {
    registration.interceptors(object : ChannelInterceptor {
        override fun preSend(message: Message<*>, channel: MessageChannel): Message<*>? {
            val accessor = MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor::class.java)
            if (accessor?.command == StompCommand.CONNECT) {
                val token = accessor.getFirstNativeHeader("Authorization")
                accessor.user = validateAndGetAuthentication(token)
            }
            return message
        }
    })
}
```

**Always validate the Origin header** with an explicit allowlist — browsers include it automatically and malicious JavaScript cannot override it. This prevents Cross-Site WebSocket Hijacking (CSWSH).

### SockJS: still relevant for edge cases

SockJS emulates the WebSocket API with automatic fallback to HTTP streaming or long polling when native WebSocket is unavailable. It was critical for IE 8/9 support but remains relevant behind **restrictive corporate proxies** that terminate long-lived connections or block WebSocket upgrades. Enable it with `.withSockJS()` on your endpoint registration. SockJS adds its own heartbeat (default 25 seconds) and message framing (`o` for open, `a[...]` for message arrays, `h` for heartbeat, `c` for close).

### Phase 2 milestone

Build a complete STOMP-based chat application with: public rooms (`/topic/room.{id}`), private messaging (`/user/queue/messages`), JWT authentication via STOMP CONNECT headers, message-level authorization, and reconnection handling. Write integration tests using `WebSocketStompClient`:

```kotlin
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ChatIntegrationTest {
    @LocalServerPort private var port: Int = 0
    private val received = LinkedBlockingDeque<String>()

    @Test
    fun `should broadcast message to subscribers`() {
        val client = WebSocketStompClient(SockJsClient(listOf(WebSocketTransport(StandardWebSocketClient()))))
        client.messageConverter = MappingJackson2MessageConverter()
        val session = client.connectAsync("ws://localhost:$port/ws/chat", StompSessionHandlerAdapter())
            .get(5, TimeUnit.SECONDS)

        session.subscribe("/topic/public", object : StompFrameHandler {
            override fun getPayloadType(headers: StompHeaders) = String::class.java
            override fun handleFrame(headers: StompHeaders, payload: Any?) {
                received.add(payload as String)
            }
        })
        session.send("/app/chat.send", """{"from":"test","text":"hello"}""")
        assertThat(received.poll(5, TimeUnit.SECONDS)).contains("hello")
    }
}
```

---

## Phase 3: Production mastery and operational excellence

Phase 3 is about everything that happens after `./gradlew bootRun` — scaling, monitoring, load balancing, security hardening, graceful degradation, and operational confidence.

### Connection management at scale

Every WebSocket connection consumes a file descriptor and memory. Budget **20–50 KB per idle connection** depending on your framework, with more for active connections with message queues. The permessage-deflate extension alone consumes ~64 KB per connection; disabling it drops usage to ~14 KB.

**OS-level tuning is non-negotiable.** Default file descriptor limits (256–1024) will cap you well before your application's theoretical capacity. In production:

```bash
# /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535

# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
```

Plan for **10K–50K connections per Spring application instance**, then scale horizontally. Well-tuned event-driven servers can reach hundreds of thousands per node, but JVM-based applications have higher per-connection overhead.

### Load balancing that actually works

WebSocket connections are inherently sticky — once established, the TCP connection pins a client to a specific server. The load balancing challenge is the **initial HTTP upgrade** and **SockJS fallback transports**.

**AWS ALB** detects the `Upgrade: websocket` header automatically and handles the upgrade without special configuration. The critical setting is **idle timeout** (default 60 seconds, configurable up to 4,000 seconds). Your application-level heartbeats must fire at an interval shorter than this timeout. Enable deregistration delay (connection draining) on the target group for graceful deployments.

**Nginx** requires specific configuration because it strips hop-by-hop headers by default:

```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400s;
}
```

The `proxy_http_version 1.1` directive is required — HTTP/1.0 does not support Upgrade. Increase `proxy_read_timeout` from the default 60 seconds or your long-lived connections will be terminated.

**The better architecture:** Externalize state entirely (Redis for session data, RabbitMQ for message brokering) so that any server can handle any client on reconnection. This eliminates the need for sticky sessions and enables true horizontal scaling.

### Monitoring what matters

Track these core metrics with Micrometer and Prometheus:

```kotlin
@Component
class WebSocketMetrics(private val registry: MeterRegistry) {
    private val activeConnections = registry.gauge(
        "websocket.connections.active", AtomicInteger(0)
    )!!
    private val messagesReceived = registry.counter("websocket.messages.received")
    private val connectionDuration = registry.timer("websocket.connection.duration")

    fun onConnect() = activeConnections.incrementAndGet()
    fun onDisconnect() = activeConnections.decrementAndGet()
    fun onMessage() = messagesReceived.increment()
    fun recordDuration(duration: Duration) = connectionDuration.record(duration)
}
```

Spring declares a `WebSocketMessageBrokerStats` bean automatically that logs connection statistics every 30 minutes at INFO level and is exportable via JMX. For distributed tracing, WebSocket's long-lived nature doesn't fit traditional request-scoped traces — create a new trace span per logical message exchange and propagate context in STOMP headers.

### Hardening security for production

Beyond Origin checking and STOMP-level authorization (covered in Phase 2), production deployments need:

- **Rate limiting:** Per-user message rate limits using a leaky bucket algorithm to prevent message flooding
- **Message size limits:** Configure `setMessageSizeLimit()` on `WebSocketTransportRegistration` (Tomcat's default is only 8 KB)
- **Connection limits:** Per-IP connection caps to prevent connection flooding DoS
- **Input validation:** Treat every WebSocket message as untrusted — validate against schema, sanitize for XSS, check for injection. Spring CVE-2018-1270 allowed RCE through crafted STOMP messages — keep dependencies updated

### Reconnection and graceful degradation

Client-side reconnection must use **exponential backoff with jitter** to avoid thundering herd on server restart. Base delay of 500ms, doubling each attempt, capped at 30 seconds, with random jitter of 0–1 second. Queue messages during disconnection and flush on reconnect. Re-subscribe to all channels after reconnection.

Server-side, configure Spring Boot's graceful shutdown:

```properties
server.shutdown=graceful
spring.lifecycle.timeout-per-shutdown-phase=30s
```

This stops accepting new connections while giving existing WebSocket sessions time to receive close frames and drain. Combine with ALB deregistration delay for zero-downtime deployments.

### STOMP heartbeat configuration

Heartbeats are your lifeline behind load balancers. Configure both server and client intervals:

```kotlin
registry.enableSimpleBroker("/topic", "/queue")
    .setHeartbeatValue(longArrayOf(10000, 10000)) // [server-sends-every, server-expects-every] ms
    .setTaskScheduler(heartbeatScheduler())
```

Set the heartbeat interval to less than your load balancer's idle timeout. For AWS ALB with a 60-second timeout, 10-second heartbeats provide comfortable margin.

### Phase 3 milestone

Deploy the Phase 2 chat application with: RabbitMQ STOMP broker relay for multi-instance scaling, Nginx reverse proxy with WebSocket support, Prometheus/Grafana dashboards tracking active connections and message rates, load testing with k6 or Artillery to find your per-instance connection limit, and zero-downtime deployment using graceful shutdown plus ALB connection draining.

---

## Recommended learning path and resources

### Essential reading

Start with the **Spring Framework WebSocket Reference** (https://docs.spring.io/spring-framework/reference/web/websocket.html) — it's comprehensive and well-structured. For protocol depth, read *High Performance Browser Networking* by Ilya Grigorik (free at hpbn.co), which has an excellent WebSocket chapter. The **OWASP WebSocket Security Cheat Sheet** is required reading before any production deployment.

### Practical tutorials

Baeldung's "Intro to WebSockets with Spring" and "Spring Security + WebSockets" guides provide solid starting points. The Spring Getting Started guide at https://spring.io/guides/gs/messaging-stomp-websocket/ walks through a complete STOMP example. For testing patterns, rieckpil's integration testing guide covers `WebSocketStompClient` usage in detail.

### Progressive project roadmap

Build these in order, each adding complexity to the previous:

1. **Raw echo server** — Learn `WebSocketHandler`, `ConcurrentWebSocketSessionDecorator`, connection lifecycle
2. **STOMP chat room** — `@MessageMapping`, `@SendTo`, simple broker, topic subscriptions
3. **Authenticated private chat** — JWT auth, `@SendToUser`, user destinations, Spring Security integration
4. **Real-time dashboard** — Server-push metrics, client reconnection with exponential backoff, heartbeats
5. **Multi-instance deployment** — RabbitMQ STOMP relay, `MultiServerUserRegistry`, Nginx proxy, external session store
6. **Production-grade system** — ALB + auto-scaling, Prometheus metrics, Grafana dashboards, k6 load testing, graceful shutdown

### GitHub repositories to study

Search GitHub topics `spring-websocket` and `spring-boot-websocket` for examples. The `kotlin-hands-on/kotlin-spring-chat` repository demonstrates Kotlin + Spring WebFlux with tests. For production patterns, study how the Spring Framework's own test suite exercises WebSocket endpoints.

---

## Conclusion

The path to WebSocket mastery isn't about memorizing Spring annotations — it's about deeply understanding the protocol, its alternatives, and the operational costs of persistent connections. The single most impactful insight in this entire curriculum is the **SSE vs. WebSocket decision**: most developers reach for WebSocket by default when SSE would be simpler, more scalable, and more operationally friendly for their unidirectional use case. True mastery means choosing WebSocket only when bidirectional communication genuinely justifies the complexity of sticky sessions, external message brokers, heartbeat management, and connection-aware load balancing. When you can articulate exactly why your feature requires WebSocket over SSE, design a multi-instance deployment with RabbitMQ relay, and confidently set up monitoring and graceful degradation — that's mastery.